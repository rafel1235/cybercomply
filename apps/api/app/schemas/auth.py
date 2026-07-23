import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    vat_number: str | None = None
    sector: str | None = None
    employee_count: int | None = None
    annual_revenue_eur: float | None = None

    class Config:
        from_attributes = True


class SyncUserRequest(BaseModel):
    """Payload inviato dal frontend subito dopo login/registrazione riuscita su Supabase,
    per creare (o aggiornare) lo specchio locale dell'utente e, alla prima registrazione,
    l'organizzazione associata."""

    full_name: str | None = None
    organization_name: str | None = None


class MeResponse(BaseModel):
    user: UserOut
    organizations: list[OrganizationOut]
