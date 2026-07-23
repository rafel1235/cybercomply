from app.core.config import get_settings
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


def test_generate_document_creates_version_1(client):
    token, _ = _sync(client, "doc-generate@cybercomplyit.it", "Org Doc Generate Srl")
    resp = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "registro_rischi"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["doc_type"] == "registro_rischi"
    assert body["version"] == 1
    assert len(body["content"]["sezioni"]) > 0


def test_generate_document_invalid_type_rejected(client):
    token, _ = _sync(client, "doc-invalid@cybercomplyit.it", "Org Doc Invalid Srl")
    resp = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "tipo_inventato"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_regenerate_increments_version_without_deleting_history(client):
    token, _ = _sync(client, "doc-version@cybercomplyit.it", "Org Doc Version Srl")
    first = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "piano_bcp"},
        headers=_auth(token),
    )
    second = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "piano_bcp"},
        headers=_auth(token),
    )
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2

    history = client.get(
        "/api/v1/documents", params={"doc_type": "piano_bcp"}, headers=_auth(token)
    ).json()
    assert len(history) == 2


def test_get_document_not_found(client):
    token, _ = _sync(client, "doc-notfound@cybercomplyit.it", "Org Doc NotFound Srl")
    resp = client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000", headers=_auth(token)
    )
    assert resp.status_code == 404


def test_update_document_content_as_admin(client):
    token, _ = _sync(client, "doc-update@cybercomplyit.it", "Org Doc Update Srl")
    generated = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "piano_formazione"},
        headers=_auth(token),
    ).json()

    resp = client.put(
        f"/api/v1/documents/{generated['id']}",
        json={
            "content": {
                "sezioni": [{"titolo": "Modificato a mano", "corpo": "Testo corretto"}]
            }
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["content"]["sezioni"][0]["titolo"] == "Modificato a mano"
    assert resp.json()["version"] == 1  # non crea una nuova versione


def test_delete_document_as_admin(client):
    token, _ = _sync(client, "doc-delete@cybercomplyit.it", "Org Doc Delete Srl")
    generated = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "registro_asset_critici"},
        headers=_auth(token),
    ).json()

    resp = client.delete(f"/api/v1/documents/{generated['id']}", headers=_auth(token))
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/documents/{generated['id']}", headers=_auth(token))
    assert resp.status_code == 404


def test_generate_pdf_produces_real_pdf_bytes(client):
    token, _ = _sync(client, "doc-pdf@cybercomplyit.it", "Org Doc Pdf Srl")
    generated = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "politica_crittografia"},
        headers=_auth(token),
    ).json()

    resp = client.post(f"/api/v1/documents/{generated['id']}/pdf", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["pdf_url"] is not None
    assert body["pdf_url"].startswith("local://documents/")

    # Verifica che il file sia stato scritto davvero e sia un PDF valido, non solo
    # simulato nella risposta JSON.
    relative_path = body["pdf_url"].removeprefix("local://")
    file_path = get_settings().local_storage_path / relative_path
    assert file_path.exists()
    assert file_path.read_bytes().startswith(b"%PDF-1.4")
