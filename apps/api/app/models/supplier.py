import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class SupplierCriticality(str, enum.Enum):
    alta = "alta"
    media = "media"
    bassa = "bassa"


class SupplierStatus(str, enum.Enum):
    conforme = "conforme"
    parziale = "parziale"
    non_conforme = "non_conforme"
    non_valutato = "non_valutato"


class Supplier(Base):
    """Voce del registro fornitori ICT critici (Modulo 4 — Supply Chain Risk)."""

    __tablename__ = "suppliers"
    __table_args__ = (Index("ix_suppliers_org_status", "organization_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    criticality: Mapped[SupplierCriticality] = mapped_column(
        Enum(SupplierCriticality, name="supplier_criticality"),
        default=SupplierCriticality.media,
    )
    status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus, name="supplier_status"),
        default=SupplierStatus.non_valutato,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="suppliers")
    questionnaires: Mapped[list["SupplierQuestionnaire"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierQuestionnaire(Base):
    """Questionario di sicurezza inviato a un fornitore.

    Supporta la compilazione senza account (Fase 4: "mandare questionario via link, il
    fornitore compila senza account") tramite `access_token`: chi ha il link può leggere e
    aggiornare solo questa riga, senza autenticarsi come utente della piattaforma.
    """

    __tablename__ = "supplier_questionnaires"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), index=True
    )
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    computed_status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus, name="supplier_status"),
        default=SupplierStatus.non_valutato,
    )
    access_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="questionnaires")
