import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.auth import OrganizationOut

__all__ = ["OrganizationOut"]


class OrganizationUpdateRequest(BaseModel):
    """Tutti i campi opzionali: si aggiorna solo ciò che viene inviato (PATCH-like PUT)."""

    name: str | None = None
    vat_number: str | None = None
    sector: str | None = None
    employee_count: int | None = None
    annual_revenue_eur: float | None = None


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class InviteMemberResponse(BaseModel):
    invited_email: EmailStr
    invite_token: str
    expires_at: datetime


class InvitePublicOut(BaseModel):
    """Anteprima pubblica di un invito (nessuna autenticazione: il possesso del token,
    ricevuto via email, è di per sé la credenziale), mostrata dalla pagina di
    registrazione prima di creare l'account."""

    organization_name: str
    invited_email: EmailStr
    role: str
    valid: bool
    reason: str | None = None
