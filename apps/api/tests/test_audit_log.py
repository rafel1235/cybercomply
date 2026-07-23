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


def test_audit_log_lists_recent_actions_most_recent_first(client):
    token, _ = _sync(client, "audit-list@cybercomplyit.it", "Org Audit List Srl")
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


def test_audit_log_respects_limit(client):
    token, _ = _sync(client, "audit-limit@cybercomplyit.it", "Org Audit Limit Srl")
    for i in range(5):
        client.post(
            "/api/v1/suppliers", json={"name": f"Fornitore {i}"}, headers=_auth(token)
        )

    resp = client.get("/api/v1/audit-log", params={"limit": 2}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_audit_log_scoped_to_organization(client):
    token_a, _ = _sync(client, "audit-org-a@cybercomplyit.it", "Org Audit A Srl")
    token_b, _ = _sync(client, "audit-org-b@cybercomplyit.it", "Org Audit B Srl")
    client.post(
        "/api/v1/suppliers", json={"name": "Fornitore Org A"}, headers=_auth(token_a)
    )

    resp_b = client.get("/api/v1/audit-log", headers=_auth(token_b))
    assert resp_b.status_code == 200
    assert all("Fornitore Org A" not in str(e["details"]) for e in resp_b.json())
