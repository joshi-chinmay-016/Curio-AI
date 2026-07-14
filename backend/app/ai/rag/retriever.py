from typing import List
from uuid import UUID
from backend.app.ai.rag.schemas import DocumentChunk

class DocumentRetriever:
    """
    Stub for PGVector retrieval pipeline.
    This will be fully implemented by Vishal during backend development.
    """
    def retrieve_relevant_chunks(self, document_id: UUID, query: str, limit: int = 3) -> List[DocumentChunk]:
        # Return an empty stub list.
        return []
