from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    document_id: UUID
    filename: str
    file_size: int
    mime_type: str
    status: str
    page_count: Optional[int] = None
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
