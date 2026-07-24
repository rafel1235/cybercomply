"""Test dell'endpoint GET /gdpr/export (GDPR Art. 20 — diritto alla portabilità dei dati,
Fase 8). Verifica che l'export contenga davvero tutto ciò che l'utente ha creato
attraverso le API pubbliche di ogni modulo, coi valori cifrati (P.IVA, dati incidente)
correttamente decifrati nella risposta."""

import uuid

from jose import jwt as jose_jwt

from app.models.audit_log import AuditLog
from app.models.subscription import Plan, Subscription
from app.models.user import User
from tests.conftest import make_token


def _sync(client, db_session, email, org_name, plan: Plan = Plan.business):
    token = make_token(email=email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = resp.json()["organizations"][0]["id"]

    # Business copre sia Incident Reporting che Supply Chain (Fase 6), così l'export può
    # includere dati di tutti i moduli con un'unica organizzazione di test.
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = plan
    db_session.commit()

    return token, org_id


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_export_contains_data_from_every_module(client, db_session):
    token, org_id = _sync(
        client, db_session, "gdpr-export@cybercomplyit.it", "Org GDPR Export Srl"
    )
    headers = _auth(token)

    client.put(
        "/api/v1/organization",
        json={"vat_number": "IT01234567890", "sector": "Manifattura"},
        headers=headers,
    )
    client.post(
        "/api/v1/assessments",
        json={
            "answers": {
                "sector_annex": "allegato_i",
                "employee_count": 80,
                "annual_revenue_eur": 5_000_000,
                "supplies_ict_to_regulated_entities": False,
                "produces_digital_product_for_eu_market": False,
            }
        },
        headers=headers,
    )
    client.patch(
        "/api/v1/compliance/measures/valutazione_rischio_annuale",
        json={"status": "conforme", "note": "Fatta a gennaio"},
        headers=headers,
    )
    client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "registro_rischi"},
        headers=headers,
    )
    incident_resp = client.post(
        "/api/v1/incidents",
        json={
            "incident_type": "Accesso non autorizzato",
            "data": {"descrizione": "Accesso non autorizzato al database clienti"},
        },
        headers=headers,
    )
    assert incident_resp.status_code == 200
    client.post(
        "/api/v1/suppliers",
        json={
            "name": "Fornitore Cloud Srl",
            "category": "hosting",
            "criticality": "alta",
        },
        headers=headers,
    )

    resp = client.get("/api/v1/gdpr/export", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["profile"]["email"] == "gdpr-export@cybercomplyit.it"
    assert "exported_at" in body

    assert len(body["organizations"]) == 1
    org = body["organizations"][0]
    assert org["id"] == org_id
    assert org["name"] == "Org GDPR Export Srl"
    # La P.IVA è cifrata a riposo (Fase 8): l'export deve restituirla comunque in chiaro,
    # come farebbe qualsiasi altro endpoint autenticato che la legge tramite l'ORM.
    assert org["vat_number"] == "IT01234567890"
    assert org["my_role"] == "admin"

    assert len(org["members"]) == 1
    assert org["members"][0]["email"] == "gdpr-export@cybercomplyit.it"

    assert len(org["assessments"]) == 1
    assert org["assessments"][0]["nis2_category"] == "essenziale"

    measure_ids = {m["measure_id"] for m in org["compliance_measures"]}
    assert "valutazione_rischio_annuale" in measure_ids
    updated = next(
        m
        for m in org["compliance_measures"]
        if m["measure_id"] == "valutazione_rischio_annuale"
    )
    assert updated["status"] == "conforme"

    assert len(org["documents"]) == 1
    assert org["documents"][0]["doc_type"] == "registro_rischi"

    assert len(org["incidents"]) == 1
    assert org["incidents"][0]["data"] == {
        "descrizione": "Accesso non autorizzato al database clienti"
    }
    assert len(org["incidents"][0]["deadlines"]) == 5

    assert len(org["suppliers"]) == 1
    assert org["suppliers"][0]["name"] == "Fornitore Cloud Srl"

    assert len(org["audit_log"]) > 0

    # L'export stesso è tracciato nell'audit log.
    export_events = (
        db_session.query(AuditLog).filter(AuditLog.action == "gdpr.data_exported").all()
    )
    assert len(export_events) == 1
    assert str(export_events[0].user_id) == body["profile"]["id"]


def test_export_with_no_organizations_returns_empty_list(client, db_session):
    """Un utente sincronizzato ha sempre almeno un'organizzazione (creata alla
    registrazione, Fase 1): questo test copre comunque il caso limite di zero
    organizzazioni, verificando che l'endpoint non fallisca ma restituisca una lista vuota.
    """
    token = make_token(email="gdpr-no-org@cybercomplyit.it")
    user_id = jose_jwt.get_unverified_claims(token)["sub"]
    user = User(id=uuid.UUID(user_id), email="gdpr-no-org@cybercomplyit.it")
    db_session.add(user)
    db_session.commit()

    resp = client.get(
        "/api/v1/gdpr/export", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["organizations"] == []
    assert body["profile"]["email"] == "gdpr-no-org@cybercomplyit.it"
