# Phase 5 RAG Infrastructure Audit Report

**Repository**: Curio-AI Backend  
**Audit Date**: 2026-10-07  
**Auditor**: Vishal (Backend Infrastructure)  
**Scope**: READ-ONLY architecture audit for Phase 5 — RAG Infrastructure

---

## Executive Summary

**Current RAG Infrastructure Maturity: ~5%**

Only metadata-only document API and AI-layer stubs exist. No file persistence, chunking, embeddings, vector search, or retrieval infrastructure is implemented. Critical security gaps exist (no document ownership, IDOR vulnerability).

---

## 1. Document Architecture

### Current State

| Component | Status | Details |
|-----------|--------|---------|
| **Document Model** (`app/models/document.py:6-13`) | Minimal | Only: `id`, `filename`, `file_size`, `mime_type`, `created_at`. **Missing**: `user_id` (ownership), `status`, `storage_path`, `content_hash`, `page_count`, `processing_error` |
| **Document Schema** (`app/schemas/document.py:6-14`) | Minimal | `DocumentResponse` mirrors model. No create/update schemas. |
| **Document Repository** (`app/repositories/document_repository.py:6-19`) | Basic | `create()` and `get()` only. **Missing**: `list_by_user()`, `get_by_status()`, `update_status()`, `delete()`, pagination |
| **Document Service** (`app/services/document_service.py:7-31`) | Basic | Thin wrapper over repo. **Missing**: file storage, extraction triggering, status management, ownership checks |
| **Document API** (`app/api/v1/documents.py:11-33`) | Partial | `POST /documents` (uploads metadata only, **no file persistence**), `GET /documents/{id}`. **Missing**: ownership enforcement, file download, status polling, delete, list user's documents |

### Foreign Keys & Ownership

- **Critical Gap**: `Document` model has **no `user_id` column** — no ownership tracking.
- `Session` has `document_id` FK (`app/models/session.py:15`) but documents aren't owned by users → **cross-user document access possible**.

### CRUD Behavior

- Create: Accepts `UploadFile`, reads metadata, **discards file content** (no storage).
- Read: Returns metadata only.
- Update/Delete: Not implemented.

---

## 2. File Ingestion

| Capability | Status | Evidence |
|------------|--------|----------|
| File upload endpoint | ✅ Exists | `POST /api/v1/documents` accepts `UploadFile` |
| File metadata persistence | ✅ Exists | Stores filename, size, mime_type |
| **File storage (content)** | ❌ **Missing** | File content read for size only, then discarded (`documents.py:17-19`) |
| PDF/text extraction | ❌ **Missing** | No extraction libraries in requirements (`pypdf`, `python-docx`, `unstructured`) |
| Supported file types | ❌ Unrestricted | Accepts any `content_type`, no validation |
| Document status/lifecycle | ❌ **Missing** | No `status` field; no processing pipeline |
| Failure handling | ❌ **Missing** | No retry, no error tracking, no dead letter |
| Large-file handling | ❌ **Missing** | No chunked upload, no size limits, no streaming to disk/S3 |

**Critical**: The upload endpoint reads the entire file into memory to get size (`file.file.seek(0, 2)`), then discards it. No persistence to disk, S3, or database blob.

---

## 3. Chunking Infrastructure

| Aspect | Status |
|--------|--------|
| Chunking exists? | ❌ **No** |
| Chunk persistence | ❌ No model, table, or repository |
| Chunk metadata | ❌ Only `DocumentChunk` schema exists in AI layer (`app/ai/rag/schemas.py:10-13`) |
| Document→Chunk relationship | ❌ None |
| Chunk size/overlap config | ❌ None |
| Location | AI layer has stub schemas; **backend has zero chunking code** |

**Boundary Decision**: Chunking is **backend infrastructure** (storage, persistence, metadata, document relationship). AI layer should only receive chunks via retrieval API.

---

## 4. Embeddings & Vector Storage

| Component | Status | Evidence |
|-----------|--------|----------|
| pgvector installed | ✅ **Yes** | Docker uses `ankane/pgvector:latest`; `init-databases.sh:35-36` creates extension |
| PostgreSQL extension | ✅ Enabled at DB init | `CREATE EXTENSION IF NOT EXISTS vector;` |
| Vector columns | ❌ **None** | No `vector` type columns in any model |
| Embedding models/providers | ❌ **None** | No `sentence-transformers`, `openai`, `cohere`, or similar in requirements |
| Embedding persistence | ❌ **None** | No embedding column on chunks/documents |
| Vector indexes | ❌ **None** | No HNSW/IVF indexes |
| Similarity search | ❌ **Stub only** | `DocumentRetriever.retrieve_relevant_chunks()` returns `[]` (`app/ai/rag/retriever.py:10-12`) |
| Vector repositories/services | ❌ **None** | No backend-side vector search service |

**Gap**: Database *supports* pgvector but schema doesn't use it. Entire embedding pipeline missing from backend.

---

## 5. Retrieval Infrastructure

| Capability | Status |
|------------|--------|
| Retrieval service (backend) | ❌ **None** — only AI-layer stub |
| Vector search | ❌ **None** |
| Metadata filtering | ❌ **None** |
| User/document ownership filtering | ❌ **None** (no ownership on documents) |
| Top-k behavior | ❌ **None** |
| Similarity thresholds | ❌ **None** |
| Pagination/limits | ❌ **None** |
| Retrieval APIs | ❌ **None** (no `/retrieve` or `/search` endpoints) |
| Performance considerations | N/A — not implemented |

**Current**: `DocumentRetriever` in `app/ai/rag/retriever.py` is a **stub** explicitly marked for backend implementation.

---

## 6. AI ↔ Backend Boundary

### Current Contract

```
Backend (ChatService) → builds AIContext → CurioEngine.process() → AIResult
```

- `AIContext` (`app/ai/schemas.py:632-750`): Contains `session`, `current_state`, `conversation`, `learning_context`, `source_context` (optional dict)
- `AIResult` (`app/ai/schemas.py:552-565`): Contains `evaluation`, `decision`, `response`, `state_updates`, plus optional report/assessment objects

### Integration Point for RAG

**Correct approach**: Extend `AIContext.source_context` (already typed as `Optional[Dict[str, Any]]`) to include retrieved chunks:

```python
source_context: Optional[Dict[str, Any]] = None  # Add: {"retrieved_chunks": [DocumentChunk, ...]}
```

**Why this works**:
- Backend owns retrieval infrastructure → calls retrieval service → injects chunks into `AIContext`
- AI layer (CurioEngine) receives chunks as **read-only context** via `source_context`
- No AI reasoning moved to backend; no direct DB access by AI layer
- Chinmay's intelligence logic unchanged — just receives additional context

### Current Usage

- `ChatService.send_message()` builds `AIContext` at `app/services/chat_service.py:403-408`
- `source_context` is passed as `None` currently
- Session `source_type` ("GENERAL" \| "DOCUMENT") exists but unused for retrieval

---

## 7. Security / Ownership

| Risk | Status | Evidence |
|------|--------|----------|
| Document ownership | ❌ **Missing** | No `user_id` on `Document` model |
| Cross-user document access | ⚠️ **Vulnerable** | `GET /documents/{id}` has no ownership check (`documents.py:28-33`) |
| Retrieval isolation | N/A | Not implemented |
| IDOR on documents | ⚠️ **High Risk** | Any authenticated user can access any document by UUID |
| File access security | ❌ **Missing** | No file storage → no access control |
| Authenticated API requirements | ✅ Exists | All endpoints use `get_current_active_user` |
| Malicious/oversized uploads | ❌ **Missing** | No size limit, no type validation, no virus scan |
| Sensitive document exposure | ⚠️ **Risk** | No encryption at rest, no access logging |

---

## 8. Database & Migration Requirements

### Required New Tables

| Table | Purpose | Columns |
|-------|---------|---------|
| `document_chunks` | Chunk storage | `id`, `document_id` (FK), `chunk_index`, `content`, `token_count`, `page_number`, `char_start`, `char_end`, `embedding` (vector), `created_at` |
| `document_embeddings` (optional) | Doc-level embeddings | `document_id` (PK, FK), `embedding` (vector), `model_name`, `created_at` |

### Required Columns on Existing Tables

| Table | Columns to Add |
|-------|----------------|
| `documents` | `user_id` (FK→users, NOT NULL), `status` (enum), `storage_path`, `content_hash`, `page_count`, `processing_error`, `chunk_count`, `embedding_model` |

### Required Indexes

- `documents.user_id` (for ownership queries)
- `documents.status` (for processing queue)
- `document_chunks.document_id` (for chunk lookup)
- `document_chunks.embedding` → **HNSW index** (`CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`)
- `document_chunks (document_id, chunk_index)` unique

### pgvector Requirements

- Extension already enabled via `init-databases.sh`
- Need `vector` type columns (e.g., `Column(Vector(1536))` for OpenAI, `Vector(384)` for MiniLM)
- HNSW index for ANN search

### Alembic Migration

- **New migration required** for all above
- No existing data backfill needed (documents table likely empty or minimal)

---

## 9. Performance & Scalability

| Concern | Current Risk |
|---------|--------------|
| Large documents | ❌ No streaming upload, no chunked processing |
| Large chunk counts | ❌ No pagination in retrieval, no chunk batching |
| Embedding generation | ❌ Sync-only, no queue/worker, no batching |
| Vector search performance | ❌ No indexes, no ANN config |
| N+1 risks | ✅ Low currently (simple queries), but chunk→document joins will need `joinedload` |
| Transaction boundaries | ⚠️ Document create + chunk insert + embedding gen should be **async job**, not single transaction |
| Sync vs async processing | ❌ All current code sync; embedding gen **must be async** (Celery/RQ/background tasks) |

---

## 10. Testing Gaps

| Area | Missing Tests |
|------|---------------|
| Document ownership | Upload by user A, access by user B → 404/403 |
| Upload | Large file (>100MB), invalid type, empty file, duplicate hash |
| Extraction | PDF with images, scanned PDF, corrupted PDF, DOCX, TXT |
| Chunking | Overlap correctness, boundary handling, metadata preservation |
| Embeddings | Model swap, dimension mismatch, batch processing |
| Vector search | Accuracy, threshold filtering, pagination, ownership filter |
| Retrieval isolation | User A cannot retrieve User B's document chunks |
| Malformed files | Null bytes, executable disguised as PDF, zip bombs |
| Large files | Streaming upload, chunked processing, memory bounds |
| Empty documents | Zero-page PDF, empty TXT |
| Duplicate documents | Same content hash → dedupe or version |
| Database failures | pgvector extension missing, index build failure, connection pool exhaustion |

---

## 11. Responsibility Boundary

| **VISHAL / BACKEND** (Infrastructure) | **CHINMAY / AI** (Intelligence) |
|----------------------------------------|----------------------------------|
| Document storage (files + metadata) | Deciding *when* retrieval is needed |
| Chunking (split, persist, metadata) | Reasoning over retrieved context |
| Embedding generation (models, batching, retry) | Prompt construction with context |
| Vector DB (pgvector, indexes, HNSW) | Pedagogical decisions |
| Retrieval service (search, filter, rank) | Answer generation |
| Retrieval API (owned-documents only) | Evaluation/assessment |
| Ownership & access control | Learning decisions |
| File upload, validation, virus scan | LangGraph workflows |
| Async processing (queue, workers) | AI providers, prompts |
| Monitoring, logging, alerting | Answer intelligence (claims, evidence) |

**Integration Contract**: Backend provides `retrieved_chunks: List[DocumentChunk]` via `AIContext.source_context`. AI layer treats as opaque context.

---

## 12. Phase 5 Task Plan

| # | Title | Purpose | Files Affected | DB Migration | API Changes | AI Changes | Security | Testing | Dependencies |
|---|-------|---------|----------------|--------------|-------------|------------|----------|---------|--------------|
| 1 | **Add document ownership & status** | Enable per-user document isolation & lifecycle tracking | `models/document.py`, `schemas/document.py`, `repositories/document_repository.py`, `services/document_service.py`, `api/v1/documents.py` | ✅ Yes (add `user_id`, `status`, `storage_path`, `content_hash`, `page_count`, `processing_error`, `chunk_count`) | ✅ Yes (ownership checks, list user docs, delete) | ❌ No | ✅ Ownership enforcement, IDOR fix | Ownership tests, IDOR tests | — |
| 2 | **Implement file storage & upload persistence** | Actually store uploaded files (local disk/S3) | `services/document_service.py`, `api/v1/documents.py`, new `storage/` module | ❌ No (uses `storage_path` from Task 1) | ✅ Yes (streaming upload, size limits, type validation) | ❌ No | ✅ Size limits, type allowlist, virus scan hook | Upload tests (large, invalid, empty) | Task 1 |
| 3 | **Add PDF/text extraction pipeline** | Extract text from uploaded documents | `services/document_service.py`, new `extraction/` module, `models/document.py` (page_count) | ❌ No | ❌ No | ❌ No | ⚠️ Malformed file handling | Extraction tests (PDF, DOCX, TXT, corrupted) | Task 2 |
| 4 | **Create chunking infrastructure** | Split documents into chunks with metadata | New `models/chunk.py`, `schemas/chunk.py`, `repositories/chunk_repository.py`, `services/chunking_service.py` | ✅ Yes (`document_chunks` table) | ❌ No | ❌ No | ✅ Chunk ownership via document | Chunking tests (boundaries, overlap, metadata) | Task 3 |
| 5 | **Add pgvector columns & HNSW indexes** | Enable vector similarity search | `models/chunk.py` (embedding column), Alembic migration | ✅ Yes | ❌ No | ❌ No | ❌ No | Index creation, dimension validation | Task 4 |
| 6 | **Implement embedding generation** | Generate embeddings for chunks (async) | New `services/embedding_service.py`, background worker (Celery/RQ), config for model/dim | ❌ No (uses Task 5 columns) | ❌ No | ❌ No | ✅ Rate limiting, retry, model versioning | Embedding tests (batch, retry, dimension) | Task 5 |
| 7 | **Build retrieval service & API** | Vector search + metadata filtering + ownership | New `services/retrieval_service.py`, `api/v1/retrieval.py`, `schemas/retrieval.py` | ❌ No | ✅ Yes (`POST /retrieve`, `GET /documents/{id}/chunks`) | ❌ No | ✅ Ownership filter, rate limits, audit log | Retrieval tests (accuracy, filter, pagination, isolation) | Task 6 |
| 8 | **Integrate retrieval into AIContext** | Supply chunks to AI engine via source_context | `services/chat_service.py` (build context), `ai/schemas.py` (DocumentChunk import) | ❌ No | ❌ No | ⚠️ Minimal (AI reads `source_context.retrieved_chunks`) | ✅ No data leakage | Integration tests (RAG flow) | Task 7 |
| 9 | **Add document processing status API** | Polling for async extraction/embedding | `api/v1/documents.py` (GET status), `services/document_service.py` | ❌ No | ✅ Yes | ❌ No | ✅ Ownership | Status polling tests | Task 3, 6 |
| 10 | **End-to-end RAG tests & hardening** | Full pipeline validation | Test files across `tests/` | ❌ No | ❌ No | ❌ No | ✅ Penetration, load | E2E RAG tests, load tests, chaos tests | All prior |

---

## 13. Final Verdict

### PHASE 5 AUDIT STATUS

**Current RAG Infrastructure Maturity**: **~5%** (Only stubs exist)

| Category | Status |
|----------|--------|
| Document metadata API | ✅ Basic (no ownership, no file storage) |
| File ingestion | ❌ Accepts upload, **discards content** |
| Chunking | ❌ Zero implementation |
| Embeddings/Vector | ❌ Schema only (pgvector enabled in DB but unused) |
| Retrieval | ❌ Stub in AI layer only |
| Security/Isolation | ❌ Critical gaps (no ownership, IDOR) |

### What Already Exists

- Document metadata model + API (minimal)
- Session→Document FK (but no document ownership)
- pgvector extension enabled in Docker DB init
- AI-layer retrieval schemas (`DocumentChunk`, `ChunkMetadata`)
- AIContext `source_context` field (ready for chunk injection)
- `DocumentRetriever` stub explicitly awaiting backend implementation

### What Is Missing (Critical)

1. **Document ownership** — no `user_id` on documents
2. **File storage** — uploads discard content
3. **Extraction pipeline** — no PDF/text libraries
4. **Chunking** — no model, table, service
5. **Embeddings** — no model, no generation, no persistence
6. **Vector indexes** — no HNSW on embedding columns
7. **Retrieval service** — no backend implementation
8. **Retrieval API** — no endpoints
9. **Async processing** — all sync, no queue for embeddings

### Critical Issues

| Severity | Issue |
|----------|-------|
| 🔴 **Critical** | No document ownership → cross-user data access |
| 🔴 **Critical** | File uploads don't persist content |
| 🟠 **High** | No size/type validation on uploads |
| 🟠 **High** | All processing synchronous (will block API) |
| 🟡 **Medium** | No extraction → RAG cannot work |

### Recommended Phase 5 Task Order

1. **Task 1**: Document ownership & status (unblocks all security)
2. **Task 2**: File storage & upload persistence (unblocks extraction)
3. **Task 3**: PDF/text extraction (unblocks chunking)
4. **Task 4**: Chunking infrastructure (unblocks embeddings)
5. **Task 5**: pgvector columns + HNSW indexes (unblocks vector search)
6. **Task 6**: Embedding generation (async worker)
7. **Task 7**: Retrieval service + API
8. **Task 8**: AIContext integration (minimal AI touch)
9. **Task 9**: Processing status API
10. **Task 10**: E2E tests & hardening

### First Task to Implement

**Task 1: Add document ownership & status** — This is the foundation. Without `user_id` on documents, no subsequent task can enforce isolation. It requires a single Alembic migration and touches ~5 files. All other tasks depend on it.