"""Chiamate alla Admin API di Supabase Auth (GDPR Art. 17 — cancellazione account, Fase 8).

Stesso principio di degradazione controllata già usato per Resend (Fase 7): solo
`httpx`, nessun SDK nuovo, e se `SUPABASE_SERVICE_ROLE_KEY`/`SUPABASE_URL` non sono
configurate l'operazione viene semplicemente saltata e loggata — mai un'eccezione. La
cancellazione dello specchio locale dell'utente (tabella `users` e tutto ciò che vi è
collegato) è l'operazione che conta davvero ai fini del GDPR ed è sempre sincrona e
garantita; l'account Supabase Auth vero e proprio è "best effort" perché richiede una
chiave che, in questa sessione, non è mai stata configurata con un valore reale (vedi
`docs/ROADMAP_PROGRESS.md`)."""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10.0


def delete_auth_user(user_id: str) -> bool:
    """Cancella l'utente da Supabase Auth tramite la Admin API.

    Ritorna True se la cancellazione è andata a buon fine, False se Supabase non è
    configurato o se la chiamata fallisce (incluso un 404: l'utente potrebbe non esistere
    più lato Supabase, non è un errore bloccante). Non solleva mai eccezioni."""
    settings = get_settings()
    if not settings.supabase_admin_configured:
        logger.info(
            "Cancellazione utente Supabase Auth saltata (Admin API non configurata): "
            "user_id=%s",
            user_id,
        )
        return False

    try:
        response = httpx.delete(
            f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            logger.info(
                "Utente non trovato su Supabase Auth (già cancellato?): user_id=%s",
                user_id,
            )
            return False
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning(
            "Cancellazione utente Supabase Auth fallita: user_id=%s: %s", user_id, exc
        )
        return False
    except (
        Exception
    ) as exc:  # difesa in profondità: "best effort" vuol dire davvero mai
        # un'eccezione qui (es. configurazione di rete anomala, proxy, DNS) non deve mai
        # impedire la cancellazione dello specchio locale, che è la parte garantita.
        logger.warning(
            "Cancellazione utente Supabase Auth fallita in modo inatteso: user_id=%s: %s",
            user_id,
            exc,
        )
        return False
