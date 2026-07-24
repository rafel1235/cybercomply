"""Test di DELETE /gdpr/account (GDPR Art. 17 — diritto alla cancellazione, Fase 8):
copre i tre esiti possibili per ogni organizzazione di cui l'utente è membro (cancellata
per intero, iscrizione rimossa, operazione rifiutata), oltre alla registrazione degli
eventi di audit e al comportamento "best effort" verso Supabase Auth (mai configurato in
questi test, quindi sempre non riuscito senza bloccare il resto)."""

from app.models.audit_log import AuditLog
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User
from tests.conftest import make_token


def _sync(client, email, org_name=None):
    token = make_token(email=email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name} if org_name else {},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, resp.json()["organizations"][0]["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _add_membership(db_session, user_email, organization_id, role):
    user = db_session.query(User).filter(User.email == user_email).first()
    db_session.add(
        OrganizationMember(user_id=user.id, organization_id=organization_id, role=role)
    )
    db_session.commit()
    return user


def test_delete_account_sole_member_deletes_organization(client, db_session):
    token, org_id = _sync(client, "gdpr-del-sole@cybercomplyit.it", "Org Del Sole Srl")

    resp = client.delete("/api/v1/gdpr/account", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["organizations_deleted"] == ["Org Del Sole Srl"]
    assert body["organizations_left"] == []
    assert body["auth_account_deleted"] is False  # Supabase Admin API non configurata

    assert db_session.get(Organization, org_id) is None
    assert (
        db_session.query(User)
        .filter(User.email == "gdpr-del-sole@cybercomplyit.it")
        .first()
        is None
    )


def test_delete_account_blocked_if_sole_admin_with_other_members(client, db_session):
    admin_token, org_id = _sync(
        client, "gdpr-del-admin1@cybercomplyit.it", "Org Del Blocked Srl"
    )
    # Un secondo utente entra come viewer nella stessa organizzazione (senza toccare la
    # propria organizzazione di default creata dal sync, irrilevante per questo test).
    _sync(client, "gdpr-del-viewer@cybercomplyit.it")
    _add_membership(
        db_session, "gdpr-del-viewer@cybercomplyit.it", org_id, OrganizationRole.viewer
    )

    resp = client.delete("/api/v1/gdpr/account", headers=_auth(admin_token))
    assert resp.status_code == 400
    assert "unico amministratore" in resp.json()["detail"]

    # Niente è stato cancellato: né l'organizzazione, né l'utente, né la sua iscrizione.
    assert db_session.get(Organization, org_id) is not None
    admin_user = (
        db_session.query(User)
        .filter(User.email == "gdpr-del-admin1@cybercomplyit.it")
        .first()
    )
    assert admin_user is not None
    assert (
        db_session.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == admin_user.id,
            OrganizationMember.organization_id == org_id,
        )
        .first()
        is not None
    )


def test_delete_account_removes_membership_when_other_admin_exists(client, db_session):
    admin1_token, org_id = _sync(
        client, "gdpr-del-admin-a@cybercomplyit.it", "Org Del TwoAdmins Srl"
    )
    _sync(client, "gdpr-del-admin-b@cybercomplyit.it")
    _add_membership(
        db_session, "gdpr-del-admin-b@cybercomplyit.it", org_id, OrganizationRole.admin
    )

    resp = client.delete("/api/v1/gdpr/account", headers=_auth(admin1_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["organizations_deleted"] == []
    assert body["organizations_left"] == ["Org Del TwoAdmins Srl"]

    # L'organizzazione sopravvive con l'altro admin, solo l'utente cancellato sparisce.
    org = db_session.get(Organization, org_id)
    assert org is not None
    remaining_members = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == org_id)
        .all()
    )
    assert len(remaining_members) == 1
    assert (
        db_session.query(User)
        .filter(User.email == "gdpr-del-admin-a@cybercomplyit.it")
        .first()
        is None
    )


def test_delete_account_removes_membership_for_viewer(client, db_session):
    _, org_id = _sync(client, "gdpr-del-owner@cybercomplyit.it", "Org Del Viewer Srl")
    viewer_token, _ = _sync(client, "gdpr-del-viewer2@cybercomplyit.it")
    _add_membership(
        db_session, "gdpr-del-viewer2@cybercomplyit.it", org_id, OrganizationRole.viewer
    )

    resp = client.delete("/api/v1/gdpr/account", headers=_auth(viewer_token))
    assert resp.status_code == 200
    body = resp.json()
    # Il viewer aveva due organizzazioni: la propria (creata dal sync, sola iscritta:
    # viene cancellata) e quella dell'owner (dove è solo viewer: viene solo rimosso).
    assert len(body["organizations_deleted"]) == 1
    assert "Org Del Viewer Srl" in body["organizations_left"]

    org = db_session.get(Organization, org_id)
    assert org is not None
    assert (
        db_session.query(User)
        .filter(User.email == "gdpr-del-viewer2@cybercomplyit.it")
        .first()
        is None
    )


def test_delete_account_records_audit_events(client, db_session):
    token, org_id = _sync(
        client, "gdpr-del-audit@cybercomplyit.it", "Org Del Audit Srl"
    )
    client.delete("/api/v1/gdpr/account", headers=_auth(token))

    org_deleted_events = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "organization.deleted")
        .all()
    )
    assert len(org_deleted_events) == 1
    assert org_deleted_events[0].organization_id is None  # SET NULL dopo la cascade
    assert org_deleted_events[0].details["name"] == "Org Del Audit Srl"

    account_deleted_events = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "gdpr.account_deleted")
        .all()
    )
    assert len(account_deleted_events) == 1
    assert (
        account_deleted_events[0].details["email"] == "gdpr-del-audit@cybercomplyit.it"
    )


def test_token_unusable_after_account_deletion(client):
    token, _ = _sync(client, "gdpr-del-reuse@cybercomplyit.it", "Org Del Reuse Srl")
    client.delete("/api/v1/gdpr/account", headers=_auth(token))

    resp = client.get("/api/v1/gdpr/export", headers=_auth(token))
    assert resp.status_code == 404
