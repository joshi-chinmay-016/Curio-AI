"""
Semantic retrieval service for document chunks.

Provides database-backed vector similarity search using pgvector.
Retrieves relevant document chunks for an authenticated user's query.
"""
from dataclasses import dataclass
from typing import List, Optional
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentChunk
from backend.app.embeddings import create_embedding_service
from backend.app.repositories.document_chunk_repository import DocumentChunkRepository

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved document chunk with similarity score."""
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    start_char: Optional[int]
    end_char: Optional[int]
    chunk_metadata: Optional[dict]
    similarity_score: float  # Cosine similarity (0 to 1, higher = more similar)


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    chunks: List[RetrievedChunk]
    query_text: str
    top_k: int
    total_matches: int


class RetrievalError(Exception):
    """Raised when retrieval fails."""
    def __init__(self, message: str, details: str = None, retryable: bool = False):
        self.message = message
        self.details = details
        self.retryable = retryable
        super().__init__(message)


class RetrievalService:
    """
    Service for semantic retrieval of document chunks.
    
    Features:
    - Generates query embedding using existing EmbeddingService
    - Performs database-side vector similarity search using pgvector
    - Enforces document ownership and optional document filtering
    - Returns ranked results with similarity scores
    
    Does NOT perform:
    - Embedding generation (delegates to EmbeddingService)
    - Chunking or document extraction
    - AI reasoning or RAG context assembly
    """

    def __init__(
        self,
        embedding_service: Optional[object] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ):
        """
        Initialize retrieval service.
        
        Args:
            embedding_service: EmbeddingService instance (created from settings if None)
            top_k: Default number of results to return
            similarity_threshold: Minimum cosine similarity (0-1) for results
        """
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold
        self._embedding_service = embedding_service or create_embedding_service()
        self._repo = DocumentChunkRepository()

    def retrieve(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        query: str,
        top_k: Optional[int] = None,
        document_ids: Optional[List[UUID]] = None,
        similarity_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            db: Database session
            user_id: Authenticated user ID (ownership enforced)
            query: Query text to search for
            top_k: Override default top-k (max results)
            document_ids: Optional list of document IDs to restrict search
            similarity_threshold: Override default minimum similarity
            
        Returns:
            RetrievalResult with ranked chunks and similarity scores
            
        Raises:
            RetrievalError: If retrieval fails
        """
        if not query or not query.strip():
            return RetrievalResult(
                chunks=[],
                query_text=query,
                top_k=top_k or self._top_k,
                total_matches=0,
            )
        
        k = top_k or self._top_k
        if k <= 0:
            raise RetrievalError("top_k must be positive", f"top_k={k}")
        
        threshold = similarity_threshold if similarity_threshold is not None else self._similarity_threshold
        if threshold < 0 or threshold > 1:
            raise RetrievalError("similarity_threshold must be between 0 and 1", f"threshold={threshold}")
        
        try:
            # Generate query embedding
            query_embedding_result = self._embedding_service.generate_embeddings([query.strip()])
            if not query_embedding_result.embeddings or not query_embedding_result.embeddings[0]:
                raise RetrievalError("Failed to generate query embedding", "Empty embedding returned")
            
            query_vector = query_embedding_result.embeddings[0]
            
            # Build and execute similarity search query
            chunks = self._search_similar_chunks(
                db=db,
                user_id=user_id,
                query_vector=query_vector,
                k=k,
                document_ids=document_ids,
                threshold=threshold,
            )
            
            return RetrievalResult(
                chunks=chunks,
                query_text=query,
                top_k=k,
                total_matches=len(chunks),
            )
            
        except Exception as e:
            if isinstance(e, RetrievalError):
                raise
            logger.exception("Unexpected retrieval error")
            raise RetrievalError(
                "Retrieval failed due to internal error",
                str(e),
                retryable=False,
            )

    def _search_similar_chunks(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        query_vector: List[float],
        k: int,
        document_ids: Optional[List[UUID]] = None,
        threshold: float = 0.0,
    ) -> List[RetrievedChunk]:
        """
        Execute vector similarity search using pgvector.
        
        Uses cosine similarity: 1 - (embedding_vector <=> query_vector)
        Returns chunks ordered by similarity (highest first).
        """
        # Format query vector for pgvector
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
        
        # Build query using raw SQL for vector operations
        from sqlalchemy import text
        
        # Build document filter
        doc_filter = ""
        params = {
            "user_id": str(user_id),
            "query_vector": vector_str,
            "k": k,
            "threshold": threshold,
        }
        
        if document_ids:
            # Verify all document_ids belong to user and build filter
            doc_ids_str = ",".join(f"'{str(d)}'" for d in document_ids)
            doc_filter = f"AND dc.document_id IN ({doc_ids_str})"
        
        # Use cosine similarity: 1 - (embedding_vector <=> query_vector)
        # Filter by threshold and ownership
        sql = f"""
            SELECT 
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.text,
                dc.start_char,
                dc.end_char,
                dc.chunk_metadata,
                1 - (dc.embedding_vector <=> :query_vector) AS similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.user_id = :user_id
            AND dc.embedding_vector IS NOT NULL
            {doc_filter}
            AND 1 - (dc.embedding_vector <=> :query_vector) >= :threshold
            ORDER BY dc.embedding_vector <=> :query_vector
            LIMIT :k
        """
        
        result = db.execute(text(sql), params).fetchall()
        
        chunks = []
        for row in result:
            chunks.append(RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                text=row.text,
                start_char=row.start_char,
                end_char=row.end_char,
                chunk_metadata=row.chunk_metadata,
                similarity_score=row.similarity,
            ))
        
        return chunks


def create_retrieval_service(
    embedding_service: Optional[object] = None,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
) -> RetrievalService:
    """
    Factory function to create RetrievalService with settings from config.
    
    Args:
        embedding_service: Override embedding service
        top_k: Override default top-k
        similarity_threshold: Override default similarity threshold
        
    Returns:
        Configured RetrievalService instance
    """
    return RetrievalService(
        embedding_service=embedding_service,
        top_k=top_k or settings.RETRIEVAL_TOP_K,
        similarity_threshold=similarity_threshold or settings.RETRIEVAL_SIMILARITY_THRESHOLD,
    )