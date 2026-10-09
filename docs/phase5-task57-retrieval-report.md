# Phase 5 Task 5.7 — Vector Index & Retrieval Service Implementation Report

**Date:** October 9, 2026  
**Phase:** RAG Infrastructure — Task 5.7  
**Status:** PASS — All 214 tests passing

---

## 1. Summary

Implemented the vector index and retrieval service for Curio's RAG pipeline. The implementation adds native pgvector storage, HNSW indexing, and a retrieval service that performs database-side vector similarity search with ownership enforcement.

---

## 2. Files Created / Modified

### New Files Created
| File | Description |
|------|-------------|
| `backend/app/retrieval/__init__.py` | Package exports |
| `backend/app/retrieval/service.py` | Core retrieval service with pgvector search |
| `backend/tests/api/test_retrieval.py` | 29 comprehensive tests |
| `backend/alembic/versions/6b4da17ad0d5_add_native_vector_column.py` | Migration for native vector column |

### Modified Files
| File | Change |
|------|--------|
| `backend/app/models/document.py` | Added `embedding_vector` column (Vector(1536)) |
| `backend/app/core/config.py` | Added `RETRIEVAL_TOP_K=5`, `RETRIEVAL_SIMILARITY_THRESHOLD=0.0` |
| `backend/tests/conftest.py` | Set `EMBEDDING_API_KEY=test-key` for tests |
| `backend/app/retrieval/__init__.py` | Package exports |

---

## 3. Schema Design

### DocumentChunk Model (Extended)
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `embedding_vector` | `Vector(1536)` | NULLABLE | Native pgvector column for cosine similarity search |
| `embedding` | `Text` | NULLABLE | Legacy JSON storage (preserved for backward compatibility) |
| `embedding_model` | `String` | NULLABLE | Tracks which model generated the embedding |

### Indexes
| Index | Type | Configuration | Purpose |
|-------|------|---------------|---------|
| `ix_document_chunks_embedding_vector_hnsw` | HNSW | `m=16, ef_construction=64` | Fast cosine similarity search |
| `uq_document_chunk_index` | Unique | `(document_id, chunk_index)` | Enforce unique chunk positions |
| `ix_document_chunks_document_id` | B-tree | `document_id` | Fast document lookup |

### Migration
| Property | Value |
|----------|-------|
| Revision | `6b4da17ad0d5` |
| Parent | `d05335a73981` (add_document_chunks_table) |
| Head | Single valid head confirmed |

---

## 4. Embedding Model Decision

**Provider:** OpenAI  
**Model:** `text-embedding-3-small`  
**Dimensions:** 1536  
**Reasoning:** Groq doesn't offer embeddings; OpenAI is industry-standard with free tier available. The `embedding` column (Text/JSON) stores vectors flexibly; native `embedding_vector` column enables pgvector search. Migration to native `pgvector.Vector` type can be done when model is finalized.

---

## 5. Retrieval Service Contract

### Service: `RetrievalService`

```python
RetrievalService(
    embedding_service: Optional[EmbeddingService] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
)
```

#### Method: `retrieve()`
```python
def retrieve(
    self,
    db: Session,
    user_id: UUID,
    query: str,
    top_k: Optional[int] = None,
    document_ids: Optional[List[UUID]] = None,
    similarity_threshold: Optional[float] = None,
) -> RetrievalResult
```

**Parameters:**
- `user_id`: Authenticated user (ownership enforced)
- `query`: Search text
- `top_k`: Max results (default: 5)
- `document_ids`: Optional document filter
- `similarity_threshold`: Min cosine similarity (0-1)

**Returns:** `RetrievalResult` with ranked `RetrievedChunk` objects

### Result Types
```python
@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    start_char: Optional[int]
    end_char: Optional[int]
    chunk_metadata: Optional[dict]
    similarity_score: float  # Cosine similarity (0-1, higher = more similar)

@dataclass
class RetrievalResult:
    chunks: List[RetrievedChunk]
    query_text: str
    top_k: int
    total_matches: int
```

---

## 6. Key Features

### Vector Search
- **Database-side**: Uses pgvector's `<=>` cosine distance operator
- **HNSW Index**: `m=16, ef_construction=64` for fast ANN search
- **Cosine Similarity**: `1 - (embedding_vector <=> query_vector)`

### Security & Ownership
- All queries filter by `user_id` through JOIN with `documents` table
- Cross-user access returns 0 results (no data leakage)
- Document ID filters verified against ownership

### Error Handling
- Empty/whitespace queries return empty results
- Invalid `top_k` or `threshold` raise `RetrievalError`
- Embedding failures wrapped in `RetrievalError` with `retryable` flag
- Provider timeouts/rate limits retried with exponential backoff

---

## 6. Test Results

| Test Suite | Tests | Passed |
|------------|-------|--------|
| `test_extraction_pipeline.py` | 35 | ✅ 35 |
| `test_documents_ownership.py` | 20 | ✅ 20 |
| `test_documents_storage.py` | 41 | ✅ 41 |
| `test_chunking.py` | 41 | ✅ 41 |
| `test_chunking_storage.py` | 16 | ✅ 16 |
| `test_embeddings.py` | 32 | ✅ 32 |
| `test_retrieval.py` | 29 | ✅ 29 |
| **Total** | **214** | **✅ 214** |

All tests pass with 214 tests across 7 test suites.

---

## 7. Limitations & Deferred Work

| Item | Status | Notes |
|------|--------|-------|
| Embedding provider flexibility | **Deferred** | Only OpenAI implemented; `EMBEDDING_PROVIDER` config exists |
| Vector index tuning | **Deferred** | HNSW params `m=16, ef_construction=64` are defaults |
| Similarity search API | **Task 5.8** | No public endpoint yet |
| RAG context assembly | **Task 5.8** | Not implemented |
| Native pgvector.Vector type | **Deferred** | Using Text/JSON for flexibility; can migrate when model finalized |
| Chunking service test PDF | **Known Issue** | Minimal test PDF doesn't extract cleanly; test verifies chunking runs |

---

## 8. Confirmation Checklist

| Requirement | Verified |
|-------------|:--------:|
| Native pgvector column (1536 dims) | ✅ |
| HNSW index with cosine similarity | ✅ |
| Migration applied to both databases | ✅ |
| Existing embeddings preserved | ✅ |
| Retrieval uses DB-side search | ✅ |
| Ownership enforcement verified | ✅ |
| Cross-user isolation tested | ✅ |
| Document filtering works | ✅ |
| Top-k and threshold filtering | ✅ |
| No AI files modified | ✅ |
| No database reset/recreation | ✅ |
| No Task 5.8+ functionality | ✅ |
| All 214 tests pass | ✅ |

---

## 9. Final Verdict

**PASS** — Task 5.7 complete. Vector index and retrieval infrastructure ready for Task 5.8 (RAG Integration).