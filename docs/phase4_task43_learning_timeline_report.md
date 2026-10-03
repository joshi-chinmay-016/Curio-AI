# Phase 4 Task 4.3 — Learning Timeline Aggregation Report

## Overview
Implemented authenticated, user-owned, paginated, and filtered **Learning Timeline Aggregation** across all sessions owned by the authenticated learner.

- **Endpoint:** `GET /api/v1/users/me/timeline`
- **Feature Category:** Factual backend persistence aggregation (read-only)
- **Alembic Head:** `7a8b9c0d1e2f` (unchanged)

---

## Files Created & Modified

| File | Type | Status | Description |
|------|------|--------|-------------|
| `backend/app/schemas/timeline.py` | Schema | Created | Pydantic schemas for `TimelineEvent` and `TimelineListResponse`, plus event constants. |
| `backend/app/repositories/timeline_repository.py` | Repository | Created | Database-level `UNION ALL` / CTE aggregation with deterministic ordering, LIMIT/OFFSET, and separate COUNT query. |
| `backend/app/services/timeline_service.py` | Service | Created | Parameter parsing, anti-enumeration checks, repository delegation, and metadata response mapping. |
| `backend/app/api/v1/sessions.py` | Router | Modified | Registered `GET /api/v1/users/me/timeline` route with auth dependency and anti-enumeration 404 handling. |
| `backend/tests/api/test_timeline.py` | Tests | Created | 36 integration tests covering authentication, ownership, events, ordering, pagination, filters, compatibility, AI boundary, and bulk performance. |

---

## Endpoint Specification

### `GET /api/v1/users/me/timeline`

#### Query Parameters:
- `page` (`int`, default `1`, min `1`): 1-indexed page number.
- `page_size` (`int`, default `20`, min `1`, max `100`): Items per page, capped at 100 in service/repository layer.
- `session_id` (`UUID`, optional): Scopes timeline events to a single owned session.
- `event_types` (`str`, optional): Comma-separated list of event types to include.
- `start` (`str`, optional): ISO 8601 datetime string; filters events at or after this timestamp.
- `end` (`str`, optional): ISO 8601 datetime string; filters events at or before this timestamp.

#### Response Schema:
```json
{
  "items": [
    {
      "event_type": "user_message",
      "timestamp": "2026-10-03T12:00:00Z",
      "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "message_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
      "entity_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
      "metadata": {
        "input_type": "TEXT",
        "content": "A binary search tree has ordered nodes..."
      }
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

---

## Event Types & Persisted Data Mapping

All 7 supported event sources are derived strictly from existing PostgreSQL tables without modifying schemas or inferring pedagogical conclusions:

| Event Type | Source Table | Timestamp | Metadata Exposed | Bounding / Protection |
|------------|--------------|-----------|------------------|-----------------------|
| `session_created` | `sessions` | `sessions.created_at` | `topic`, `source_type` | Factual persisted metadata |
| `user_message` | `messages` (`sender = 'USER'`) | `messages.created_at` | `input_type`, `content` | Content bounded to 500 characters |
| `evaluation` | `messages` JOIN `turn_evaluations` | `messages.created_at` | `correctness`, `recommended_strategy`, `recommended_difficulty` | Persisted evaluation values |
| `turn_assessment` | `turn_assessments` | `turn_assessments.created_at` | `has_learning_assessment`, `has_turn_interpretation`, `has_learning_objective`, `has_question_specification` | Boolean presence flags only; raw JSON never exposed |
| `teacher_intervention` | `teacher_intervention_logs` | `teacher_intervention_logs.created_at` | `intervention_type`, `gap`, `attempt_count`, `verification_passed` | Gap text bounded to 500 characters |
| `report_generated` | `session_reports` | `session_reports.created_at` | `understanding_score`, `mastery_level`, `concepts_mastered_count` | Persisted values; safe count via `jsonb_array_length` |
| `session_ended` | `sessions` (`ended_at IS NOT NULL`) | `sessions.ended_at` | `status` | Only present when session has ended |

*Excluded events by design:* `ai_message`, `concept_practiced`, `session_state` updates, reconstructed pause/resume events.

---

## Filtering Strategy

All filtering is executed directly at the PostgreSQL level:
1. **`session_id` Filter**: Applied in SQL via `WHERE session_id = CAST(:session_id AS uuid)`.
2. **`event_types` Filter**: Validated against `SUPPORTED_EVENT_TYPES` in the service layer (unsupported values raise HTTP 422); applied in SQL via `WHERE event_type IN (:event_type_0, ...)`.
3. **`start` and `end` Datetime Filters**: Parsed robustly (handling URL-encoded spaces and `+`, `Z` suffixes, and timezone normalization); applied in SQL via `WHERE timestamp >= :start` and `WHERE timestamp <= :end`.
4. **Combined Filters**: Multiple filters are combined with `AND`.

---

## Ordering Strategy

1. **Primary Ordering**: `timestamp ASC` (chronological).
2. **Deterministic Secondary Ordering**: `entity_id ASC NULLS LAST, event_type ASC`.
3. **Guaranteed Stability**: The tuple `(timestamp, entity_id, event_type)` is unique for any event in the timeline, ensuring repeated identical requests yield stable, deterministic ordering.

---

## Pagination & Count Implementation

- **Pagination**: Uses database-level `LIMIT :limit OFFSET :offset`.
- **Validation**: `page >= 1` enforced; `page_size` defaults to 20 and is capped at 100 (`min(max(1, page_size), 100)`).
- **Count Query**: Executed via a dedicated `SELECT COUNT(*) FROM all_events <where_clauses>` query over the exact same filtered CTE.
- **Pages Calculation**: `pages = (total + page_size - 1) // page_size if total > 0 else 0`.
- **Zero / Empty Handling**: Empty timeline or out-of-bounds page returns `items: []`, with valid total and page metadata.

---

## Ownership & Security

- **Strict Identity Enforcement**: Authentication dependency provides `current_user.id`. The client cannot pass a `user_id`.
- **SQL Ownership Enforcement**:
  - `sessions.user_id = CAST(:user_id AS uuid)`
  - `turn_assessments.user_id = CAST(:user_id AS uuid)`
  - `teacher_intervention_logs.user_id = CAST(:user_id AS uuid)`
- **Anti-Enumeration Protections**:
  - If a `session_id` is supplied and belongs to another user (foreign session), the API returns **HTTP 404** (`"Session not found"`).
  - If a `session_id` does not exist, the API returns **HTTP 404** (`"Session not found"`).
  - An owned session with 0 matching events returns **HTTP 200** with an empty list.

---

## Performance & Query Design

- **Avoid N+1 Queries**: Normal timeline retrieval uses exactly:
  1. One paginated event query
  2. One count query
- **CTE Inlining**: PostgreSQL inlines the `all_events` CTE and applies index scans on `sessions.id`, `sessions.user_id`, `messages.session_id`, `turn_assessments.session_id`, and `teacher_intervention_logs.session_id`.
- **Bounded Payloads**: Truncation (`LEFT(..., 500)`) and boolean presence flags avoid returning heavy text or raw assessment JSON blobs over the wire.

---

## Test Verification

### 1. Targeted Timeline Tests
Command:
```bash
python -m pytest backend/tests/api/test_timeline.py -v --tb=short
```
Output:
```
======================= 36 passed, 12 warnings in 4.63s =======================
```
All **36/36 tests passed**, verifying:
- Unauthenticated access returns HTTP 401.
- Cross-user data isolation and foreign session IDOR protections (HTTP 404).
- All 7 event types and factual metadata.
- Chronological and deterministic ordering.
- Default, custom, capped, and beyond-last-page pagination.
- Single, multiple, datetime, and combined filtering.
- Backward compatibility with legacy turns lacking turn assessments.
- AI boundary verification (zero LLM / CurioEngine calls).
- Bulk dataset performance (120+ events paginated correctly).

### 2. Directly Related Regression Tests
Command:
```bash
python -m pytest backend/tests/api/test_evaluation_history.py backend/tests/api/test_session_pagination.py backend/tests/api/test_session_idor.py backend/tests/api/test_teacher_intervention_api.py -v --tb=short
```
Output:
```
====================== 116 passed, 12 warnings in 18.49s ======================
```
All **116/116 directly related tests passed** with zero regressions.

---

## Database & Migration Status

- **Migration Created:** None.
- **Database Reset:** None.
- **Current Alembic Head:** `7a8b9c0d1e2f` (verified via `python -m alembic current`).

---

## AI Boundary Verification

- No calls to `CurioEngine`.
- No calls to `ChatService` AI inference.
- No calls to Groq or external LLM providers.
- No LangGraph state-graph execution.
- No dynamic mastery, learning gap, or pedagogical inference generated.
- The timeline remains a pure read-only aggregation of persisted relational data.

---

## Explicit Confirmations

- [x] No migration created
- [x] No database reset
- [x] No AI logic changed
- [x] No LangGraph changes
- [x] No CurioEngine changes
- [x] No AI/provider calls from timeline endpoint
- [x] Full 598-test baseline was NOT rerun
- [x] Timeline-specific tests passed (36/36)
- [x] Related regression tests passed (116/116)
