"""Test del servizio di storage dei PDF (Fase 9): verifica il comportamento di default
(disco locale, invariato rispetto a prima di questa fase) e il percorso Supabase Storage,
con `httpx` sempre sostituito da un doppio di test — nessuna chiamata di rete reale, come
per ogni altra integrazione esterna di questa piattaforma."""

import uuid

import httpx
import pytest

from app.core.config import get_settings
from app.services import pdf_storage

_FAKE_PDF_BYTES = b"%PDF-1.4 contenuto finto per i test"


def test_save_and_load_local_when_supabase_not_configured():
    settings = get_settings()
    assert settings.supabase_storage_configured is False

    org_id = uuid.uuid4()
    pdf_url = pdf_storage.save_pdf(
        organization_id=org_id, filename="doc_v1.pdf", pdf_bytes=_FAKE_PDF_BYTES
    )

    assert pdf_url == f"local://documents/{org_id}/doc_v1.pdf"
    assert pdf_storage.load_pdf(pdf_url) == _FAKE_PDF_BYTES


def test_load_pdf_returns_none_for_missing_local_file():
    assert pdf_storage.load_pdf("local://documents/non-esiste/x.pdf") is None


def test_load_pdf_returns_none_for_unrecognized_reference():
    assert pdf_storage.load_pdf("ftp://qualcosa/x.pdf") is None


@pytest.fixture()
def _configure_supabase_storage(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", "https://abcdproject.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "sb_service_role_fake")
    yield settings


def test_save_pdf_uses_supabase_when_configured(
    monkeypatch, _configure_supabase_storage
):
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

    def _fake_post(url, *, headers, content, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["content"] = content
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", _fake_post)

    org_id = uuid.uuid4()
    pdf_url = pdf_storage.save_pdf(
        organization_id=org_id, filename="doc_v1.pdf", pdf_bytes=_FAKE_PDF_BYTES
    )

    assert pdf_url == f"supabase://documents/{org_id}/doc_v1.pdf"
    assert captured["url"] == (
        f"https://abcdproject.supabase.co/storage/v1/object/documents/"
        f"documents/{org_id}/doc_v1.pdf"
    )
    assert captured["headers"]["Authorization"] == "Bearer sb_service_role_fake"
    assert captured["content"] == _FAKE_PDF_BYTES

    # Non deve aver scritto nulla su disco locale.
    settings = get_settings()
    local_path = settings.local_storage_path / "documents" / str(org_id) / "doc_v1.pdf"
    assert not local_path.exists()


def test_save_pdf_falls_back_to_local_on_supabase_failure(
    monkeypatch, _configure_supabase_storage
):
    def _fake_post(*a, **k):
        raise httpx.ConnectError("connessione rifiutata")

    monkeypatch.setattr(httpx, "post", _fake_post)

    org_id = uuid.uuid4()
    pdf_url = pdf_storage.save_pdf(
        organization_id=org_id, filename="doc_v1.pdf", pdf_bytes=_FAKE_PDF_BYTES
    )

    # Ripiego sicuro: il PDF non va perso solo perché Supabase Storage non risponde.
    assert pdf_url == f"local://documents/{org_id}/doc_v1.pdf"
    assert pdf_storage.load_pdf(pdf_url) == _FAKE_PDF_BYTES


def test_load_pdf_from_supabase(monkeypatch, _configure_supabase_storage):
    class _FakeResponse:
        status_code = 200
        content = _FAKE_PDF_BYTES

        def raise_for_status(self):
            return None

    def _fake_get(url, *, headers, timeout):
        assert "Authorization" in headers
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = pdf_storage.load_pdf("supabase://documents/org-x/doc_v1.pdf")
    assert result == _FAKE_PDF_BYTES


def test_load_pdf_from_supabase_returns_none_on_404(
    monkeypatch, _configure_supabase_storage
):
    class _FakeResponse:
        status_code = 404

        def raise_for_status(self):
            raise AssertionError("non dovrebbe essere chiamato su 404")

    def _fake_get(*a, **k):
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert pdf_storage.load_pdf("supabase://documents/org-x/mai-esistito.pdf") is None


def test_load_pdf_from_supabase_returns_none_on_connection_error(
    monkeypatch, _configure_supabase_storage
):
    def _fake_get(*a, **k):
        raise httpx.ConnectError("connessione rifiutata")

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert pdf_storage.load_pdf("supabase://documents/org-x/doc_v1.pdf") is None
