import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class IncidentStatus(str, enum.Enum):
    aperto = "aperto"
    in_gestione = "in_gestione"
    chiuso = "chiuso"


class NotificationPhase(str, enum.Enum):
    """Le tre scadenze di notifica previste da NIS2 Art. 23 (Guida al Servizio, §2.3) più il
    canale CRA verso ENISA."""

    early_warning_24h = "early_warning_24h"
    notifica_72h = "notifica_72h"
    relazione_30gg = "relazione_30gg"
    cra_enisa_24h = "cra_enisa_24h"
    cra_enisa_72h = "cra_enisa_72h"


class Incident(Base):
    """Un incidente registrato nel Modulo 3 — Incident Reporting.

    `reference_code` è l'identificativo leggibile mostrato all'utente (es. "INC-2026-014"),
    generato lato applicazione (Fase 3): `id` resta la chiave tecnica UUID usata dalle altre
    tabelle e dalle API.
    """

    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_org_opened", "organization_id", "opened_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    reference_code: Mapped[str] = mapped_column(String(32), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"), default=IncidentStatus.aperto
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="incidents")
    created_by_user: Mapped["User | None"] = relationship()
    notifications: Mapped[list["IncidentNotification"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentNotification(Base):
    """Traccia dell'invio di una notifica (24h/72h/30gg) per un incidente: la roadmap la
    vuole persistita per poter mostrare lo stato delle scadenze nella UI (Fase 4)."""

    __tablename__ = "incident_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    phase: Mapped[NotificationPhase] = mapped_column(
        Enum(NotificationPhase, name="notification_phase")
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped["Incident"] = relationship(back_populates="notifications")
