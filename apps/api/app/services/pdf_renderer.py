"""Generatore di PDF per i documenti di conformità, senza dipendenze esterne.

Scrive direttamente la sintassi PDF (font base Helvetica), come già fatto in Fase 3.
Rispetto alla prima versione (`pdf_stub.py`, ora sostituito da questo modulo), la Fase 5
aggiunge: intestazione con organizzazione e titolo documento, piè di pagina con numero
pagina/versione/data di generazione, e un disclaimer quando il contenuto è stato scritto
dall'AI. Resta deliberatamente senza librerie di rendering HTML→PDF (WeasyPrint,
Puppeteer): questo ambiente di sviluppo ha già avuto problemi seri nell'installare nuove
dipendenze (vedi incidente node_modules, Fase 4), quindi si rimanda quella scelta a
un'infrastruttura di produzione più stabile.
"""

import textwrap
from datetime import datetime

_PAGE_WIDTH = 595  # A4 in punti, arrotondato
_PAGE_HEIGHT = 842
_MARGIN = 50
_LINE_HEIGHT = 16
_FONT_SIZE = 11
_TITLE_FONT_SIZE = 16
_HEADER_FOOTER_FONT_SIZE = 8
_HEADER_RESERVED = 30  # spazio in punti riservato all'intestazione in cima alla pagina
_FOOTER_RESERVED = 30  # spazio in punti riservato al piè di pagina in fondo alla pagina
_USABLE_HEIGHT = _PAGE_HEIGHT - 2 * _MARGIN - _HEADER_RESERVED - _FOOTER_RESERVED
_LINES_PER_PAGE = max(1, _USABLE_HEIGHT // _LINE_HEIGHT)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap_lines(text: str, width: int = 95) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        wrapped = textwrap.wrap(paragraph, width=width) or [""]
        lines.extend(wrapped)
    return lines


def render_document_pdf(
    title: str,
    sections: list[dict],
    *,
    organization_name: str = "",
    version: int | None = None,
    generated_at: datetime | None = None,
    ai_generated: bool = False,
) -> bytes:
    """Costruisce un PDF multi-pagina con intestazione, titolo, sezioni (titolo + corpo) e
    piè di pagina. `sections` è una lista di dict con chiavi "titolo" e "corpo".
    """
    body_lines: list[tuple[str, str]] = [("title", title), ("blank", "")]
    for section in sections:
        body_lines.append(("heading", section.get("titolo", "")))
        for line in _wrap_lines(section.get("corpo", "")):
            body_lines.append(("body", line))
        body_lines.append(("blank", ""))

    if ai_generated:
        body_lines.append(("blank", ""))
        for line in _wrap_lines(
            "Documento generato con assistenza di intelligenza artificiale. Prima "
            "dell'uso a fini di conformità o in caso di ispezione, va rivisto e validato "
            "da un professionista qualificato."
        ):
            body_lines.append(("disclaimer", line))

    pages: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for kind, text in body_lines:
        current.append((kind, text))
        if len(current) >= _LINES_PER_PAGE:
            pages.append(current)
            current = []
    if current:
        pages.append(current)
    if not pages:
        pages = [[]]

    total_pages = len(pages)
    generated_label = (generated_at or datetime.now()).strftime("%d/%m/%Y %H:%M")

    objects: list[bytes] = []

    def add_object(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    font_obj_num = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_nums = []
    content_obj_nums = []
    for page_index, page_lines in enumerate(pages, start=1):
        stream_parts = ["BT"]

        # Intestazione: organizzazione — titolo, in alto, in corpo ridotto.
        header_text = f"{organization_name} — {title}" if organization_name else title
        header_y = _PAGE_HEIGHT - _MARGIN + _HEADER_RESERVED - _LINE_HEIGHT
        stream_parts.append(
            f"/F1 {_HEADER_FOOTER_FONT_SIZE} Tf 1 0 0 1 {_MARGIN} {header_y} Tm "
            f"({_escape_pdf_text(header_text)}) Tj"
        )

        y = _PAGE_HEIGHT - _MARGIN
        for kind, text in page_lines:
            if kind == "title":
                size = _TITLE_FONT_SIZE
            elif kind == "heading":
                size = _FONT_SIZE + 2
            elif kind == "disclaimer":
                size = _FONT_SIZE - 2
            else:
                size = _FONT_SIZE
            if text:
                stream_parts.append(
                    f"/F1 {size} Tf 1 0 0 1 {_MARGIN} {y} Tm ({_escape_pdf_text(text)}) Tj"
                )
            y -= _LINE_HEIGHT

        # Piè di pagina: numero pagina, versione, data di generazione.
        footer_parts = [f"Pagina {page_index} di {total_pages}"]
        if version is not None:
            footer_parts.append(f"Versione {version}")
        footer_parts.append(f"Generato il {generated_label}")
        footer_text = " · ".join(footer_parts)
        footer_y = _MARGIN - _FOOTER_RESERVED + _LINE_HEIGHT
        stream_parts.append(
            f"/F1 {_HEADER_FOOTER_FONT_SIZE} Tf 1 0 0 1 {_MARGIN} {footer_y} Tm "
            f"({_escape_pdf_text(footer_text)}) Tj"
        )

        stream_parts.append("ET")
        stream = "\n".join(stream_parts).encode("latin-1", errors="replace")
        content_obj_num = add_object(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
        content_obj_nums.append(content_obj_num)

    pages_obj_placeholder_num = (
        len(objects) + 1 + len(pages)
    )  # reserved, computed below

    for content_obj_num in content_obj_nums:
        page_dict = (
            f"<< /Type /Page /Parent {pages_obj_placeholder_num} 0 R "
            f"/MediaBox [0 0 {_PAGE_WIDTH} {_PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/Contents {content_obj_num} 0 R >>"
        ).encode()
        page_obj_nums.append(add_object(page_dict))

    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)
    pages_obj_num = add_object(
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_nums)} >>".encode()
    )
    assert (
        pages_obj_num == pages_obj_placeholder_num
    ), "riferimento /Parent disallineato"

    catalog_obj_num = add_object(
        f"<< /Type /Catalog /Pages {pages_obj_num} 0 R >>".encode()
    )

    buffer = bytearray()
    buffer += b"%PDF-1.4\n"
    offsets = [0] * (len(objects) + 1)
    for i, obj in enumerate(objects, start=1):
        offsets[i] = len(buffer)
        buffer += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(buffer)
    buffer += f"xref\n0 {len(objects) + 1}\n".encode()
    buffer += b"0000000000 65535 f \n"
    for i in range(1, len(objects) + 1):
        buffer += f"{offsets[i]:010} 00000 n \n".encode()

    buffer += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj_num} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()

    return bytes(buffer)
