from app.models.subscription import Plan, Subscription
from tests.conftest import make_token


def _sync(client, db_session, email, org_name):
    """Fase 6: il modulo fornitori (usato qui solo per generare eventi di audit di prova)
    richiede il piano Business: l'organizzazione viene portata a Business subito dopo la
    sincronizzazione, così questi test restano concentrati sull'audit log e non
    sull'entitlement in sé (testato a parte in test_entitlements.py)."""
    token = make_token(email=email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = resp.json()["organizations"][0]["id"]

    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()

    return token, org_id


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_audit_log_lists_recent_actions_most_recent_first(client, db_session):
    token, _ = _sync(
        client, db_session, "audit-list@cybercomplyit.it", "Org Audit List Srl"
    )
    client.post(
        "/api/v1/suppliers", json={"name": "Fornitore Uno"}, headers=_auth(token)
    )
    client.post(
        "/api/v1/suppliers", json={"name": "Fornitore Due"}, headers=_auth(token)
    )

    resp = client.get("/api/v1/audit-log", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 2
    actions = [e["action"] for e in body]
    assert "supplier.created" in actions
    # dal più recente al meno recente
    timestamps = [e["created_at"] for e in body]
    assert timestamps == sorted(timestamps, reverse=True)


def test_audit_log_respects_limit(client, db_session):
    token, _ = _sync(
        client, db_session, "audit-limit@cybercomplyit.it", "Org Audit Limit Srl"
    )
    for i in range(5):
        client.post(
            "/api/v1/suppliers", json={"name": f"Fornitore {i}"}, headers=_auth(token)
        )

    resp = client.get("/api/v1/audit-log", params={"limit": 2}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_audit_log_scoped_to_organization(client, db_session):
    token_a, _ = _sync(
        client, db_session, "audit-org-a@cybercomplyit.it", "Org Audit A Srl"
    )
    token_b, _ = _sync(
        client, db_session, "audit-org-b@cybercomplyit.it", "Org Audit B Srl"
    )
    client.post(
        "/api/v1/suppliers", json={"name": "Fornitore Org A"}, headers=_auth(token_a)
    )

    resp_b = client.get("/api/v1/audit-log", headers=_auth(token_b))
    assert resp_b.status_code == 200
    assert all("Fornitore Org A" not in str(e["details"]) for e in resp_b.json())
