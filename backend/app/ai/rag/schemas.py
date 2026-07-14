from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class ChunkMetadata(BaseModel):
    document_id: UUID
    page_number: Optional[int] = None
    char_offset: Optional[int] = None

class DocumentChunk(BaseModel):
    chunk_id: UUID
    content: str
    metadata: ChunkMetadata
    similarity_score: Optional[float] = None
