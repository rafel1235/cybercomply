from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.supplier import Supplier, SupplierQuestionnaire
from app.schemas.supplier import (
    QuestionnairePublicOut,
    QuestionnaireSubmitRequest,
)
from app.services.supplier_scoring import (
    QUESTIONNAIRE_QUESTIONS,
    compute_supplier_status,
)

router = APIRouter(prefix="/public/questionnaires", tags=["public-questionnaires"])


def _get_questionnaire_by_token(db: Session, token: str) -> SupplierQuestionnaire:
    """Nessuna verifica di autenticazione: il possesso del token è di per sé la
    credenziale, come da design del modello (compilazione senza account)."""
    questionnaire = (
        db.query(SupplierQuestionnaire)
        .filter(SupplierQuestionnaire.access_token == token)
        .first()
    )
    if questionnaire is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Questionario non trovato"
        )
    return questionnaire


@router.get("/{token}", response_model=QuestionnairePublicOut)
def get_public_questionnaire(
    token: str, db: Session = Depends(get_db)
) -> QuestionnairePublicOut:
    questionnaire = _get_questionnaire_by_token(db, token)
    supplier = db.get(Supplier, questionnaire.supplier_id)
    return QuestionnairePublicOut(
        supplier_name=supplier.name if supplier else "",
        questions=QUESTIONNAIRE_QUESTIONS,
        answers=questionnaire.answers,
        completed_at=questionnaire.completed_at,
    )


@router.post("/{token}", response_model=QuestionnairePublicOut)
def submit_public_questionnaire(
    token: str, payload: QuestionnaireSubmitRequest, db: Session = Depends(get_db)
) -> QuestionnairePublicOut:
    """Il fornitore invia le risposte. Lo stato calcolato aggiorna sia il questionario
    sia il fornitore collegato, così il registro fornitori riflette sempre l'ultima
    valutazione ricevuta."""
    questionnaire = _get_questionnaire_by_token(db, token)
    computed_status = compute_supplier_status(payload.answers)

    questionnaire.answers = payload.answers
    questionnaire.computed_status = computed_status
    questionnaire.completed_at = datetime.now(timezone.utc)
    db.add(questionnaire)

    supplier = db.get(Supplier, questionnaire.supplier_id)
    if supplier is not None:
        supplier.status = computed_status
        supplier.last_reviewed_at = datetime.now(timezone.utc)
        db.add(supplier)

    db.commit()
    db.refresh(questionnaire)

    return QuestionnairePublicOut(
        supplier_name=supplier.name if supplier else "",
        questions=QUESTIONNAIRE_QUESTIONS,
        answers=questionnaire.answers,
        completed_at=questionnaire.completed_at,
    )
