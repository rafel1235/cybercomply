from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentMembership,
    get_current_entitlements,
    get_current_membership,
    get_db,
    require_admin,
)
from app.models.audit_log import AuditLog
from app.models.compliance import ComplianceMeasure, MeasureStatus
from app.schemas.compliance import (
    ComplianceHistoryPoint,
    ComplianceMeasureOut,
    ComplianceMeasureUpdateRequest,
    ComplianceScoreOut,
)
from app.services.audit import record_audit_event
from app.services.compliance_catalog import COMPLIANCE_MEASURE_CATALOG
from app.services.entitlements import PlanEntitlements

router = APIRouter(prefix="/compliance", tags=["compliance"])

_CATALOG_BY_ID = {m.measure_id: m for m in COMPLIANCE_MEASURE_CATALOG}

_SCORE_WEIGHTS = {
    MeasureStatus.conforme: 1.0,
    MeasureStatus.parziale: 0.5,
    MeasureStatus.non_conforme: 0.0,
}


def _ensure_catalog_provisioned(
    db: Session, organization_id
) -> list[ComplianceMeasure]:
    """Crea le righe mancanti del catalogo per l'organizzazione (stato iniziale
    'non_applicabile'), così il tracker mostra sempre tutte le 15 misure anche per le
    organizzazioni appena create."""
    existing = (
        db.query(ComplianceMeasure)
        .filter(ComplianceMeasure.organization_id == organization_id)
        .all()
    )
    existing_ids = {m.measure_id for m in existing}
    missing_ids = [mid for mid in _CATALOG_BY_ID if mid not in existing_ids]

    for measure_id in missing_ids:
        db.add(
            ComplianceMeasure(
                organization_id=organization_id,
                measure_id=measure_id,
                status=MeasureStatus.non_applicabile,
            )
        )
    if missing_ids:
        db.commit()
        existing = (
            db.query(ComplianceMeasure)
            .filter(ComplianceMeasure.organization_id == organization_id)
            .all()
        )
    return existing


def _to_out(measure: ComplianceMeasure) -> ComplianceMeasureOut:
    definition = _CATALOG_BY_ID.get(measure.measure_id)
    return ComplianceMeasureOut(
        id=measure.id,
        measure_id=measure.measure_id,
        label=definition.label if definition else measure.measure_id,
        normative_reference=definition.normative_reference if definition else "",
        status=measure.status.value,
        note=measure.note,
        updated_at=measure.updated_at,
    )


def _compute_score(measures: list[ComplianceMeasure]) -> ComplianceScoreOut:
    counters = {status: 0 for status in MeasureStatus}
    for m in measures:
        counters[m.status] += 1

    scored_measures = [m for m in measures if m.status != MeasureStatus.non_applicabile]
    if scored_measures:
        total_points = sum(_SCORE_WEIGHTS[m.status] for m in scored_measures)
        score_percent = round((total_points / len(scored_measures)) * 100, 1)
    else:
        score_percent = 0.0

    return ComplianceScoreOut(
        score_percent=score_percent,
        measures_conformi=counters[MeasureStatus.conforme],
        measures_parziali=counters[MeasureStatus.parziale],
        measures_non_conformi=counters[MeasureStatus.non_conforme],
        measures_non_applicabili=counters[MeasureStatus.non_applicabile],
        measures_total=len(measures),
    )


@router.get("/measures", response_model=list[ComplianceMeasureOut])
def list_measures(
    membership: CurrentMembership = Depends(get_current_membership),
    entitlements: PlanEntitlements = Depends(get_current_entitlements),
    db: Session = Depends(get_db),
) -> list[ComplianceMeasureOut]:
    """Fase 6: il piano Free vede solo le prime N misure del catalogo (in sola lettura,
    imposto lato PATCH — qui basta restituirne meno), come "assaggio" del tracker completo.
    """
    measures = _ensure_catalog_provisioned(db, membership.organization.id)
    # L'ordine per measure_id è quello storico (Fase 3): qui si ordina invece secondo
    # l'ordine del catalogo, così "le prime N" corrisponde a un elenco scelto
    # deliberatamente (vedi entitlements.py) e non all'ordine alfabetico degli id.
    catalog_order = {mid: i for i, mid in enumerate(_CATALOG_BY_ID)}
    ordered = sorted(
        measures, key=lambda m: catalog_order.get(m.measure_id, len(catalog_order))
    )
    if entitlements.compliance_measures_limit is not None:
        ordered = ordered[: entitlements.compliance_measures_limit]
    return [_to_out(m) for m in ordered]


@router.patch("/measures/{measure_id}", response_model=ComplianceMeasureOut)
def update_measure(
    measure_id: str,
    payload: ComplianceMeasureUpdateRequest,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    entitlements: PlanEntitlements = Depends(get_current_entitlements),
    db: Session = Depends(get_db),
) -> ComplianceMeasureOut:
    if not entitlements.compliance_measures_editable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Il Compliance Tracker è in sola lettura nel piano Free. Passa a "
            "Essential o superiore per aggiornare lo stato delle misure.",
        )
    if payload.status not in MeasureStatus._value2member_map_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Stato non valido"
        )

    measure = (
        db.query(ComplianceMeasure)
        .filter(
            ComplianceMeasure.organization_id == membership.organization.id,
            ComplianceMeasure.measure_id == measure_id,
        )
        .first()
    )
    if measure is None:
        if measure_id not in _CATALOG_BY_ID:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Misura non trovata nel catalogo",
            )
        measure = ComplianceMeasure(
            organization_id=membership.organization.id, measure_id=measure_id
        )
        db.add(measure)

    measure.status = MeasureStatus(payload.status)
    measure.note = payload.note
    measure.updated_by = membership.user.id
    db.commit()
    db.refresh(measure)

    all_measures = _ensure_catalog_provisioned(db, membership.organization.id)
    score = _compute_score(all_measures)

    record_audit_event(
        db,
        action="compliance.measure_updated",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="compliance_measure",
        details={"measure_id": measure_id, "status": measure.status.value},
        ip_address=request.client.host if request.client else None,
    )
    # Snapshot dello score ad ogni modifica: non esiste una tabella storica dedicata
    # (schema Fase 2), quindi lo storico del punteggio viene ricostruito onestamente a
    # partire da questi eventi di audit, invece di essere inventato o calcolato solo "ora".
    record_audit_event(
        db,
        action="compliance.score_snapshot",
        organization_id=membership.organization.id,
        entity="compliance_score",
        details={"score_percent": score.score_percent},
    )

    return _to_out(measure)


@router.get("/score", response_model=ComplianceScoreOut)
def get_score(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> ComplianceScoreOut:
    measures = _ensure_catalog_provisioned(db, membership.organization.id)
    return _compute_score(measures)


@router.get("/history", response_model=list[ComplianceHistoryPoint])
def get_history(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[ComplianceHistoryPoint]:
    """Storico del punteggio di compliance, ricostruito dagli eventi di audit
    'compliance.score_snapshot' registrati ad ogni aggiornamento di misura."""
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.organization_id == membership.organization.id,
            AuditLog.action == "compliance.score_snapshot",
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    return [
        ComplianceHistoryPoint(
            recorded_at=e.created_at, score_percent=e.details.get("score_percent", 0.0)
        )
        for e in events
    ]
