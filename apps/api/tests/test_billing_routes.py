"""Test degli endpoint /billing (Fase 6): sempre con Stripe mockato, mai una vera
chiamata di rete o un vero addebito."""

import stripe

from app.core.config import get_settings
from app.models.subscription import Plan, Subscription
from tests.conftest import make_token


def _sync(client, email, org_name):
    token = make_token(email=email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, resp.json()["organizations"][0]["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_get_subscription_reflects_trial_on_essential(client):
    token, _ = _sync(client, "bill-sub@cybercomplyit.it", "Org Billing Sub Srl")
    resp = client.get("/api/v1/billing/subscription", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "essential"
    assert body["status"] == "trialing"
    assert body["trial_ends_at"] is not None
    assert body["entitlements"]["incident_reporting_enabled"] is True
    assert body["entitlements"]["supply_chain_enabled"] is False
    assert body["usage"]["users_count"] == 1


def test_checkout_fails_gracefully_when_stripe_not_configured(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "stripe_secret_key", "replace-with-real-key-when-fase-6-inizia"
    )

    token, _ = _sync(
        client, "bill-nostripe@cybercomplyit.it", "Org Billing NoStripe Srl"
    )
    resp = client.post(
        "/api/v1/billing/checkout", json={"plan": "business"}, headers=_auth(token)
    )
    assert resp.status_code == 400
    assert "Stripe" in resp.json()["detail"]


def test_checkout_returns_url_when_stripe_configured(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_price_id_business", "price_business_fake")
    monkeypatch.setattr(
        stripe.Customer, "create", lambda **k: {"id": "cus_checkout_test"}
    )
    monkeypatch.setattr(
        stripe.checkout.Session,
        "create",
        lambda **k: {"url": "https://checkout.stripe.com/xyz"},
    )

    token, _ = _sync(
        client, "bill-checkout@cybercomplyit.it", "Org Billing Checkout Srl"
    )
    resp = client.post(
        "/api/v1/billing/checkout", json={"plan": "business"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/xyz"


def test_checkout_rejects_free_and_enterprise(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    token, _ = _sync(
        client, "bill-checkout-invalid@cybercomplyit.it", "Org Billing Invalid Srl"
    )

    for plan in ("free", "enterprise"):
        resp = client.post(
            "/api/v1/billing/checkout", json={"plan": plan}, headers=_auth(token)
        )
        assert resp.status_code == 400


def test_checkout_requires_admin(client, db_session):
    from app.models.organization import OrganizationMember, OrganizationRole
    from app.models.user import User

    admin_token, org_id = _sync(
        client, "bill-viewer-admin@cybercomplyit.it", "Org Billing Viewer Srl"
    )
    viewer_token = make_token(email="bill-viewer@cybercomplyit.it")
    client.post("/api/v1/auth/sync", json={}, headers=_auth(viewer_token))
    viewer = (
        db_session.query(User)
        .filter(User.email == "bill-viewer@cybercomplyit.it")
        .first()
    )
    db_session.query(OrganizationMember).filter(
        OrganizationMember.user_id == viewer.id
    ).delete()
    db_session.add(
        OrganizationMember(
            user_id=viewer.id, organization_id=org_id, role=OrganizationRole.viewer
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/v1/billing/checkout",
        json={"plan": "business"},
        headers=_auth(viewer_token),
    )
    assert resp.status_code == 403


def test_portal_requires_existing_customer(client):
    token, _ = _sync(
        client, "bill-portal-none@cybercomplyit.it", "Org Billing Portal None Srl"
    )
    resp = client.post("/api/v1/billing/portal", headers=_auth(token))
    assert resp.status_code == 400


def test_portal_returns_url_when_customer_exists(client, db_session, monkeypatch):
    token, org_id = _sync(
        client, "bill-portal-ok@cybercomplyit.it", "Org Billing Portal Ok Srl"
    )
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.stripe_customer_id = "cus_portal_test"
    db_session.commit()

    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(
        stripe.billing_portal.Session,
        "create",
        lambda **k: {"url": "https://billing.stripe.com/xyz"},
    )

    resp = client.post("/api/v1/billing/portal", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["portal_url"] == "https://billing.stripe.com/xyz"


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")

    def _raise(*a, **k):
        raise stripe.error.SignatureVerificationError("bad", "sig")

    monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)

    resp = client.post(
        "/api/v1/billing/webhook",
        data=b"{}",
        headers={"stripe-signature": "invalid"},
    )
    assert resp.status_code == 400


def test_webhook_applies_valid_event(client, db_session, monkeypatch):
    token, org_id = _sync(
        client, "bill-webhook@cybercomplyit.it", "Org Billing Webhook Srl"
    )

    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_webhook_test",
                "subscription": "sub_webhook_test",
                "metadata": {"organization_id": org_id, "plan": "business"},
            }
        },
    }
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **k: fake_event)

    resp = client.post(
        "/api/v1/billing/webhook",
        data=b"{}",
        headers={"stripe-signature": "whatever"},
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True

    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    assert subscription.plan == Plan.business
    assert subscription.stripe_customer_id == "cus_webhook_test"
