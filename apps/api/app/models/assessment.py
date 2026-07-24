import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class Nis2Category(str, enum.Enum):
    """Esito del modulo 1 — Assessment automatico (Guida al Servizio, §4.2)."""

    essenziale = "essenziale"
    importante = "importante"
    non_in_perimetro = "non_in_perimetro"


class AssessmentResult(Base):
    """Risultato di una esecuzione dell'assessment NIS2 + CRA.

    Ogni nuova esecuzione crea una nuova riga (non sovrascrive la precedente): la roadmap
    richiede esplicitamente di conservare lo storico ("Permettere di rifare l'assessment,
    crea nuova versione, non sovrascrive" — Fase 4). L'ultimo risultato per organizzazione è
    quello con `created_at` più recente.
    """

    __tablename__ = "assessment_results"
    __table_args__ = (
        Index("ix_assessment_results_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    nis2_category: Mapped[Nis2Category] = mapped_column(
        Enum(Nis2Category, name="nis2_category")
    )
    cra_in_scope: Mapped[bool] = mapped_column(Boolean, default=False)
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="assessment_results"
    )
    created_by_user: Mapped["User | None"] = relationship()
