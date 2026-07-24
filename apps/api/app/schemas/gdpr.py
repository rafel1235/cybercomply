import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.assessment import AssessmentResultOut
from app.schemas.audit import AuditLogEntryOut
from app.schemas.compliance import ComplianceMeasureOut
from app.schemas.document import DocumentOut
from app.schemas.incident import IncidentOut
from app.schemas.organization import MemberOut
from app.schemas.supplier import SupplierOut


class GdprUserProfileOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    created_at: datetime


class GdprOrganizationExportOut(BaseModel):
    """Tutti i dati riconducibili a una singola organizzazione di cui l'utente è membro.

    L'export è organizzato per organizzazione (invece che come un'unica lista piatta)
    perché è così che il modello dati di CyberComplyIT è strutturato: quasi ogni tabella
    è scope-ata a `organization_id` (Fase 2), quindi è la struttura più fedele ai dati
    realmente posseduti."""

    id: uuid.UUID
    name: str
    vat_number: str | None = None
    sector: str | None = None
    employee_count: int | None = None
    annual_revenue_eur: float | None = None
    created_at: datetime
    my_role: str
    members: list[MemberOut]
    assessments: list[AssessmentResultOut]
    compliance_measures: list[ComplianceMeasureOut]
    documents: list[DocumentOut]
    incidents: list[IncidentOut]
    suppliers: list[SupplierOut]
    audit_log: list[AuditLogEntryOut]


class GdprExportOut(BaseModel):
    """Risposta di GET /gdpr/export (GDPR Art. 20 — diritto alla portabilità dei dati)."""

    exported_at: datetime
    profile: GdprUserProfileOut
    organizations: list[GdprOrganizationExportOut]


class GdprAccountDeletionOut(BaseModel):
    """Risposta di DELETE /gdpr/account (GDPR Art. 17 — diritto alla cancellazione)."""

    deleted_at: datetime
    organizations_deleted: list[str]
    organizations_left: list[str]
    auth_account_deleted: bool
