from app.models.subscription import Plan, Subscription
from tests.conftest import make_token


def _sync(client, db_session, email, org_name):
    """Fase 6: il modulo Supply Chain è riservato ai piani Business/Enterprise, mentre il
    trial automatico alla registrazione è su Essential (vedi routes/auth.py). Questi test
    riguardano proprio il modulo fornitori, quindi portano l'organizzazione al piano
    Business subito dopo la sincronizzazione — il gating in sé è testato a parte in
    test_entitlements.py."""
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


def test_create_supplier_defaults_to_non_valutato(client, db_session):
    token, _ = _sync(
        client, db_session, "sup-create@cybercomplyit.it", "Org Supplier Create Srl"
    )
    resp = client.post(
        "/api/v1/suppliers",
        json={
            "name": "Cloud Provider SpA",
            "category": "Cloud provider",
            "criticality": "alta",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "non_valutato"
    assert body["criticality"] == "alta"


def test_create_supplier_invalid_criticality_rejected(client, db_session):
    token, _ = _sync(
        client, db_session, "sup-invalid@cybercomplyit.it", "Org Supplier Invalid Srl"
    )
    resp = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore X", "criticality": "altissima"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_list_and_get_supplier(client, db_session):
    token, _ = _sync(
        client, db_session, "sup-list@cybercomplyit.it", "Org Supplier List Srl"
    )
    created = client.post(
        "/api/v1/suppliers", json={"name": "MSP Locale Srl"}, headers=_auth(token)
    ).json()

    listed = client.get("/api/v1/suppliers", headers=_auth(token)).json()
    assert any(s["id"] == created["id"] for s in listed)

    fetched = client.get(f"/api/v1/suppliers/{created['id']}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "MSP Locale Srl"


def test_delete_supplier_requires_admin(client, db_session):
    from app.models.organization import OrganizationMember, OrganizationRole
    from app.models.user import User

    admin_token, org_id = _sync(
        client, db_session, "sup-del-admin@cybercomplyit.it", "Org Supplier Del Srl"
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Da Cancellare Srl"},
        headers=_auth(admin_token),
    ).json()

    viewer_token = make_token(email="sup-del-viewer@cybercomplyit.it")
    client.post("/api/v1/auth/sync", json={}, headers=_auth(viewer_token))
    viewer = (
        db_session.query(User)
        .filter(User.email == "sup-del-viewer@cybercomplyit.it")
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

    forbidden = client.delete(
        f"/api/v1/suppliers/{supplier['id']}", headers=_auth(viewer_token)
    )
    assert forbidden.status_code == 403

    allowed = client.delete(
        f"/api/v1/suppliers/{supplier['id']}", headers=_auth(admin_token)
    )
    assert allowed.status_code == 204


def test_update_supplier_fields_and_status_sets_last_reviewed(client, db_session):
    token, _ = _sync(
        client, db_session, "sup-update@cybercomplyit.it", "Org Supplier Update Srl"
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore da Aggiornare Srl"},
        headers=_auth(token),
    ).json()
    assert supplier["last_reviewed_at"] is None

    resp = client.put(
        f"/api/v1/suppliers/{supplier['id']}",
        json={"criticality": "bassa", "status": "conforme"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["criticality"] == "bassa"
    assert body["status"] == "conforme"
    assert body["last_reviewed_at"] is not None


def test_update_supplier_invalid_criticality_rejected(client, db_session):
    token, _ = _sync(
        client,
        db_session,
        "sup-update-invalid@cybercomplyit.it",
        "Org Supplier Update Invalid Srl",
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore Invalido Srl"},
        headers=_auth(token),
    ).json()
    resp = client.put(
        f"/api/v1/suppliers/{supplier['id']}",
        json={"criticality": "estrema"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_update_supplier_invalid_status_rejected(client, db_session):
    token, _ = _sync(
        client,
        db_session,
        "sup-update-invalid-status@cybercomplyit.it",
        "Org Supplier Update Status Srl",
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore Stato Invalido Srl"},
        headers=_auth(token),
    ).json()
    resp = client.put(
        f"/api/v1/suppliers/{supplier['id']}",
        json={"status": "boh"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_update_supplier_not_found(client, db_session):
    token, _ = _sync(
        client,
        db_session,
        "sup-update-notfound@cybercomplyit.it",
        "Org Supplier Update NotFound Srl",
    )
    resp = client.put(
        "/api/v1/suppliers/00000000-0000-0000-0000-000000000000",
        json={"name": "Non esiste"},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_list_questionnaires_for_supplier(client, db_session):
    token, _ = _sync(
        client,
        db_session,
        "sup-listquest@cybercomplyit.it",
        "Org Supplier ListQuest Srl",
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore Con Questionari Srl"},
        headers=_auth(token),
    ).json()
    client.post(
        f"/api/v1/suppliers/{supplier['id']}/questionnaires", headers=_auth(token)
    )
    client.post(
        f"/api/v1/suppliers/{supplier['id']}/questionnaires", headers=_auth(token)
    )

    resp = client.get(
        f"/api/v1/suppliers/{supplier['id']}/questionnaires", headers=_auth(token)
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_create_questionnaire_generates_unique_token(client, db_session):
    token, _ = _sync(
        client, db_session, "sup-quest@cybercomplyit.it", "Org Supplier Quest Srl"
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore Questionario Srl"},
        headers=_auth(token),
    ).json()

    resp = client.post(
        f"/api/v1/suppliers/{supplier['id']}/questionnaires", headers=_auth(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["access_token"]) > 20
    assert body["completed_at"] is None
    assert body["sent_at"] is not None


def test_public_questionnaire_get_and_submit_updates_supplier_status(
    client, db_session
):
    token, _ = _sync(
        client, db_session, "sup-public@cybercomplyit.it", "Org Supplier Public Srl"
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore Pubblico Srl"},
        headers=_auth(token),
    ).json()
    questionnaire = client.post(
        f"/api/v1/suppliers/{supplier['id']}/questionnaires", headers=_auth(token)
    ).json()
    access_token = questionnaire["access_token"]

    public_get = client.get(f"/api/v1/public/questionnaires/{access_token}")
    assert public_get.status_code == 200
    assert public_get.json()["supplier_name"] == "Fornitore Pubblico Srl"
    assert "mfa_attivo" in public_get.json()["questions"]

    submit = client.post(
        f"/api/v1/public/questionnaires/{access_token}",
        json={
            "answers": {
                "mfa_attivo": True,
                "certificazione_iso27001": True,
                "backup_testato": True,
                "incident_response_documentato": True,
                "formazione_sicurezza_annuale": True,
            }
        },
    )
    assert submit.status_code == 200
    assert submit.json()["completed_at"] is not None

    updated_supplier = client.get(
        f"/api/v1/suppliers/{supplier['id']}", headers=_auth(token)
    ).json()
    assert updated_supplier["status"] == "conforme"


def test_public_questionnaire_partial_answers_give_parziale(client, db_session):
    token, _ = _sync(
        client, db_session, "sup-partial@cybercomplyit.it", "Org Supplier Partial Srl"
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Fornitore Parziale Srl"},
        headers=_auth(token),
    ).json()
    questionnaire = client.post(
        f"/api/v1/suppliers/{supplier['id']}/questionnaires", headers=_auth(token)
    ).json()

    submit = client.post(
        f"/api/v1/public/questionnaires/{questionnaire['access_token']}",
        json={"answers": {"mfa_attivo": True}},
    )
    assert submit.status_code == 200

    updated_supplier = client.get(
        f"/api/v1/suppliers/{supplier['id']}", headers=_auth(token)
    ).json()
    assert updated_supplier["status"] == "parziale"


def test_public_questionnaire_unknown_token_rejected(client):
    resp = client.get("/api/v1/public/questionnaires/token-inesistente")
    assert resp.status_code == 404


def test_suppliers_blocked_on_essential_plan(client, db_session):
    """Il trial automatico è su Essential (Fase 6): senza upgrade a Business, il modulo
    Supply Chain deve restare bloccato con un messaggio chiaro invece di un errore generico.
    """
    token = make_token(email="sup-essential@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Org Supplier Essential Srl"},
        headers=_auth(token),
    )
    resp = client.get("/api/v1/suppliers", headers=_auth(token))
    assert resp.status_code == 403
    assert "Supply Chain" in resp.json()["detail"]
