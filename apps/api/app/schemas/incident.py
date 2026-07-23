import uuid
from datetime import datetime

from pydantic import BaseModel


class IncidentCreateRequest(BaseModel):
    incident_type: str
    data: dict = {}


class IncidentUpdateRequest(BaseModel):
    incident_type: str | None = None
    data: dict | None = None


class IncidentNotificationCreateRequest(BaseModel):
    phase: str
    recipient: str
    content: str | None = None


class IncidentNotificationOut(BaseModel):
    id: uuid.UUID
    phase: str
    sent_at: datetime
    recipient: str
    content: str | None = None

    class Config:
        from_attributes = True


class DeadlineStatusOut(BaseModel):
    phase: str
    due_at: datetime
    sent: bool
    sent_at: datetime | None = None
    overdue: bool


class IncidentOut(BaseModel):
    id: uuid.UUID
    reference_code: str
    incident_type: str
    status: str
    opened_at: datetime
    closed_at: datetime | None = None
    data: dict
    notifications: list[IncidentNotificationOut] = []
    deadlines: list[DeadlineStatusOut] = []

    class Config:
        from_attributes = True
