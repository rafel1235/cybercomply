"""Generatore di PDF segnaposto, senza dipendenze esterne.

Fase 3 richiede un endpoint PDF funzionante end-to-end (non solo simulato): questo modulo
produce un PDF reale e valido a partire dal contenuto del documento, scrivendo
direttamente la sintassi PDF (font base Helvetica, nessuna libreria di terze parti). Non è
pensato per l'impaginazione definitiva: in Fase 5/6 verrà sostituito da un motore di
rendering più ricco (es. WeasyPrint) e lo storage passerà da locale a Supabase Storage.
"""

import textwrap

_PAGE_WIDTH = 595  # A4 in punti, arrotondato
_PAGE_HEIGHT = 842
_MARGIN = 50
_LINE_HEIGHT = 16
_FONT_SIZE = 11
_TITLE_FONT_SIZE = 16
_LINES_PER_PAGE = (_PAGE_HEIGHT - 2 * _MARGIN) // _LINE_HEIGHT


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap_lines(text: str, width: int = 95) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        wrapped = textwrap.wrap(paragraph, width=width) or [""]
        lines.extend(wrapped)
    return lines


def render_placeholder_pdf(title: str, sections: list[dict]) -> bytes:
    """Costruisce un PDF multi-pagina con titolo e sezioni (titolo + corpo).

    `sections` è una lista di dict con chiavi "titolo" e "corpo", nello stesso formato
    prodotto da `document_catalog.build_placeholder_content`.
    """
    all_lines: list[tuple[str, str]] = [("title", title), ("blank", "")]
    for section in sections:
        all_lines.append(("heading", section.get("titolo", "")))
        for line in _wrap_lines(section.get("corpo", "")):
            all_lines.append(("body", line))
        all_lines.append(("blank", ""))

    pages: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for kind, text in all_lines:
        current.append((kind, text))
        if len(current) >= _LINES_PER_PAGE:
            pages.append(current)
            current = []
    if current:
        pages.append(current)
    if not pages:
        pages = [[]]

    objects: list[bytes] = []

    def add_object(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    font_obj_num = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_nums = []
    content_obj_nums = []
    for page_lines in pages:
        stream_parts = ["BT"]
        y = _PAGE_HEIGHT - _MARGIN
        for kind, text in page_lines:
            if kind == "title":
                size = _TITLE_FONT_SIZE
            elif kind == "heading":
                size = _FONT_SIZE + 2
            else:
                size = _FONT_SIZE
            if text:
                stream_parts.append(
                    f"/F1 {size} Tf 1 0 0 1 {_MARGIN} {y} Tm ({_escape_pdf_text(text)}) Tj"
                )
            y -= _LINE_HEIGHT
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
