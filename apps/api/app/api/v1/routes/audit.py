from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentMembership, get_current_membership, get_db
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogEntryOut

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogEntryOut])
def list_audit_log(
    limit: int = 20,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[AuditLogEntryOut]:
    """Ultime azioni registrate per l'organizzazione, dalla più recente. `limit` è
    limitato a un massimo di 100 per evitare risposte troppo pesanti sulla dashboard."""
    capped_limit = max(1, min(limit, 100))
    entries = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == membership.organization.id)
        .order_by(AuditLog.created_at.desc())
        .limit(capped_limit)
        .all()
    )
    return [AuditLogEntryOut.model_validate(e) for e in entries]
