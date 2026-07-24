import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """Registro immutabile delle azioni rilevanti (solo insert, mai update/delete).

    Obbligatorio per NIS2: CyberComplyIT è essa stessa soggetta alla normativa che aiuta i
    clienti a rispettare (vedi roadmap, Fase 8).

    Fase 10 (performance): questa è di gran lunga la tabella con la crescita più rapida
    dell'intero schema (una riga per ogni azione rilevante), eppure fino a questa fase non
    aveva alcun indice oltre alla chiave primaria — nonostante sia interrogata ad ogni
    caricamento della dashboard (`GET /audit-log`) e dal grafico di andamento compliance
    (`GET /compliance/history`, filtrato anche per `action`). Analizzata con
    `EXPLAIN ANALYZE`: senza indice, entrambe le query degenerano in una scansione
    sequenziale dell'intera tabella quando cresce. Aggiunti due indici compositi mirati
    alle query reali, non uno generico su ogni colonna.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_org_created", "organization_id", "created_at"),
        Index(
            "ix_audit_logs_org_action_created",
            "organization_id",
            "action",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
