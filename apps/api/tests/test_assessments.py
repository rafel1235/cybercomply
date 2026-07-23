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


def test_create_assessment_classifies_essenziale(client):
    token, _ = _sync(client, "assess-essenziale@cybercomplyit.it", "Ospedale Test SpA")
    resp = client.post(
        "/api/v1/assessments",
        json={
            "answers": {
                "sector_annex": "allegato_i",
                "employee_count": 300,
                "annual_revenue_eur": 50_000_000,
                "supplies_ict_to_regulated_entities": False,
                "produces_digital_product_for_eu_market": False,
            }
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_category"] == "essenziale"
    assert body["cra_in_scope"] is False
    assert "rationale" in body and len(body["rationale"]) > 0


def test_create_assessment_supply_chain_fallback(client):
    token, _ = _sync(
        client, "assess-supplychain@cybercomplyit.it", "Piccolo Fornitore Srl"
    )
    resp = client.post(
        "/api/v1/assessments",
        json={
            "answers": {
                "sector_annex": "nessuno",
                "employee_count": 5,
                "annual_revenue_eur": 300_000,
                "supplies_ict_to_regulated_entities": True,
                "produces_digital_product_for_eu_market": False,
            }
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["nis2_category"] == "importante"


def test_create_assessment_out_of_scope(client):
    token, _ = _sync(
        client, "assess-outofscope@cybercomplyit.it", "Bottega Piccola Srl"
    )
    resp = client.post(
        "/api/v1/assessments",
        json={
            "answers": {
                "sector_annex": "nessuno",
                "employee_count": 4,
                "annual_revenue_eur": 200_000,
                "supplies_ict_to_regulated_entities": False,
                "produces_digital_product_for_eu_market": False,
            }
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["nis2_category"] == "non_in_perimetro"


def test_latest_assessment_requires_prior_run(client):
    token, _ = _sync(client, "assess-none@cybercomplyit.it", "Org Senza Assessment Srl")
    resp = client.get("/api/v1/assessments/latest", headers=_auth(token))
    assert resp.status_code == 404


def test_history_never_overwrites(client):
    token, _ = _sync(client, "assess-history@cybercomplyit.it", "Org Storico Srl")
    answers = {
        "sector_annex": "nessuno",
        "employee_count": 2,
        "annual_revenue_eur": 100_000,
        "supplies_ict_to_regulated_entities": False,
        "produces_digital_product_for_eu_market": False,
    }
    client.post("/api/v1/assessments", json={"answers": answers}, headers=_auth(token))
    client.post("/api/v1/assessments", json={"answers": answers}, headers=_auth(token))

    resp = client.get("/api/v1/assessments", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    latest = client.get("/api/v1/assessments/latest", headers=_auth(token))
    assert latest.status_code == 200
