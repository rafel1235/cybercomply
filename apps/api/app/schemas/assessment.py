import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AssessmentAnswers(BaseModel):
    """Risposte strutturate del questionario di assessment (Guida al Servizio, Modulo 1)."""

    sector_annex: Literal["allegato_i", "allegato_ii", "nessuno"]
    employee_count: int = Field(ge=0)
    annual_revenue_eur: int = Field(ge=0)
    supplies_ict_to_regulated_entities: bool = False
    produces_digital_product_for_eu_market: bool = False


class AssessmentCreateRequest(BaseModel):
    answers: AssessmentAnswers


class AssessmentResultOut(BaseModel):
    id: uuid.UUID
    nis2_category: str
    cra_in_scope: bool
    answers: dict
    rationale: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
