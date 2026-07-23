import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogEntryOut(BaseModel):
    id: uuid.UUID
    action: str
    entity: str | None = None
    details: dict
    user_id: uuid.UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True
