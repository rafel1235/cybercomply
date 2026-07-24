import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentMembership,
    get_current_membership,
    get_db,
    require_admin,
    require_supply_chain,
)
from app.models.supplier import (
    Supplier,
    SupplierCriticality,
    SupplierQuestionnaire,
    SupplierStatus,
)
from app.schemas.supplier import (
    SupplierCreateRequest,
    SupplierOut,
    SupplierQuestionnaireOut,
    SupplierUpdateRequest,
)
from app.services.audit import record_audit_event

# Fase 6: il modulo Supply Chain Risk è riservato ai piani Business/Enterprise (vedi
# entitlements.py). Il link pubblico del questionario (public_questionnaires.py) resta
# volutamente fuori da questo router e non gated: un fornitore che ha già ricevuto un
# link deve poterlo compilare anche se l'organizzazione cambia piano nel frattempo.
router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(require_supply_chain)],
)


def _to_out(supplier: Supplier) -> SupplierOut:
    return SupplierOut(
        id=supplier.id,
        name=supplier.name,
        category=supplier.category,
        criticality=supplier.criticality.value,
        status=supplier.status.value,
        last_reviewed_at=supplier.last_reviewed_at,
        created_at=supplier.created_at,
        questionnaires=[
            SupplierQuestionnaireOut.model_validate(q) for q in supplier.questionnaires
        ],
    )


def _get_owned_supplier(db: Session, organization_id, supplier_id) -> Supplier:
    supplier = (
        db.query(Supplier)
        .filter(Supplier.organization_id == organization_id, Supplier.id == supplier_id)
        .first()
    )
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fornitore non trovato"
        )
    return supplier


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[SupplierOut]:
    suppliers = (
        db.query(Supplier)
        .filter(Supplier.organization_id == membership.organization.id)
        .order_by(Supplier.created_at.desc())
        .all()
    )
    return [_to_out(s) for s in suppliers]


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: str,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> SupplierOut:
    supplier = _get_owned_supplier(db, membership.organization.id, supplier_id)
    return _to_out(supplier)


@router.post("", response_model=SupplierOut)
def create_supplier(
    payload: SupplierCreateRequest,
    request: Request,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> SupplierOut:
    if payload.criticality not in SupplierCriticality._value2member_map_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Criticità non valida",
        )

    supplier = Supplier(
        organization_id=membership.organization.id,
        name=payload.name,
        category=payload.category,
        criticality=SupplierCriticality(payload.criticality),
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    record_audit_event(
        db,
        action="supplier.created",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="supplier",
        details={"name": payload.name},
        ip_address=request.client.host if request.client else None,
    )
    return _to_out(supplier)


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: str,
    payload: SupplierUpdateRequest,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> SupplierOut:
    supplier = _get_owned_supplier(db, membership.organization.id, supplier_id)
    updates = payload.model_dump(exclude_unset=True)

    if "criticality" in updates:
        if updates["criticality"] not in SupplierCriticality._value2member_map_:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Criticità non valida",
            )
        updates["criticality"] = SupplierCriticality(updates["criticality"])
    if "status" in updates:
        if updates["status"] not in SupplierStatus._value2member_map_:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stato non valido",
            )
        updates["status"] = SupplierStatus(updates["status"])
        updates["last_reviewed_at"] = datetime.now(timezone.utc)

    for field, value in updates.items():
        setattr(supplier, field, value)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _to_out(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: str,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    supplier = _get_owned_supplier(db, membership.organization.id, supplier_id)
    db.delete(supplier)
    db.commit()

    record_audit_event(
        db,
        action="supplier.deleted",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="supplier",
        details={"supplier_id": str(supplier_id)},
        ip_address=request.client.host if request.client else None,
    )


@router.post("/{supplier_id}/questionnaires", response_model=SupplierQuestionnaireOut)
def create_questionnaire(
    supplier_id: str,
    request: Request,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> SupplierQuestionnaireOut:
    """Crea un nuovo questionario con un access_token univoco, pronto per essere inviato al
    fornitore via link pubblico (compilazione senza account, endpoint pubblico separato).
    """
    supplier = _get_owned_supplier(db, membership.organization.id, supplier_id)

    questionnaire = SupplierQuestionnaire(
        supplier_id=supplier.id,
        access_token=secrets.token_urlsafe(32),
        sent_at=datetime.now(timezone.utc),
    )
    db.add(questionnaire)
    db.commit()
    db.refresh(questionnaire)

    record_audit_event(
        db,
        action="supplier.questionnaire_sent",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="supplier_questionnaire",
        details={"supplier_id": str(supplier.id)},
        ip_address=request.client.host if request.client else None,
    )
    return SupplierQuestionnaireOut.model_validate(questionnaire)


@router.get(
    "/{supplier_id}/questionnaires", response_model=list[SupplierQuestionnaireOut]
)
def list_questionnaires(
    supplier_id: str,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[SupplierQuestionnaireOut]:
    supplier = _get_owned_supplier(db, membership.organization.id, supplier_id)
    return [SupplierQuestionnaireOut.model_validate(q) for q in supplier.questionnaires]
