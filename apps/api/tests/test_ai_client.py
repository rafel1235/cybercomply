"""Test unitari per il wrapper AI (Fase 5). Nessuna chiamata di rete reale: `httpx.Client`
viene sempre sostituito con un doppio di test, sia per non dipendere da una chiave API
reale sia per non spendere soldi veri o dipendere dalla raggiungibilità di rete durante i
test automatici."""

import httpx
import pytest

from app.core.config import get_settings
from app.services import ai_client


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or str(json_data)

    def json(self):
        return self._json_data


class _FakeClient:
    """Sostituisce `httpx.Client`: restituisce in sequenza le risposte pre-programmate,
    così i test su retry/backoff non dipendono da timing reale né da rete."""

    _queue: list[object] = []
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        _FakeClient.calls += 1
        item = _FakeClient._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _configure_key(monkeypatch):
    """Simula una chiave API reale per la durata dei test in questo file, e azzera il
    contatore/coda del doppio di test ad ogni test."""
    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-fake-key")
    _FakeClient._queue = []
    _FakeClient.calls = 0
    monkeypatch.setattr(ai_client, "_sleep_backoff", lambda attempt: None)
    yield


def test_is_ai_configured_false_with_placeholder_key(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "anthropic_api_key", "replace-with-real-key-when-fase-5-inizia"
    )
    assert ai_client.is_ai_configured() is False


def test_is_ai_configured_true_with_real_looking_key():
    assert ai_client.is_ai_configured() is True


def test_call_claude_success_first_try(monkeypatch):
    _FakeClient._queue = [
        _FakeResponse(
            200,
            {
                "content": [{"type": "text", "text": '{"sezioni": []}'}],
                "usage": {"input_tokens": 120, "output_tokens": 340},
                "model": "claude-sonnet-5",
            },
        )
    ]
    monkeypatch.setattr(httpx, "Client", _FakeClient)

    result = ai_client.call_claude("system", "user")

    assert result.text == '{"sezioni": []}'
    assert result.input_tokens == 120
    assert result.output_tokens == 340
    assert _FakeClient.calls == 1


def test_call_claude_retries_on_overloaded_then_succeeds(monkeypatch):
    _FakeClient._queue = [
        _FakeResponse(529, text="overloaded"),
        _FakeResponse(503, text="unavailable"),
        _FakeResponse(
            200,
            {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 10, "output_tokens": 20},
                "model": "claude-sonnet-5",
            },
        ),
    ]
    monkeypatch.setattr(httpx, "Client", _FakeClient)

    result = ai_client.call_claude("system", "user")

    assert result.text == "ok"
    assert _FakeClient.calls == 3


def test_call_claude_raises_after_exhausting_retries(monkeypatch):
    _FakeClient._queue = [
        _FakeResponse(529, text="overloaded"),
        _FakeResponse(529, text="overloaded"),
        _FakeResponse(529, text="overloaded"),
    ]
    monkeypatch.setattr(httpx, "Client", _FakeClient)

    with pytest.raises(ai_client.AiGenerationError):
        ai_client.call_claude("system", "user")

    assert _FakeClient.calls == 3


def test_call_claude_non_retryable_error_fails_immediately(monkeypatch):
    _FakeClient._queue = [_FakeResponse(401, text="invalid api key")]
    monkeypatch.setattr(httpx, "Client", _FakeClient)

    with pytest.raises(ai_client.AiGenerationError):
        ai_client.call_claude("system", "user")

    assert _FakeClient.calls == 1


def test_call_claude_raises_when_not_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    with pytest.raises(ai_client.AiGenerationError):
        ai_client.call_claude("system", "user")


def test_estimated_cost_none_when_pricing_not_configured():
    result = ai_client.AiCallResult(
        text="x",
        model="claude-sonnet-5",
        input_tokens=1000,
        output_tokens=1000,
        duration_ms=10,
    )
    assert result.estimated_cost_usd() is None


def test_estimated_cost_computed_when_pricing_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_input_cost_per_mtok", 3.0)
    monkeypatch.setattr(settings, "anthropic_output_cost_per_mtok", 15.0)
    result = ai_client.AiCallResult(
        text="x",
        model="claude-sonnet-5",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        duration_ms=10,
    )
    assert result.estimated_cost_usd() == 18.0
