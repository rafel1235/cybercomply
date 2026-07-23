"""Deprecato: sostituito da `app.services.pdf_renderer` in Fase 5.

Questo file non può essere eliminato dall'ambiente di sviluppo usato in questa sessione
(permessi del filesystem sincronizzato), quindi resta come shim di compatibilità che
rimanda all'implementazione reale, invece di duplicare la logica di rendering. Nessun
codice del progetto lo importa più: `app/api/v1/routes/documents.py` usa
`render_document_pdf` da `pdf_renderer`.
"""

from app.services.pdf_renderer import render_document_pdf


def render_placeholder_pdf(title: str, sections: list[dict]) -> bytes:
    return render_document_pdf(title, sections)
