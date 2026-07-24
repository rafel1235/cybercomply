"""Test della paginazione condivisa (Fase 10 — performance): verifica che le liste che
possono crescere nel tempo (documenti, incidenti, fornitori, assessment, storico
compliance) non restituiscano mai più righe di `limit`, che l'header `X-Total-Count`
rifletta il conteggio reale, e che `limit`/`offset` fuori range vengano riportati in un
intervallo sicuro invece di causare un errore o un comportamento indefinito."""

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


def _upgrade_to_business(db_session, org_id):
    """Supply Chain (fornitori) richiede il piano Business/Enterprise (Fase 6)."""
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_documents_list_is_paginated(client):
    token, _ = _sync(client, "pag-docs@cybercomplyit.it", "Org Pag Docs Srl")
    for _ in range(5):
        resp = client.post(
            "/api/v1/documents/generate",
            json={"doc_type": "registro_rischi"},
            headers=_auth(token),
        )
        assert resp.status_code == 200

    resp = client.get("/api/v1/documents", params={"limit": 2}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert resp.headers["X-Total-Count"] == "5"

    # La seconda pagina contiene le righe successive, non le stesse.
    page1 = client.get(
        "/api/v1/documents", params={"limit": 2, "offset": 0}, headers=_auth(token)
    ).json()
    page2 = client.get(
        "/api/v1/documents", params={"limit": 2, "offset": 2}, headers=_auth(token)
    ).json()
    assert {d["id"] for d in page1}.isdisjoint({d["id"] for d in page2})


def test_documents_limit_is_clamped_to_maximum(client):
    token, _ = _sync(
        client, "pag-docs-clamp@cybercomplyit.it", "Org Pag Docs Clamp Srl"
    )
    resp = client.get(
        "/api/v1/documents", params={"limit": 999999}, headers=_auth(token)
    )
    assert resp.status_code == 200
    # Nessun documento generato in questo test: verifica solo che una richiesta con un
    # limit assurdo non causi un errore (clamping silenzioso, non un 422).
    assert resp.headers["X-Total-Count"] == "0"


def test_documents_negative_offset_is_clamped_to_zero(client):
    token, _ = _sync(client, "pag-docs-neg@cybercomplyit.it", "Org Pag Docs Neg Srl")
    client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "registro_rischi"},
        headers=_auth(token),
    )
    resp = client.get("/api/v1/documents", params={"offset": -50}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_incidents_list_is_paginated(client):
    token, _ = _sync(client, "pag-inc@cybercomplyit.it", "Org Pag Incidenti Srl")
    for i in range(4):
        resp = client.post(
            "/api/v1/incidents",
            json={"incident_type": "malware", "data": {"nota": f"caso {i}"}},
            headers=_auth(token),
        )
        assert resp.status_code == 200

    resp = client.get("/api/v1/incidents", params={"limit": 3}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 3
    assert resp.headers["X-Total-Count"] == "4"


def test_assessments_list_is_paginated(client):
    token, _ = _sync(client, "pag-assess@cybercomplyit.it", "Org Pag Assess Srl")
    answers = {
        "sector_annex": "nessuno",
        "employee_count": 5,
        "annual_revenue_eur": 500_000,
        "supplies_ict_to_regulated_entities": False,
        "produces_digital_product_for_eu_market": False,
    }
    for _ in range(3):
        resp = client.post(
            "/api/v1/assessments", json={"answers": answers}, headers=_auth(token)
        )
        assert resp.status_code == 200

    resp = client.get("/api/v1/assessments", params={"limit": 1}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.headers["X-Total-Count"] == "3"


def test_suppliers_list_is_paginated(client, db_session):
    token, org_id = _sync(client, "pag-sup@cybercomplyit.it", "Org Pag Fornitori Srl")
    _upgrade_to_business(db_session, org_id)

    for i in range(3):
        resp = client.post(
            "/api/v1/suppliers",
            json={
                "name": f"Fornitore {i}",
                "category": "Cloud provider",
                "criticality": "media",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 200

    resp = client.get("/api/v1/suppliers", params={"limit": 2}, headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert resp.headers["X-Total-Count"] == "3"


def test_compliance_history_is_paginated_and_stays_chronological(client):
    token, _ = _sync(client, "pag-hist@cybercomplyit.it", "Org Pag Storico Srl")
    measures = client.get("/api/v1/compliance/measures", headers=_auth(token)).json()

    # Aggiorna 3 misure distinte: 3 snapshot dello score in ordine cronologico.
    for measure in measures[:3]:
        resp = client.patch(
            f"/api/v1/compliance/measures/{measure['measure_id']}",
            json={"status": "conforme"},
            headers=_auth(token),
        )
        assert resp.status_code == 200

    full_history = client.get("/api/v1/compliance/history", headers=_auth(token))
    assert full_history.headers["X-Total-Count"] == "3"

    limited = client.get(
        "/api/v1/compliance/history", params={"limit": 2}, headers=_auth(token)
    )
    assert limited.status_code == 200
    points = limited.json()
    assert len(points) == 2
    # Devono essere i 2 più recenti (non i 2 più vecchi) e restare in ordine crescente.
    assert points == sorted(points, key=lambda p: p["recorded_at"])
    full_points = full_history.json()
    assert points == full_points[-2:]
