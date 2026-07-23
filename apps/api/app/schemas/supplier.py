import uuid
from datetime import datetime

from pydantic import BaseModel


class SupplierCreateRequest(BaseModel):
    name: str
    category: str | None = None
    criticality: str = "media"


class SupplierUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    criticality: str | None = None
    status: str | None = None


class SupplierQuestionnaireOut(BaseModel):
    id: uuid.UUID
    answers: dict
    computed_status: str
    access_token: str
    sent_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None = None
    criticality: str
    status: str
    last_reviewed_at: datetime | None = None
    created_at: datetime
    questionnaires: list[SupplierQuestionnaireOut] = []

    class Config:
        from_attributes = True


class QuestionnairePublicOut(BaseModel):
    """Vista pubblica del questionario: niente riferimenti interni all'organizzazione o
    all'utente, solo ciò che serve al fornitore per compilare."""

    supplier_name: str
    questions: list[str]
    answers: dict
    completed_at: datetime | None = None


class QuestionnaireSubmitRequest(BaseModel):
    answers: dict
