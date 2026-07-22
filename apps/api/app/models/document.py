import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class DocumentType(str, enum.Enum):
    """I 9 documenti generabili dalla piattaforma (Guida al Servizio, §4.3)."""

    registro_rischi = "registro_rischi"
    procedura_incident_response = "procedura_incident_response"
    piano_bcp = "piano_bcp"
    politica_supply_chain = "politica_supply_chain"
    politica_crittografia = "politica_crittografia"
    politica_controllo_accessi = "politica_controllo_accessi"
    procedura_vulnerability_disclosure = "procedura_vulnerability_disclosure"
    piano_formazione = "piano_formazione"
    registro_asset_critici = "registro_asset_critici"


class Document(Base):
    """Documento generato (Fase 5: dal contenuto strutturato in `content` si genera il PDF
    on-demand, salvato poi su storage e referenziato da `pdf_url`)."""

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_org_created", "organization_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="document_type"))
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    created_by_user: Mapped["User | None"] = relationship()
