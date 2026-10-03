# Phase 4 Task 4.2 — Evaluation History API

## Overview
Implemented authenticated, user-owned, paginated Evaluation History API for a specific session.

**Endpoint:** `GET /api/v1/sessions/{session_id}/evaluations`

## Files Modified

| File | Status |
|------|--------|
| `backend/app/api/v1/sessions.py` | Modified — Added endpoint (lines 190-215) |
| `backend/app/services/evaluation_history_service.py` | Modified — Applied pagination bounds in service layer |
| `backend/tests/api/test_evaluation_history.py` | Created — 30 comprehensive tests |

**Pre-existing files (no changes):**
- `backend/app/repositories/evaluation_history_repository.py`
- `backend/app/schemas/evaluation_history.py`
- `backend/app/models/evaluation.py`
- `backend/app/models/turn_assessment.py`
- `backend/app/models/message.py`

## Response Schema

```json
{
  "items": [
    {
      "message": {
        "message_id": "uuid",
        "session_id": "uuid",
        "sender": "USER",
        "content": "string",
        "created_at": "datetime"
      },
      "evaluation": {
        "correctness": 0.8,
        "clarity": 0.7,
        "completeness": 0.75,
        "depth": 0.6,
        "relevance": 1.0,
        "stuck_probability": 0.1,
        "misconceptions": [],
        "missing_concepts": [],
        "undefined_terms": [],
        "mastered_concepts": ["concept1"],
        "knowledge_gap": null,
        "recommended_strategy": "PROBE_WHY",
        "recommended_difficulty": 2
      },
      "assessment": {
        "id": "uuid",
        "message_id": "uuid",
        "session_id": "uuid",
        "user_id": "uuid",
        "learning_assessment": {...},
        "turn_interpretation": {...},
        "learning_objective": {...},
        "question_specification": {...},
        "created_at": "datetime"
      } | null
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

## Database Query Strategy

- **INNER JOIN** `messages` → `turn_evaluations` (only USER messages with evaluations)
- **LEFT OUTER JOIN** `turn_assessments` (preserves old turns without assessments)
- Ownership enforced via `sessions.user_id = :user_id` in query
- Ordering: `messages.created_at ASC, messages.id ASC` (deterministic)
- Pagination: Database-level `LIMIT/OFFSET`
- Count: Separate `COUNT(*)` without `turn_assessments` join (prevents duplicate multiplication)

## Pagination

- `page ≥ 1`, `page_size ≥ 1`, `page_size` capped at 100
- Response echoes capped `page_size`
- `pages = ceil(total / page_size)` (0 when total=0)
- Follows Task 4.1 conventions exactly

## Ownership & Anti-Enumeration

| Scenario | Response |
|----------|----------|
| Unauthenticated | 401 |
| Owner | 200 |
| Foreign session | 404 |
| Nonexistent session | 404 |
| Inactive user | 400 |

## Backward Compatibility

- Old turns (pre-migration `7a8b9c0d1e2f`) have `TurnEvaluation` only → `assessment: null`
- New turns have both `TurnEvaluation` + `TurnAssessment` → full assessment data
- Mixed sessions return all evaluations chronologically

## Test Coverage (30 new tests)

- **Authentication:** 2 tests (401 unauthenticated)
- **Owner Access:** 4 tests (empty, eval-only, with assessment, mixed old/new)
- **Pagination:** 7 tests (defaults, page 2, custom size, cap at 100, min bounds, beyond-last)
- **Ordering:** 2 tests (chronological, deterministic same-timestamp)
- **Cross-User Isolation:** 4 tests (404 anti-enumeration with/without assessments)
- **Nonexistent Session:** 1 test (404)
- **Response Schema:** 4 tests (structure, eval-only, with assessment, nested JSON preservation)
- **Edge Cases:** 5 tests (AI messages excluded, no-eval excluded, count correctness, invalid UUID, inactive user)
- **AI Boundary:** 1 test (no AI calls)
- **Performance:** 1 test (1000 evaluations, page 50 loads only 10 rows)

## Verification

```bash
# Run all new tests
pytest backend/tests/api/test_evaluation_history.py -v

# Regression suite
pytest backend/tests/api/test_evaluation_history.py \
       backend/tests/api/test_session_idor.py \
       backend/tests/api/test_session_pagination.py \
       backend/tests/api/test_phase3_api.py \
       backend/tests/services/test_turn_assessment_persistence.py \
       backend/tests/services/test_chat_service.py -v

# Full suite count
pytest backend/tests/ --collect-only  # 598 tests collected
```

## Results

- **598 tests collected** (568 baseline + 30 new)
- **All 598 pass**
- No migrations required
- No database resets
- No AI logic modified
- No AI/provider calls from endpoint

## Performance Notes

- Single query with JOINs (no N+1)
- Database-level LIMIT/OFFSET and COUNT
- Tested with 1000 evaluations: page 50 returns in <100ms
- For production scale (>10K evaluations/session), consider:
  ```sql
  CREATE INDEX ix_messages_session_sender_created 
  ON messages (session_id, sender, created_at, id);
  ```

## Limitations

- Only USER messages with TurnEvaluation appear (by design)
- page_size cap of 100 enforced in service layer
- Assessment JSON is opaque; no backend transformation of pedagogical content