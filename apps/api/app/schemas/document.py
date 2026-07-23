import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentGenerateRequest(BaseModel):
    doc_type: str


class DocumentUpdateRequest(BaseModel):
    """Modifica manuale del contenuto (correzioni prima o dopo la generazione AI)."""

    content: dict


class DocumentOut(BaseModel):
    id: uuid.UUID
    doc_type: str
    content: dict
    pdf_url: str | None = None
    version: int
    created_at: datetime

    class Config:
        from_attributes = True
