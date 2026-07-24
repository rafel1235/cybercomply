from datetime import datetime, timedelta, timezone

from app.models.organization import OrganizationInvite
from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.services import email_service
from tests.conftest import make_token


def test_sync_creates_user_and_organization(client):
    token = make_token(email="founder@cybercomplyit.it")
    response = client.post(
        "/api/v1/auth/sync",
        json={"full_name": "Mario Rossi", "organization_name": "Rossi SRL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "founder@cybercomplyit.it"
    assert len(body["organizations"]) == 1
    assert body["organizations"][0]["name"] == "Rossi SRL"


def test_sync_sends_welcome_email_on_first_registration(client, monkeypatch):
    captured = {}

    def _fake_send_email(*, to, subject, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["html"] = html
        return True

    monkeypatch.setattr(email_service, "send_email", _fake_send_email)

    token = make_token(email="welcome@cybercomplyit.it")
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Welcome Srl"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert captured["to"] == "welcome@cybercomplyit.it"
    assert "Welcome Srl" in captured["subject"] or "Welcome Srl" in captured["html"]


def test_sync_does_not_resend_welcome_email_on_subsequent_sync(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        email_service, "send_email", lambda **k: calls.append(k) or True
    )

    token = make_token(email="welcome-twice@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Welcome Twice Srl"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/api/v1/auth/sync",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(calls) == 1


def test_sync_is_idempotent_and_does_not_duplicate_org(client):
    token = make_token(email="same-user@cybercomplyit.it")
    first = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Prima Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    second = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Non deve crearsi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["organizations"]) == 1
    assert second.json()["organizations"][0]["name"] == "Prima Org"


def test_me_requires_prior_sync(client):
    token = make_token(email="never-synced@cybercomplyit.it")
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_me_returns_data_after_sync(client):
    token = make_token(email="synced@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Synced Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "synced@cybercomplyit.it"


def test_missing_token_is_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_login_event_locks_account_after_repeated_failures(client):
    token = make_token(email="target@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Target Org"},
        headers={"Authorization": f"Bearer {token}"},
    )

    last_response = None
    for _ in range(5):
        last_response = client.post(
            "/api/v1/auth/login-events",
            json={"email": "target@cybercomplyit.it", "success": False},
        )

    assert last_response.status_code == 200

    locked_response = client.post(
        "/api/v1/auth/login-events",
        json={"email": "target@cybercomplyit.it", "success": False},
    )
    assert locked_response.status_code == 423


def test_locked_account_cannot_use_a_valid_jwt(client, db_session):
    """Bug reale corretto in Fase 10 (audit finale): prima di questa correzione, il
    blocco account era applicato solo da POST /auth/login-events, che gira DOPO che il
    frontend ha già autenticato l'utente direttamente contro Supabase — un account
    "bloccato" poteva quindi continuare a usare un JWT valido su qualunque altro
    endpoint. Verifica che ora un utente con `locked_until` nel futuro venga rifiutato
    (423) anche con un JWT perfettamente valido, non solo sull'endpoint di tracciamento.

    Imposta `locked_until` direttamente sul DB (invece di ripetere 5 chiamate reali a
    /auth/login-events, già coperte dal test sopra) per non consumare inutilmente il
    budget del rate limiter IP-based condiviso con altri test in questo stesso file."""
    token = make_token(email="locked-user@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Locked Org"},
        headers={"Authorization": f"Bearer {token}"},
    )

    user = (
        db_session.query(User)
        .filter(User.email == "locked-user@cybercomplyit.it")
        .first()
    )
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    db_session.commit()

    # Stesso identico token JWT valido di prima: l'account risulta bloccato lato nostro
    # DB, quindi anche un endpoint qualunque (non solo login-events) deve rifiutarlo.
    response = client.get(
        "/api/v1/organization", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 423

    # Passato lo sblocco, lo stesso token torna valido.
    user.locked_until = None
    db_session.commit()
    response_after_unlock = client.get(
        "/api/v1/organization", headers={"Authorization": f"Bearer {token}"}
    )
    assert response_after_unlock.status_code == 200


def _create_invite(
    client, db_session, admin_email: str, org_name: str, invited_email: str
) -> tuple[str, str]:
    """Crea un'organizzazione admin (portata a Business per non sbattere sul limite
    posti di Essential), invita `invited_email` come viewer, e ritorna (org_id, token).
    """
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
    assert invite_resp.status_code == 200
    return org_id, invite_resp.json()["invite_token"]


def test_sync_redeems_valid_invite_and_joins_existing_org(client, db_session):
    org_id, token = _create_invite(
        client,
        db_session,
        "admin-invite-ok@cybercomplyit.it",
        "Org Invito OK Srl",
        "collega@cybercomplyit.it",
    )

    invited_token = make_token(email="collega@cybercomplyit.it")
    resp = client.post(
        "/api/v1/auth/sync",
        json={"invite_token": token},
        headers={"Authorization": f"Bearer {invited_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["organizations"]) == 1
    assert body["organizations"][0]["id"] == org_id

    invite = (
        db_session.query(OrganizationInvite)
        .filter(OrganizationInvite.token == token)
        .first()
    )
    assert invite.accepted_at is not None


def test_sync_ignores_invite_with_wrong_email(client, db_session):
    _org_id, token = _create_invite(
        client,
        db_session,
        "admin-invite-wrong@cybercomplyit.it",
        "Org Invito Wrong Srl",
        "collega2@cybercomplyit.it",
    )

    stranger_token = make_token(email="estraneo@cybercomplyit.it")
    resp = client.post(
        "/api/v1/auth/sync",
        json={"invite_token": token, "organization_name": "La Mia Org Separata"},
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["organizations"][0]["name"] == "La Mia Org Separata"


def test_sync_ignores_expired_invite(client, db_session):
    org_id, token = _create_invite(
        client,
        db_session,
        "admin-invite-exp@cybercomplyit.it",
        "Org Invito Scaduto Srl",
        "collega3@cybercomplyit.it",
    )
    invite = (
        db_session.query(OrganizationInvite)
        .filter(OrganizationInvite.token == token)
        .first()
    )
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    invited_token = make_token(email="collega3@cybercomplyit.it")
    resp = client.post(
        "/api/v1/auth/sync",
        json={"invite_token": token},
        headers={"Authorization": f"Bearer {invited_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["organizations"][0]["id"] != org_id


def test_sync_ignores_already_accepted_invite(client, db_session):
    org_id, token = _create_invite(
        client,
        db_session,
        "admin-invite-used@cybercomplyit.it",
        "Org Invito Usato Srl",
        "collega4@cybercomplyit.it",
    )
    invite = (
        db_session.query(OrganizationInvite)
        .filter(OrganizationInvite.token == token)
        .first()
    )
    invite.accepted_at = datetime.now(timezone.utc)
    db_session.commit()

    invited_token = make_token(email="collega4@cybercomplyit.it")
    resp = client.post(
        "/api/v1/auth/sync",
        json={"invite_token": token},
        headers={"Authorization": f"Bearer {invited_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["organizations"][0]["id"] != org_id
