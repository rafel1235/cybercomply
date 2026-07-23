"""Test dell'orchestratore di generazione documenti (Fase 5): verifica sia il percorso
"AI configurata e risponde bene" sia i fallback (non configurata, risposta malformata,
chiamata fallita), tutti senza mai chiamare la vera API Claude."""

from types import SimpleNamespace

from app.models.document import DocumentType
from app.services import ai_document_generator
from app.services.ai_client import AiCallResult, AiGenerationError
from app.services.document_catalog import DOCUMENT_SECTION_TEMPLATES


def _fake_org() -> SimpleNamespace:
    return SimpleNamespace(
        name="Acme Manifatture Srl", sector="manifatturiero", employee_count=42
    )


def test_falls_back_to_placeholder_when_ai_not_configured(monkeypatch):
    monkeypatch.setattr(ai_document_generator, "is_ai_configured", lambda: False)

    content, meta = ai_document_generator.generate_document_content(
        DocumentType.registro_rischi, _fake_org()
    )

    assert meta["generato_da"] == "placeholder"
    assert len(content["sezioni"]) == len(
        DOCUMENT_SECTION_TEMPLATES[DocumentType.registro_rischi]
    )


def test_uses_ai_content_when_call_succeeds(monkeypatch):
    monkeypatch.setattr(ai_document_generator, "is_ai_configured", lambda: True)

    expected_titles = DOCUMENT_SECTION_TEMPLATES[DocumentType.piano_bcp]
    fake_sections = [
        {"titolo": t, "corpo": f"Contenuto reale per {t}."} for t in expected_titles
    ]
    import json

    fake_result = AiCallResult(
        text=json.dumps({"sezioni": fake_sections}),
        model="claude-sonnet-5",
        input_tokens=500,
        output_tokens=900,
        duration_ms=1234,
    )
    monkeypatch.setattr(
        ai_document_generator, "call_claude", lambda *a, **k: fake_result
    )

    content, meta = ai_document_generator.generate_document_content(
        DocumentType.piano_bcp, _fake_org()
    )

    assert meta["generato_da"] == "ai"
    assert meta["input_tokens"] == 500
    assert meta["output_tokens"] == 900
    assert meta["modello"] == "claude-sonnet-5"
    assert content["sezioni"][0]["corpo"].startswith("Contenuto reale")
    assert content["disclaimer"]


def test_handles_json_wrapped_in_code_fence(monkeypatch):
    monkeypatch.setattr(ai_document_generator, "is_ai_configured", lambda: True)
    expected_titles = DOCUMENT_SECTION_TEMPLATES[DocumentType.registro_asset_critici]
    fake_sections = [{"titolo": t, "corpo": "x"} for t in expected_titles]
    import json

    wrapped = "```json\n" + json.dumps({"sezioni": fake_sections}) + "\n```"
    fake_result = AiCallResult(
        text=wrapped,
        model="claude-sonnet-5",
        input_tokens=1,
        output_tokens=1,
        duration_ms=1,
    )
    monkeypatch.setattr(
        ai_document_generator, "call_claude", lambda *a, **k: fake_result
    )

    content, meta = ai_document_generator.generate_document_content(
        DocumentType.registro_asset_critici, _fake_org()
    )
    assert meta["generato_da"] == "ai"
    assert len(content["sezioni"]) == len(expected_titles)


def test_falls_back_to_placeholder_on_invalid_json(monkeypatch):
    monkeypatch.setattr(ai_document_generator, "is_ai_configured", lambda: True)
    fake_result = AiCallResult(
        text="questo non è JSON",
        model="claude-sonnet-5",
        input_tokens=1,
        output_tokens=1,
        duration_ms=1,
    )
    monkeypatch.setattr(
        ai_document_generator, "call_claude", lambda *a, **k: fake_result
    )

    content, meta = ai_document_generator.generate_document_content(
        DocumentType.piano_formazione, _fake_org()
    )
    assert meta["generato_da"] == "placeholder"
    assert "motivo" in meta


def test_falls_back_to_placeholder_on_wrong_section_count(monkeypatch):
    monkeypatch.setattr(ai_document_generator, "is_ai_configured", lambda: True)
    import json

    fake_result = AiCallResult(
        text=json.dumps({"sezioni": [{"titolo": "Solo una", "corpo": "x"}]}),
        model="claude-sonnet-5",
        input_tokens=1,
        output_tokens=1,
        duration_ms=1,
    )
    monkeypatch.setattr(
        ai_document_generator, "call_claude", lambda *a, **k: fake_result
    )

    content, meta = ai_document_generator.generate_document_content(
        DocumentType.registro_rischi, _fake_org()
    )
    assert meta["generato_da"] == "placeholder"


def test_falls_back_to_placeholder_when_api_call_raises(monkeypatch):
    monkeypatch.setattr(ai_document_generator, "is_ai_configured", lambda: True)

    def _raise(*a, **k):
        raise AiGenerationError("API sovraccarica dopo 3 tentativi")

    monkeypatch.setattr(ai_document_generator, "call_claude", _raise)

    content, meta = ai_document_generator.generate_document_content(
        DocumentType.politica_crittografia, _fake_org()
    )
    assert meta["generato_da"] == "placeholder"
    assert "sovraccarica" in meta["motivo"]
