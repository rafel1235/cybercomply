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


def test_create_incident_generates_reference_code_and_deadlines(client):
    token, _ = _sync(client, "inc-create@cybercomplyit.it", "Org Incident Create Srl")
    resp = client.post(
        "/api/v1/incidents",
        json={"incident_type": "Phishing mirato", "data": {"descrizione": "Test"}},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reference_code"].startswith("INC-")
    assert body["status"] == "aperto"
    assert len(body["deadlines"]) == 5
    phases = {d["phase"] for d in body["deadlines"]}
    assert phases == {
        "early_warning_24h",
        "notifica_72h",
        "relazione_30gg",
        "cra_enisa_24h",
        "cra_enisa_72h",
    }
    assert all(d["sent"] is False for d in body["deadlines"])


def test_reference_codes_increment_per_organization(client):
    token, _ = _sync(
        client, "inc-sequence@cybercomplyit.it", "Org Incident Sequence Srl"
    )
    first = client.post(
        "/api/v1/incidents", json={"incident_type": "DDoS"}, headers=_auth(token)
    ).json()
    second = client.post(
        "/api/v1/incidents", json={"incident_type": "Ransomware"}, headers=_auth(token)
    ).json()
    assert first["reference_code"] != second["reference_code"]
    assert first["reference_code"].endswith("-001")
    assert second["reference_code"].endswith("-002")


def test_close_incident_sets_closed_at(client):
    token, _ = _sync(client, "inc-close@cybercomplyit.it", "Org Incident Close Srl")
    incident = client.post(
        "/api/v1/incidents",
        json={"incident_type": "Accesso non autorizzato"},
        headers=_auth(token),
    ).json()

    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/close", headers=_auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "chiuso"
    assert resp.json()["closed_at"] is not None


def test_close_already_closed_incident_rejected(client):
    token, _ = _sync(
        client, "inc-doubleclose@cybercomplyit.it", "Org Incident DoubleClose Srl"
    )
    incident = client.post(
        "/api/v1/incidents", json={"incident_type": "Malware"}, headers=_auth(token)
    ).json()
    client.post(f"/api/v1/incidents/{incident['id']}/close", headers=_auth(token))

    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/close", headers=_auth(token)
    )
    assert resp.status_code == 400


def test_record_notification_marks_deadline_as_sent(client):
    token, _ = _sync(client, "inc-notify@cybercomplyit.it", "Org Incident Notify Srl")
    incident = client.post(
        "/api/v1/incidents", json={"incident_type": "Data breach"}, headers=_auth(token)
    ).json()

    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/notifications",
        json={
            "phase": "early_warning_24h",
            "recipient": "CSIRT Italia",
            "content": "Notifica inviata",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["notifications"]) == 1
    early_warning = next(
        d for d in body["deadlines"] if d["phase"] == "early_warning_24h"
    )
    assert early_warning["sent"] is True
    assert early_warning["overdue"] is False


def test_cannot_send_duplicate_notification_for_same_phase(client):
    token, _ = _sync(
        client, "inc-duplicate@cybercomplyit.it", "Org Incident Duplicate Srl"
    )
    incident = client.post(
        "/api/v1/incidents", json={"incident_type": "Data breach"}, headers=_auth(token)
    ).json()
    client.post(
        f"/api/v1/incidents/{incident['id']}/notifications",
        json={"phase": "notifica_72h", "recipient": "CSIRT Italia"},
        headers=_auth(token),
    )
    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/notifications",
        json={"phase": "notifica_72h", "recipient": "CSIRT Italia"},
        headers=_auth(token),
    )
    assert resp.status_code == 409


def test_list_incidents_filters_by_status(client):
    token, _ = _sync(client, "inc-filter@cybercomplyit.it", "Org Incident Filter Srl")
    open_incident = client.post(
        "/api/v1/incidents", json={"incident_type": "Phishing"}, headers=_auth(token)
    ).json()
    closed_incident = client.post(
        "/api/v1/incidents", json={"incident_type": "DDoS"}, headers=_auth(token)
    ).json()
    client.post(
        f"/api/v1/incidents/{closed_incident['id']}/close", headers=_auth(token)
    )

    resp = client.get(
        "/api/v1/incidents", params={"status_filter": "aperto"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert open_incident["id"] in ids
    assert closed_incident["id"] not in ids


def test_get_incident_not_found(client):
    token, _ = _sync(
        client, "inc-notfound@cybercomplyit.it", "Org Incident NotFound Srl"
    )
    resp = client.get(
        "/api/v1/incidents/00000000-0000-0000-0000-000000000000", headers=_auth(token)
    )
    assert resp.status_code == 404
