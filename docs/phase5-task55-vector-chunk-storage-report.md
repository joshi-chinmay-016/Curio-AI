# Phase 5 Task 5.5 — Vector Database Schema & Persistent Chunk Storage Implementation Report

**Date:** October 9, 2026  
**Phase:** RAG Infrastructure — Task 5.5  
**Status:** PASS — All 153 tests passing (including 16 new chunking storage tests)

---

## 1. Schema Design

### DocumentChunk Model
Added `DocumentChunk` model to `backend/app/models/document.py`:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Chunk identifier |
| `document_id` | UUID | FK → documents.id, CASCADE, NOT NULL, INDEX | Parent document |
| `chunk_index` | Integer | NOT NULL | Zero-based position within document |
| `text` | Text | NOT NULL | Chunk content |
| `start_char` | Integer | NULLABLE | Start offset in source text |
| `end_char` | Integer | NULLABLE | End offset in source text |
| `chunk_metadata` | JSONB | NULLABLE | Structured metadata (page_number, etc.) |
| `embedding` | Text | NULLABLE | Embedding vector as JSON string (flexible until model finalized) |
| `embedding_model` | String | NULLABLE | Embedding model name |
| `created_at` | DateTime | NOT NULL, default=now() | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, default=now(), onupdate=now() | Update timestamp |

### Relationships
- `Document.chunks` → `DocumentChunk` (one-to-many, `cascade="all, delete-orphan"`, `lazy="dynamic"`)
- `DocumentChunk.document` → `Document` (many-to-one)

### Constraints
- Unique constraint on `(document_id, chunk_index)` → `uq_document_chunk_index`
- Foreign key with `ON DELETE CASCADE` → chunks deleted when document deleted
- Index on `document_id` for efficient lookups

---

## 2. Embedding Model & Dimension Decision

**Decision:** Deferred until embedding provider selected.

**Rationale:** 
- Project uses Groq for generation (not embeddings)
- No embedding model configured in settings
- Premature dimension choice would force schema migration later

**Implementation:**
- `embedding` column uses `Text` (flexible string storage)
- `embedding_model` column tracks which model was used
- Can migrate to `pgvector.Vector(dim)` when model finalized
- Chunks remain valid without embeddings (`NULL` allowed)

---

## 3. Migration Details

| Property | Value |
|----------|-------|
| **Revision** | `d05335a73981` |
| **Parent** | `add_document_ownership` |
| **Head** | Single valid head confirmed |
| **Table** | `document_chunks` |
| **Indexes** | PK on `id`, Unique on `(document_id, chunk_index)`, Index on `document_id` |
| **FK** | `document_id` → `documents.id` with `ON DELETE CASCADE` |

**Applied to:**
- Test database (`curio_test_db`) ✅
- Development database (`curio_db`) ✅

---

## 4. Repository Implementation

**File:** `backend/app/repositories/document_chunk_repository.py`

| Method | Description |
|--------|-------------|
| `create_chunks(db, document_id, chunks)` | Batch insert chunks |
| `get_chunks_by_document(db, document_id, user_id)` | Ordered by `chunk_index` |
| `get_chunk_by_id(db, chunk_id, user_id)` | Ownership-scoped retrieval |
| `delete_chunks_by_document(db, document_id, user_id)` | Ownership-verified deletion |
| `replace_chunks_for_document(db, document_id, user_id, new_chunks)` | Atomic replace (delete + insert) |
| `update_chunk_embedding(db, chunk_id, user_id, embedding, embedding_model)` | Embedding update |
| `count_chunks(db, document_id, user_id)` | Ownership-scoped count |

**Security:** All operations verify document ownership via `user_id` before operating on chunks.

---

## 5. Ownership & Deletion Behavior

- **Ownership:** Enforced through `Document.user_id` → chunks accessible only through owned documents
- **Cascade Delete:** `ON DELETE CASCADE` on FK ensures chunks auto-deleted when document deleted
- **Atomic Replace:** `replace_chunks_for_document()` uses single transaction (delete old + insert new)
- **Rollback Safety:** Failed batch operations roll back, preserving existing chunks

---

## 6. Files Created / Modified

### New Files
| File | Description |
|------|-------------|
| `backend/app/repositories/document_chunk_repository.py` | Chunk repository with ownership-safe operations |
| `backend/alembic/versions/d05335a73981_add_document_chunks_table.py` | Migration for `document_chunks` table |
| `backend/tests/api/test_chunking_storage.py` | 16 focused tests |

### Modified Files
| File | Change |
|------|--------|
| `backend/app/models/document.py` | Added `DocumentChunk` model + `chunks` relationship |
| `backend/app/chunking/__init__.py` | Export `DocumentChunkRepository` |

---

## 7. Test Results

### New Chunking Storage Tests (16/16 passed)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestDocumentChunkModel` | 3 | Model creation, unique constraint, multi-doc isolation |
| `TestDocumentChunkRepository` | 10 | CRUD, ownership, atomic replace, embedding update, count |
| `TestCascadeDeletion` | 1 | CASCADE delete verification |
| `TestDocumentIntegration` | 1 | Existing pipeline intact |
| `TestMigrationCompatibility` | 1 | Schema, indexes, FK, single head |

### Regression Suites (All Passing)

| Suite | Tests | Status |
|-------|-------|--------|
| `test_extraction_pipeline.py` | 35 | ✅ |
| `test_documents_ownership.py` | 20 | ✅ |
| `test_documents_storage.py` | 41 | ✅ |
| `test_chunking.py` | 41 | ✅ |
| `test_chunking_storage.py` | 16 | ✅ |
| **Total** | **153** | **✅ All Pass** |

---

## 8. Development & Test Database Migration Results

| Database | Status |
|----------|--------|
| `curio_test_db` (port 5433) | ✅ Migrated to head |
| `curio_db` (port 5433) | ✅ Migrated to head |

Both databases verified with:
- Table existence
- Column completeness
- Indexes (PK, unique, document_id)
- Foreign key with CASCADE
- Single migration head

---

## 9. Limitations & Deferred Decisions

| Item | Status | Notes |
|------|--------|-------|
| Embedding model selection | **Deferred** | No provider chosen; column uses flexible `Text` |
| Vector index (HNSW/IVFFlat) | **Deferred** | Requires known dimension |
| Embedding generation | **Task 5.6+** | Not implemented |
| Similarity search | **Task 5.6+** | Not implemented |
| Public chunk APIs | **Task 5.6+** | Internal repository only |

---

## 10. Confirmation Checklist

| Requirement | Verified |
|-------------|:--------:|
| No AI files modified (`backend/app/ai/`) | ✅ |
| No database reset/recreation | ✅ |
| No Task 5.6+ functionality | ✅ |
| No unrelated refactoring | ✅ |
| Single migration head | ✅ |
| Both databases migrated | ✅ |
| All regression tests pass | ✅ (153/153) |
| Ownership enforcement on chunks | ✅ |
| CASCADE delete verified | ✅ |

---

## Final Verdict

**PASS** — Task 5.5 complete. Persistent chunk storage infrastructure implemented with:
- `DocumentChunk` model with proper relationships, constraints, and cascade delete
- Safe Alembic migration applied to both databases
- Ownership-safe repository with atomic operations
- Flexible embedding storage for future model selection
- 153 tests passing (35 extraction + 20 ownership + 41 storage + 41 chunking + 16 chunk storage)

**Ready for Task 5.6 (Embedding Generation).**