from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_supabase_user, get_current_user, get_db
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import SupabaseUser
from app.models.organization import (
    Organization,
    OrganizationInvite,
    OrganizationMember,
    OrganizationRole,
)
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.models.user import User
from app.schemas.auth import MeResponse, OrganizationOut, SyncUserRequest, UserOut
from app.services import email_service
from app.services.audit import record_audit_event
from app.services.email_templates import welcome_email

TRIAL_DURATION_DAYS = 14

router = APIRouter(prefix="/auth", tags=["auth"])

LOCK_THRESHOLD = 5
LOCK_DURATION_MINUTES = 15


def _find_redeemable_invite(
    db: Session, invite_token: str | None, user_email: str
) -> OrganizationInvite | None:
    """Un token mancante, sconosciuto, scaduto, già accettato, o per un'email diversa da
    quella con cui l'utente si è appena registrato viene ignorato silenziosamente:
    l'utente riceve comunque una propria organizzazione, invece di bloccare la
    registrazione per un problema sull'invito (stesso principio di degradazione
    controllata usato per AI e Stripe)."""
    if not invite_token:
        return None

    invite = (
        db.query(OrganizationInvite)
        .filter(OrganizationInvite.token == invite_token)
        .first()
    )
    if invite is None:
        return None
    if invite.accepted_at is not None:
        return None
    if invite.expires_at <= datetime.now(timezone.utc):
        return None
    if invite.invited_email.lower() != user_email.lower():
        return None
    return invite


@router.post("/sync", response_model=MeResponse)
def sync_user(
    payload: SyncUserRequest,
    request: Request,
    supabase_user: SupabaseUser = Depends(get_current_supabase_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Chiamato dal frontend subito dopo login/registrazione riuscita su Supabase.

    Crea (o aggiorna) lo specchio locale dell'utente. Alla primissima sincronizzazione,
    se non esiste ancora nessuna organizzazione associata, ne crea una (richiesto per poter
    usare Assessment/Compliance Tracker/etc. che sono sempre legati a un'organizzazione).
    """
    if supabase_user.email is None:
        raise HTTPException(status_code=400, detail="Token senza email valida")

    user = db.get(User, supabase_user.id)
    is_new_user = user is None
    if user is None:
        user = User(
            id=supabase_user.id, email=supabase_user.email, full_name=payload.full_name
        )
        db.add(user)
    else:
        user.email = supabase_user.email
        if payload.full_name:
            user.full_name = payload.full_name
    db.commit()
    db.refresh(user)

    if is_new_user:
        invite = _find_redeemable_invite(db, payload.invite_token, user.email)

        if invite is not None:
            # Fase 7: chi si registra con un invito valido si unisce all'organizzazione
            # che lo ha invitato, con il ruolo deciso dall'admin, invece di ricevere una
            # propria organizzazione nuova (bug corretto in questa fase: prima l'invito
            # veniva creato ma non esisteva alcun modo di redimerlo davvero).
            organization = db.get(Organization, invite.organization_id)
            membership = OrganizationMember(
                user_id=user.id,
                organization_id=organization.id,
                role=invite.role,
                joined_at=datetime.now(timezone.utc),
            )
            db.add(membership)
            invite.accepted_at = datetime.now(timezone.utc)
            db.add(invite)
            db.commit()

            record_audit_event(
                db,
                action="user.joined_via_invite",
                user_id=user.id,
                organization_id=organization.id,
                entity="organization_member",
                details={"role": invite.role.value},
                ip_address=request.client.host if request.client else None,
            )
        else:
            org_name = payload.organization_name or f"Organizzazione di {user.email}"
            organization = Organization(name=org_name)
            db.add(organization)
            db.commit()
            db.refresh(organization)

            membership = OrganizationMember(
                user_id=user.id,
                organization_id=organization.id,
                role=OrganizationRole.admin,
                joined_at=datetime.now(timezone.utc),
            )
            db.add(membership)

            # Fase 6: ogni nuova organizzazione parte con un trial di 14 giorni sul piano
            # Essential, senza richiedere una carta di credito (NUOVI PIANI.pdf, §7.1).
            # Allo scadere del trial, l'entitlement service degrada automaticamente a
            # Free (lazy, nessun cron necessario) mantenendo i dati esistenti in sola
            # lettura.
            subscription = Subscription(
                organization_id=organization.id,
                plan=Plan.essential,
                status=SubscriptionStatus.trialing,
                trial_ends_at=datetime.now(timezone.utc)
                + timedelta(days=TRIAL_DURATION_DAYS),
            )
            db.add(subscription)
            db.commit()

            record_audit_event(
                db,
                action="user.registered",
                user_id=user.id,
                organization_id=organization.id,
                entity="user",
                ip_address=request.client.host if request.client else None,
            )

            # Fase 7: email di benvenuto. Come per l'invito, un problema di invio non
            # deve mai bloccare la registrazione (send_email non solleva eccezioni).
            settings = get_settings()
            subject, html = welcome_email(
                organization_name=organization.name,
                trial_days=TRIAL_DURATION_DAYS,
                dashboard_url=f"{settings.frontend_base_url}/dashboard",
            )
            email_service.send_email(to=user.email, subject=subject, html=html)
    else:
        record_audit_event(
            db,
            action="user.login",
            user_id=user.id,
            entity="user",
            ip_address=request.client.host if request.client else None,
        )

    return _build_me_response(db, user)


@router.get("/me", response_model=MeResponse)
def read_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    return _build_me_response(db, user)


def _build_me_response(db: Session, user: User) -> MeResponse:
    memberships = user.memberships
    org_ids = [m.organization_id for m in memberships]
    organizations = (
        db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        if org_ids
        else []
    )
    return MeResponse(
        user=UserOut.model_validate(user),
        organizations=[OrganizationOut.model_validate(o) for o in organizations],
    )


class LoginEvent(BaseModel):
    email: str
    success: bool


@router.post("/login-events")
@limiter.limit(get_settings().login_rate_limit)
def record_login_event(
    request: Request,
    payload: LoginEvent,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Registrato dal frontend dopo ogni tentativo di login su Supabase (riuscito o no).

    Applica rate limiting per IP (Fase 1) e blocco temporaneo dell'account dopo troppi
    tentativi falliti consecutivi.
    """
    ip = request.client.host if request.client else None
    user = db.query(User).filter(User.email == payload.email).first()

    if user is not None:
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporaneamente bloccato per troppi tentativi falliti. "
                f"Riprova dopo {user.locked_until.isoformat()}.",
            )

        if payload.success:
            user.failed_login_count = 0
            user.locked_until = None
        else:
            user.failed_login_count += 1
            if user.failed_login_count >= LOCK_THRESHOLD:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCK_DURATION_MINUTES
                )
        db.commit()

    record_audit_event(
        db,
        action="user.login_attempt",
        user_id=user.id if user else None,
        entity="user",
        details={"success": payload.success, "email": payload.email},
        ip_address=ip,
    )
    return {"status": "recorded"}
