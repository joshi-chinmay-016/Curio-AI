"""
Comprehensive test suite for Curio AI's upgraded RAG pipeline:
- Gemini embedding provider with 1536 dimensions
- Structure-aware chunking with headings & equation preservation
- Hybrid retrieval (dense + lexical) with Reciprocal Rank Fusion (RRF)
- Evidence sufficiency classification (SUFFICIENT, PARTIAL, INSUFFICIENT, CONFLICTING)
- Seamless PDF-grounded and random-topic learning continuity
"""
import uuid
import pytest
from unittest.mock import MagicMock

from backend.app.embeddings.gemini_provider import GeminiEmbeddingProvider
from backend.app.embeddings.service import create_embedding_service, EmbeddingService
from backend.app.chunking.service import ChunkingService, create_chunking_service
from backend.app.retrieval.service import (
    RetrievalService,
    RetrievedChunk,
    EvidenceSufficiency,
    create_retrieval_service,
)
from backend.app.ai.rag.models import (
    DocumentSourceContext,
    DocumentRetrievalStatus,
    parse_document_source_context,
)


def test_gemini_embedding_provider_initialization():
    provider = GeminiEmbeddingProvider(
        api_key="curio-dev-mock-key",
        model="gemini-embedding-001",
        dimensions=1536,
        batch_size=50,
    )
    assert provider.model == "gemini-embedding-001"
    assert provider.dimensions == 1536
    assert provider.batch_size == 50
    assert provider._is_mock is True


def test_gemini_embedding_provider_deterministic_generation():
    provider = GeminiEmbeddingProvider(
        api_key="curio-dev-mock-key",
        model="gemini-embedding-001",
        dimensions=1536,
    )
    texts = [
        "Binary search operates on sorted arrays in O(log n) time.",
        "Photosynthesis converts sunlight into chemical energy.",
        "",  # Empty text
    ]
    result = provider.generate_embeddings(texts)
    assert len(result.embeddings) == 3
    assert len(result.embeddings[0]) == 1536
    assert len(result.embeddings[1]) == 1536
    assert len(result.embeddings[2]) == 0  # Empty text gets empty vector
    assert result.model == "gemini-embedding-001"

    # Determinism check: same text generates identical embedding vector
    res_repeat = provider.generate_embeddings([texts[0]])
    assert res_repeat.embeddings[0] == result.embeddings[0]


def test_embedding_service_gemini_factory():
    service = create_embedding_service(
        provider="gemini",
        model="gemini-embedding-001",
        dimensions=1536,
    )
    assert isinstance(service, EmbeddingService)
    assert service._provider == "gemini"
    assert service._dimensions == 1536
    res = service.generate_embeddings(["Merge sort divide and conquer."])
    assert len(res.embeddings[0]) == 1536


def test_structure_aware_chunking_headings_and_equations():
    chunker = ChunkingService(chunk_size=300, chunk_overlap=50)
    sample_text = (
        "# 1. Introduction to Dynamic Programming\n\n"
        "Dynamic programming solves complex problems by breaking them down into simpler subproblems.\n\n"
        "## Optimal Substructure\n\n"
        "A problem has optimal substructure if an optimal solution contains optimal solutions to subproblems.\n"
        "The recurrence relation is given by:\n"
        "$$ OPT(i) = \\max(OPT(i-1), OPT(i-2) + v_i) $$\n\n"
        "This formula guarantees convergence in polynomial time."
    )
    result = chunker.chunk_text(sample_text)
    assert result.total_chunks >= 1
    # Verify metadata on chunks
    headings_found = [c.metadata.get("section_heading") for c in result.chunks if c.metadata.get("section_heading")]
    assert len(headings_found) > 0
    # Equation detection
    eq_chunks = [c for c in result.chunks if c.metadata.get("has_equations")]
    assert len(eq_chunks) > 0


def test_reciprocal_rank_fusion():
    service = RetrievalService(embedding_service=MagicMock())
    doc_id = uuid.uuid4()
    c1_id = uuid.uuid4()
    c2_id = uuid.uuid4()

    dense_chunks = [
        RetrievedChunk(
            chunk_id=c1_id,
            document_id=doc_id,
            chunk_index=0,
            text="Binary search divide and conquer.",
            start_char=0,
            end_char=35,
            chunk_metadata={"page_number": 1},
            similarity_score=0.88,
        ),
        RetrievedChunk(
            chunk_id=c2_id,
            document_id=doc_id,
            chunk_index=1,
            text="Sorting is a necessary precondition.",
            start_char=36,
            end_char=75,
            chunk_metadata={"page_number": 1},
            similarity_score=0.72,
        ),
    ]

    lexical_chunks = [
        RetrievedChunk(
            chunk_id=c2_id,
            document_id=doc_id,
            chunk_index=1,
            text="Sorting is a necessary precondition.",
            start_char=36,
            end_char=75,
            chunk_metadata={"page_number": 1},
            similarity_score=1.0,
        ),
    ]

    merged = service._reciprocal_rank_fusion(dense_chunks, lexical_chunks, k=5, rrf_constant=60)
    assert len(merged) == 2
    # Verify both chunks have valid fused similarity scores
    for ch in merged:
        assert 0.0 <= ch.similarity_score <= 1.0
        assert ch.rrf_score is not None


def test_evidence_sufficiency_assessment():
    service = RetrievalService(embedding_service=MagicMock())
    doc_id = uuid.uuid4()

    # Sufficient case
    high_chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=0,
            text="The invariant requires sorted elements.",
            start_char=0,
            end_char=40,
            chunk_metadata={"page_number": 1},
            similarity_score=0.85,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=1,
            text="Pointer midpoint divides the search space in half.",
            start_char=41,
            end_char=90,
            chunk_metadata={"page_number": 1},
            similarity_score=0.78,
        ),
    ]
    assert service._assess_evidence_sufficiency(high_chunks, "how does binary search divide?") == "SUFFICIENT"

    # Conflicting case
    conflict_chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=0,
            text="It is always possible to find the element in logarithmic time.",
            start_char=0,
            end_char=65,
            chunk_metadata={"page_number": 2},
            similarity_score=0.75,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=1,
            text="It is never possible if the array is unsorted.",
            start_char=66,
            end_char=110,
            chunk_metadata={"page_number": 2},
            similarity_score=0.74,
        ),
    ]
    assert service._assess_evidence_sufficiency(conflict_chunks, "is it possible?") == "CONFLICTING"


def test_document_source_context_with_evidence_sufficiency():
    raw_payload = {
        "retrieval_status": "success",
        "evidence_sufficiency": "SUFFICIENT",
        "query_text": "invariant",
        "chunks": [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_1",
                "chunk_index": 0,
                "text": "The array must be sorted.",
                "page_number": 4,
                "similarity_score": 0.91,
            }
        ],
    }
    ctx = parse_document_source_context(raw_payload)
    assert ctx.status == DocumentRetrievalStatus.SUCCESS
    assert ctx.is_grounded is True
    assert ctx.evidence_sufficiency == "SUFFICIENT"
    formatted = ctx.format_evidence_context()
    assert "EVIDENCE SUFFICIENCY: SUFFICIENT" in formatted
    assert "Page 4" in formatted
    assert "The array must be sorted." in formatted
