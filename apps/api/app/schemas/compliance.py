import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ComplianceMeasureOut(BaseModel):
    id: uuid.UUID
    measure_id: str
    label: str
    normative_reference: str
    status: str
    note: str | None = None
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceMeasureUpdateRequest(BaseModel):
    status: str
    note: str | None = None


class ComplianceScoreOut(BaseModel):
    score_percent: float = Field(ge=0, le=100)
    measures_conformi: int
    measures_parziali: int
    measures_non_conformi: int
    measures_non_applicabili: int
    measures_total: int


class ComplianceHistoryPoint(BaseModel):
    recorded_at: datetime
    score_percent: float
