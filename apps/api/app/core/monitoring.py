"""Error tracking in produzione con Sentry (Fase 9 — roadmap tecnica: "Integrare Sentry
per error tracking, piano gratuito sufficiente all'inizio").

Stesso principio di degradazione controllata già usato per ogni integrazione esterna di
questa piattaforma (Resend, Stripe, Anthropic, Supabase Admin API): se `SENTRY_DSN` non è
configurato — mai successo in questa sessione di sviluppo, nessun progetto Sentry reale è
mai stato creato — il monitoraggio è semplicemente disattivato. L'applicazione si
comporta esattamente come se questo modulo non esistesse: nessuna eccezione, nessun
rallentamento, nessuna chiamata di rete.
"""

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


def configure_sentry(settings: Settings) -> bool:
    """Inizializza Sentry se `SENTRY_DSN` è configurato con un valore reale.

    Ritorna True se l'inizializzazione è avvenuta, False altrimenti (non configurato, o
    fallita). Non deve mai poter impedire l'avvio dell'applicazione: qualunque errore
    nell'inizializzazione viene loggato e ignorato, mai propagato."""
    if not settings.sentry_configured:
        logger.info(
            "Sentry non configurato (SENTRY_DSN assente): error tracking disattivato."
        )
        return False

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            # Fase 9: percentuale di richieste campionate per le performance (APM), bassa
            # in produzione per restare nei limiti del piano gratuito. L'error tracking
            # (le eccezioni) non è soggetto a questo campionamento: viene sempre inviato.
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            # GDPR (Fase 8): non inviare automaticamente dati potenzialmente personali
            # (IP, cookie, header) insieme agli eventi. Il codice applicativo resta
            # comunque libero di allegare contesto esplicito e non personale (es.
            # organization_id) dove utile.
            send_default_pii=False,
        )
    except Exception as exc:  # difesa in profondità, come per gli altri servizi esterni
        logger.warning(
            "Inizializzazione di Sentry fallita, si prosegue senza error tracking: %s",
            exc,
        )
        return False

    logger.info("Sentry attivato (environment=%s).", settings.environment)
    return True


def capture_exception(exc: BaseException) -> None:
    """Invia un'eccezione a Sentry, se configurato.

    Chiamare `sentry_sdk.capture_exception` quando Sentry non è mai stato inizializzato
    è già di per sé sicuro e senza effetto (comportamento nativo dell'SDK): questo
    wrapper esiste soprattutto per rendere esplicito, nei punti in cui viene chiamato
    (es. l'handler globale delle eccezioni non gestite), che l'invio è intenzionale, e
    per restare comunque protetti se in futuro questa funzione dovesse fare qualcosa di
    più elaborato."""
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception as inner_exc:  # non deve mai mascherare l'errore originale
        logger.warning("Invio dell'eccezione a Sentry fallito: %s", inner_exc)
