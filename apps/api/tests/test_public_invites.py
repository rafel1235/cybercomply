"""Test dell'anteprima pubblica di un invito (Fase 7), usata dalla pagina di
registrazione prima di creare l'account: nessuna autenticazione, il possesso del token è
di per sé la credenziale."""

from datetime import datetime, timedelta, timezone

from app.models.organization import OrganizationInvite
from app.models.subscription import Plan, Subscription
from tests.conftest import make_token


def _create_invite(
    client, db_session, admin_email: str, org_name: str, invited_email: str
) -> str:
    admin_token = make_token(email=admin_email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    org_id = resp.json()["organizations"][0]["id"]
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()

    invite_resp = client.post(
        "/api/v1/organization/invites",
        json={"email": invited_email, "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return invite_resp.json()["invite_token"]


def test_public_invite_unknown_token_is_404(client):
    resp = client.get("/api/v1/public/invites/token-inesistente")
    assert resp.status_code == 404


def test_public_invite_valid_shows_organization_and_role(client, db_session):
    token = _create_invite(
        client,
        db_session,
        "admin-pub-ok@cybercomplyit.it",
        "Org Pubblica OK Srl",
        "invitato@cybercomplyit.it",
    )
    resp = client.get(f"/api/v1/public/invites/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["organization_name"] == "Org Pubblica OK Srl"
    assert body["invited_email"] == "invitato@cybercomplyit.it"
    assert body["role"] == "viewer"
    assert body["valid"] is True
    assert body["reason"] is None


def test_public_invite_expired_is_invalid_with_reason(client, db_session):
    token = _create_invite(
        client,
        db_session,
        "admin-pub-exp@cybercomplyit.it",
        "Org Pubblica Scaduta Srl",
        "invitato2@cybercomplyit.it",
    )
    invite = (
        db_session.query(OrganizationInvite)
        .filter(OrganizationInvite.token == token)
        .first()
    )
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    resp = client.get(f"/api/v1/public/invites/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "scaduto" in body["reason"]


def test_public_invite_already_accepted_is_invalid_with_reason(client, db_session):
    token = _create_invite(
        client,
        db_session,
        "admin-pub-used@cybercomplyit.it",
        "Org Pubblica Usata Srl",
        "invitato3@cybercomplyit.it",
    )
    invite = (
        db_session.query(OrganizationInvite)
        .filter(OrganizationInvite.token == token)
        .first()
    )
    invite.accepted_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.get(f"/api/v1/public/invites/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "accettato" in body["reason"]
