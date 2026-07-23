"""Orchestratore della generazione documenti (Fase 5): decide se generare con l'AI o con
il contenuto segnaposto, senza mai far fallire la richiesta dell'utente per un problema
lato AI — un cliente pagante che genera un documento non deve ricevere un errore 500
perché l'API Claude è momentaneamente sovraccarica: riceve il segnaposto e può rigenerare.
"""

import json
import logging
from datetime import datetime, timezone

from app.models.document import DocumentType
from app.models.organization import Organization
from app.services.ai_client import AiGenerationError, call_claude, is_ai_configured
from app.services.document_catalog import (
    DOCUMENT_SECTION_TEMPLATES,
    build_placeholder_content,
)
from app.services.document_prompts import build_document_prompt

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "Documento generato con assistenza di intelligenza artificiale. Prima dell'uso a fini "
    "di conformità o in caso di ispezione, va rivisto e validato da un professionista "
    "qualificato (avvocato o consulente specializzato in diritto ICT)."
)


def generate_document_content(
    doc_type: DocumentType, organization: Organization, context: dict | None = None
) -> tuple[dict, dict]:
    """Ritorna (content, ai_meta).

    `content` ha sempre la forma `{"sezioni": [...], "generato_il": ..., ...}`, consumata
    identicamente dal frontend indipendentemente da come è stato generato.
    `ai_meta` è pensato per finire nei dettagli dell'audit event: tiene traccia se la
    generazione ha usato l'AI o il segnaposto, e in caso affermativo token/costo/durata
    per il monitoraggio spesa richiesto dalla roadmap.
    """
    context = context or {}
    generated_at = datetime.now(timezone.utc).isoformat()

    if not is_ai_configured():
        content = build_placeholder_content(doc_type)
        content["generato_il"] = generated_at
        return content, {
            "generato_da": "placeholder",
            "motivo": "ANTHROPIC_API_KEY non configurata",
        }

    system_prompt, user_prompt = build_document_prompt(doc_type, organization, context)

    try:
        result = call_claude(system_prompt, user_prompt)
        sections = _parse_ai_sections(result.text, doc_type)
        content = {
            "generato_da": "ai",
            "modello": result.model,
            "generato_il": generated_at,
            "disclaimer": _DISCLAIMER,
            "sezioni": sections,
        }
        ai_meta = {
            "generato_da": "ai",
            "modello": result.model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "durata_ms": result.duration_ms,
            "costo_stimato_usd": result.estimated_cost_usd(),
        }
        return content, ai_meta

    except (AiGenerationError, ValueError) as exc:
        # Fallback esplicito e loggato, mai un 500 per il cliente: meglio un documento
        # segnaposto rigenerabile che un errore in un flusso di conformità critico.
        logger.warning("Generazione AI fallita per %s: %s", doc_type.value, exc)
        content = build_placeholder_content(doc_type)
        content["generato_il"] = generated_at
        return content, {"generato_da": "placeholder", "motivo": str(exc)}


def _parse_ai_sections(raw_text: str, doc_type: DocumentType) -> list[dict]:
    """Valida che l'AI abbia restituito il JSON atteso con tutte le sezioni richieste.
    Solleva ValueError (gestito dal chiamante come fallback) se il formato non torna,
    invece di mostrare all'utente un documento troncato o malformato."""
    text = raw_text.strip()
    # Alcuni modelli avvolgono il JSON in un blocco ```json ... ``` nonostante le
    # istruzioni: viene ripulito prima del parsing invece di fallire subito.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Risposta AI non è JSON valido: {exc}") from exc

    sections = parsed.get("sezioni")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Risposta AI priva del campo 'sezioni' atteso")

    expected_titles = DOCUMENT_SECTION_TEMPLATES.get(doc_type, [])
    for section in sections:
        if (
            not isinstance(section, dict)
            or "titolo" not in section
            or "corpo" not in section
        ):
            raise ValueError("Una sezione della risposta AI non ha 'titolo'/'corpo'")

    if expected_titles and len(sections) != len(expected_titles):
        raise ValueError(
            f"Attese {len(expected_titles)} sezioni, ricevute {len(sections)}"
        )

    return sections
