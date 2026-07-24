from app.models.organization import OrganizationMember, OrganizationRole
from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.services import email_service
from tests.conftest import make_token


def _sync(client, email, org_name):
    token = make_token(email=email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, resp.json()["organizations"][0]["id"]


def test_get_organization_returns_current_org(client):
    token, org_id = _sync(client, "org-get@cybercomplyit.it", "Org Get Srl")
    resp = client.get(
        "/api/v1/organization", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == org_id
    assert resp.json()["name"] == "Org Get Srl"


def test_update_organization_as_admin(client):
    token, _ = _sync(client, "org-update@cybercomplyit.it", "Org Update Srl")
    resp = client.put(
        "/api/v1/organization",
        json={"sector": "Sanità", "employee_count": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["sector"] == "Sanità"
    assert resp.json()["employee_count"] == 120


def test_update_organization_forbidden_for_viewer(client, db_session):
    admin_token, org_id = _sync(
        client, "org-viewer-admin@cybercomplyit.it", "Org Viewer Srl"
    )

    viewer_token = make_token(email="org-viewer@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    viewer = (
        db_session.query(User)
        .filter(User.email == "org-viewer@cybercomplyit.it")
        .first()
    )
    # rimuove la propria organizzazione creata dal sync e la sostituisce con
    # un'iscrizione come viewer all'organizzazione dell'admin, per testare i permessi
    db_session.query(OrganizationMember).filter(
        OrganizationMember.user_id == viewer.id
    ).delete()
    db_session.add(
        OrganizationMember(
            user_id=viewer.id, organization_id=org_id, role=OrganizationRole.viewer
        )
    )
    db_session.commit()

    resp = client.put(
        "/api/v1/organization",
        json={"sector": "Non dovrebbe funzionare"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


def test_list_members_includes_admin(client):
    token, _ = _sync(client, "org-members@cybercomplyit.it", "Org Members Srl")
    resp = client.get(
        "/api/v1/organization/members", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    emails = [m["email"] for m in resp.json()]
    assert "org-members@cybercomplyit.it" in emails
    assert resp.json()[0]["role"] == "admin"


def test_cannot_remove_last_admin(client):
    token, _ = _sync(client, "org-lastadmin@cybercomplyit.it", "Org Last Admin Srl")
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["user"]["id"]

    resp = client.delete(
        f"/api/v1/organization/members/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_invite_creates_pending_invite(client, db_session):
    # Fase 6: il trial automatico è su Essential (max 1 utente): senza upgrade, l'invito
    # sarebbe bloccato dal limite di posti (vedi test_invite_blocked_at_seat_limit sotto).
    token, org_id = _sync(client, "org-invite@cybercomplyit.it", "Org Invite Srl")
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()

    resp = client.post(
        "/api/v1/organization/invites",
        json={"email": "collega@cybercomplyit.it", "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["invited_email"] == "collega@cybercomplyit.it"
    assert len(body["invite_token"]) > 20


def test_invite_sends_email_to_invited_address(client, db_session, monkeypatch):
    token, org_id = _sync(
        client, "org-invite-email@cybercomplyit.it", "Org Invite Email Srl"
    )
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()

    captured = {}

    def _fake_send_email(*, to, subject, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["html"] = html
        return True

    monkeypatch.setattr(email_service, "send_email", _fake_send_email)

    resp = client.post(
        "/api/v1/organization/invites",
        json={"email": "invitato-email@cybercomplyit.it", "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    invite_token = resp.json()["invite_token"]

    assert captured["to"] == "invitato-email@cybercomplyit.it"
    assert "Org Invite Email Srl" in captured["html"]
    assert invite_token in captured["html"]


def test_invite_blocked_at_seat_limit(client):
    """Il trial è su Essential (1 utente): l'organizzazione ha già il proprio admin, quindi
    un secondo invito deve essere rifiutato finché non si passa a un piano superiore."""
    token, _ = _sync(
        client, "org-invite-limit@cybercomplyit.it", "Org Invite Limit Srl"
    )
    resp = client.post(
        "/api/v1/organization/invites",
        json={"email": "altro@cybercomplyit.it", "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
