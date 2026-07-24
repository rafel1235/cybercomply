"""Invio email transazionali (Fase 7 — roadmap tecnica) via l'API REST di Resend.

Stesso principio di degradazione controllata già usato per l'AI (Fase 5) e Stripe (Fase
6): niente SDK nuovo (solo `httpx`, già una dipendenza del progetto), e se
`RESEND_API_KEY` non è configurata l'invio viene semplicemente saltato e loggato — mai
un'eccezione. Ogni email di questo modulo è un side-effect di un'altra azione (una
registrazione, un invito, un webhook di pagamento...) e non deve mai poter far fallire
quell'azione.
"""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
REQUEST_TIMEOUT_SECONDS = 10.0


def is_email_configured() -> bool:
    return get_settings().email_configured


def send_email(*, to: str, subject: str, html: str) -> bool:
    """Invia un'email transazionale tramite Resend.

    Ritorna True se l'invio è andato a buon fine, False se Resend non è configurato o se
    la chiamata fallisce. Non solleva mai eccezioni: un problema di invio email è sempre
    secondario rispetto all'azione che lo ha generato (l'utente deve poter registrarsi,
    essere invitato, ricevere un webhook di pagamento applicato, ecc. anche se in questo
    momento le email non funzionano)."""
    settings = get_settings()
    if not settings.email_configured:
        logger.info(
            "Email non inviata (RESEND_API_KEY non configurata): a=%s subject=%r",
            to,
            subject,
        )
        return False

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.email_from_address,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("Invio email fallito (a=%s subject=%r): %s", to, subject, exc)
        return False
