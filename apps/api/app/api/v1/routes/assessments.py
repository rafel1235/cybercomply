from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentMembership, get_current_membership, get_db
from app.core.pagination import DEFAULT_LIMIT, apply_pagination
from app.models.assessment import AssessmentResult
from app.schemas.assessment import AssessmentCreateRequest, AssessmentResultOut
from app.services.assessment_classifier import AssessmentAnswersData, classify

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _to_out(
    result: AssessmentResult, rationale: str | None = None
) -> AssessmentResultOut:
    if rationale is None:
        # Ricalcola la motivazione dalle risposte salvate, così anche i risultati storici
        # mostrano il perché della classificazione senza doverla denormalizzare in colonna.
        rationale = classify(AssessmentAnswersData(**result.answers)).rationale
    return AssessmentResultOut(
        id=result.id,
        nis2_category=result.nis2_category.value,
        cra_in_scope=result.cra_in_scope,
        answers=result.answers,
        rationale=rationale,
        created_at=result.created_at,
    )


@router.post("", response_model=AssessmentResultOut)
def create_assessment(
    payload: AssessmentCreateRequest,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> AssessmentResultOut:
    """Salva una nuova esecuzione dell'assessment. Non sovrascrive mai le precedenti: ogni
    chiamata crea una nuova riga (storico richiesto dalla roadmap, Fase 4)."""
    classification = classify(AssessmentAnswersData(**payload.answers.model_dump()))

    result = AssessmentResult(
        organization_id=membership.organization.id,
        nis2_category=classification.nis2_category,
        cra_in_scope=classification.cra_in_scope,
        answers=payload.answers.model_dump(),
        created_by=membership.user.id,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return _to_out(result, rationale=classification.rationale)


@router.get("/latest", response_model=AssessmentResultOut)
def get_latest_assessment(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> AssessmentResultOut:
    result = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.organization_id == membership.organization.id)
        .order_by(AssessmentResult.created_at.desc())
        .first()
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessun assessment ancora eseguito per questa organizzazione",
        )
    return _to_out(result)


@router.get("", response_model=list[AssessmentResultOut])
def list_assessments(
    response: Response,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[AssessmentResultOut]:
    """Storico degli assessment eseguiti, dal più recente al più vecchio. Paginato
    (Fase 10 — performance): `limit`/`offset` mai illimitati, conteggio totale
    nell'header `X-Total-Count`."""
    query = db.query(AssessmentResult).filter(
        AssessmentResult.organization_id == membership.organization.id
    )
    query = query.order_by(AssessmentResult.created_at.desc())
    query = apply_pagination(query, response, limit=limit, offset=offset)
    results = query.all()
    return [_to_out(r) for r in results]
