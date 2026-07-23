from datetime import datetime, timezone

from app.services.pdf_renderer import render_document_pdf


def test_pdf_includes_header_footer_and_version():
    pdf_bytes = render_document_pdf(
        title="Registro Rischi",
        organization_name="Acme Srl",
        sections=[{"titolo": "Sezione 1", "corpo": "Contenuto di prova"}],
        version=3,
        generated_at=datetime(2026, 7, 24, 10, 30, tzinfo=timezone.utc),
        ai_generated=False,
    )
    text = pdf_bytes.decode("latin-1", errors="ignore")

    assert text.startswith("%PDF-1.4")
    assert "Acme Srl" in text
    assert "Registro Rischi" in text
    assert "Versione 3" in text
    assert "Pagina 1 di 1" in text
    assert "24/07/2026" in text


def test_pdf_includes_disclaimer_when_ai_generated():
    pdf_bytes = render_document_pdf(
        title="Piano BCP",
        organization_name="Acme Srl",
        sections=[{"titolo": "Sezione 1", "corpo": "Contenuto"}],
        version=1,
        ai_generated=True,
    )
    text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "intelligenza artificiale" in text


def test_pdf_omits_disclaimer_when_not_ai_generated():
    pdf_bytes = render_document_pdf(
        title="Piano BCP",
        organization_name="Acme Srl",
        sections=[{"titolo": "Sezione 1", "corpo": "Contenuto"}],
        version=1,
        ai_generated=False,
    )
    text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "intelligenza artificiale" not in text


def test_pdf_paginates_long_content():
    long_sections = [
        {"titolo": f"Sezione {i}", "corpo": "Riga di contenuto molto lunga. " * 20}
        for i in range(10)
    ]
    pdf_bytes = render_document_pdf(
        title="Documento Lungo",
        organization_name="Acme Srl",
        sections=long_sections,
        version=1,
    )
    text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "Pagina 1 di" in text
    # Con questo volume di contenuto ci si aspetta più di una pagina.
    assert "di 1)" not in text  # sanity: non è tutto forzato su una riga
    import re

    total_pages = int(re.search(r"Pagina 1 di (\d+)", text).group(1))
    assert total_pages > 1
