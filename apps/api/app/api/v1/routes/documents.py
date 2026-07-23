from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentMembership,
    get_current_membership,
    get_db,
    require_admin,
)
from app.core.config import get_settings
from app.models.document import Document, DocumentType
from app.schemas.document import (
    DocumentGenerateRequest,
    DocumentOut,
    DocumentUpdateRequest,
)
from app.services.audit import record_audit_event
from app.services.document_catalog import build_placeholder_content
from app.services.pdf_stub import render_placeholder_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        doc_type=document.doc_type.value,
        content=document.content,
        pdf_url=document.pdf_url,
        version=document.version,
        created_at=document.created_at,
    )


def _get_owned_document(db: Session, organization_id, document_id) -> Document:
    document = (
        db.query(Document)
        .filter(Document.organization_id == organization_id, Document.id == document_id)
        .first()
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento non trovato"
        )
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    doc_type: str | None = None,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[DocumentOut]:
    """Storico completo dei documenti generati (tutte le versioni), dal più recente."""
    query = db.query(Document).filter(
        Document.organization_id == membership.organization.id
    )
    if doc_type is not None:
        if doc_type not in DocumentType._value2member_map_:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo documento non valido",
            )
        query = query.filter(Document.doc_type == DocumentType(doc_type))
    documents = query.order_by(Document.created_at.desc()).all()
    return [_to_out(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DocumentOut:
    document = _get_owned_document(db, membership.organization.id, document_id)
    return _to_out(document)


@router.post("/generate", response_model=DocumentOut)
def generate_document(
    payload: DocumentGenerateRequest,
    request: Request,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Genera una nuova versione del documento richiesto.

    In questa fase il contenuto è segnaposto strutturato (vedi `document_catalog`): il
    motore AI che scrive il contenuto vero arriva in Fase 5. Ogni chiamata crea una nuova
    versione, non sovrascrive le precedenti (stesso principio degli assessment)."""
    if payload.doc_type not in DocumentType._value2member_map_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo documento non valido",
        )
    doc_type = DocumentType(payload.doc_type)

    last_version = (
        db.query(Document)
        .filter(
            Document.organization_id == membership.organization.id,
            Document.doc_type == doc_type,
        )
        .order_by(Document.version.desc())
        .first()
    )
    next_version = (last_version.version + 1) if last_version else 1

    document = Document(
        organization_id=membership.organization.id,
        doc_type=doc_type,
        content=build_placeholder_content(doc_type),
        version=next_version,
        created_by=membership.user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    record_audit_event(
        db,
        action="document.generated",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="document",
        details={"doc_type": doc_type.value, "version": next_version},
        ip_address=request.client.host if request.client else None,
    )
    return _to_out(document)


@router.put("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Modifica manuale del contenuto della versione esistente (correzioni), senza
    creare una nuova versione: la nuova versione si crea solo rigenerando."""
    document = _get_owned_document(db, membership.organization.id, document_id)
    document.content = payload.content
    db.add(document)
    db.commit()
    db.refresh(document)

    record_audit_event(
        db,
        action="document.updated",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="document",
        details={"document_id": str(document.id)},
        ip_address=request.client.host if request.client else None,
    )
    return _to_out(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    document = _get_owned_document(db, membership.organization.id, document_id)
    db.delete(document)
    db.commit()

    record_audit_event(
        db,
        action="document.deleted",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="document",
        details={"document_id": str(document_id)},
        ip_address=request.client.host if request.client else None,
    )


@router.post("/{document_id}/pdf", response_model=DocumentOut)
def generate_pdf(
    document_id: str,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Genera un PDF reale (non simulato) a partire dal contenuto attuale del documento e
    lo salva su storage locale, in attesa dell'integrazione con Supabase Storage (Fase
    5/6). L'impaginazione è minimale: verrà sostituita da un motore di rendering più
    ricco quando arriverà il contenuto vero generato dall'AI."""
    document = _get_owned_document(db, membership.organization.id, document_id)

    pdf_bytes = render_placeholder_pdf(
        title=document.doc_type.value.replace("_", " ").title(),
        sections=document.content.get("sezioni", []),
    )

    settings = get_settings()
    org_dir = (
        settings.local_storage_path / "documents" / str(membership.organization.id)
    )
    org_dir.mkdir(parents=True, exist_ok=True)
    file_path = org_dir / f"{document.id}_v{document.version}.pdf"
    file_path.write_bytes(pdf_bytes)

    document.pdf_url = (
        f"local://documents/{membership.organization.id}/{file_path.name}"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _to_out(document)


@router.get("/{document_id}/pdf")
def download_pdf(
    document_id: str,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Scarica i byte reali del PDF già generato (POST .../pdf crea/rigenera il file,
    questo endpoint lo restituisce). Separato dalla generazione così il frontend può
    offrire un link di download diretto senza rigenerare il PDF ad ogni click."""
    document = _get_owned_document(db, membership.organization.id, document_id)
    if not document.pdf_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF non ancora generato per questo documento: chiama prima "
            "POST /documents/{id}/pdf",
        )

    settings = get_settings()
    relative_path = document.pdf_url.removeprefix("local://")
    file_path = settings.local_storage_path / relative_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File PDF non trovato su disco: rigeneralo con POST /documents/{id}/pdf",
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{document.doc_type.value}_v{document.version}.pdf",
    )
