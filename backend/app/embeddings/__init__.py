"""
Embeddings package for document chunk embedding generation.
"""
from backend.app.embeddings.service import (
    EmbeddingService,
    EmbeddingResult,
    EmbeddingError,
    create_embedding_service,
)

__all__ = [
    "EmbeddingService",
    "EmbeddingResult",
    "EmbeddingError",
    "create_embedding_service",
]