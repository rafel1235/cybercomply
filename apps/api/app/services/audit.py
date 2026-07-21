from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    *,
    action: str,
    user_id: UUID | None = None,
    organization_id: UUID | None = None,
    entity: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Inserisce un evento nell'audit log. Solo insert: l'audit log non va mai aggiornato
    né cancellato (requisito NIS2, vedi roadmap Fase 8)."""
    log = AuditLog(
        action=action,
        user_id=user_id,
        organization_id=organization_id,
        entity=entity,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
