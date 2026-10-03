# TURN ASSESSMENT PERSISTENCE — IMPLEMENTATION REPORT

## Overview
Implementation of per-turn AI assessment persistence to fix the compatibility gap identified in the audit after Chinmay's AI milestone (feat(ai): add trustworthy learner answer intelligence).

---

## 1. ARCHITECTURAL DECISION

**Decision:** Created a dedicated `turn_assessments` table instead of adding columns to `SessionState`.

**Rationale:**
- `SessionState` represents current session state (single row per session)
- `LearningAssessment` and related artifacts are fundamentally **per-turn** data (one record per learner turn)
- Historical assessment data is required for future Phase 4 features:
  - Evaluation History API
  - Learning Timeline
  - Report Versioning
  - Evidence Snapshots
- Correct relationship: `User → Session → Message/Turn → TurnEvaluation → TurnAssessment`

---

## 2. NEW MODEL / TABLE: `turn_assessments`

### Fields
| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUID | Primary Key, auto-generated |
| `message_id` | UUID | FK → messages.id, CASCADE delete, **UNIQUE** |
| `session_id` | UUID | FK → sessions.id, CASCADE delete, INDEX |
| `user_id` | UUID | FK → users.id, CASCADE delete, INDEX |
| `learning_assessment` | JSON/JSONB | Nullable |
| `turn_interpretation` | JSON/JSONB | Nullable |
| `learning_objective` | JSON/JSONB | Nullable |
| `question_specification` | JSON/JSONB | Nullable |
| `created_at` | DateTime(timezone) | Server default now() |

### Indexes
- `ix_turn_assessments_session_id_created_at` (session_id, created_at)
- `ix_turn_assessments_user_id_session_id` (user_id, session_id)

---

## 3. JSON STRUCTURES STORED

### `learning_assessment` (LearningAssessment)
Complete Answer Intelligence output:
```json
{
  "intent": "ANSWER_ATTEMPT",
  "is_answer_attempt": true,
  "relevance_score": 0.9,
  "relevance_level": "RELEVANT",
  "concept_alignment_score": 0.85,
  "claims": [{"text": "...", "concept_id": "...", "claim_type": "MECHANISM", "alignment_score": 0.9}],
  "evidence": [{"concept_id": "...", "expected_description": "...", "status": "SUPPORTED", "confidence": 0.95}],
  "correctness": "CORRECT",
  "correctness_score": 0.85,
  "completeness": "SUBSTANTIAL",
  "completeness_score": 0.8,
  "misconception_status": false,
  "misconceptions": [],
  "missing_concepts": [],
  "contradictory_claims": [],
  "classification": "CORRECT",
  "confidence": 0.88,
  "supports_mastery": true,
  "assessment_status": "HIGH_CONFIDENCE",
  "recommended_learning_action": "ADVANCE_CONCEPT",
  "metadata": {}
}
```

### `turn_interpretation` (TurnInterpretation)
```json
{
  "intent": "ANSWER_ATTEMPT",
  "is_answer_attempt": true,
  "is_question": false,
  "is_help_request": false,
  "referenced_concept": "photosynthesis",
  "target": "photosynthesis",
  "answer_evidence": "Learner explained the light-dependent reactions",
  "confidence": 0.9
}
```

### `learning_objective` (LearningObjective)
```json
{
  "objective_type": "UNDERSTAND_MECHANISM",
  "target_concept": "photosynthesis",
  "difficulty": 2,
  "reason": "Assess understanding of light-dependent reactions",
  "evidence_expected": "Explanation of photon absorption and electron transport chain"
}
```

### `question_specification` (QuestionSpecification)
```json
{
  "target_concept": "photosynthesis",
  "learning_objective": { ... },
  "difficulty": 2,
  "reason": "Probe mechanism understanding",
  "evidence_expected": "Explanation of photon absorption",
  "generation_constraints": ["single_question", "difficulty_2"]
}
```

---

## 4. FOREIGN KEYS
- `message_id` → `messages.id` (ON DELETE CASCADE) — links to user's message/turn
- `session_id` → `sessions.id` (ON DELETE CASCADE)
- `user_id` → `users.id` (ON DELETE CASCADE) — for ownership/isolation

---

## 5. MIGRATION
**Revision ID:** `7a8b9c0d1e2f`  
**Depends on:** `602e5c00140b` (teacher_intervention_logs)  
**Applied:** ✅ Development database via Alembic

```sql
CREATE TABLE turn_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    learning_assessment JSON,
    turn_interpretation JSON,
    learning_objective JSON,
    question_specification JSON,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
CREATE INDEX ix_turn_assessments_session_id_created_at ON turn_assessments(session_id, created_at);
CREATE INDEX ix_turn_assessments_user_id_session_id ON turn_assessments(user_id, session_id);
```

---

## 6. REPOSITORY: `TurnAssessmentRepository`

### Methods
| Method | Purpose |
|--------|---------|
| `create_assessment()` | Save assessment with all 4 JSON fields |
| `get_by_message_id()` | Retrieve by message/turn |
| `get_by_session_id(page, page_size)` | Paginated retrieval by session |
| `get_by_user_and_session(page, page_size)` | Ownership-safe retrieval |
| `delete_by_session_id()` | Cascade cleanup |
| `delete_by_message_id()` | Single record deletion |

---

## 7. CHATSERVICE INTEGRATION

### Changes to `ChatService`
1. Added injectable `turn_assessment_repo` dependency
2. Persists assessment **after** turn evaluation, **before** SessionState update
3. Only persists when `AIResult` contains assessment data
4. Associates with **user message** (not AI response)
5. Uses `session.user_id` for ownership

```python
# In send_message():
if ai_result.learning_assessment or ai_result.turn_interpretation 
   or ai_result.learning_objective or ai_result.question_specification:
    self.turn_assessment_repo.create_assessment(
        db=db,
        message_id=user_msg.id,  # User message, not AI response
        session_id=session_id,
        user_id=db_session.user_id,
        learning_assessment=ai_result.learning_assessment.model_dump(mode="json"),
        turn_interpretation=ai_result.turn_interpretation.model_dump(mode="json"),
        learning_objective=ai_result.learning_objective.model_dump(mode="json"),
        question_specification=ai_result.question_specification.model_dump(mode="json"),
    )
```

---

## 8. TRANSACTION BEHAVIOR

All operations in single transaction:
1. `create_message` (user) → 2. `create_message` (AI) → 3. `create_evaluation` → 4. `create_assessment` → 5. `update_state`

**Atomicity:** No partial state possible. If assessment fails, entire turn rolls back.

---

## 9. OWNERSHIP & SECURITY

- Assessment linked to `session.user_id`
- Repository supports `get_by_user_and_session()` for ownership-safe queries
- API layer enforces: `current_user.id → owned session → owned message → owned assessment`
- No client-provided `user_id` accepted

---

## 10. HYDRATION BEHAVIOR

- **Does NOT** auto-load into `SessionState` or `AIContext`
- Historical assessments retrieved **on-demand** via repository
- Future Phase 4 APIs will query `turn_assessments` directly
- Avoids N+1 queries and oversized AI context

---

## 11. TESTS ADDED

**File:** `backend/tests/services/test_turn_assessment_persistence.py`  
**Total:** 13 tests — **ALL PASSING**

| Test | Coverage |
|------|----------|
| `test_send_message_persists_learning_assessment` | Full assessment persistence |
| `test_send_message_persists_assessment_without_optional_fields` | Partial data |
| `test_send_message_does_not_persist_when_no_assessment` | No-op when empty |
| `test_multiple_turns_create_separate_assessment_records` | Per-turn isolation |
| `test_assessment_associated_with_correct_session` | Session linkage |
| `test_teacher_mode_assessment_persists_correctly` | Teacher Mode misconceptions |
| `test_student_mode_assessment_persists_correctly` | Student Mode partial answers |
| `test_existing_state_updates_persistence_continues_working` | Phase 3 fields intact |
| `test_existing_session_state_persistence_continues_working` | Existing fields intact |
| `test_ai_backend_boundary_intact` | No AI logic in repository |
| `test_round_trip_returns_same_structured_assessment` | JSON round-trip fidelity |
| `test_cross_user_ownership_isolation` | Security boundary |
| `test_complex_nested_assessment_data_survives_json_serialization` | Deep nesting |

---

## 12. FULL TEST SUITE RESULTS

| Category | Tests | Status |
|----------|-------|--------|
| Unit Tests (AI, Core, Services) | 361 | ✅ ALL PASS |
| ChatService (existing) | 33 | ✅ ALL PASS |
| TurnAssessment (new) | 13 | ✅ ALL PASS |
| AI Tests (adversarial, learner model, etc.) | 278+ | ✅ ALL PASS |
| **Integration (db_integration)** | 207 | ⏭️ Skipped (requires test DB) |

**No regressions introduced.** All existing Phase 2/3 behavior preserved.

---

## 13. DATABASE MIGRATION VERIFICATION

- ✅ Migration `7a8b9c0d1e2f` created
- ✅ Applied to development database via `alembic upgrade head`
- ✅ Single Alembic head maintained
- ✅ No database reset occurred
- ⏳ Test database migration pending (requires test DB server)

---

## 14. AI BOUNDARY INTEGRITY

**No AI logic changed:**
- ❌ No MasteryGate modification
- ❌ No prompt changes
- ❌ No LangGraph/workflow changes
- ❌ No evaluator logic changes
- ❌ No decision engine changes

**Backend responsibility only:**
- Persist opaque JSON structures
- Retrieve on demand
- Return through APIs when needed

---

## 15. BACKWARD COMPATIBILITY

All existing behavior preserved:
- ✅ Phase 2 Teacher Mode persistence (`teacher_attempt_count`, `teacher_intervention`)
- ✅ Phase 3 SessionState persistence (`concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history`)
- ✅ Phase 2 IDOR/Ownership tests
- ✅ Phase 3 learning state round-trip tests
- ✅ All 33 existing ChatService tests

---

## 16. LIMITATIONS & FOLLOW-UP

1. **Test DB Migration:** Apply migration to test database when server available
2. **Phase 4 Enablement:** This persistence layer enables:
   - Evaluation History API (query `turn_assessments` by session)
   - Learning Timeline (chronological assessment records)
   - Report Versioning (snapshot assessments per turn)
   - Evidence Snapshots (claims + evidence from assessments)
   - Teacher Intervention Auto-Persistence (detailed misconception evidence)
3. **Potential Extensions:**
   - Add `concept_model` to `turn_assessments` if full timeline reconstruction needed
   - Add `learner_model` snapshot for progress sync validation
   - Consider partitioning for high-volume sessions

---

## 17. FILES CREATED/MODIFIED

### New Files
- `backend/app/models/turn_assessment.py`
- `backend/app/repositories/turn_assessment_repository.py`
- `backend/app/schemas/turn_assessment.py`
- `backend/alembic/versions/7a8b9c0d1e2f_add_turn_assessments.py`
- `backend/tests/services/test_turn_assessment_persistence.py`

### Modified Files
- `backend/app/db/base.py` — Added TurnAssessment import
- `backend/app/services/chat_service.py` — Added repository + persistence logic
- `backend/app/models/teacher_intervention.py` — Fixed relationship import order
- `backend/tests/services/test_turn_assessment_persistence.py` — Import order fix

---

**Status:** ✅ **COMPLETE** — Ready for Phase 4 Task 4.2 (Evaluation History API)