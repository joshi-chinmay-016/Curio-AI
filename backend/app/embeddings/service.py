"""
Embedding generation service for document chunks.

Provides deterministic, batched embedding generation using OpenAI API.
Persists embeddings to document chunks with ownership verification.
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import logging
import time

from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from sqlalchemy.orm import Session as SQLAlchemySession
from uuid import UUID

from backend.app.core.config import settings
from backend.app.models.document import DocumentChunk
from backend.app.repositories.document_chunk_repository import DocumentChunkRepository

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: List[List[float]]  # One vector per input text
    model: str
    dimensions: int
    total_tokens: int


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    def __init__(self, message: str, details: str = None, retryable: bool = False):
        self.message = message
        self.details = details
        self.retryable = retryable
        super().__init__(message)


class EmbeddingService:
    """
    Service for generating embeddings for document chunks.
    
    Features:
    - Batched embedding generation with configurable batch size
    - Automatic retry with exponential backoff for retryable errors
    - Input validation and dimension checking
    - Ownership-aware persistence via DocumentChunkRepository
    - Idempotent: skips chunks that already have valid embeddings from the same model
    
    Does NOT perform:
    - Chunking or document extraction
    - Similarity search or retrieval
    - AI reasoning or RAG context assembly
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        batch_size: Optional[int] = None,
        client: Optional[OpenAI] = None,
    ):
        """
        Initialize embedding service with configuration.
        
        Args:
            api_key: OpenAI API key (from settings if None)
            model: Embedding model name (from settings if None)
            dimensions: Expected vector dimensions (from settings if None)
            timeout: Request timeout in seconds (from settings if None)
            max_retries: Max retry attempts for retryable errors (from settings if None)
            batch_size: Max texts per API call (from settings if None)
            client: Optional OpenAI client for testing/mocking
            
        Raises:
            EmbeddingError: If configuration is invalid
        """
        self._api_key = api_key or settings.EMBEDDING_API_KEY
        self._model = model or settings.EMBEDDING_MODEL
        self._dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self._timeout = timeout or settings.EMBEDDING_TIMEOUT_SECONDS
        self._max_retries = max_retries if max_retries is not None else settings.EMBEDDING_MAX_RETRIES
        self._batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        
        if not self._api_key:
            raise EmbeddingError("Embedding API key not configured", "Set EMBEDDING_API_KEY in environment")
        
        if self._dimensions <= 0:
            raise EmbeddingError("Embedding dimensions must be positive", f"dimensions={self._dimensions}")
        
        if self._batch_size <= 0:
            raise EmbeddingError("Batch size must be positive", f"batch_size={self._batch_size}")
        
        self._client = client or OpenAI(
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=0,  # We handle retries ourselves
        )
        
        self._repo = DocumentChunkRepository()

    def generate_embeddings(self, texts: List[str]) -> EmbeddingResult:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text chunks to embed
            
        Returns:
            EmbeddingResult with vectors, model info, and token count
            
        Raises:
            EmbeddingError: If generation fails or validation fails
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model=self._model,
                dimensions=self._dimensions,
                total_tokens=0,
            )
        
        # Filter out empty texts
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                valid_indices.append(i)
        
        if not valid_texts:
            # All texts were empty
            return EmbeddingResult(
                embeddings=[[] for _ in texts],
                model=self._model,
                dimensions=self._dimensions,
                total_tokens=0,
            )
        
        all_embeddings = []
        total_tokens = 0
        
        # Process in batches
        for i in range(0, len(valid_texts), self._batch_size):
            batch = valid_texts[i:i + self._batch_size]
            batch_result = self._generate_batch(batch)
            all_embeddings.extend(batch_result.embeddings)
            total_tokens += batch_result.total_tokens
        
        # Map back to original positions (empty texts get empty vectors)
        result_embeddings = []
        valid_idx = 0
        valid_indices_set = set(valid_indices)
        for i in range(len(texts)):
            if i in valid_indices_set:
                result_embeddings.append(all_embeddings[valid_idx])
                valid_idx += 1
            else:
                result_embeddings.append([])
        
        return EmbeddingResult(
            embeddings=result_embeddings,
            model=self._model,
            dimensions=self._dimensions,
            total_tokens=total_tokens,
        )

    def _generate_batch(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a single batch with retries."""
        last_error = None
        
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.embeddings.create(
                    model=self._model,
                    input=texts,
                    encoding_format="float",
                )
                
                embeddings = [item.embedding for item in response.data]
                total_tokens = response.usage.total_tokens if response.usage else 0
                
                # Validate dimensions
                for i, emb in enumerate(embeddings):
                    if len(emb) != self._dimensions:
                        raise EmbeddingError(
                            f"Embedding dimension mismatch: expected {self._dimensions}, got {len(emb)}",
                            f"text index {i}",
                            retryable=False,
                        )
                    # Validate finite values
                    for val in emb:
                        if not isinstance(val, (int, float)) or val != val or val == float('inf') or val == float('-inf'):
                            raise EmbeddingError(
                                "Embedding contains non-finite values",
                                f"text index {i}",
                                retryable=False,
                            )
                
                return EmbeddingResult(
                    embeddings=embeddings,
                    model=self._model,
                    dimensions=self._dimensions,
                    total_tokens=total_tokens,
                )
                
            except RateLimitError as e:
                last_error = e
                if attempt < self._max_retries:
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self._max_retries})")
                    time.sleep(wait_time)
                else:
                    raise EmbeddingError(
                        "Rate limit exceeded after retries",
                        str(e),
                        retryable=True,
                    )
            except APITimeoutError as e:
                last_error = e
                if attempt < self._max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"Timeout, retrying in {wait_time}s (attempt {attempt + 1}/{self._max_retries})")
                    time.sleep(wait_time)
                else:
                    raise EmbeddingError(
                        "API timeout after retries",
                        str(e),
                        retryable=True,
                    )
            except APIConnectionError as e:
                last_error = e
                if attempt < self._max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(f"Connection error, retrying in {wait_time}s (attempt {attempt + 1}/{self._max_retries})")
                    time.sleep(wait_time)
                else:
                    raise EmbeddingError(
                        "API connection error after retries",
                        str(e),
                        retryable=True,
                    )
            except EmbeddingError:
                # Re-raise EmbeddingError as-is (including validation errors)
                raise
            except Exception as e:
                logger.exception("Unexpected embedding error")
                raise EmbeddingError(
                    "Embedding generation failed",
                    str(e),
                    retryable=False,
                )
        
        # Should not reach here
        raise EmbeddingError(
            "Embedding generation failed after retries",
            str(last_error) if last_error else "Unknown error",
            retryable=True,
        )

    def generate_and_persist_embeddings(
        self,
        db: SQLAlchemySession,
        document_id: UUID,
        user_id: UUID,
        force_regenerate: bool = False,
    ) -> int:
        """
        Generate and persist embeddings for all chunks of a document.
        
        Args:
            db: Database session
            document_id: Document UUID
            user_id: User UUID (for ownership verification)
            force_regenerate: If True, regenerate embeddings even if they exist
            
        Returns:
            Number of chunks that were embedded
            
        Raises:
            EmbeddingError: If generation or persistence fails
        """
        # Get all chunks for the document (ownership verified)
        chunks = self._repo.get_chunks_by_document(db, document_id, user_id)
        
        if not chunks:
            logger.info(f"No chunks found for document {document_id}")
            return 0
        
        # Filter chunks that need embedding
        texts_to_embed = []
        chunks_to_embed = []
        
        for chunk in chunks:
            has_valid_embedding = (
                chunk.embedding is not None 
                and chunk.embedding_model == self._model
                and chunk.embedding.strip() != ""
            )
            
            if force_regenerate or not has_valid_embedding:
                texts_to_embed.append(chunk.text)
                chunks_to_embed.append(chunk)
        
        if not texts_to_embed:
            logger.info(f"All chunks for document {document_id} already have embeddings from model {self._model}")
            return 0
        
        logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks of document {document_id}")
        
        # Generate embeddings
        result = self.generate_embeddings(texts_to_embed)
        
        # Persist embeddings
        embedded_count = 0
        for chunk, embedding_vector in zip(chunks_to_embed, result.embeddings):
            if not embedding_vector:  # Empty text produced empty vector
                continue
            
            # Serialize embedding to JSON string
            embedding_json = json.dumps(embedding_vector)
            
            self._repo.update_chunk_embedding(
                db=db,
                chunk_id=chunk.id,
                user_id=chunk.document.user_id if hasattr(chunk, 'document') and chunk.document else user_id,
                embedding=embedding_json,
                embedding_model=self._model,
            )
            embedded_count += 1
        
        logger.info(f"Persisted embeddings for {embedded_count} chunks of document {document_id}")
        return embedded_count


def create_embedding_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    dimensions: Optional[int] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    batch_size: Optional[int] = None,
    client: Optional[OpenAI] = None,
) -> EmbeddingService:
    """
    Factory function to create EmbeddingService with settings from config.
    
    Args:
        api_key: Override API key
        model: Override model name
        dimensions: Override dimensions
        timeout: Override timeout
        max_retries: Override max retries
        batch_size: Override batch size
        client: Optional OpenAI client for testing
        
    Returns:
        Configured EmbeddingService instance
    """
    return EmbeddingService(
        api_key=api_key,
        model=model,
        dimensions=dimensions,
        timeout=timeout,
        max_retries=max_retries,
        batch_size=batch_size,
        client=client,
    )