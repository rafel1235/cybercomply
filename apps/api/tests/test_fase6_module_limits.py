"""Test di integrazione dei limiti di piano applicati ai moduli esistenti (Fase 6):
quota documenti/mese, Compliance Tracker limitato/sola lettura su Free, Incident
Reporting bloccato su Free. Il gating di Supply Chain è già coperto in
test_suppliers.py (test_suppliers_blocked_on_essential_plan)."""

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


def _downgrade_to_free(db_session, org_id):
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.free
    db_session.commit()


def test_document_generation_blocked_on_free_plan(client, db_session):
    token, org_id = _sync(
        client, "limit-doc-free@cybercomplyit.it", "Org Limit Doc Free Srl"
    )
    _downgrade_to_free(db_session, org_id)

    resp = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "registro_rischi"},
        headers=_auth(token),
    )
    assert resp.status_code == 403
    assert "documenti" in resp.json()["detail"]


def test_document_generation_quota_enforced_on_essential(client):
    """Il trial è su Essential: 5 documenti/mese consentiti, il sesto viene rifiutato."""
    token, _ = _sync(
        client, "limit-doc-essential@cybercomplyit.it", "Org Limit Doc Essential Srl"
    )

    doc_types = [
        "registro_rischi",
        "procedura_incident_response",
        "piano_bcp",
        "politica_supply_chain",
        "politica_crittografia",
    ]
    for doc_type in doc_types:
        resp = client.post(
            "/api/v1/documents/generate",
            json={"doc_type": doc_type},
            headers=_auth(token),
        )
        assert resp.status_code == 200

    sixth = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "politica_controllo_accessi"},
        headers=_auth(token),
    )
    assert sixth.status_code == 403


def test_document_generation_unlimited_on_business(client, db_session):
    token, org_id = _sync(
        client, "limit-doc-business@cybercomplyit.it", "Org Limit Doc Business Srl"
    )
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()

    doc_types = [
        "registro_rischi",
        "procedura_incident_response",
        "piano_bcp",
        "politica_supply_chain",
        "politica_crittografia",
        "politica_controllo_accessi",
    ]
    for doc_type in doc_types:
        resp = client.post(
            "/api/v1/documents/generate",
            json={"doc_type": doc_type},
            headers=_auth(token),
        )
        assert resp.status_code == 200


def test_compliance_measures_limited_and_readonly_on_free(client, db_session):
    token, org_id = _sync(
        client,
        "limit-compliance-free@cybercomplyit.it",
        "Org Limit Compliance Free Srl",
    )
    _downgrade_to_free(db_session, org_id)

    measures = client.get("/api/v1/compliance/measures", headers=_auth(token)).json()
    assert len(measures) == 3

    resp = client.patch(
        f"/api/v1/compliance/measures/{measures[0]['measure_id']}",
        json={"status": "conforme"},
        headers=_auth(token),
    )
    assert resp.status_code == 403


def test_compliance_measures_full_and_editable_on_essential(client):
    token, _ = _sync(
        client,
        "limit-compliance-essential@cybercomplyit.it",
        "Org Limit Compliance Essential Srl",
    )

    measures = client.get("/api/v1/compliance/measures", headers=_auth(token)).json()
    assert len(measures) == 15

    resp = client.patch(
        f"/api/v1/compliance/measures/{measures[0]['measure_id']}",
        json={"status": "conforme"},
        headers=_auth(token),
    )
    assert resp.status_code == 200


def test_incident_reporting_blocked_on_free_plan(client, db_session):
    token, org_id = _sync(
        client, "limit-incident-free@cybercomplyit.it", "Org Limit Incident Free Srl"
    )
    _downgrade_to_free(db_session, org_id)

    resp = client.get("/api/v1/incidents", headers=_auth(token))
    assert resp.status_code == 403
    assert "Incident Reporting" in resp.json()["detail"]


def test_incident_reporting_allowed_on_essential_trial(client):
    token, _ = _sync(
        client,
        "limit-incident-essential@cybercomplyit.it",
        "Org Limit Incident Essential Srl",
    )
    resp = client.get("/api/v1/incidents", headers=_auth(token))
    assert resp.status_code == 200
