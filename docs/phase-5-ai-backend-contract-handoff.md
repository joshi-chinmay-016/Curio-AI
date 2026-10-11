# Phase 5 AI–Backend Contract Handoff

**Prepared for:** Chinmay (feature/ai branch)  
**Date:** 2026-10-10  
**Backend Branch:** main (Phase 5 complete)  
**Status:** All 240 focused Phase 5 tests passing

---

## 1. AIContext Construction (ChatService)

**File:** `backend/app/services/chat_service.py`

| Step | Location | Description |
|------|----------|-------------|
| **Determine retrieval trigger** | Lines 856-881 | `_retrieve_source_context()` checks: `user_id` present, `session.source_type == "DOCUMENT"`, `session.document_id` exists, query non-empty |
| **Call retrieval service** | Lines 889-894 | `self.retrieval_service.retrieve(db, user_id, query.strip(), document_ids=[session_doc_id])` |
| **Handle empty results** | Lines 896-903 | Returns `{"chunks": [], "total_matches": 0, "query_text": ..., "retrieval_status": "no_results"}` |
| **Handle retrieval errors** | Lines 927-956 | Catches `RetrievalError` → returns `"retrieval_status": "error"` with `error_message`, `error_retryable`; catches generic `Exception` → `"retrieval_status": "error"`, `error_retryable: false` |
| **Construct source_context** | Lines 905-924 | Serializes `RetrievedChunk` dataclasses to dicts with fields: `chunk_id`, `document_id`, `chunk_index`, `text`, `start_char`, `end_char`, `chunk_metadata`, `similarity_score` |
| **Construct AIContext** | Lines 407-423 | `AIContext(session=session_info, current_state=current_state, conversation=conversation, learning_context=learning_context)` then `context.source_context = source_context` |
| **Invoke CurioEngine** | Line 426 | `ai_result: AIResult = self.ai_engine.process(context)` |

**Retrieval Trigger Conditions** (from `_retrieve_source_context` docstring, lines 863-870):
- Session has a `document_id` (single document mode)
- Session `source_type` is `"DOCUMENT"`
- User is authenticated (`user_id` present)
- Query is non-empty

**No retrieval for:** `GENERAL` source mode, missing `document_id`, unauthenticated requests, empty/whitespace queries.

---

## 2. Exact `source_context` Payload Structure

**Implementation:** `backend/app/services/chat_service.py:898-925`

### Success Case (`retrieval_status: "success"`)
```json
{
  "chunks": [
    {
      "chunk_id": "uuid-string",
      "document_id": "uuid-string",
      "chunk_index": 0,
      "text": "Retrieved passage text...",
      "start_char": 0,
      "end_char": 512,
      "chunk_metadata": {"page_number": 1} | null,
      "similarity_score": 0.89
    }
  ],
  "total_matches": 3,
  "query_text": "user question",
  "top_k": 5,
  "retrieval_status": "success"
}
```

### No Results (`retrieval_status: "no_results"`)
```json
{
  "chunks": [],
  "total_matches": 0,
  "query_text": "user question",
  "retrieval_status": "no_results"
}
```

### Retrieval Error (`retrieval_status: "error"`)
```json
{
  "chunks": [],
  "total_matches": 0,
  "query_text": "user question",
  "retrieval_status": "error",
  "error_message": "Embedding provider unavailable",
  "error_retryable": true
}
```

**Fields actually created by code** (lines 908-916):
| Field | Type | Source |
|-------|------|--------|
| `chunk_id` | string | `str(chunk.chunk_id)` |
| `document_id` | string | `str(chunk.document_id)` |
| `chunk_index` | int | `chunk.chunk_index` |
| `text` | string | `chunk.text` |
| `start_char` | int \| null | `chunk.start_char` |
| `end_char` | int \| null | `chunk.end_char` |
| `chunk_metadata` | object \| null | `chunk.chunk_metadata` |
| `similarity_score` | float | `chunk.similarity_score` |
| `total_matches` | int | `result.total_matches` |
| `query_text` | string | `result.query_text` |
| `top_k` | int | `result.top_k` |
| `retrieval_status` | string | `"success" \| "no_results" \| "error"` |
| `error_message` | string | Only on error |
| `error_retryable` | bool | Only on error |

**Absent / Unverified:**
- Page numbers: `chunk_metadata` may contain `page_number` if extraction provided it, but not guaranteed
- Document citations in API response: **Not present** — `source_context` reaches AI engine but is not echoed in `ChatTurnResponse`
- Source references in `AIResult`: Not populated by backend; depends on AI engine

---

## 3. Current AI Contract Definitions

| Contract | Module Path | Key Fields |
|----------|-------------|------------|
| `AIContext` | `backend/app/ai/schemas.py:866` | `session: SessionInfo`, `current_state: SessionState`, `conversation: ConversationContext`, `learning_context: LearningContext`, `source_context: Optional[Dict[str, Any]]` |
| `AIResult` | `backend/app/ai/schemas.py:786` | `evaluation: TurnEvaluation`, `decision: LearningDecision`, `response: AIResponse`, `state_updates: StateUpdates`, `session_evaluation?: SessionEvaluation`, `learning_report?: LearningReport`, `turn_interpretation?: TurnInterpretation`, `learning_objective?: LearningObjective`, `question_specification?: QuestionSpecification`, `concept_model?: ConceptModel`, `learner_model?: LearnerModel`, `learning_assessment?: LearningAssessment` |
| `LearningAssessment` | `backend/app/ai/answer_intelligence/schemas.py` (imported) | Not directly constructed by backend; passed through from AI engine |
| `StateUpdates` | `backend/app/ai/schemas.py:578` | `active_concept?`, `interrupted_question?`, `mastered_concepts?`, `unresolved_misconceptions?`, `teacher_intervention?`, `current_question?`, `current_mode?`, `difficulty?`, `confidence?`, `concept_mastery?`, `consecutive_failures?`, `consecutive_successes?`, `teacher_attempt_count?`, `recent_strategy_history?`, `misconception_counts?`, `mode_switch_history?`, `concept_model?`, `learner_model?`, `current_objective?`, `latest_interpretation?`, `question_specification?` |

**Construction:** `ChatService` constructs `AIContext` directly (no builder/helper) at lines 407-423. The `source_context` dict is assigned to the optional `source_context` field after base construction.

**Transformations:** None — `source_context` is passed as-is dict. The `AIContext` model validator (`adapt_legacy_or_flat_inputs`) accepts nested or flat inputs but backend always uses nested.

**Schema locations:**
- `AIContext`, `AIResult`, `StateUpdates`: `backend/app/ai/schemas.py`
- `LearningAssessment`: `backend/app/ai/answer_intelligence/schemas.py` (imported at schemas.py:6)
- `ChatTurnResponse` (API response): `backend/app/schemas/message.py:50`

---

## 4. Phase 5 Test Fixtures & Evidence

**File:** `backend/tests/services/test_rag_integration.py`

| Test | Lines | Demonstrates |
|------|-------|--------------|
| `test_retrieved_passages_included_in_aicontext` | 210-255 | Successful retrieval → `source_context` with chunks, `"retrieval_status": "success"`, `total_matches >= 1` |
| `test_aicontext_receives_serializable_context` | 257-306 | `source_context` is pure dict (no ORM), `json.dumps()` succeeds, chunk fields are correct types |
| `test_rag_disabled_chat_follows_existing_behavior` | 308-338 | `GENERAL` source mode → `source_context` is `None` or `{}` |
| `test_empty_retrieval_results_do_not_break_chat` | 340-380 | Zero-similarity vectors → `"retrieval_status": "no_results"`, empty chunks, chat continues |
| `test_selected_document_filter_respected` | 382-423 | Only chunks from `session.document_id` retrieved |
| `test_cross_user_documents_cannot_enter_source_context` | 425-465 | User B cannot retrieve User A's document → `total_matches == 0` |
| `test_invalid_document_selection_handled_safely` | 467-502 | Non-existent `document_id` → `no_results`, chat continues |
| `test_retrieval_provider_failure_fallback_policy` | 504-552 | `RetrievalError` raised → `"retrieval_status": "error"`, `error_retryable: true`, chat continues |
| `test_persistence_remains_intact` | 554-590 | Message, evaluation, session state persistence all called |
| `test_teacher_mode_compatibility` | 592-657 | Teacher Mode state hydrated and persisted with RAG |
| `test_native_vector_column_used_by_retrieval` | 660-705 | Retrieval works with only `embedding_vector` (no legacy JSON) |
| `test_source_references_correspond_to_retrieved_chunks` | 708-758 | Retrieved chunks match query similarity ordering |

**File:** `backend/tests/services/test_chat_service.py`

| Test | Lines | Demonstrates |
|------|-------|--------------|
| `test_send_message_invokes_curio_engine_with_canonical_context` | 150-208 | `CurioEngine.process(context)` called with canonical `AIContext`; verifies all nested fields |

**File:** `backend/tests/api/test_embeddings.py`

| Test | Lines | Demonstrates |
|------|-------|--------------|
| `test_persist_embeddings_new` | ~389 | Embeddings persisted to both `embedding` (JSON) and `embedding_vector` (pgvector) |
| `test_force_regenerate` | ~439 | `force_regenerate=True` overwrites existing embeddings |
| `test_skip_existing_embeddings` | ~401 | Idempotent: skips chunks with valid embeddings from same model |

**File:** `backend/tests/api/test_document_status.py`

| Test | Demonstrates |
|------|--------------|
| `test_processed_status` | `GET /documents/{id}` returns `status: "PROCESSED"`, `page_count`, `chunk_count` |
| `test_failed_status_with_safe_error` | `processing_error` not exposed in API response |
| `test_chunk_count_persisted` | `chunk_count` reflects persisted chunks (0 if pipeline not run) |

---

## 5. Response Path: AIResult → ChatTurnResponse

**Trace** (`backend/app/services/chat_service.py`):

| Step | Code Location | What Happens |
|------|---------------|--------------|
| 1. Persist AI message | Lines 433-438 | `message_repo.create_message("AI", response.content)` |
| 2. Persist turn evaluation | Lines 441-456 | Maps `TurnEvaluation` → `TurnEvaluationResponse` → `message_repo.create_evaluation()` |
| 3. Persist turn assessment | Lines 458-485 | If `ai_result.learning_assessment` etc. present → `turn_assessment_repo.create_assessment()` |
| 4. Update session state | Lines 487-661 | Merges `StateUpdates` with existing DB state |
| 4. Persist teacher intervention | Lines 666-729 | Creates/updates `TeacherInterventionLog` |
| 5. Sync concept progress | Lines 958-1017 | Updates `UserConceptProgress` from `StateUpdates.concept_mastery` |
| 6. Build response | Lines 819-879 | Returns `ChatTurnResponse` |

**ChatTurnResponse Definition** (`backend/app/schemas/message.py:50-54`):
```python
class ChatTurnResponse(BaseModel):
    user_message: MessageResponse
    ai_message: MessageResponse
    evaluation: TurnEvaluationResponse
    decision: LearningDecisionResponse
```

**What IS returned to frontend:**
- `user_message` / `ai_message` (content, sender, timestamps)
- `evaluation` (scores, misconceptions, knowledge_gap, recommended_strategy)
- `decision` (next_mode, strategy, difficulty, confidence, reason, active_concept, termination flags)

**What is NOT returned:**
- `source_context` — not in response
- Document/chunk IDs or citations — not in response
- Page numbers — not in response
- `learning_assessment`, `turn_interpretation`, `learning_objective`, `question_specification` — persisted but not returned
- `session_evaluation`, `learning_report` — not returned

**Evidence Flow:**
| Stage | Who Sees Source Context |
|-------|------------------------|
| Supplied to AI | ✅ `AIContext.source_context` |
| Identified by AI | ⚠️ Up to AI engine (not verified) |
| Persisted by backend | ✅ `TurnAssessment` stores AI-generated structured data |
| Returned by API | ❌ Not in `ChatTurnResponse` |

---

## 6. Compatibility Facts & Unverified Items

### ✅ Confirmed Compatible (Backend Implemented & Tested)

| Item | Evidence |
|------|----------|
| `AIContext.source_context` dict payload | `test_aicontext_receives_serializable_context` (line 290-306) |
| Retrieval only for `DOCUMENT` source mode | `test_rag_disabled_chat_follows_existing_behavior` (line 338) |
| Ownership filtering at retrieval layer | `test_cross_user_documents_cannot_enter_source_context` (line 425) |
| Empty results → `"no_results"` | `test_empty_retrieval_results_do_not_break_chat` (line 377) |
| Retrieval errors → `"error"` + `error_retryable` | `test_retrieval_provider_failure_fallback_policy` (line 549) |
| `CurioEngine.process(context)` called with canonical `AIContext` | `test_send_message_invokes_curio_engine_with_canonical_context` (line 182) |
| `StateUpdates` merge preserves DB values when `None` | `test_send_message_merges_partial_state_updates` (line 210) |
| Teacher Mode state hydrated & persisted with RAG | `test_teacher_mode_compatibility` (line 592) |
| Native `embedding_vector` column used by retrieval | `test_native_vector_column_used_by_retrieval` (line 660) |
| 240 focused tests pass | `pytest` runs (144 + 96 = 240) |

---

### ⚠️ Unverified / Requires Comparison with Chinmay's `feature/ai`

| Item | Status |
|------|--------|
| `AIContext` / `AIResult` / `StateUpdates` schema exact match | Backend uses current `schemas.py`; must compare against `feature/ai` branch |
| `LearningAssessment` schema compatibility | Backend persists if present; must verify Chinmay's schema |
| `AIResponse` includes source citations | **Not implemented** — backend does not add citations to `ChatTurnResponse` |
| `source_context` consumed by AI engine prompting | Backend delivers; Chinmay's engine must consume |
| Multi-document retrieval | **Not supported** — single `document_id` per session |
| `source_references` in API response | **Missing** — `ChatTurnResponse` has no citation fields |
| `LearningAssessment` → `TurnAssessment` persistence | Implemented (lines 458-485) but schema must match |

---

## 7. Key File References

| Purpose | File | Key Lines |
|---------|------|-----------|
| Retrieval trigger & payload construction | `backend/app/services/chat_service.py` | 850-956 (`_retrieve_source_context`) |
| AIContext construction & engine call | `backend/app/services/chat_service.py` | 407-426 |
| AIResult handling & persistence | `backend/app/services/chat_service.py` | 426-700 |
| AIContext schema | `backend/app/ai/schemas.py` | 866-950 |
| AIResult schema | `backend/app/ai/schemas.py` | 786-798 |
| StateUpdates schema | `backend/app/ai/schemas.py` | 578-608 |
| RetrievalService SQL | `backend/app/retrieval/service.py` | 204-222 |
| RetrievedChunk dataclass | `backend/app/retrieval/service.py` | 24-34 |
| Test fixtures | `backend/tests/services/test_rag_integration.py` | 45-100 |
| RAG integration tests | `backend/tests/services/test_rag_integration.py` | 210-552 |
| ChatService integration tests | `backend/tests/services/test_chat_service.py` | 150-208 |

---

## 8. Final Summary for Chinmay

**What works today:**
- Backend delivers `source_context` as serializable dict with chunks, similarity scores, metadata
- Retrieval respects ownership, document filter, source mode
- Graceful degradation for no-results and provider errors
- `CurioEngine.process(context)` receives canonical `AIContext`
- All 240 focused Phase 5 tests pass

**What needs your attention:**
1. **Add citation fields to `ChatTurnResponse`** if UI needs document/chunk references
2. **Verify `AIContext`/`AIResult`/`StateUpdates` schema match** against `feature/ai` branch
3. **Implement RAG prompting** in your engine using `context.source_context.chunks`
4. **Decide on multi-document support** — currently single-doc only

**No blocking defects.** Backend contract is stable and ready for integration.