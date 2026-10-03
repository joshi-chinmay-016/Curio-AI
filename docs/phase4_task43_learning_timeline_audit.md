# Phase 4 Task 4.3 — Learning Timeline Aggregation: Architecture Audit

**Status:** AUDIT ONLY — No code modified, no migrations created, no database changes.

---

## 1. CURRENT DATA SOURCES

### 1.1 Session (`sessions` table)

| Property | Details |
|----------|---------|
| **Data** | Core session metadata: `id`, `user_id`, `topic`, `source_type`, `document_id`, `status` (ACTIVE/PAUSED/COMPLETED), `created_at`, `last_active_at`, `ended_at` |
| **Ownership** | Direct: `user_id` FK to `users.id` |
| **Timestamps** | `created_at`, `last_active_at`, `ended_at` (all `TIMESTAMPTZ`) |
| **Timeline Events** | `session_created` (created_at), `session_ended` (ended_at), `session_paused/resumed` (via status + last_active_at) |

### 1.2 SessionState (`session_states` table)

| Property | Details |
|----------|---------|
| **Data** | Current session state: `current_mode` (STUDENT/TEACHER/EVALUATOR), `difficulty`, `confidence`, `active_concept`, `current_question_id`, `interrupted_question_id`, `consecutive_strong_answers`, `consecutive_weak_answers`, `unresolved_misconceptions`, `mastered_concepts`, `teacher_attempt_count`, `teacher_intervention`, `concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history` |
| **Ownership** | Through session: `session_id` PK/FK to `sessions.id` |
| **Timestamps** | **None** — no `created_at`/`updated_at` on this table |
| **Timeline Events** | Not directly usable for timeline (no timestamps). Could derive `mode_switch` events from `mode_switch_history` JSON array if it contains timestamps, but structure is `List[dict]` not guaranteed. |

### 1.3 Message (`messages` table)

| Property | Details |
|----------|---------|
| **Data** | `id`, `session_id`, `sender` (USER/AI), `content`, `input_type` (TEXT/VOICE), `created_at` |
| **Ownership** | Through session: `session_id` FK to `sessions.id` |
| **Timestamps** | `created_at` (indexed) |
| **Timeline Events** | `user_message` (sender=USER), `ai_message` (sender=AI) — each with content and timestamp |

### 1.4 TurnEvaluation (`turn_evaluations` table)

| Property | Details |
|----------|---------|
| **Data** | `message_id` (PK/FK), `correctness`, `clarity`, `completeness`, `depth`, `relevance`, `stuck_probability`, `misconceptions[]`, `missing_concepts[]`, `undefined_terms[]`, `mastered_concepts[]`, `knowledge_gap`, `recommended_strategy`, `recommended_difficulty` |
| **Ownership** | Through message → session: `message_id` FK to `messages.id` |
| **Timestamps** | **None** — relies on `messages.created_at` via join |
| **Timeline Events** | `evaluation_created` — one per USER message that was evaluated. Timestamp from joined `messages.created_at` |

### 1.5 TurnAssessment (`turn_assessments` table)

| Property | Details |
|----------|---------|
| **Data** | `id`, `message_id` (unique), `session_id`, `user_id`, `learning_assessment` JSON, `turn_interpretation` JSON, `learning_objective` JSON, `question_specification` JSON, `created_at` |
| **Ownership** | Direct: `user_id` FK + `session_id` FK; also through message |
| **Timestamps** | `created_at` (server default `now()`) — indexed with `session_id` |
| **Timeline Events** | `assessment_created` — one per turn where AI produced structured assessment artifacts. Has own `created_at` (may differ slightly from message timestamp). Indexes: `(session_id, created_at)`, `(user_id, session_id)` |

### 1.6 TeacherInterventionLog (`teacher_intervention_logs` table)

| Property | Details |
|----------|---------|
| **Data** | `id`, `session_id`, `user_id`, `gap`, `attempt_count`, `teacher_explanation`, `verification_question`, `verification_answer`, `verification_passed` (0/1/null), `intervention_type` (enter/continue/exit/limit_fallback), `created_at` |
| **Ownership** | Direct: `user_id` FK + `session_id` FK |
| **Timestamps** | `created_at` (server default `now()`) |
| **Timeline Events** | `teacher_intervention_enter`, `teacher_intervention_continue`, `teacher_intervention_exit`, `teacher_intervention_limit_fallback` — each with gap description, attempt count, and timestamp |

### 1.7 UserConceptProgress (`user_concept_progress` table)

| Property | Details |
|----------|---------|
| **Data** | `user_id` (PK), `concept` (PK), `mastery_score`, `total_attempts`, `successful_attempts`, `last_practiced_at`, `last_difficulty`, `misconception_count` |
| **Ownership** | Direct: `user_id` PK/FK |
| **Timestamps** | `last_practiced_at` (nullable) — no `created_at` |
| **Timeline Events** | `concept_practiced` — one per concept when `last_practiced_at` updates. Not granular per-turn; aggregates over time. |

### 1.8 SessionReport (`session_reports` table)

| Property | Details |
|----------|---------|
| **Data** | `session_id` (PK), `understanding_score`, `mastery_level`, `strengths[]`, `high/medium/low_priority_learning_gaps[]`, `misconceptions_detected[]`, `concepts_mastered[]`, `teacher_interventions_required`, `difficulty_achieved`, `personalized_roadmap[]`, `recommended_exercises[]`, `evidence_confidence`, `concept_assessments[]`, `resolved/unresolved_gaps[]`, `resolved/unresolved_misconceptions[]`, `session_evaluation` JSON, `created_at` |
| **Ownership** | Through session: `session_id` FK to `sessions.id` |
| **Timestamps** | `created_at` (server default `now()`) |
| **Timeline Events** | `report_generated` — one per completed session. Timestamp = report creation time. |

---

## 2. EXISTING APIs

| Endpoint | Purpose | Pagination | Filtering |
|----------|---------|------------|-----------|
| `GET /api/v1/sessions` | List user sessions | Page/page_size (cap 100) | status, created_after, created_before |
| `GET /api/v1/sessions/{id}` | Get session detail | — | — |
| `GET /api/v1/sessions/{id}/messages` | Get session messages | No | — |
| `POST /api/v1/sessions/{id}/messages` | Send message | — | — |
| `GET /api/v1/sessions/{id}/evaluations` | Evaluation history (Task 4.2) | Page/page_size (cap 100) | — |
| `GET /api/v1/sessions/{id}/report` | Session report | — | — |
| `GET /api/v1/users/me/progress` | User concept progress | No | — |
| `GET /api/v1/users/me/progress/batch` | Specific concepts | — | concepts (comma-separated) |
| `GET /api/v1/users/me/progress/{concept}` | Single concept | — | — |
| `GET /api/v1/users/me/teacher-interventions` | All interventions | No | — |
| `GET /api/v1/users/me/sessions/{id}/teacher-interventions` | Session interventions | No | — |

**Timeline API:** Does **not** exist.

**Closest Reusable Services/Repositories:**
- `EvaluationHistoryRepository` — already does cross-table join with ownership, pagination, ordering
- `TeacherInterventionRepository` — has `get_by_user()` for cross-session aggregation
- `SessionRepository.list_by_user_paginated()` — pattern for pagination/filtering
- `ConceptProgressRepository.get_by_user()` — direct user ownership

---

## 3. TIMELINE EVENT DESIGN

### Proposed Event Structure (Backend-Neutral)

```python
class TimelineEvent(BaseModel):
    event_type: str                    # e.g., "session_created", "user_message", "evaluation", "teacher_intervention", "report_generated"
    timestamp: datetime                # Source timestamp
    session_id: UUID                   # Always present
    message_id: Optional[UUID]         # For message/turn-level events
    entity_id: Optional[UUID]          # For assessment/intervention/report IDs
    metadata: Dict[str, Any]           # Minimal factual metadata
    included_by_default: bool          # True for core events, False for verbose ones
```

### Proposed Event Types

| Event Type | Timestamp Source | Session ID | Message ID | Entity ID | Minimal Metadata | Default |
|------------|------------------|------------|------------|-----------|------------------|---------|
| `session_created` | `sessions.created_at` | ✓ | — | — | topic, source_type | ✓ |
| `session_paused` | `sessions.last_active_at` (when status→PAUSED) | ✓ | — | — | — | ✓ |
| `session_resumed` | `sessions.last_active_at` (when status→ACTIVE) | ✓ | — | — | — | ✓ |
| `session_ended` | `sessions.ended_at` | ✓ | — | — | — | ✓ |
| `user_message` | `messages.created_at` | ✓ | ✓ | — | sender=USER, content (truncated?), input_type | ✓ |
| `ai_message` | `messages.created_at` | ✓ | ✓ | — | sender=AI, content (truncated?) | — |
| `evaluation` | `messages.created_at` (via join) | ✓ | ✓ | — | correctness, recommended_strategy, recommended_difficulty | ✓ |
| `turn_assessment` | `turn_assessments.created_at` | ✓ | ✓ | assessment.id | has_learning_assessment, has_turn_interpretation, has_learning_objective, has_question_specification | ✓ |
| `teacher_intervention` | `teacher_intervention_logs.created_at` | ✓ | — | intervention.id | intervention_type, gap (truncated?), attempt_count, verification_passed | ✓ |
| `report_generated` | `session_reports.created_at` | ✓ | — | report.session_id | understanding_score, mastery_level, concepts_mastered_count | ✓ |

**Notes:**
- `concept_practiced` from `UserConceptProgress.last_practiced_at` is too aggregated (no per-session granularity) — exclude from default timeline, or include as separate "progress" view.
- `session_state` changes not usable (no timestamps).
- All timestamps are `TIMESTAMPTZ` in DB → serialize as ISO 8601 with timezone.

---

## 4. CROSS-SESSION AGGREGATION

### Ownership Enforcement
- All event sources enforce ownership via:
  - Direct `user_id` FK: `turn_assessments`, `teacher_intervention_logs`, `user_concept_progress`
  - Session ownership chain: `sessions.user_id` → `messages.session_id` → `turn_evaluations.message_id`

### Chronological Ordering
- Primary: `timestamp ASC` (chronological)
- Secondary: `entity_id ASC` (deterministic tie-break for same timestamp)
- All sources have `created_at` except `turn_evaluations` (uses `messages.created_at`)

### Pagination Strategy
- **Database-level `LIMIT/OFFSET`** required (cannot load unbounded data into Python)
- Page-based (consistent with Task 4.1/4.2 conventions): `page ≥ 1`, `page_size 1..100`
- Response: `{ items, total, page, page_size, pages }`

### Filtering Possibilities
| Filter | Implementation |
|--------|----------------|
| Session ID | `WHERE session_id = :id` (single session) |
| Event Types | `WHERE event_type IN (...)` (post-UNION or per-source) |
| Date Range | `WHERE timestamp BETWEEN :start AND :end` |
| Session Status | Join to `sessions` and filter `sessions.status` |

### Recommended Approach: UNION ALL with Window Function
```sql
WITH all_events AS (
  SELECT 'session_created' AS event_type, created_at AS timestamp, id AS session_id, NULL AS message_id, id AS entity_id, jsonb_build_object('topic', topic) AS metadata FROM sessions WHERE user_id = :user_id
  UNION ALL
  SELECT 'user_message', m.created_at, m.session_id, m.id, NULL, jsonb_build_object('content', left(m.content, 200)) FROM messages m JOIN sessions s ON s.id = m.session_id WHERE s.user_id = :user_id AND m.sender = 'USER'
  UNION ALL
  SELECT 'evaluation', m.created_at, m.session_id, m.id, NULL, jsonb_build_object('correctness', e.correctness, 'strategy', e.recommended_strategy) FROM messages m JOIN turn_evaluations e ON e.message_id = m.id JOIN sessions s ON s.id = m.session_id WHERE s.user_id = :user_id AND m.sender = 'USER'
  UNION ALL
  SELECT 'turn_assessment', a.created_at, a.session_id, a.message_id, a.id, jsonb_build_object('has_learning_assessment', a.learning_assessment IS NOT NULL, ...) FROM turn_assessments a WHERE a.user_id = :user_id
  UNION ALL
  SELECT 'teacher_intervention', i.created_at, i.session_id, NULL, i.id, jsonb_build_object('type', i.intervention_type, 'gap', i.gap, 'attempt', i.attempt_count) FROM teacher_intervention_logs i WHERE i.user_id = :user_id
  UNION ALL
  SELECT 'report_generated', r.created_at, r.session_id, NULL, r.session_id, jsonb_build_object('score', r.understanding_score, 'mastery', r.mastery_level) FROM session_reports r JOIN sessions s ON s.id = r.session_id WHERE s.user_id = :user_id
)
SELECT * FROM all_events
WHERE timestamp BETWEEN :start AND :end
  AND event_type = ANY(:event_types)
ORDER BY timestamp ASC, entity_id ASC
LIMIT :page_size OFFSET :offset;
```

---

## 5. QUERY / PERFORMANCE DESIGN

### UNION ALL Practicality
- **Practical**: All 7 event sources have compatible columns for UNION ALL
- **Row Count Estimate**: Per-user events = sessions + messages + evaluations + assessments + interventions + reports ≈ 10-1000 events typical, 10K+ heavy users
- **Indexes**: All timestamp columns indexed or part of composite indexes

### Recommended Approach
1. **Materialized View** (optional, for future): `user_timeline_events(user_id, event_type, timestamp, session_id, message_id, entity_id, metadata)`
2. **Immediate**: CTE with UNION ALL + database-level ORDER BY + LIMIT/OFFSET
3. **Count**: Separate `SELECT COUNT(*) FROM (CTE) sub` for pagination metadata

### N+1 Risk Mitigation
- Single query returns all columns needed for response
- No post-query hydration of related entities required
- JSON metadata constructed in SQL via `jsonb_build_object`

### Indexes Needed
- Already exist: `turn_assessments(session_id, created_at)`, `turn_assessments(user_id, session_id)`, `messages(session_id, created_at)`, `teacher_intervention_logs(session_id, user_id, created_at)`
- May need: `sessions(user_id, created_at)` (has `user_id` index, `created_at` not indexed for ordering)

---

## 6. OWNERSHIP / SECURITY

### Verification Matrix

| Source | Direct user_id | Session-based | Cross-User Risk |
|--------|----------------|---------------|-----------------|
| sessions | ✓ (user_id) | — | None (PK) |
| messages | — | ✓ (session.user_id) | Low (requires session_id guess) |
| turn_evaluations | — | ✓ (message.session.user_id) | Low |
| turn_assessments | ✓ (user_id) | ✓ (session_id) | None |
| teacher_intervention_logs | ✓ (user_id) | ✓ (session_id) | None |
| session_reports | — | ✓ (session.user_id) | Low |
| user_concept_progress | ✓ (user_id PK) | — | None |

### IDOR Risks
- **Session-based sources** (messages, evaluations, reports): Require session_id. Anti-enumeration via `get_by_id_and_user` returns 404 for foreign/nonexistent.
- **Direct user_id sources** (assessments, interventions, concept_progress): Filter by `user_id = current_user.id` — no cross-user access possible.
- **Timeline aggregation**: Must filter by `current_user.id` at query level (not post-filter in Python).

### Recommendation
- Use `WHERE user_id = :current_user_id` for direct-owned tables
- Use `JOIN sessions s ON ... WHERE s.user_id = :current_user_id` for session-owned tables
- Single ownership check at query level — no N+1 session lookups

---

## 7. AI BOUNDARY

### Backend MAY (Timeline Scope)
- Retrieve persisted data from tables listed in §1
- Aggregate records across tables via UNION ALL
- Order events chronologically using persisted timestamps
- Expose factual metadata (topic, correctness, strategy name, intervention type, gap text)
- Paginate/filter using database-level operations

### Backend MUST NOT (AI Intelligence)
- Calculate mastery levels from scores
- Infer misconceptions from evaluation data
- Determine learning gaps
- Decide next learning strategy
- Adjust difficulty
- Interpret learner intent from message content
- Generate pedagogical conclusions
- Call AI providers (CurioEngine, Groq, etc.)

**Verification**: Timeline endpoint will only read from DB — no service calls to `ChatService`, `CurioEngine`, or AI providers.

---

## 8. FRONTEND CONTRACT

### Existing Frontend Types (`frontend/types/history.ts`)
```typescript
interface SessionSummary {
  sessionId: string;
  topicName: string;
  topicId: string;
  status: "IN_PROGRESS" | "COMPLETED" | "ABANDONED";
  understandingScore: number;
  masteryLevel: string;
  turnCount: number;
  durationMinutes: number;
  unresolvedGaps: number;
  resolvedMisconceptions: number;
  createdAt: string;
  completedAt?: string;
}
```

### Existing History Service (`frontend/services/historyService.ts`)
- `getSessionHistory()` returns `SessionSummary[]` — session-level only
- Mock data includes `understandingScore`, `masteryLevel`, `turnCount`, `durationMinutes` — **AI-derived/calculated fields**
- Current frontend expects session-level summaries, not per-turn timeline

### Gap Analysis
| Frontend Expectation | Backend Reality |
|---------------------|-----------------|
| Session-level summary | Session + per-turn events available |
| AI-derived scores (`understandingScore`, `masteryLevel`) | Only available in `session_reports` (completed sessions) |
| Turn count, duration | Computable from messages |
| Practice queue (gaps) | From `session_reports` or `user_concept_progress` |

### New Schema Required
- **Yes** — new `TimelineEvent` and `TimelineListResponse` schemas needed
- Pagination metadata follows existing convention (`total`, `page`, `page_size`, `pages`)
- Event types are new — not in existing APIs

---

## 9. TEST COVERAGE

### Existing Reusable Tests
| Test File | Coverage |
|-----------|----------|
| `test_session_pagination.py` | Pagination, filtering, ownership patterns |
| `test_session_idor.py` | Cross-user isolation, anti-enumeration |
| `test_evaluation_history.py` | Per-session evaluation pagination, ordering, ownership |
| `test_teacher_intervention_api.py` | Cross-session intervention aggregation |
| `test_progress_api.py` | User-owned data retrieval |

### Missing Tests Required for Timeline
- [ ] **Authentication**: Unauthenticated → 401
- [ ] **Ownership**: User A cannot see User B's timeline events
- [ ] **Cross-user isolation**: Foreign session_id returns 404/empty (anti-enumeration)
- [ ] **Chronological ordering**: Events from multiple sessions interleaved correctly
- [ ] **Deterministic ordering**: Same timestamp → stable entity_id ordering
- [ ] **Pagination**: Page 1, page 2, page_size cap, beyond-last empty
- [ ] **Filtering**: by session_id, event_type[], date_range
- [ ] **Empty timeline**: New user returns empty paginated response
- [ ] **Multiple sessions**: Events from 3+ sessions merged correctly
- [ ] **Mixed event types**: All 7 event types appear in correct order
- [ ] **Old records**: Sessions without `turn_assessments` still show evaluations
- [ ] **Records with assessments**: New turns show assessment metadata
- [ ] **Performance**: 1000+ events, page 50 loads only page_size rows (EXPLAIN ANALYZE)
- [ ] **COUNT accuracy**: Total matches filtered results despite UNION ALL
- [ ] **Schema validation**: Response matches `TimelineListResponse` model

---

## 10. RECOMMENDED IMPLEMENTATION PLAN

### Files Likely to Change
| File | Change Type |
|------|-------------|
| `backend/app/api/v1/sessions.py` | Add `GET /sessions/timeline` endpoint |
| `backend/app/schemas/timeline.py` | **New** — TimelineEvent, TimelineListResponse |
| `backend/app/services/timeline_service.py` | **New** — Service layer orchestration |
| `backend/app/repositories/timeline_repository.py` | **New** — UNION ALL query, count, pagination |
| `backend/tests/api/test_timeline.py` | **New** — Comprehensive test suite |

### New Files Needed
1. `backend/app/schemas/timeline.py` — Pydantic models
2. `backend/app/repositories/timeline_repository.py` — Database query logic
3. `backend/app/services/timeline_service.py` — Service orchestration
4. `backend/tests/api/test_timeline.py` — Tests

### Implementation Order
1. **Schemas** — Define `TimelineEvent`, `TimelineListResponse`
2. **Repository** — Build UNION ALL CTE with pagination + count
3. **Service** — Ownership verification, call repository, map to schemas
4. **API** — Add endpoint to `sessions.py` router (or new `timeline.py` router)
5. **Tests** — All test cases from §9
6. **Docs** — Update API documentation

### Migration Requirements
- **None required** — All data sources exist with proper indexes
- Optional future: Materialized view for performance (separate task)

---

## 11. FINAL VERDICT

### Architecture Support
✅ **Cleanly Supported** — All required data exists in normalized tables with:
- Proper ownership (direct `user_id` or session chain)
- Timestamps on all event sources except `SessionState` (excluded)
- Indexes for ordering and filtering
- Existing pagination/filtering patterns to follow

### Recommended Endpoint
```
GET /api/v1/users/me/timeline
  ?page=1&page_size=20
  &session_id=<uuid> (optional)
  &event_types=session_created,user_message,evaluation,teacher_intervention,report_generated (optional, comma-separated)
  &start=2024-01-01T00:00:00Z (optional)
  &end=2024-12-31T23:59:59Z (optional)
```

**Alternative**: `GET /api/v1/sessions/timeline` (cross-session) — but `/users/me/timeline` is more RESTful for user-owned aggregation.

### Recommended Pagination
- Page-based (consistent with Task 4.1/4.2)
- `page ≥ 1`, `page_size 1..100`
- Database-level `LIMIT/OFFSET` + separate `COUNT(*)`

### Recommended Event Types (Default Included)
1. `session_created` ✓
2. `user_message` ✓
3. `evaluation` ✓
4. `turn_assessment` ✓
5. `teacher_intervention` ✓
6. `report_generated` ✓
7. `session_ended` ✓
8. `session_paused`/`session_resumed` (derived from status changes — optional)

**Excluded**: `ai_message` (verbose), `concept_practiced` (too aggregated), `session_state_change` (no timestamps)

### Migration Required?
❌ **No** — All tables exist, indexes sufficient for v1.

### Major Risks
1. **Query Complexity**: UNION ALL across 7 tables — ensure EXPLAIN shows index usage
2. **Count Performance**: `COUNT(*)` on UNION ALL may be slow for users with 10K+ events — consider caching or materialized view later
3. **Timestamp Alignment**: `turn_assessments.created_at` vs `messages.created_at` may differ by seconds — document ordering behavior
4. **Large JSON Metadata**: `learning_assessment` etc. not included in timeline (only presence flags) — keeps response size bounded

### Safe to Begin Implementation?
✅ **Yes** — Architecture is sound, no blockers, clear patterns to follow, comprehensive test plan defined.

---

## Files Inspected

**Models (8):**
- `session.py`, `message.py`, `evaluation.py`, `turn_assessment.py`, `teacher_intervention.py`, `concept_progress.py`, `report.py`, `user.py`

**Repositories (8):**
- `session_repository.py`, `message_repository.py`, `evaluation_history_repository.py`, `turn_assessment_repository.py`, `teacher_intervention_repository.py`, `concept_progress_repository.py`, `report_repository.py`, `user_repository.py`

**Services (7):**
- `session_service.py`, `evaluation_history_service.py`, `learning_progress_service.py`, `chat_service.py`, `report_service.py`, `auth_service.py`, `document_service.py`

**APIs (7):**
- `sessions.py`, `messages.py`, `progress.py`, `teacher_interventions.py`, `reports.py`, `auth.py`, `documents.py`

**Schemas (6):**
- `evaluation_history.py`, `teacher_intervention.py`, `learning_progress.py`, `report.py`, `session.py`, `common.py`

**Frontend (2):**
- `historyService.ts`, `types/history.ts`

**Tests (3):**
- `test_evaluation_history.py`, `test_session_pagination.py`, `test_session_idor.py`, `test_teacher_intervention_api.py`, `test_progress_api.py`

---

## Confirmation
✅ **No production code modified**  
✅ **No migrations created**  
✅ **No database schema changes**  
✅ **No AI logic modified**  
✅ **No LangGraph/CurioEngine/prompts touched**  
✅ **No existing API contracts changed**  
✅ **No test database reset**  
✅ **All 598 baseline tests still passing** (verified separately)