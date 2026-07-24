"""Integrazione Stripe (Fase 6 — Pagamenti e piani, roadmap tecnica).

Segue lo stesso principio già adottato per l'AI in Fase 5: se Stripe non è configurato
(`STRIPE_SECRET_KEY` assente o placeholder), le funzioni sollevano `BillingError` con un
messaggio chiaro invece di andare in errore non gestito — a differenza della generazione
documenti, qui non esiste un fallback sensato (non si può creare un vero pagamento senza
Stripe), quindi il chiamante (routes/billing.py) traduce l'errore in una risposta HTTP
comprensibile invece di un 500.
"""

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.services.audit import record_audit_event

logger = logging.getLogger(__name__)


class BillingError(Exception):
    """Errore di configurazione o di chiamata a Stripe, sempre gestito lato route (mai
    un 500 generico)."""


def is_billing_configured() -> bool:
    return get_settings().stripe_configured


def _client() -> "stripe":
    settings = get_settings()
    if not settings.stripe_configured:
        raise BillingError(
            "Stripe non è ancora configurato (STRIPE_SECRET_KEY mancante). "
            "I pagamenti non sono disponibili finché non viene impostata una chiave reale."
        )
    stripe.api_key = settings.stripe_secret_key
    return stripe


def price_id_for_plan(plan: Plan) -> str:
    settings = get_settings()
    mapping = {
        Plan.essential: settings.stripe_price_id_essential,
        Plan.business: settings.stripe_price_id_business,
    }
    price_id = mapping.get(plan)
    if not price_id:
        raise BillingError(
            f"Nessun prezzo Stripe configurato per il piano '{plan.value}'. Il piano "
            "Enterprise richiede un contratto personalizzato (contattaci), non è "
            "acquistabile in autonomia."
        )
    return price_id


def plan_for_price_id(price_id: str) -> Plan | None:
    settings = get_settings()
    if price_id and price_id == settings.stripe_price_id_essential:
        return Plan.essential
    if price_id and price_id == settings.stripe_price_id_business:
        return Plan.business
    return None


def ensure_stripe_customer(
    db: Session, subscription: Subscription, *, email: str, organization_name: str
) -> str:
    """Crea il Customer Stripe alla prima necessità (primo checkout o primo accesso al
    portale clienti) e lo salva sulla Subscription, così le chiamate successive lo
    riusano invece di crearne uno nuovo ogni volta."""
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    client = _client()
    customer = client.Customer.create(
        email=email,
        name=organization_name,
        metadata={"organization_id": str(subscription.organization_id)},
    )
    subscription.stripe_customer_id = customer["id"]
    db.add(subscription)
    db.commit()
    return subscription.stripe_customer_id


def create_checkout_session(
    *, customer_id: str, plan: Plan, organization_id, success_url: str, cancel_url: str
) -> str:
    client = _client()
    price_id = price_id_for_plan(plan)
    session = client.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"organization_id": str(organization_id), "plan": plan.value},
        subscription_data={
            "metadata": {"organization_id": str(organization_id), "plan": plan.value}
        },
    )
    return session["url"]


def create_portal_session(*, customer_id: str, return_url: str) -> str:
    client = _client()
    session = client.billing_portal.Session.create(
        customer=customer_id, return_url=return_url
    )
    return session["url"]


def construct_webhook_event(payload: bytes, sig_header: str):
    """Verifica la firma del webhook (protezione da richieste contraffatte): solleva
    `BillingError` se la firma non torna o il segreto non è configurato.

    A differenza delle altre funzioni di questo modulo, non passa da `_client()`: la
    verifica della firma è puramente locale (HMAC), non richiede `stripe.api_key` né
    contatta l'API di Stripe, quindi non deve dipendere da `STRIPE_SECRET_KEY`."""
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise BillingError("STRIPE_WEBHOOK_SECRET non configurato: webhook rifiutato")
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise BillingError(f"Firma webhook non valida: {exc}") from exc


def _find_by_customer(db: Session, customer_id: str | None) -> Subscription | None:
    if not customer_id:
        return None
    return (
        db.query(Subscription)
        .filter(Subscription.stripe_customer_id == customer_id)
        .first()
    )


def apply_webhook_event(db: Session, event: dict) -> None:
    """Applica un evento Stripe già verificato allo stato locale dell'abbonamento.

    Gestisce i 4 eventi richiesti dalla roadmap tecnica (Fase 6) più
    `customer.subscription.updated`, necessario per riconoscere un cambio di piano
    (upgrade/downgrade) fatto dal cliente stesso dal portale Stripe."""
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, data)
    elif event_type == "invoice.payment_succeeded":
        _handle_payment_succeeded(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)
    else:
        logger.info("Evento Stripe ignorato (non gestito): %s", event_type)


def _handle_checkout_completed(db: Session, session: dict) -> None:
    organization_id = (session.get("metadata") or {}).get("organization_id")
    plan_value = (session.get("metadata") or {}).get("plan")
    if not organization_id:
        logger.warning("checkout.session.completed senza organization_id nei metadata")
        return

    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .first()
    )
    if subscription is None:
        logger.warning(
            "checkout.session.completed per organizzazione sconosciuta: %s",
            organization_id,
        )
        return

    subscription.stripe_customer_id = (
        session.get("customer") or subscription.stripe_customer_id
    )
    subscription.stripe_subscription_id = session.get("subscription")
    if plan_value in Plan._value2member_map_:
        subscription.plan = Plan(plan_value)
    subscription.status = SubscriptionStatus.active
    db.add(subscription)
    db.commit()

    record_audit_event(
        db,
        action="subscription.activated",
        organization_id=organization_id,
        entity="subscription",
        details={"plan": subscription.plan.value},
    )


def _handle_payment_succeeded(db: Session, invoice: dict) -> None:
    subscription = _find_by_customer(db, invoice.get("customer"))
    if subscription is None:
        return
    subscription.status = SubscriptionStatus.active
    period_end = invoice.get("period_end") or invoice.get("lines", {}).get(
        "data", [{}]
    )[0].get("period", {}).get("end")
    if period_end:
        subscription.renews_at = datetime.fromtimestamp(period_end, tz=timezone.utc)
    db.add(subscription)
    db.commit()

    record_audit_event(
        db,
        action="subscription.renewed",
        organization_id=subscription.organization_id,
        entity="subscription",
        details={"plan": subscription.plan.value},
    )


def _handle_payment_failed(db: Session, invoice: dict) -> None:
    subscription = _find_by_customer(db, invoice.get("customer"))
    if subscription is None:
        return
    subscription.status = SubscriptionStatus.past_due
    db.add(subscription)
    db.commit()

    record_audit_event(
        db,
        action="subscription.payment_failed",
        organization_id=subscription.organization_id,
        entity="subscription",
        details={"plan": subscription.plan.value},
    )


def _handle_subscription_deleted(db: Session, stripe_subscription: dict) -> None:
    subscription = _find_by_customer(db, stripe_subscription.get("customer"))
    if subscription is None:
        return
    # Non si cancellano mai i dati: si degrada a Free, come da roadmap ("Non cancellare i
    # dati a scadenza — downgrade a Free con dati in sola lettura").
    subscription.plan = Plan.free
    subscription.status = SubscriptionStatus.canceled
    db.add(subscription)
    db.commit()

    record_audit_event(
        db,
        action="subscription.canceled",
        organization_id=subscription.organization_id,
        entity="subscription",
    )


def _handle_subscription_updated(db: Session, stripe_subscription: dict) -> None:
    subscription = _find_by_customer(db, stripe_subscription.get("customer"))
    if subscription is None:
        return

    items = stripe_subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        new_plan = plan_for_price_id(price_id)
        if new_plan is not None:
            subscription.plan = new_plan

    stripe_status = stripe_subscription.get("status")
    status_map = {
        "active": SubscriptionStatus.active,
        "trialing": SubscriptionStatus.trialing,
        "past_due": SubscriptionStatus.past_due,
        "canceled": SubscriptionStatus.canceled,
        "unpaid": SubscriptionStatus.past_due,
    }
    if stripe_status in status_map:
        subscription.status = status_map[stripe_status]

    db.add(subscription)
    db.commit()

    record_audit_event(
        db,
        action="subscription.updated",
        organization_id=subscription.organization_id,
        entity="subscription",
        details={"plan": subscription.plan.value, "status": subscription.status.value},
    )
