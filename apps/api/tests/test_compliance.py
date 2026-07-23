from app.models.organization import OrganizationMember, OrganizationRole
from app.models.user import User
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


def test_list_measures_auto_provisions_catalog(client):
    token, _ = _sync(client, "compl-list@cybercomplyit.it", "Org Compliance List Srl")
    resp = client.get("/api/v1/compliance/measures", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 15
    assert all(m["status"] == "non_applicabile" for m in body)


def test_update_measure_changes_status_and_score(client):
    token, _ = _sync(
        client, "compl-update@cybercomplyit.it", "Org Compliance Update Srl"
    )
    measures = client.get("/api/v1/compliance/measures", headers=_auth(token)).json()
    measure_id = measures[0]["measure_id"]

    resp = client.patch(
        f"/api/v1/compliance/measures/{measure_id}",
        json={"status": "conforme", "note": "Verificato durante audit interno"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "conforme"

    score = client.get("/api/v1/compliance/score", headers=_auth(token)).json()
    assert score["measures_conformi"] == 1
    assert score["score_percent"] > 0


def test_update_measure_invalid_status_rejected(client):
    token, _ = _sync(
        client, "compl-invalid@cybercomplyit.it", "Org Compliance Invalid Srl"
    )
    measures = client.get("/api/v1/compliance/measures", headers=_auth(token)).json()
    measure_id = measures[0]["measure_id"]

    resp = client.patch(
        f"/api/v1/compliance/measures/{measure_id}",
        json={"status": "stato_inventato"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_update_measure_forbidden_for_viewer(client, db_session):
    admin_token, org_id = _sync(
        client, "compl-viewer-admin@cybercomplyit.it", "Org Compliance Viewer Srl"
    )
    client.get("/api/v1/compliance/measures", headers=_auth(admin_token))

    viewer_token = make_token(email="compl-viewer@cybercomplyit.it")
    client.post("/api/v1/auth/sync", json={}, headers=_auth(viewer_token))
    viewer = (
        db_session.query(User)
        .filter(User.email == "compl-viewer@cybercomplyit.it")
        .first()
    )
    db_session.query(OrganizationMember).filter(
        OrganizationMember.user_id == viewer.id
    ).delete()
    db_session.add(
        OrganizationMember(
            user_id=viewer.id, organization_id=org_id, role=OrganizationRole.viewer
        )
    )
    db_session.commit()

    measures = client.get(
        "/api/v1/compliance/measures", headers=_auth(viewer_token)
    ).json()
    resp = client.patch(
        f"/api/v1/compliance/measures/{measures[0]['measure_id']}",
        json={"status": "conforme"},
        headers=_auth(viewer_token),
    )
    assert resp.status_code == 403


def test_score_with_no_scored_measures_is_zero(client):
    token, _ = _sync(client, "compl-zero@cybercomplyit.it", "Org Compliance Zero Srl")
    score = client.get("/api/v1/compliance/score", headers=_auth(token)).json()
    assert score["score_percent"] == 0.0
    assert score["measures_total"] == 15


def test_history_grows_after_each_update(client):
    token, _ = _sync(
        client, "compl-history@cybercomplyit.it", "Org Compliance History Srl"
    )
    measures = client.get("/api/v1/compliance/measures", headers=_auth(token)).json()

    empty_history = client.get(
        "/api/v1/compliance/history", headers=_auth(token)
    ).json()
    assert empty_history == []

    client.patch(
        f"/api/v1/compliance/measures/{measures[0]['measure_id']}",
        json={"status": "conforme"},
        headers=_auth(token),
    )
    client.patch(
        f"/api/v1/compliance/measures/{measures[1]['measure_id']}",
        json={"status": "parziale"},
        headers=_auth(token),
    )

    history = client.get("/api/v1/compliance/history", headers=_auth(token)).json()
    assert len(history) == 2
    assert history[0]["recorded_at"] <= history[1]["recorded_at"]
