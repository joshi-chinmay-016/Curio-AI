from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    document_id: UUID
    filename: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True
