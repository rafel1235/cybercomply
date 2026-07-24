from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentMembership,
    get_current_entitlements,
    get_current_membership,
    get_db,
    require_admin,
)
from app.models.assessment import AssessmentResult
from app.models.document import Document, DocumentType
from app.schemas.document import (
    DocumentGenerateRequest,
    DocumentOut,
    DocumentUpdateRequest,
)
from app.services import pdf_storage
from app.services.ai_document_generator import generate_document_content
from app.services.audit import record_audit_event
from app.services.entitlements import PlanEntitlements
from app.services.pdf_renderer import render_document_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


def _documents_generated_this_month(db: Session, organization_id) -> int:
    """Conta le generazioni del mese solare corrente: nessun contatore dedicato da
    azzerare a fine mese, si ricalcola sempre dai record esistenti (stesso approccio già
    usato per lo storico compliance e le scadenze incidenti)."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(Document)
        .filter(
            Document.organization_id == organization_id,
            Document.created_at >= month_start,
        )
        .count()
    )


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
    entitlements: PlanEntitlements = Depends(get_current_entitlements),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Genera una nuova versione del documento richiesto.

    Il contenuto è scritto dall'API Claude quando `ANTHROPIC_API_KEY` è configurata (Fase
    5); altrimenti (o se la chiamata AI fallisce) ricade sul contenuto segnaposto
    strutturato di `document_catalog`, così l'endpoint non fallisce mai per un problema
    lato AI. Ogni chiamata crea una nuova versione, non sovrascrive le precedenti (stesso
    principio degli assessment).

    Fase 6: la quota mensile di documenti generabili dipende dal piano (0 per Free, 5 per
    Essential, illimitata per Business/Enterprise — vedi `entitlements.py`)."""
    if entitlements.max_ai_documents_per_month is not None:
        generated_this_month = _documents_generated_this_month(
            db, membership.organization.id
        )
        if generated_this_month >= entitlements.max_ai_documents_per_month:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Hai raggiunto il limite di "
                    f"{entitlements.max_ai_documents_per_month} documenti generabili questo "
                    "mese con il tuo piano attuale. Passa a un piano superiore per "
                    "generarne altri."
                ),
            )

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

    latest_assessment = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.organization_id == membership.organization.id)
        .order_by(AssessmentResult.created_at.desc())
        .first()
    )
    context = {}
    if latest_assessment is not None:
        context["nis2_category"] = latest_assessment.nis2_category.value
        context["cra_in_scope"] = latest_assessment.cra_in_scope

    content, ai_meta = generate_document_content(
        doc_type, membership.organization, context
    )

    document = Document(
        organization_id=membership.organization.id,
        doc_type=doc_type,
        content=content,
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
        details={"doc_type": doc_type.value, "version": next_version, **ai_meta},
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
    lo salva su Supabase Storage se configurato, altrimenti su disco locale (Fase 9:
    vedi app/services/pdf_storage.py — su un host con filesystem effimero il solo disco
    locale non è persistente tra un deploy e l'altro)."""
    document = _get_owned_document(db, membership.organization.id, document_id)

    pdf_bytes = render_document_pdf(
        title=document.doc_type.value.replace("_", " ").title(),
        organization_name=membership.organization.name,
        sections=document.content.get("sezioni", []),
        version=document.version,
        generated_at=document.created_at,
        ai_generated=document.content.get("generato_da") == "ai",
    )

    filename = f"{document.id}_v{document.version}.pdf"
    document.pdf_url = pdf_storage.save_pdf(
        organization_id=membership.organization.id,
        filename=filename,
        pdf_bytes=pdf_bytes,
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
) -> Response:
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

    pdf_bytes = pdf_storage.load_pdf(document.pdf_url)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File PDF non trovato: rigeneralo con POST /documents/{id}/pdf",
        )

    filename = f"{document.doc_type.value}_v{document.version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
