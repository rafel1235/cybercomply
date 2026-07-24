import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class MeasureStatus(str, enum.Enum):
    """Stato di una misura del Compliance Tracker (Fase 4: 'conformi/parziali/non
    conformi/N/D')."""

    conforme = "conforme"
    parziale = "parziale"
    non_conforme = "non_conforme"
    non_applicabile = "non_applicabile"


class ComplianceMeasure(Base):
    """Stato di una delle 15 misure tecniche/organizzative della Det. ACN 164179/2025 per una
    specifica organizzazione.

    `measure_id` è uno slug stabile definito lato applicazione (es. "mfa_accessi_remoti",
    "backup_cifrati") che identifica la misura nel catalogo statico delle 15 misure — il
    catalogo stesso non ha bisogno di una tabella perché non varia per organizzazione, ma è
    versionato nel codice applicativo (Fase 3/4).
    """

    __tablename__ = "compliance_measures"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "measure_id", name="uq_compliance_measure_per_org"
        ),
        Index("ix_compliance_measures_org_updated", "organization_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    measure_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[MeasureStatus] = mapped_column(
        Enum(MeasureStatus, name="measure_status"),
        default=MeasureStatus.non_applicabile,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="compliance_measures"
    )
    updated_by_user: Mapped["User | None"] = relationship()
