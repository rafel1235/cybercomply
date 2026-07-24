from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentMembership,
    get_current_membership,
    get_db,
    require_admin,
)
from app.core.config import get_settings
from app.models.document import Document
from app.models.organization import OrganizationMember
from app.models.subscription import Plan
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    EntitlementsOut,
    PortalResponse,
    SubscriptionOut,
    UsageOut,
)
from app.services import billing
from app.services.entitlements import (
    PLAN_ENTITLEMENTS,
    get_or_create_subscription,
    sync_trial_expiry,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    """Stato dell'abbonamento, i limiti del piano attivo, e l'utilizzo corrente — usato
    dal frontend sia per la pagina Impostazioni > Fatturazione sia per mostrare avvisi di
    upgrade quando un limite viene raggiunto."""
    subscription = get_or_create_subscription(db, membership.organization.id)
    subscription = sync_trial_expiry(db, subscription)
    entitlements = PLAN_ENTITLEMENTS[subscription.plan]

    # Stesso calcolo "mese solare corrente" di documents.py: duplicato qui volutamente per
    # evitare un import circolare tra routes; se la logica cresce ulteriormente andrà
    # estratta in entitlements.py.
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    documents_this_month = (
        db.query(Document)
        .filter(
            Document.organization_id == membership.organization.id,
            Document.created_at >= month_start,
        )
        .count()
    )
    users_count = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == membership.organization.id)
        .count()
    )

    return SubscriptionOut(
        plan=subscription.plan.value,
        status=subscription.status.value,
        trial_ends_at=subscription.trial_ends_at,
        renews_at=subscription.renews_at,
        entitlements=EntitlementsOut(
            max_users=entitlements.max_users,
            max_ai_documents_per_month=entitlements.max_ai_documents_per_month,
            compliance_measures_limit=entitlements.compliance_measures_limit,
            compliance_measures_editable=entitlements.compliance_measures_editable,
            incident_reporting_enabled=entitlements.incident_reporting_enabled,
            supply_chain_enabled=entitlements.supply_chain_enabled,
            quarterly_reports_enabled=entitlements.quarterly_reports_enabled,
            white_label_enabled=entitlements.white_label_enabled,
            api_access_enabled=entitlements.api_access_enabled,
        ),
        usage=UsageOut(
            documents_generated_this_month=documents_this_month, users_count=users_count
        ),
    )


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    """Crea una sessione di Stripe Checkout per passare a un piano a pagamento. Riservato
    agli admin dell'organizzazione (è un'azione con impatto economico)."""
    if payload.plan not in Plan._value2member_map_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Piano non valido"
        )
    plan = Plan(payload.plan)
    if plan in (Plan.free, Plan.enterprise):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il piano Free non richiede pagamento; il piano Enterprise richiede "
            "un contratto personalizzato (contattaci) e non è acquistabile qui.",
        )

    subscription = get_or_create_subscription(db, membership.organization.id)
    settings = get_settings()

    try:
        customer_id = billing.ensure_stripe_customer(
            db,
            subscription,
            email=membership.user.email,
            organization_name=membership.organization.name,
        )
        checkout_url = billing.create_checkout_session(
            customer_id=customer_id,
            plan=plan,
            organization_id=membership.organization.id,
            success_url=f"{settings.frontend_base_url}/settings/billing?checkout=success",
            cancel_url=f"{settings.frontend_base_url}/settings/billing?checkout=cancelled",
        )
    except billing.BillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PortalResponse:
    """Link al portale clienti Stripe (gestisci abbonamento, cambia carta, scarica
    fatture). Richiede che l'organizzazione abbia già un Customer Stripe, cioè abbia
    almeno iniziato una volta un checkout."""
    subscription = get_or_create_subscription(db, membership.organization.id)
    if not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessun abbonamento a pagamento attivo: effettua prima un upgrade.",
        )

    settings = get_settings()
    try:
        portal_url = billing.create_portal_session(
            customer_id=subscription.stripe_customer_id,
            return_url=f"{settings.frontend_base_url}/settings/billing",
        )
    except billing.BillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PortalResponse(portal_url=portal_url)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Riceve gli eventi da Stripe. Nessuna autenticazione utente (Stripe non ha un
    token dell'app): la sicurezza è interamente affidata alla verifica della firma
    (`Stripe-Signature`), che garantisce che il payload provenga davvero da Stripe e non
    sia stato alterato in transito."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = billing.construct_webhook_event(payload, sig_header)
    except billing.BillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    billing.apply_webhook_event(db, event)
    return {"received": True}
