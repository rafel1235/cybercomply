from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import extract
from sqlalchemy.orm import Session, selectinload

from app.api.deps import (
    CurrentMembership,
    get_current_membership,
    get_db,
    require_incident_reporting,
)
from app.core.pagination import DEFAULT_LIMIT, apply_pagination
from app.models.incident import (
    Incident,
    IncidentNotification,
    IncidentStatus,
    NotificationPhase,
)
from app.schemas.incident import (
    IncidentCreateRequest,
    IncidentNotificationCreateRequest,
    IncidentNotificationOut,
    IncidentOut,
    IncidentUpdateRequest,
)
from app.services.audit import record_audit_event
from app.services.incident_deadlines import compute_deadlines

# Fase 6: l'intero modulo Incident Reporting è riservato ai piani Essential e superiori
# (vedi entitlements.py). La dipendenza a livello di router applica il controllo a ogni
# endpoint sotto /incidents senza doverlo ripetere in ciascuna funzione.
router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_incident_reporting)],
)


def _to_out(incident: Incident) -> IncidentOut:
    deadlines = compute_deadlines(incident.opened_at, incident.notifications)
    return IncidentOut(
        id=incident.id,
        reference_code=incident.reference_code,
        incident_type=incident.incident_type,
        status=incident.status.value,
        opened_at=incident.opened_at,
        closed_at=incident.closed_at,
        data=incident.data,
        notifications=[
            IncidentNotificationOut.model_validate(n) for n in incident.notifications
        ],
        deadlines=[
            {
                "phase": d.phase.value,
                "due_at": d.due_at,
                "sent": d.sent,
                "sent_at": d.sent_at,
                "overdue": d.overdue,
            }
            for d in deadlines
        ],
    )


def _get_owned_incident(db: Session, organization_id, incident_id) -> Incident:
    incident = (
        db.query(Incident)
        .filter(Incident.organization_id == organization_id, Incident.id == incident_id)
        .first()
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incidente non trovato"
        )
    return incident


def _next_reference_code(db: Session, organization_id) -> str:
    year = datetime.now(timezone.utc).year
    count_this_year = (
        db.query(Incident)
        .filter(
            Incident.organization_id == organization_id,
            extract("year", Incident.opened_at) == year,
        )
        .count()
    )
    return f"INC-{year}-{count_this_year + 1:03d}"


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    response: Response,
    status_filter: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[IncidentOut]:
    """Paginato (Fase 10 — performance): `limit`/`offset` mai illimitati, conteggio totale
    nell'header `X-Total-Count`. `selectinload` sulle notifiche evita un bug reale di
    query N+1 scoperto in questa fase: senza, `_to_out` (che legge `incident.notifications`
    per calcolare le scadenze) eseguiva una query separata per ogni incidente della
    pagina — fino a `limit` query aggiuntive per una singola richiesta."""
    query = (
        db.query(Incident)
        .options(selectinload(Incident.notifications))
        .filter(Incident.organization_id == membership.organization.id)
    )
    if status_filter is not None:
        if status_filter not in IncidentStatus._value2member_map_:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stato non valido",
            )
        query = query.filter(Incident.status == IncidentStatus(status_filter))
    query = query.order_by(Incident.opened_at.desc())
    query = apply_pagination(query, response, limit=limit, offset=offset)
    incidents = query.all()
    return [_to_out(i) for i in incidents]


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: str,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = _get_owned_incident(db, membership.organization.id, incident_id)
    return _to_out(incident)


@router.post("", response_model=IncidentOut)
def create_incident(
    payload: IncidentCreateRequest,
    request: Request,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = Incident(
        organization_id=membership.organization.id,
        reference_code=_next_reference_code(db, membership.organization.id),
        incident_type=payload.incident_type,
        data=payload.data,
        created_by=membership.user.id,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    record_audit_event(
        db,
        action="incident.created",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="incident",
        details={
            "reference_code": incident.reference_code,
            "incident_type": payload.incident_type,
        },
        ip_address=request.client.host if request.client else None,
    )
    return _to_out(incident)


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: str,
    payload: IncidentUpdateRequest,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = _get_owned_incident(db, membership.organization.id, incident_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(incident, field, value)
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return _to_out(incident)


@router.post("/{incident_id}/close", response_model=IncidentOut)
def close_incident(
    incident_id: str,
    request: Request,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = _get_owned_incident(db, membership.organization.id, incident_id)
    if incident.status == IncidentStatus.chiuso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incidente già chiuso"
        )

    incident.status = IncidentStatus.chiuso
    incident.closed_at = datetime.now(timezone.utc)
    db.add(incident)
    db.commit()
    db.refresh(incident)

    record_audit_event(
        db,
        action="incident.closed",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="incident",
        details={"reference_code": incident.reference_code},
        ip_address=request.client.host if request.client else None,
    )
    return _to_out(incident)


@router.post("/{incident_id}/notifications", response_model=IncidentOut)
def record_notification(
    incident_id: str,
    payload: IncidentNotificationCreateRequest,
    request: Request,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> IncidentOut:
    """Registra l'invio di una notifica di una delle fasi NIS2/CRA. Al massimo una
    notifica per fase per incidente: se la fase è già stata inviata, l'operazione è
    rifiutata invece di creare un duplicato silenzioso."""
    incident = _get_owned_incident(db, membership.organization.id, incident_id)

    if payload.phase not in NotificationPhase._value2member_map_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fase non valida"
        )
    phase = NotificationPhase(payload.phase)

    already_sent = any(n.phase == phase for n in incident.notifications)
    if already_sent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Notifica per la fase '{phase.value}' già registrata per questo incidente",
        )

    notification = IncidentNotification(
        incident_id=incident.id,
        phase=phase,
        recipient=payload.recipient,
        content=payload.content,
    )
    db.add(notification)
    db.commit()

    record_audit_event(
        db,
        action="incident.notification_recorded",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="incident_notification",
        details={"reference_code": incident.reference_code, "phase": phase.value},
        ip_address=request.client.host if request.client else None,
    )

    db.refresh(incident)
    return _to_out(incident)
