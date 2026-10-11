"""
RAG (Retrieval-Augmented Generation) package for Curio AI.
Provides strongly validated models and adapters for retrieved document context.
"""
from backend.app.ai.rag.models import (
    DocumentChunkEvidence,
    DocumentRetrievalStatus,
    DocumentSourceContext,
    parse_document_source_context,
)

__all__ = [
    "DocumentChunkEvidence",
    "DocumentRetrievalStatus",
    "DocumentSourceContext",
    "parse_document_source_context",
]
