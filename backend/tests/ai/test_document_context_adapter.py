"""
Unit tests for Objective A: Typed Document Context Adapter.
Verifies all 12 contract requirements and safety invariants.
"""
import math
import pytest
from backend.app.ai.rag.models import (
    DocumentChunkEvidence,
    DocumentRetrievalStatus,
    DocumentSourceContext,
    parse_document_source_context,
)


def test_1_none_produces_disabled_state():
    """1. None produces the intended disabled state."""
    ctx = parse_document_source_context(None)
    assert ctx.status == DocumentRetrievalStatus.DISABLED
    assert ctx.chunks == []
    assert not ctx.is_grounded


def test_2_valid_success_produces_typed_chunks():
    """2. Valid success payload produces typed chunks."""
    raw = {
        "retrieval_status": "success",
        "total_matches": 1,
        "query_text": "binary search",
        "chunks": [
            {
                "chunk_id": "c-101",
                "document_id": "doc-505",
                "chunk_index": 0,
                "text": "Binary search runs in O(log n) time.",
                "start_char": 0,
                "end_char": 36,
                "similarity_score": 0.88,
                "chunk_metadata": {"page_number": 3},
            }
        ],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.SUCCESS
    assert ctx.is_grounded
    assert len(ctx.chunks) == 1
    chunk = ctx.chunks[0]
    assert isinstance(chunk, DocumentChunkEvidence)
    assert chunk.chunk_id == "c-101"
    assert chunk.document_id == "doc-505"
    assert chunk.chunk_index == 0
    assert chunk.text == "Binary search runs in O(log n) time."
    assert chunk.start_char == 0
    assert chunk.end_char == 36
    assert chunk.page_number == 3
    assert chunk.similarity_score == 0.88


def test_3_valid_no_results_distinct_from_error():
    """3. Valid no-results payload remains distinct from an error."""
    raw = {
        "retrieval_status": "no_results",
        "total_matches": 0,
        "query_text": "quantum computing",
        "chunks": [],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.NO_RESULTS
    assert not ctx.is_grounded
    assert ctx.chunks == []
    assert ctx.total_matches == 0
    assert ctx.error_message is None


def test_4_valid_retrieval_error_preserves_retryability():
    """4. Valid retrieval error preserves retryability."""
    raw = {
        "retrieval_status": "error",
        "error_message": "Embedding provider timeout",
        "error_retryable": True,
        "chunks": [],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.ERROR
    assert not ctx.is_grounded
    assert ctx.error_message == "Embedding provider timeout"
    assert ctx.error_retryable is True


def test_5_missing_required_fields_classified_invalid():
    """5. Missing required status field is classified invalid."""
    raw = {"query_text": "some query", "total_matches": 5}
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.INVALID
    assert len(ctx.validation_issues) > 0


def test_6_invalid_identifiers_and_indexes_rejected():
    """6. Invalid identifiers and chunk indexes are handled safely."""
    # Empty chunk_id
    raw_empty_id = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Some text",
            }
        ],
    }
    ctx1 = parse_document_source_context(raw_empty_id)
    assert ctx1.status == DocumentRetrievalStatus.INVALID

    # Negative chunk_index
    raw_neg_index = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": -1,
                "text": "Some text",
            }
        ],
    }
    ctx2 = parse_document_source_context(raw_neg_index)
    assert ctx2.status == DocumentRetrievalStatus.INVALID


def test_7_invalid_offsets_rejected():
    """7. Invalid offsets (end before start) are rejected."""
    raw = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Valid text",
                "start_char": 100,
                "end_char": 50,  # Invalid: end < start
            }
        ],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.INVALID
    assert any("end_char" in issue for issue in ctx.validation_issues)


def test_8_non_finite_similarity_scores_rejected():
    """8. Non-finite similarity scores (NaN, Inf) are rejected."""
    raw_nan = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Valid text",
                "similarity_score": float("nan"),
            }
        ],
    }
    ctx1 = parse_document_source_context(raw_nan)
    assert ctx1.status == DocumentRetrievalStatus.INVALID

    raw_inf = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Valid text",
                "similarity_score": float("inf"),
            }
        ],
    }
    ctx2 = parse_document_source_context(raw_inf)
    assert ctx2.status == DocumentRetrievalStatus.INVALID


def test_9_malformed_metadata_handled_explicitly():
    """9. Malformed metadata (e.g. non-positive or string page) is handled safely."""
    raw = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Valid text",
                "chunk_metadata": {"page": -5},  # Non-positive page is stripped safely
            }
        ],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.SUCCESS
    assert ctx.chunks[0].page_number is None  # Safeguarded, not fabricated


def test_10_contradictory_status_chunk_combinations_rejected():
    """10. Contradictory status/chunk combinations are rejected."""
    # success with 0 chunks is contradictory
    raw_empty_success = {
        "retrieval_status": "success",
        "chunks": [],
    }
    ctx1 = parse_document_source_context(raw_empty_success)
    assert ctx1.status == DocumentRetrievalStatus.INVALID

    # no_results with chunks is contradictory
    raw_no_results_with_chunks = {
        "retrieval_status": "no_results",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Sneaky text",
            }
        ],
    }
    ctx2 = parse_document_source_context(raw_no_results_with_chunks)
    assert ctx2.status == DocumentRetrievalStatus.INVALID

    # error with chunks is contradictory
    raw_error_with_chunks = {
        "retrieval_status": "error",
        "error_message": "Failed",
        "chunks": [
            {
                "chunk_id": "c-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Sneaky text",
            }
        ],
    }
    ctx3 = parse_document_source_context(raw_error_with_chunks)
    assert ctx3.status == DocumentRetrievalStatus.INVALID


def test_11_unknown_status_values_do_not_silently_become_disabled():
    """11. Unknown status values do not silently become disabled."""
    raw = {
        "retrieval_status": "UNKNOWN_CUSTOM_STATUS",
        "chunks": [],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.INVALID


def test_12_legacy_payload_compatibility():
    """12. Legacy payload compatibility works for 'content' key fallback."""
    raw = {
        "retrieval_status": "success",
        "chunks": [
            {
                "chunk_id": "c-legacy",
                "document_id": "doc-legacy",
                "chunk_index": 0,
                "content": "Legacy content key used instead of text.",
            }
        ],
    }
    ctx = parse_document_source_context(raw)
    assert ctx.status == DocumentRetrievalStatus.SUCCESS
    assert ctx.chunks[0].text == "Legacy content key used instead of text."
