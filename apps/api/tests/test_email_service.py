"""Test del servizio email (Fase 7). Nessuna chiamata di rete reale: `httpx.post` viene
sempre sostituito con un doppio di test, sia per non dipendere da una chiave Resend reale
sia per non inviare email vere durante i test automatici."""

import httpx
import pytest

from app.core.config import get_settings
from app.services import email_service


@pytest.fixture(autouse=True)
def _configure_email(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "resend_api_key", "re_test_fake")
    yield


def test_is_email_configured_false_with_placeholder(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "resend_api_key", "replace-with-real-key-when-fase-7-inizia"
    )
    assert email_service.is_email_configured() is False


def test_is_email_configured_true_with_real_looking_key():
    assert email_service.is_email_configured() is True


def test_send_email_skips_silently_when_not_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "resend_api_key", "")

    def _should_not_be_called(*a, **k):
        raise AssertionError("httpx.post non doveva essere chiamato")

    monkeypatch.setattr(httpx, "post", _should_not_be_called)

    result = email_service.send_email(to="a@b.it", subject="Test", html="<p>Test</p>")
    assert result is False


def test_send_email_success(monkeypatch):
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

    def _fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = email_service.send_email(
        to="destinatario@example.it", subject="Ciao", html="<p>Ciao</p>"
    )

    assert result is True
    assert captured["url"] == email_service.RESEND_API_URL
    assert captured["headers"]["Authorization"] == "Bearer re_test_fake"
    assert captured["json"]["to"] == ["destinatario@example.it"]
    assert captured["json"]["subject"] == "Ciao"


def test_send_email_returns_false_on_http_error(monkeypatch):
    def _fake_post(*a, **k):
        raise httpx.ConnectError("connessione rifiutata")

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = email_service.send_email(to="a@b.it", subject="Test", html="<p>Test</p>")
    assert result is False
