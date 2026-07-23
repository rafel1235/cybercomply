"""Verifica che l'endpoint POST /documents/generate usi davvero l'orchestratore AI (Fase
5) e che i metadati (token, costo, modello) finiscano nell'audit log per il monitoraggio
spesa richiesto dalla roadmap. Il client HTTP verso Claude resta sempre mockato."""

from app.api.v1.routes import documents as documents_route
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


def test_generate_document_uses_placeholder_by_default_no_ai_meta_cost(client):
    """Senza ANTHROPIC_API_KEY reale (default nei test), l'endpoint deve continuare a
    funzionare esattamente come in Fase 3/4: nessuna regressione introdotta dalla Fase 5.
    """
    token, _ = _sync(
        client, "doc-ai-default@cybercomplyit.it", "Org Doc AI Default Srl"
    )
    resp = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "registro_rischi"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["content"]["sezioni"]) > 0

    audit = client.get("/api/v1/audit-log", headers=_auth(token)).json()
    entry = next(e for e in audit if e["action"] == "document.generated")
    assert entry["details"]["generato_da"] == "placeholder"


def test_generate_document_records_ai_metadata_in_audit_log(client, monkeypatch):
    def _fake_generate(doc_type, organization, context=None):
        content = {
            "generato_da": "ai",
            "modello": "claude-sonnet-5",
            "disclaimer": "test",
            "sezioni": [
                {"titolo": "Sezione", "corpo": "Contenuto generato dall'AI di test"}
            ],
        }
        meta = {
            "generato_da": "ai",
            "modello": "claude-sonnet-5",
            "input_tokens": 321,
            "output_tokens": 654,
            "durata_ms": 987,
            "costo_stimato_usd": 0.012,
        }
        return content, meta

    monkeypatch.setattr(documents_route, "generate_document_content", _fake_generate)

    token, _ = _sync(client, "doc-ai-mocked@cybercomplyit.it", "Org Doc AI Mocked Srl")
    resp = client.post(
        "/api/v1/documents/generate",
        json={"doc_type": "piano_bcp"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert (
        resp.json()["content"]["sezioni"][0]["corpo"]
        == "Contenuto generato dall'AI di test"
    )

    audit = client.get("/api/v1/audit-log", headers=_auth(token)).json()
    entry = next(e for e in audit if e["action"] == "document.generated")
    assert entry["details"]["generato_da"] == "ai"
    assert entry["details"]["input_tokens"] == 321
    assert entry["details"]["output_tokens"] == 654
    assert entry["details"]["costo_stimato_usd"] == 0.012
