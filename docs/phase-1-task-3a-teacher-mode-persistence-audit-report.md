# Curio AI — Phase 1, Task 3A: Teacher Mode State Persistence Design Audit Report

**Author:** Senior Backend Architect  
**Project:** Curio AI (Feynman Role-Reversal Learning Platform)  
**Date:** September 21, 2026  
**Status:** Design Audit Complete — Ready for Implementation  
**Repository:** `joshi-chinmay-016/Curio-AI`  
**Current Branch:** `backend`  
**Architectural Contract:** `AIContext` $\rightarrow$ `CurioEngine.process()` $\rightarrow$ `AIResult`

---

## 1. Executive Summary

During the Phase 1 AI–Backend Integration Compatibility Audit ([`docs/phase-1-ai-backend-integration-audit-report.md`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/phase-1-ai-backend-integration-audit-report.md)), a Priority 1 (P1) defect was identified:
- When a learner enters Teacher Mode, Chinmay's AI logic calculates and emits `teacher_attempt_count: int` and `teacher_intervention: Optional[TeacherIntervention]`.
- Because the PostgreSQL database model `SessionState` and Pydantic schema `SessionStateBase` lack columns/fields for these attributes, `ChatService` drops them during persistence.
- Consequently, on every subsequent turn, `teacher_attempt_count` defaults to `0` and resets the pedagogical attempt count to `1`, preventing Teacher Mode from advancing through its three-tier instructional progression (Attempt 1: Conceptual $\rightarrow$ Attempt 2: Analogy $\rightarrow$ Attempt 3: Worked Example).

This design audit defines the persistence, migration, schema, repository, and service-layer changes required to safely persist and hydrate `teacher_attempt_count` and `teacher_intervention` without altering any AI intelligence.

---

## 2. Strict Responsibility Boundary

- **Backend Responsibility (User)**: PostgreSQL models, Alembic migrations, database schemas, repository CRUD operations, service-layer state hydration, and transaction safety.
- **AI Intelligence Responsibility (Chinmay)**: Prompts, evaluation metrics, pedagogical decision policies, Teacher Mode response generation, and LangGraph state machines.
- **Rule**: Do not rewrite or modify AI intelligence or pedagogical decision heuristics.

---

## 3. Current Schema and Contract Findings

### A. AI Contract Definitions ([`backend/app/ai/schemas.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py))
- **`TeacherIntervention`**:
  ```python
  class TeacherIntervention(BaseModel):
      active: bool = False
      gap: str = ""
      attempt_count: int = Field(default=0, ge=0)
      verification_required: bool = True
  ```
- **`SessionState` (Input Contract)**:
  Contains both `teacher_attempt_count: int = Field(default=0, ge=0)` and `teacher_intervention: Optional[TeacherIntervention] = None`.
- **`StateUpdates` (Output Contract)**:
  Emits both `teacher_attempt_count: Optional[int] = Field(default=None, ge=0)` and `teacher_intervention: Optional[TeacherIntervention] = None`.
- **`LearningContext`**:
  Also defines `teacher_intervention: Optional[TeacherIntervention] = None`.

### B. How the AI Engine Uses These Fields ([`backend/app/ai/nodes/student_nodes.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/nodes/student_nodes.py))
- **Attempt Progression**:
  When in Teacher Mode, lines 179–183 inspect both fields to calculate the next attempt count:
  ```python
  curr_attempts = context.current_state.teacher_attempt_count or 0
  if context.current_state.teacher_intervention and context.current_state.teacher_intervention.attempt_count:
      curr_attempts = max(curr_attempts, context.current_state.teacher_intervention.attempt_count)
  attempt_count = curr_attempts + 1
  ```
- **State Updates Output**:
  - **Entering / Continuing Teacher Mode**: Emits `teacher_attempt_count=attempt_count` and `teacher_intervention=TeacherIntervention(active=True, gap=..., attempt_count=attempt_count, verification_required=True)`.
  - **Exiting Teacher Mode** (`should_restore_interrupted_question=True`): Emits `teacher_attempt_count=0` and `teacher_intervention=TeacherIntervention(active=False, gap="", attempt_count=0, verification_required=False)`.
  - **Normal Student Mode**: Emits `teacher_attempt_count=0` and `teacher_intervention=None`.
- **Decision Engine Usage** ([`backend/app/ai/decision_engine.py:155-158`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/decision_engine.py#L155-L158)):
  `DecisionEngine` checks `context.current_state.teacher_intervention.gap` to match against `evaluation.knowledge_gap` for repeated failure detection (Trigger C).

### C. Backend Gaps Identified
- **SQLAlchemy Model ([`models/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L26-L40))**: `SessionState` has no columns for `teacher_attempt_count` or `teacher_intervention`.
- **Pydantic Schemas ([`schemas/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/session.py#L7-L23))**: `SessionStateBase` and `SessionStateResponse` omit both fields.
- **Repository ([`repositories/session_repository.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py#L53-L73))**: `update_state` does not copy or persist these fields.
- **Service Layer ([`services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L198-L340))**: `ChatService` does not hydrate these fields into `AIContext` (leaving them as default `0` and `None`), and drops them from `StateUpdates` when saving to the database.

---

## 4. Recommended Backend Storage Design with Reasoning

### A. Column Types
| Field | Recommended DB Type | Rationale |
|---|---|---|
| `teacher_attempt_count` | `Integer`, `default=0`, `server_default='0'`, `nullable=False` | A pure scalar counter. Using a dedicated integer column allows direct indexing, atomic increments, and query filtering. |
| `teacher_intervention` | `JSON`, `default=None`, `nullable=True` | A structured composite object (`active: bool`, `gap: str`, `attempt_count: int`, `verification_required: bool`). Storing as `JSON` aligns with existing patterns in the codebase (`unresolved_misconceptions: JSON`, `session_evaluation: JSON`). It allows serialization directly from/to `TeacherIntervention.model_dump()` and handles `null` cleanly when outside of Teacher Mode. |

### B. Session-Level vs. Turn-Level State
- **Session-Level (`session_states` table)**:
  Both fields belong in `session_states` because they track the **current active operational state** of the session that drives the next conversational turn.
- **Turn-Level (`turn_evaluations` & `messages` tables)**:
  Historical teacher interventions are already reconstructible from the transcript in Phase 3 via `SessionEvidenceBuilder`. Storing the active intervention state in `session_states` keeps `ChatService` performant ($O(1)$ state lookup per turn without scanning message history).

---

## 5. Required Model and Schema Changes

### A. SQLAlchemy Model: [`backend/app/models/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py)
Add two columns to `SessionState`:
```python
class SessionState(Base):
    __tablename__ = "session_states"
    # Existing columns ...
    consecutive_weak_answers = Column(Integer, default=0, nullable=False)
    unresolved_misconceptions = Column(JSON, default=list, nullable=False)
    mastered_concepts = Column(JSON, default=list, nullable=False)
    
    # New Teacher Mode tracking columns
    teacher_attempt_count = Column(Integer, default=0, server_default="0", nullable=False)
    teacher_intervention = Column(JSON, nullable=True)
```

### B. Backend Schemas: [`backend/app/schemas/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/session.py)
Update `SessionStateBase`:
```python
class SessionStateBase(BaseModel):
    current_mode: LearningMode = LearningMode.STUDENT
    difficulty: int = 1
    confidence: float = 0.0
    active_concept: str = "Core Definition"
    current_question_id: Optional[UUID] = None
    interrupted_question_id: Optional[UUID] = None
    consecutive_strong_answers: int = 0
    consecutive_weak_answers: int = 0
    unresolved_misconceptions: List[str] = []
    mastered_concepts: List[str] = []
    teacher_attempt_count: int = 0
    teacher_intervention: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
```

### C. Session Repository: [`backend/app/repositories/session_repository.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py)
In `create()`:
```python
db_state = SessionState(
    session_id=db_session.id,
    ...
    teacher_attempt_count=0,
    teacher_intervention=None,
)
```
In `update_state()`:
```python
db_state.teacher_attempt_count = state_in.teacher_attempt_count
db_state.teacher_intervention = state_in.teacher_intervention
```

---

## 6. Required ChatService Changes ([`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py))

### A. AIContext Hydration (Lines 198–225)
Hydrate `teacher_attempt_count` and `teacher_intervention`:
```python
# Hydrate TeacherIntervention object safely
teacher_intervention_obj: Optional[TeacherIntervention] = None
raw_intervention = getattr(db_session.state, "teacher_intervention", None)
if raw_intervention:
    if isinstance(raw_intervention, TeacherIntervention):
        teacher_intervention_obj = raw_intervention
    elif isinstance(raw_intervention, dict):
        try:
            teacher_intervention_obj = TeacherIntervention(**raw_intervention)
        except Exception:
            teacher_intervention_obj = None

attempt_count_val = getattr(db_session.state, "teacher_attempt_count", 0) or 0

current_state = SessionState(
    session_id=str(session_id),
    current_mode=current_mode,
    current_difficulty=db_session.state.difficulty,
    understanding_confidence=db_session.state.confidence,
    active_concept=db_session.state.active_concept,
    current_question=current_question_obj,
    interrupted_question=interrupted_question_obj,
    consecutive_successes=db_session.state.consecutive_strong_answers,
    consecutive_failures=db_session.state.consecutive_weak_answers,
    unresolved_misconceptions=db_session.state.unresolved_misconceptions or [],
    teacher_attempt_count=attempt_count_val,
    teacher_intervention=teacher_intervention_obj,
)

learning_context = LearningContext(
    mastered_concepts=db_session.state.mastered_concepts or [],
    unresolved_misconceptions=db_session.state.unresolved_misconceptions or [],
    teacher_intervention=teacher_intervention_obj,
)
```

### B. StateUpdates Merging & Persistence (Lines 260–340)
Merge `updates.teacher_attempt_count` and `updates.teacher_intervention`:
```python
# Teacher attempt count tracking
if updates.teacher_attempt_count is not None:
    new_teacher_attempts = updates.teacher_attempt_count
elif new_mode == LearningMode.STUDENT:
    new_teacher_attempts = 0
else:
    new_teacher_attempts = getattr(db_session.state, "teacher_attempt_count", 0)

# Teacher intervention tracking
if decision and decision.should_restore_interrupted_question:
    new_teacher_intervention = None
elif updates.teacher_intervention is not None:
    new_teacher_intervention = (
        updates.teacher_intervention.model_dump()
        if hasattr(updates.teacher_intervention, "model_dump")
        else updates.teacher_intervention
    )
elif new_mode == LearningMode.STUDENT:
    new_teacher_intervention = None
else:
    new_teacher_intervention = getattr(db_session.state, "teacher_intervention", None)

state_update = SessionStateBase(
    current_mode=new_mode,
    difficulty=new_difficulty,
    confidence=new_confidence,
    active_concept=new_active_concept,
    current_question_id=current_qid,
    interrupted_question_id=new_interrupted_qid,
    consecutive_strong_answers=consecutive_strong,
    consecutive_weak_answers=consecutive_weak,
    unresolved_misconceptions=new_misconceptions,
    mastered_concepts=new_mastered,
    teacher_attempt_count=new_teacher_attempts,
    teacher_intervention=new_teacher_intervention,
)

self.session_repo.update_state(db, session_id, state_update)
```

---

## 7. Migration Plan

### A. Alembic Migration Revision
- **Target File**: `backend/alembic/versions/<revision_id>_add_teacher_mode_state_fields.py`
- **Down Revision**: `a1b2c3d4e5f6` (the current head: `add_phase3_evaluation_fields`)
- **Operations**:
  ```python
  def upgrade() -> None:
      op.add_column(
          'session_states',
          sa.Column('teacher_attempt_count', sa.Integer(), server_default='0', nullable=False)
      )
      op.add_column(
          'session_states',
          sa.Column('teacher_intervention', sa.JSON(), nullable=True)
      )

  def downgrade() -> None:
      op.drop_column('session_states', 'teacher_intervention')
      op.drop_column('session_states', 'teacher_attempt_count')
  ```

### B. Database Compatibility
- `server_default='0'` ensures zero table rewrite lock contention and guarantees that all pre-existing active sessions in PostgreSQL have a valid integer value (`0`).
- `nullable=True` for `teacher_intervention` ensures existing records cleanly default to `NULL` without needing backfill scripts.

---

## 8. Required Tests

### A. Unit Tests ([`backend/tests/services/test_chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/services/test_chat_service.py))
- **`test_send_message_hydrates_teacher_state_into_aicontext`**:
  Verify that when `db_session.state` has `teacher_attempt_count=2` and an active `teacher_intervention`, `AIContext.current_state` receives `teacher_attempt_count=2` and a validated `TeacherIntervention` instance.
- **`test_send_message_merges_and_persists_teacher_state_updates`**:
  Verify that `StateUpdates(teacher_attempt_count=1, teacher_intervention=...)` is mapped into `SessionStateBase` and passed to `session_repo.update_state`.
- **`test_send_message_clears_teacher_state_on_mode_exit`**:
  Verify that when returning to `STUDENT` mode (`should_restore_interrupted_question=True`), `teacher_attempt_count` resets to `0` and `teacher_intervention` resets to `None`.
- **`test_send_message_safe_handling_of_malformed_intervention_json`**:
  Verify that corrupted or unexpected JSON in `teacher_intervention` falls back gracefully to `None` without crashing.

### B. Live Database Integration Tests ([`backend/tests/integration/test_teacher_mode_persistence.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/integration/test_teacher_mode_persistence.py))
- **`test_multi_turn_teacher_mode_increments_attempt_count`**:
  Execute 3 sequential turns in Teacher Mode against PostgreSQL:
  - Turn 1 (enter): `teacher_attempt_count == 1`.
  - Turn 2 (continue): `teacher_attempt_count == 2`.
  - Turn 3 (continue): `teacher_attempt_count == 3`.
- **`test_teacher_mode_exit_clears_db_state`**:
  Execute successful verification turn against PostgreSQL:
  - `reloaded_state.teacher_attempt_count == 0`
  - `reloaded_state.teacher_intervention is None`

---

## 9. Risks and Backward-Compatibility Considerations

1. **Schema Backward Compatibility**:
   - `teacher_attempt_count` has `default=0` and `teacher_intervention` has `default=None`.
   - Existing code constructing `SessionState` or `SessionStateBase` without these fields will continue to instantiate with valid defaults without errors.
2. **Defensive Deserialization**:
   - `teacher_intervention` can be `None`, a Python `dict`, or a `TeacherIntervention` instance depending on whether it was freshly loaded from SQLAlchemy or passed in-memory. The hydration helper handles all three cases safely.
3. **Pedagogical Invariant Safety**:
   - This design does **not** alter prompts, Socratic rules, or decision logic.
   - It strictly repairs the backend persistence pipeline so Chinmay's attempt-aware adaptation logic (`student_nodes.py` lines 179–183) can function across multi-turn user interactions.
