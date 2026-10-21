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

from enum import Enum
import re

logger = logging.getLogger(__name__)


class EvidenceSufficiency(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


@dataclass
class RetrievedChunk:
    """A retrieved document chunk with similarity score and structural provenance."""
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    start_char: Optional[int]
    end_char: Optional[int]
    chunk_metadata: Optional[dict]
    similarity_score: float  # Fused similarity or cosine similarity (0 to 1)
    dense_score: Optional[float] = None
    lexical_score: Optional[float] = None
    rrf_score: Optional[float] = None

    @property
    def page_number(self) -> Optional[int]:
        if self.chunk_metadata and isinstance(self.chunk_metadata, dict):
            p = self.chunk_metadata.get("page_number") or self.chunk_metadata.get("page")
            if p is not None:
                try:
                    return int(p)
                except (ValueError, TypeError):
                    return None
        return None

    @property
    def section_heading(self) -> Optional[str]:
        if self.chunk_metadata and isinstance(self.chunk_metadata, dict):
            return self.chunk_metadata.get("section_heading")
        return None


@dataclass
class RetrievalResult:
    """Result of a retrieval operation with evidence sufficiency assessment."""
    chunks: List[RetrievedChunk]
    query_text: str
    top_k: int
    total_matches: int
    evidence_sufficiency: str = "SUFFICIENT"


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
            
            # Execute dense vector similarity search
            dense_chunks = self._search_similar_chunks(
                db=db,
                user_id=user_id,
                query_vector=query_vector,
                k=k * 2,  # Retrieve candidate pool for reranking
                document_ids=document_ids,
                threshold=threshold,
            )

            # If hybrid retrieval is enabled, also execute lexical candidate search
            hybrid_enabled = getattr(settings, "RETRIEVAL_HYBRID_ENABLED", True)
            if hybrid_enabled:
                lexical_chunks = self._search_lexical_chunks(
                    db=db,
                    user_id=user_id,
                    query=query.strip(),
                    k=k * 2,
                    document_ids=document_ids,
                )
                final_chunks = self._reciprocal_rank_fusion(
                    dense_chunks=dense_chunks,
                    lexical_chunks=lexical_chunks,
                    k=k,
                    rrf_constant=getattr(settings, "RETRIEVAL_RRF_K", 60),
                )
            else:
                final_chunks = dense_chunks[:k]

            # Assess evidence sufficiency
            sufficiency = self._assess_evidence_sufficiency(final_chunks, query)

            return RetrievalResult(
                chunks=final_chunks,
                query_text=query,
                top_k=k,
                total_matches=len(final_chunks),
                evidence_sufficiency=sufficiency,
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
                similarity_score=float(row.similarity) if row.similarity is not None else 0.0,
                dense_score=float(row.similarity) if row.similarity is not None else 0.0,
            ))
        
        return chunks

    def _search_lexical_chunks(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        query: str,
        k: int,
        document_ids: Optional[List[UUID]] = None,
    ) -> List[RetrievedChunk]:
        """
        Execute lexical search over document chunks to catch exact terms, equations, and names.
        """
        from sqlalchemy import text
        # Extract meaningful terms (> 2 chars, letters/numbers)
        terms = [t for t in re.findall(r'\b[A-Za-z0-9_-]{3,}\b', query.lower()) if t not in {
            "what", "when", "where", "which", "how", "why", "the", "and", "for", "with", "from", "that", "this"
        }]
        if not terms:
            return []

        doc_filter = ""
        params = {"user_id": str(user_id), "k": k}
        if document_ids:
            doc_ids_str = ",".join(f"'{str(d)}'" for d in document_ids)
            doc_filter = f"AND dc.document_id IN ({doc_ids_str})"

        # Build term ILIKE conditions
        like_clauses = []
        for idx, term in enumerate(terms[:8]):
            p_name = f"t_{idx}"
            params[p_name] = f"%{term}%"
            like_clauses.append(f"CASE WHEN dc.text ILIKE :{p_name} THEN 1 ELSE 0 END")

        rank_expr = " + ".join(like_clauses)
        sql = f"""
            SELECT 
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.text,
                dc.start_char,
                dc.end_char,
                dc.chunk_metadata,
                ({rank_expr}) AS match_count
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.user_id = :user_id
            {doc_filter}
            AND ({rank_expr}) > 0
            ORDER BY match_count DESC
            LIMIT :k
        """
        try:
            result = db.execute(text(sql), params).fetchall()
            max_matches = max(len(terms), 1)
            lexical_chunks = []
            for row in result:
                norm_score = min(1.0, float(row.match_count) / float(max_matches))
                lexical_chunks.append(RetrievedChunk(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    chunk_index=row.chunk_index,
                    text=row.text,
                    start_char=row.start_char,
                    end_char=row.end_char,
                    chunk_metadata=row.chunk_metadata,
                    similarity_score=norm_score,
                    lexical_score=norm_score,
                ))
            return lexical_chunks
        except Exception as e:
            logger.warning("Lexical candidate retrieval failed: %s", e)
            return []

    def _reciprocal_rank_fusion(
        self,
        dense_chunks: List[RetrievedChunk],
        lexical_chunks: List[RetrievedChunk],
        k: int,
        rrf_constant: int = 60,
    ) -> List[RetrievedChunk]:
        """
        Combines dense and lexical candidate rankings using Reciprocal Rank Fusion (RRF).
        """
        scores = {}
        chunk_map = {}

        # Dense ranking contributions
        for rank, ch in enumerate(dense_chunks):
            cid = str(ch.chunk_id)
            chunk_map[cid] = ch
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_constant + rank + 1))
            ch.dense_score = ch.similarity_score

        # Lexical ranking contributions
        for rank, ch in enumerate(lexical_chunks):
            cid = str(ch.chunk_id)
            if cid not in chunk_map:
                chunk_map[cid] = ch
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_constant + rank + 1))
            ch.lexical_score = ch.similarity_score

        # Sort by RRF score descending
        sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        max_possible_rrf = 2.0 / (rrf_constant + 1)

        merged = []
        for cid in sorted_cids[:k]:
            chunk = chunk_map[cid]
            raw_rrf = scores[cid]
            chunk.rrf_score = raw_rrf
            # Scale RRF score into a standardized similarity metric (0-1)
            fused_score = min(1.0, (raw_rrf / max_possible_rrf) * 0.95 + 0.05)
            # If dense score exists, blend gently to keep cosine scale
            if chunk.dense_score is not None:
                chunk.similarity_score = round(chunk.dense_score * 0.7 + fused_score * 0.3, 4)
            else:
                chunk.similarity_score = round(fused_score, 4)
            merged.append(chunk)

        return merged

    def _assess_evidence_sufficiency(self, chunks: List[RetrievedChunk], query: str) -> str:
        """
        Determines whether the retrieved passages are SUFFICIENT, PARTIAL, INSUFFICIENT, or CONFLICTING.
        """
        if not chunks:
            return EvidenceSufficiency.INSUFFICIENT.value

        top_score = max((c.similarity_score for c in chunks), default=0.0)
        
        # Check for direct contradictions across chunks (e.g. positive vs negative claims)
        if len(chunks) >= 2:
            texts = [c.text.lower() for c in chunks[:3]]
            has_conflict = False
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    if (
                        ("impossible" in texts[i] and "possible" in texts[j])
                        or ("always" in texts[i] and "never" in texts[j])
                        or ("requires" in texts[i] and "does not require" in texts[j])
                    ):
                        has_conflict = True
                        break
            if has_conflict:
                return EvidenceSufficiency.CONFLICTING.value

        if top_score >= 0.60 or (top_score >= 0.50 and len(chunks) >= 2):
            return EvidenceSufficiency.SUFFICIENT.value
        elif top_score >= 0.30:
            return EvidenceSufficiency.PARTIAL.value
        else:
            return EvidenceSufficiency.INSUFFICIENT.value


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