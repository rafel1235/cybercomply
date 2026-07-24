"""Test del servizio di fatturazione (Fase 6). Stripe non viene mai chiamato davvero: le
funzioni della sua SDK vengono sostituite con doppi di test, sia per non dipendere da
credenziali reali sia per non generare veri addebiti durante i test automatici."""

import uuid

import pytest
import stripe

from app.core.config import get_settings
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.models.user import User
from app.services import billing, email_service


@pytest.fixture(autouse=True)
def _configure_stripe(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")
    monkeypatch.setattr(settings, "stripe_price_id_essential", "price_essential_fake")
    monkeypatch.setattr(settings, "stripe_price_id_business", "price_business_fake")
    yield


def _make_org_with_subscription(
    db_session, plan=Plan.essential, **kwargs
) -> Subscription:
    org = Organization(id=uuid.uuid4(), name="Org Billing Test Srl")
    db_session.add(org)
    db_session.commit()
    kwargs.setdefault("status", SubscriptionStatus.active)
    subscription = Subscription(organization_id=org.id, plan=plan, **kwargs)
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


def _add_admin(db_session, subscription: Subscription, email: str) -> None:
    user = User(id=uuid.uuid4(), email=email)
    db_session.add(user)
    db_session.commit()
    db_session.add(
        OrganizationMember(
            user_id=user.id,
            organization_id=subscription.organization_id,
            role=OrganizationRole.admin,
        )
    )
    db_session.commit()


def test_is_billing_configured_false_with_placeholder(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "stripe_secret_key", "replace-with-real-key-when-fase-6-inizia"
    )
    assert billing.is_billing_configured() is False


def test_is_billing_configured_true_with_real_looking_key():
    assert billing.is_billing_configured() is True


def test_price_id_for_plan_essential_and_business():
    assert billing.price_id_for_plan(Plan.essential) == "price_essential_fake"
    assert billing.price_id_for_plan(Plan.business) == "price_business_fake"


def test_price_id_for_plan_raises_for_enterprise():
    with pytest.raises(billing.BillingError):
        billing.price_id_for_plan(Plan.enterprise)


def test_plan_for_price_id_maps_back_correctly():
    assert billing.plan_for_price_id("price_essential_fake") == Plan.essential
    assert billing.plan_for_price_id("price_business_fake") == Plan.business
    assert billing.plan_for_price_id("price_sconosciuto") is None


def test_ensure_stripe_customer_reuses_existing_without_calling_stripe(
    db_session, monkeypatch
):
    subscription = _make_org_with_subscription(
        db_session, stripe_customer_id="cus_existing"
    )

    def _should_not_be_called(*a, **k):
        raise AssertionError("stripe.Customer.create non doveva essere chiamato")

    monkeypatch.setattr(stripe.Customer, "create", _should_not_be_called)

    customer_id = billing.ensure_stripe_customer(
        db_session, subscription, email="a@b.it", organization_name="Acme"
    )
    assert customer_id == "cus_existing"


def test_ensure_stripe_customer_creates_and_persists(db_session, monkeypatch):
    subscription = _make_org_with_subscription(db_session)
    assert subscription.stripe_customer_id is None

    monkeypatch.setattr(
        stripe.Customer, "create", lambda **kwargs: {"id": "cus_new_123", **kwargs}
    )

    customer_id = billing.ensure_stripe_customer(
        db_session, subscription, email="founder@acme.it", organization_name="Acme Srl"
    )
    assert customer_id == "cus_new_123"
    db_session.refresh(subscription)
    assert subscription.stripe_customer_id == "cus_new_123"


def test_create_checkout_session_returns_url(monkeypatch):
    captured = {}

    def _fake_create(**kwargs):
        captured.update(kwargs)
        return {"url": "https://checkout.stripe.com/session/xyz"}

    monkeypatch.setattr(stripe.checkout.Session, "create", _fake_create)

    org_id = uuid.uuid4()
    url = billing.create_checkout_session(
        customer_id="cus_1",
        plan=Plan.essential,
        organization_id=org_id,
        success_url="https://app/success",
        cancel_url="https://app/cancel",
    )
    assert url == "https://checkout.stripe.com/session/xyz"
    assert captured["customer"] == "cus_1"
    assert captured["mode"] == "subscription"
    assert captured["line_items"][0]["price"] == "price_essential_fake"
    assert captured["metadata"]["organization_id"] == str(org_id)
    assert captured["metadata"]["plan"] == "essential"


def test_create_portal_session_returns_url(monkeypatch):
    monkeypatch.setattr(
        stripe.billing_portal.Session,
        "create",
        lambda **k: {"url": "https://billing.stripe.com/session/abc"},
    )
    url = billing.create_portal_session(
        customer_id="cus_1", return_url="https://app/settings"
    )
    assert url == "https://billing.stripe.com/session/abc"


def test_construct_webhook_event_success(monkeypatch):
    monkeypatch.setattr(
        stripe.Webhook, "construct_event", lambda *a, **k: {"type": "test.event"}
    )
    event = billing.construct_webhook_event(b"payload", "sig")
    assert event["type"] == "test.event"


def test_construct_webhook_event_invalid_signature_raises(monkeypatch):
    def _raise(*a, **k):
        raise stripe.error.SignatureVerificationError("bad sig", "sig_header")

    monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)
    with pytest.raises(billing.BillingError):
        billing.construct_webhook_event(b"payload", "bad-sig")


def test_construct_webhook_event_without_secret_raises(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    with pytest.raises(billing.BillingError):
        billing.construct_webhook_event(b"payload", "sig")


def test_apply_checkout_completed_activates_plan(db_session):
    subscription = _make_org_with_subscription(db_session, plan=Plan.free)
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_abc",
                "subscription": "sub_abc",
                "metadata": {
                    "organization_id": str(subscription.organization_id),
                    "plan": "business",
                },
            }
        },
    }
    billing.apply_webhook_event(db_session, event)
    db_session.refresh(subscription)
    assert subscription.plan == Plan.business
    assert subscription.status == SubscriptionStatus.active
    assert subscription.stripe_customer_id == "cus_abc"
    assert subscription.stripe_subscription_id == "sub_abc"


def test_apply_payment_succeeded_marks_active(db_session):
    subscription = _make_org_with_subscription(
        db_session,
        plan=Plan.essential,
        stripe_customer_id="cus_pay_ok",
        status=SubscriptionStatus.past_due,
    )
    event = {
        "type": "invoice.payment_succeeded",
        "data": {"object": {"customer": "cus_pay_ok", "period_end": 1893456000}},
    }
    billing.apply_webhook_event(db_session, event)
    db_session.refresh(subscription)
    assert subscription.status == SubscriptionStatus.active
    assert subscription.renews_at is not None


def test_apply_payment_failed_marks_past_due(db_session):
    subscription = _make_org_with_subscription(
        db_session, stripe_customer_id="cus_pay_fail"
    )
    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_pay_fail"}},
    }
    billing.apply_webhook_event(db_session, event)
    db_session.refresh(subscription)
    assert subscription.status == SubscriptionStatus.past_due


def test_apply_subscription_deleted_downgrades_to_free(db_session):
    subscription = _make_org_with_subscription(
        db_session, plan=Plan.business, stripe_customer_id="cus_cancel"
    )
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_cancel"}},
    }
    billing.apply_webhook_event(db_session, event)
    db_session.refresh(subscription)
    assert subscription.plan == Plan.free
    assert subscription.status == SubscriptionStatus.canceled


def test_apply_subscription_updated_detects_plan_change(db_session):
    subscription = _make_org_with_subscription(
        db_session, plan=Plan.essential, stripe_customer_id="cus_upgrade"
    )
    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "customer": "cus_upgrade",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_business_fake"}}]},
            }
        },
    }
    billing.apply_webhook_event(db_session, event)
    db_session.refresh(subscription)
    assert subscription.plan == Plan.business


def test_apply_webhook_event_for_unknown_customer_is_noop(db_session):
    # Nessuna eccezione, nessun crash: un evento per un customer che non esiste
    # localmente viene semplicemente ignorato (loggato).
    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_non_esistente"}},
    }
    billing.apply_webhook_event(db_session, event)


def test_apply_unhandled_event_type_is_noop(db_session):
    event = {"type": "customer.created", "data": {"object": {}}}
    billing.apply_webhook_event(db_session, event)


def test_apply_payment_succeeded_emails_admin_with_invoice_link(
    db_session, monkeypatch
):
    subscription = _make_org_with_subscription(
        db_session, plan=Plan.essential, stripe_customer_id="cus_pay_email"
    )
    _add_admin(db_session, subscription, "admin-pay-ok@cybercomplyit.it")

    captured = {}
    monkeypatch.setattr(
        email_service, "send_email", lambda **k: captured.update(k) or True
    )

    event = {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "customer": "cus_pay_email",
                "period_end": 1893456000,
                "hosted_invoice_url": "https://stripe.example/invoice/1",
            }
        },
    }
    billing.apply_webhook_event(db_session, event)

    assert captured["to"] == "admin-pay-ok@cybercomplyit.it"
    assert "https://stripe.example/invoice/1" in captured["html"]


def test_apply_payment_failed_emails_admin(db_session, monkeypatch):
    subscription = _make_org_with_subscription(
        db_session, stripe_customer_id="cus_fail_email"
    )
    _add_admin(db_session, subscription, "admin-pay-fail@cybercomplyit.it")

    captured = {}
    monkeypatch.setattr(
        email_service, "send_email", lambda **k: captured.update(k) or True
    )

    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_fail_email"}},
    }
    billing.apply_webhook_event(db_session, event)

    assert captured["to"] == "admin-pay-fail@cybercomplyit.it"


def test_apply_subscription_deleted_emails_admin(db_session, monkeypatch):
    subscription = _make_org_with_subscription(
        db_session, plan=Plan.business, stripe_customer_id="cus_cancel_email"
    )
    _add_admin(db_session, subscription, "admin-cancel@cybercomplyit.it")

    captured = {}
    monkeypatch.setattr(
        email_service, "send_email", lambda **k: captured.update(k) or True
    )

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_cancel_email"}},
    }
    billing.apply_webhook_event(db_session, event)

    assert captured["to"] == "admin-cancel@cybercomplyit.it"


def test_apply_payment_failed_does_not_email_when_no_admin_found(
    db_session, monkeypatch
):
    """Nessun crash se l'organizzazione non ha (ancora) un membro admin registrato
    localmente: send_email semplicemente non viene chiamato."""
    _make_org_with_subscription(db_session, stripe_customer_id="cus_no_admin")

    def _should_not_be_called(**_k):
        raise AssertionError("send_email non doveva essere chiamato senza admin")

    monkeypatch.setattr(email_service, "send_email", _should_not_be_called)

    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_no_admin"}},
    }
    billing.apply_webhook_event(db_session, event)
