# COMPATIBILITY AUDIT REPORT





## Chinmay's AI Changes vs Phase 3 Backend Persistence

---

### 1. OVERALL COMPATIBILITY
**Status: Potential Conflict / Backend Change Required**

The AI implementation has added significant new structured state (`LearningAssessment`, `ConceptModel`, `LearnerModel`, `QuestionSpecification`, `TurnInterpretation`, `LearningObjective`) that the backend currently **does not persist**. While existing Phase 3 fields continue to work, the new assessment pipeline produces rich pedagogical provenance that is being silently dropped at the persistence boundary.

---

### 2. AIResult CHANGES

| Field | Before | After | Backend Impact |
|-------|--------|-------|----------------|
| `evaluation` | `TurnEvaluation` | `TurnEvaluation` | ✅ Compatible |
| `decision` | `LearningDecision` | `LearningDecision` | ✅ Compatible |
| `response` | `AIResponse` | `AIResponse` | ✅ Compatible |
| `state_updates` | `StateUpdates` | `StateUpdates` (expanded) | ⚠️ New fields in StateUpdates |
| `session_evaluation` | None | `Optional[SessionEvaluation]` | ⚠️ New - not persisted |
| `learning_report` | None | `Optional[LearningReport]` | ⚠️ New - not persisted |
| `turn_interpretation` | None | `Optional[TurnInterpretation]` | ⚠️ New - not persisted |
| `learning_objective` | None | `Optional[LearningObjective]` | ⚠️ New - not persisted |
| `question_specification` | None | `Optional[QuestionSpecification]` | ⚠️ New - not persisted |
| `concept_model` | None | `Optional[ConceptModel]` | ⚠️ New - not persisted |
| `learner_model` | None | `Optional[LearnerModel]` | ⚠️ New - not persisted |
| **`learning_assessment`** | None | **`Optional[LearningAssessment]`** | **❌ Major new field - NOT persisted** |

**Backend Impact**: ChatService extracts only `evaluation`, `decision`, `response`, and `state_updates` from AIResult. The new `learning_assessment` and other fields are **completely ignored** and never reach persistence.

---

### 3. StateUpdates CHANGES

| Field | Before | After | Backend Impact |
|-------|--------|-------|----------------|
| `active_concept` | `Optional[str]` | `Optional[str]` | ✅ Compatible |
| `interrupted_question` | `Optional[CurrentQuestion]` | `Optional[CurrentQuestion]` | ✅ Compatible |
| `mastered_concepts` | `Optional[List[str]]` | `Optional[List[str]]` | ✅ Compatible |
| `unresolved_misconceptions` | `Optional[List[str]]` | `Optional[List[str]]` | ✅ Compatible |
| `teacher_intervention` | `Optional[TeacherIntervention]` | `Optional[TeacherIntervention]` | ✅ Compatible |
| `current_question` | `Optional[CurrentQuestion]` | `Optional[CurrentQuestion]` | ✅ Compatible |
| `current_mode` | `Optional[Mode]` | `Optional[Mode]` | ✅ Compatible |
| `difficulty` | `Optional[int]` | `Optional[int]` | ✅ Compatible |
| `confidence` | `Optional[float]` | `Optional[float]` | ✅ Compatible |
| `concept_mastery` | `Optional[Dict[str, float]]` | `Optional[Dict[str, float]]` | ✅ Compatible |
| `consecutive_failures` | `Optional[int]` | `Optional[int]` | ✅ Compatible |
| `consecutive_successes` | `Optional[int]` | `Optional[int]` | ✅ Compatible |
| `teacher_attempt_count` | `Optional[int]` | `Optional[int]` | ✅ Compatible |
| `recent_strategy_history` | `Optional[List[Strategy]]` | `Optional[List[Strategy]]` | ✅ Compatible |
| `misconception_counts` | `Optional[Dict[str, int]]` | `Optional[Dict[str, int]]` | ✅ Compatible |
| `mode_switch_history` | `Optional[List[ModeTransition]]` | `Optional[List[ModeTransition]]` | ✅ Compatible |
| **`concept_model`** | None | **`Optional[ConceptModel]`** | **❌ New - NOT persisted** |
| **`learner_model`** | None | **`Optional[LearnerModel]`** | **❌ New - NOT persisted** |
| **`current_objective`** | None | **`Optional[LearningObjective]`** | **❌ New - NOT persisted** |
| **`latest_interpretation`** | None | **`Optional[TurnInterpretation]`** | **❌ New - NOT persisted** |
| **`question_specification`** | None | **`Optional[QuestionSpecification]`** | **❌ New - NOT persisted** |

**Backend Impact**: ChatService maps StateUpdates → SessionStateBase → SessionState DB model. The 5 new fields above have **no corresponding DB columns** and are silently dropped during `update_state()`.

---

### 4. SessionState COMPATIBILITY

#### AI Schema (`backend/app/ai/schemas.py:253-290`)
```python
class SessionState(BaseModel):
    # ... existing fields ...
    learning_assessment: Optional[LearningAssessment] = None  # NEW (line 275)
```

#### DB Model (`backend/app/models/session.py:28-48`)
```python
class SessionState(Base):
    # ... existing fields (lines 31-47) ...
    # NO learning_assessment column
    # NO concept_model column
    # NO learner_model column
    # NO question_specification column
    # NO current_objective column
    # NO latest_interpretation column
```

#### SessionStateBase Schema (`backend/app/schemas/session.py:7-24`)
```python
class SessionStateBase(BaseModel):
    # ... existing 16 fields ...
    # NO learning_assessment field
```

**Persistence Concerns**:
- **Compatible fields**: All Phase 3 fields (`concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history`, `teacher_attempt_count`, `teacher_intervention`, `mastered_concepts`, `unresolved_misconceptions`, streak counters, mode/difficulty/confidence, question tracking) continue to work correctly.
- **New/unhandled fields**: `learning_assessment` (from AIResult), plus `concept_model`, `learner_model`, `question_specification`, `current_objective`, `latest_interpretation` (from StateUpdates) have **zero persistence path**.
- **Partial updates**: ChatService correctly handles `None` in StateUpdates as "preserve existing" for all Phase 3 fields.
- **Explicit clearing**: `StateUpdates` uses `None` for "no change" and explicit values for updates - this works correctly for existing fields.
- **DB → AIContext hydration**: ChatService correctly hydrates all Phase 3 fields from DB into AIContext. New fields cannot be hydrated because they don't exist in DB.
- **AIResult → ChatService → SessionState → PostgreSQL**: Pipeline works for Phase 3 fields. **Breaks for new AI fields** - they are extracted in `state_updates_node` but dropped at `SessionStateBase` construction (line 605-623 in chat_service.py).

---

### 5. TEACHER MODE COMPATIBILITY

| Aspect | Status |
|--------|--------|
| `teacher_attempt_count` | ✅ Fully persisted (DB column + ChatService logic) |
| `teacher_intervention` (JSON) | ✅ Fully persisted (DB column + ChatService logic) |
| Mode transitions (STUDENT ↔ TEACHER) | ✅ Works via `mode_switch_history` |
| Verification state | ✅ Persisted via `teacher_intervention.verification_required` |
| Restored Student question state | ✅ Via `interrupted_question_id` |
| TeacherInterventionLog infrastructure | ✅ Separate table, unaffected |
| **New assessment-derived Teacher state** | ❌ `LearningAssessment` contains misconception evidence, claim-level provenance, mastery gate decisions - **NOT persisted** |

**Teacher Mode Persistence Mismatch**: The unified assessment pipeline now produces `LearningAssessment` during Teacher Mode verification turns (see `evaluation_node` line 180-187). This includes:
- `misconceptions` with `MisconceptionEvidence` (concept_id, description, learner_statement, severity, counter_evidence)
- `evidence` items with `EvidenceStatus` (SUPPORTED/PARTIALLY_SUPPORTED/CONTRADICTED/MISSING)
- `mastery_decision` metadata from MasteryGate

**None of this is persisted.** Phase 3 only saves the coarse `teacher_intervention` JSON and `teacher_attempt_count`.

---

### 6. AI ↔ BACKEND BOUNDARY

| Boundary Concern | Status |
|------------------|--------|
| Backend reproduces assessment logic | ❌ **No violation** - ChatService only passes AIResult/StateUpdates to DB |
| Backend reproduces MasteryGate | ❌ **No violation** - MasteryGate runs inside AI (LearnerModelManager) |
| Backend reproduces correctness logic | ❌ **No violation** |
| **Duplication risk** | ⚠️ **Potential** - If backend adds `learning_assessment` persistence, must store as opaque JSON, not decompose into columns that replicate AI logic |

**Key Finding**: The boundary is currently clean. The backend treats AIResult as opaque payload for persistence. The risk emerges only if backend tries to *interpret* the new assessment fields for API responses or reporting - which Phase 4 tasks may require.

---

### 7. PHASE 4 IMPACT

| Upcoming Task | Dependency on New AI Contract | Adjustment Needed |
|---------------|-------------------------------|-------------------|
| **Evaluation History API** | HIGH - Needs `LearningAssessment` history (intent, relevance, claims, evidence, misconceptions, mastery decisions) | **Yes** - Requires new DB storage for assessment provenance |
| **Learning Timeline** | HIGH - Needs per-turn `LearningAssessment` + `TurnInterpretation` + `QuestionSpecification` | **Yes** - Requires new DB storage |
| **Report Versioning** | MEDIUM - `SessionEvaluation`/`LearningReport` already in AIResult, but need versioned snapshots | **Yes** - New table or JSON column |
| **Teacher Intervention Persistence** | HIGH - Current `TeacherInterventionLog` is coarse; new `LearningAssessment` has granular misconception evidence | **Yes** - Schema expansion needed |
| **Progress Synchronization** | HIGH - `LearnerModel` + `concept_mastery` + `misconception_counts` now have dual sources (AI + DB) | **Yes** - Need authoritative source decision |
| **Evidence Snapshots** | HIGH - `LearningAssessment.evidence` + `claims` + `misconceptions` are the evidence | **Yes** - New storage required |

**Critical Path**: The `LearningAssessment` object is the **single source of truth** for pedagogical provenance. Phase 4 cannot build Evaluation History, Learning Timeline, or rich Teacher Intervention logs without persisting it.

---

### 8. REQUIRED BACKEND CHANGES

| Change | Required? | Rationale |
|--------|-----------|-----------|
| Add `learning_assessment` JSON column to `session_states` | **YES** | Primary artifact of new assessment pipeline; needed for all Phase 4 tasks |
| Add `concept_model` JSON column to `session_states` | **RECOMMENDED** | Enables hydration of full concept graph without rebuild; supports Learning Timeline |
| Add `learner_model` JSON column to `session_states` | **RECOMMENDED** | Authoritative per-concept state (mastery, evidence_count, misconceptions, gaps); avoids dual-source drift |
| Add `question_specification` JSON column to `session_states` | **OPTIONAL** | Useful for Evaluation History to show what was asked and why |
| Add `current_objective` JSON column to `session_states` | **OPTIONAL** | Tracks active learning objective per turn |
| Add `latest_interpretation` JSON column to `session_states` | **OPTIONAL** | Tracks intent classification per turn |
| Update `SessionStateBase` schema to include new fields | **YES** (for any persisted fields) | ChatService uses this for `update_state()` |
| Update `SessionRepository.update_state()` to handle new columns | **YES** (for any persisted fields) | Current implementation only sets known attributes |
| Create migration for new columns | **YES** (for any persisted fields) | Alembic migration required |

**Minimal Required Change**: Add `learning_assessment` JSON column to `session_states` + update `SessionStateBase` + `SessionRepository.update_state()`.

**Recommended Change**: Also persist `learner_model` (authoritative concept state) and `concept_model` (avoids rebuild on hydration).

---

### 9. TEST COVERAGE

| Area | Existing Coverage | Missing Coverage |
|------|-------------------|------------------|
| **AIResult contract** | `test_send_message_invokes_curio_engine_with_canonical_context` validates structure | No test validates `learning_assessment` field presence/content |
| **StateUpdates contract** | `test_send_message_merges_partial_state_updates` tests None-merging | No test for new StateUpdates fields (`concept_model`, `learner_model`, etc.) |
| **SessionState persistence** | `test_session_repository_persists_and_updates_teacher_mode_fields` | No test for `learning_assessment` persistence |
| **Teacher Mode persistence** | `test_teacher_mode_persists_attempt_count_and_intervention`, multi-turn tests | No test for Teacher Mode `LearningAssessment` content |
| **DB → AIContext hydration** | `test_send_message_hydrates_teacher_state_into_aicontext`, `test_database_hydration_of_question_objects` | No test for hydrating `learning_assessment`, `learner_model`, `concept_model` |
| **Phase 3 learning state** | `test_send_message_merges_partial_state_updates` covers concept_mastery, misconception_counts, strategy_history | No test verifying new assessment data flows through to DB |
| **Regression areas** | Good coverage for Phase 3 fields | **High risk**: New AI fields silently dropped; no test fails when they're missing from DB |

**Critical Gap**: All existing tests mock `AIResult` with handcrafted `StateUpdates` containing only Phase 3 fields. The real AI engine now produces `learning_assessment` and other new fields - **no test verifies they survive the persistence round-trip**.

---

### 10. RECOMMENDED NEXT STEP

**Do NOT start Task 4.2 (Evaluation History API) until:**

1. **Add `learning_assessment` JSON column to `session_states` table** via migration
2. **Update `SessionStateBase` schema** to include `learning_assessment: Optional[Dict] = None`
3. **Update `SessionRepository.update_state()`** to persist `learning_assessment`
4. **Update `ChatService.send_message()`** to extract `ai_result.learning_assessment` into `state_update.learning_assessment`
5. **Add integration test** verifying `LearningAssessment` round-trips: AIResult → ChatService → DB → AIContext hydration

**Then** Task 4.2 can query `session_states.learning_assessment` for Evaluation History API.

**Alternative (if schema change blocked)**: Store `LearningAssessment` in a new `turn_assessments` table keyed by `message_id` (1:1 with turn evaluations). This avoids SessionState schema migration but requires new repository.

---

**Audit Complete.** No files modified. No migrations created. No code changed.