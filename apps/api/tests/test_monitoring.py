"""Test dell'integrazione Sentry (Fase 9 — error tracking in produzione): verifica che il
monitoraggio sia disattivato di default (nessun DSN reale mai configurato in questa
sessione di sviluppo), che si attivi con un DSN valido, e che qualunque errore
nell'inizializzazione o nell'invio non si propaghi mai al chiamante — stesso principio di
degradazione controllata delle altre integrazioni esterne (Resend, Stripe, Anthropic)."""

from app.core import monitoring
from app.core.config import get_settings

# DSN sintatticamente valido ma verso un progetto Sentry che non esiste: sentry_sdk.init()
# non fa alcuna chiamata di rete in fase di inizializzazione (la trasmissione degli eventi
# è asincrona e successiva), quindi è sicuro da usare nei test senza rischiare timeout o
# chiamate esterne reali.
_FAKE_DSN = "https://abc123def456@o000000.ingest.sentry.io/0000000"


def test_sentry_not_configured_by_default():
    settings = get_settings()
    assert settings.sentry_configured is False
    assert monitoring.configure_sentry(settings) is False


def test_sentry_not_configured_with_placeholder(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "sentry_dsn", "replace-with-real-dsn-when-fase-9-inizia"
    )
    assert settings.sentry_configured is False
    assert monitoring.configure_sentry(settings) is False


def test_sentry_configured_with_real_dsn(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sentry_dsn", _FAKE_DSN)
    assert settings.sentry_configured is True
    assert monitoring.configure_sentry(settings) is True

    import sentry_sdk

    # L'inizializzazione ha effettivamente attivato un client Sentry.
    assert sentry_sdk.is_initialized() is True


def test_sentry_init_failure_is_caught(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sentry_dsn", _FAKE_DSN)

    import sentry_sdk

    def _boom(*args, **kwargs):
        raise RuntimeError("DSN non raggiungibile")

    monkeypatch.setattr(sentry_sdk, "init", _boom)
    assert monitoring.configure_sentry(settings) is False


def test_capture_exception_never_raises_when_not_configured():
    # Nessun sentry_sdk.init() mai chiamato in questo test: capture_exception deve
    # comunque essere sicura da chiamare (comportamento nativo dell'SDK quando non c'è
    # un client attivo).
    try:
        raise ValueError("errore di prova")
    except ValueError as exc:
        monitoring.capture_exception(exc)  # non deve sollevare nulla


def test_capture_exception_never_raises_on_internal_error(monkeypatch):
    import sentry_sdk

    def _boom(*args, **kwargs):
        raise RuntimeError("invio fallito")

    monkeypatch.setattr(sentry_sdk, "capture_exception", _boom)
    try:
        raise ValueError("errore di prova")
    except ValueError as exc:
        monitoring.capture_exception(
            exc
        )  # non deve propagare l'eccezione di sentry_sdk
