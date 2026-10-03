# Phase 4 Task 4.5 — Teacher Intervention Auto-Persistence
## Architecture Audit Report

---

### 1. Executive Summary

This audit examines the current Teacher Intervention persistence infrastructure and identifies exactly how to connect it to the Teacher Mode runtime flow in `ChatService.send_message()`.

**Key Finding**: The `TeacherInterventionRepository.create()` method exists and the `TeacherInterventionLog` model is fully implemented, but `ChatService` does **not** automatically persist intervention events during conversation execution. The AI layer (`CurioEngine`) produces rich structured Teacher Mode data in `AIResult.state_updates.teacher_intervention` (a `TeacherIntervention` object with `active`, `gap`, `attempt_count`, `verification_required` fields), but this data is only persisted to `SessionState` (JSON columns), not to the dedicated `teacher_intervention_logs` table.

**Gap to Close**: Automatic creation of `TeacherInterventionLog` records when the AI engine emits structured Teacher Mode intervention data during a turn.

---

### 2. Current Teacher Intervention Flow

**Current Flow (Phase 3 + Phase 4.1-4.4)**:
```
User Message → ChatService.send_message()
    → Persist user message
    → Build AIContext (hydrates SessionState including teacher_intervention JSON)
    → CurioEngine.process(AIContext) → AIResult
    → Persist AI message
    → Persist TurnEvaluation
    → Persist TurnAssessment (if present)
    → Merge StateUpdates into SessionState (includes teacher_intervention JSON, teacher_attempt_count)
    → Return ChatTurnResponse
```

**Missing Step**: No `TeacherInterventionRepository.create()` call anywhere in this flow.

**Read APIs (Already Implemented)**:
- `GET /users/me/teacher-interventions` — all user interventions
- `GET /users/me/sessions/{id}/teacher-interventions` — session-specific (with IDOR protection)
- `SessionEvidenceBuilder.build_from_history()` — reads from `teacher_intervention_logs` when `db` + `user_id` provided
- `TimelineRepository` — includes `teacher_intervention` event type from `teacher_intervention_logs`

---

### 3. Current AIResult Contract

**AIResult Fields** (`backend/app/ai/schemas.py:552-565`):
```python
class AIResult(BaseModel):
    evaluation: TurnEvaluation
    decision: LearningDecision
    response: AIResponse
    state_updates: StateUpdates
    session_evaluation: Optional[SessionEvaluation] = None
    learning_report: Optional[LearningReport] = None
    turn_interpretation: Optional[TurnInterpretation] = None
    learning_objective: Optional[LearningObjective] = None
    question_specification: Optional[QuestionSpecification] = None
    concept_model: Optional[ConceptModel] = None
    learner_model: Optional[LearnerModel] = None
    learning_assessment: Optional[LearningAssessment] = None
```

**StateUpdates Fields** (`backend/app/ai/schemas.py:344-374`):
```python
class StateUpdates(BaseModel):
    # ... other fields ...
    teacher_intervention: Optional[TeacherIntervention] = None
    teacher_attempt_count: Optional[int] = Field(default=None, ge=0)
    # ...
```

**TeacherIntervention Schema** (`backend/app/ai/schemas.py:81-86`):
```python
class TeacherIntervention(BaseModel):
    active: bool = False
    gap: str = ""
    attempt_count: int = Field(default=0, ge=0)
    verification_required: bool = True
```

**What AIResult Currently Provides for Persistence**:
| Field | Available in AIResult | Notes |
|-------|----------------------|-------|
| `gap` | ✅ `state_updates.teacher_intervention.gap` | The learning gap being addressed |
| `attempt_count` | ✅ `state_updates.teacher_intervention.attempt_count` | Current attempt number |
| `teacher_explanation` | ❌ Not directly exposed | AI response content contains this |
| `verification_question` | ❌ Not directly exposed | Embedded in AI response content |
| `verification_answer` | ❌ Not in AIResult | User's next message (next turn) |
| `verification_passed` | ❌ Not directly exposed | Determined by next turn's evaluation |
| `intervention_type` | ❌ Not in AIResult | Must be inferred from context |

**Critical Observation**: The AIResult **does not** currently expose `teacher_explanation`, `verification_question`, `verification_answer`, `verification_passed`, or `intervention_type` as structured fields. These are either embedded in the AI response text (which we must NOT parse) or determined in subsequent turns.

---

### 4. Current StateUpdates Contract

**StateUpdates** serves dual purpose:
1. **Session-state fields** (persisted to `session_states` table): `current_mode`, `difficulty`, `confidence`, `active_concept`, `current_question`, `interrupted_question`, `consecutive_successes`, `consecutive_failures`, `mastered_concepts`, `unresolved_misconceptions`, `concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history`, `teacher_attempt_count`, `teacher_intervention` (JSON)
2. **Intervention event data**: `teacher_intervention` (TeacherIntervention object) — this represents the **current intervention state**, not a discrete event log entry

**Data Belonging**:
| Data | Belongs In | NOT In |
|------|------------|--------|
| Current teacher mode active flag | `SessionState.teacher_intervention` (JSON) | `TeacherInterventionLog` |
| Current attempt count | `SessionState.teacher_attempt_count` | `TeacherInterventionLog` (as current state) |
| Current gap being taught | `SessionState.teacher_intervention.gap` | `TeacherInterventionLog` (as current state) |
| **Discrete intervention event record** | | `TeacherInterventionLog` (append-only) |
| Teacher explanation given | | `TeacherInterventionLog.teacher_explanation` |
| Verification question asked | | `TeacherInterventionLog.verification_question` |
| Learner's verification answer | | `TeacherInterventionLog.verification_answer` |
| Whether verification passed | | `TeacherInterventionLog.verification_passed` |
| Intervention phase (enter/continue/exit/limit_fallback) | | `TeacherInterventionLog.intervention_type` |

**Do NOT collapse** `TeacherInterventionLog` into `SessionState`. The log is append-only event history; session state is current mutable state.

---

### 5. TeacherInterventionLog Schema Audit

**Current Schema** (`backend/app/models/teacher_intervention.py`):
```python
class TeacherInterventionLog(Base):
    id: UUID (PK)
    session_id: UUID (FK → sessions, CASCADE)
    user_id: UUID (FK → users, CASCADE)
    gap: Text (NOT NULL)
    attempt_count: Integer (default=1)
    teacher_explanation: Text (nullable)
    verification_question: Text (nullable)
    verification_answer: Text (nullable)
    verification_passed: Integer (nullable, 0/1)
    intervention_type: String (nullable)  # enter, continue, exit, limit_fallback
    created_at: DateTime (server_default=now())
```

**Sufficiency Analysis**:
| Field | Sufficient? | Notes |
|-------|-------------|-------|
| `id`, `session_id`, `user_id`, `gap`, `attempt_count`, `created_at` | ✅ Yes | Core identity |
| `teacher_explanation` | ⚠️ Partial | Available only when AI emits explanation (enter/continue) |
| `verification_question` | ⚠️ Partial | Available when AI emits verification question |
| `verification_answer` | ⚠️ Partial | Available on NEXT turn (user message) |
| `verification_passed` | ⚠️ Partial | Determined on NEXT turn evaluation |
| `intervention_type` | ⚠️ Partial | Must be inferred from mode transition |

**Missing Fields for Complete Automatic Persistence**:
- No direct link to `message_id` (AI message that delivered explanation/question)
- No direct link to `turn_assessment_id` or `evaluation_id`
- No `intervention_type` provided by AI — must be derived

**Migration Candidate**: 
- Add `message_id` (FK to messages) to link intervention to the AI message that triggered it
- Add `intervention_type` enum constraint (currently free string)

---

### 6. Intervention Event Semantics

**Current AI Behavior** (from `student_nodes.py` and `decision_engine.py`):

| AI Turn | Mode Transition | What Happens | Persistence Event? |
|---------|----------------|--------------|-------------------|
| Turn N | STUDENT → TEACHER | Teacher enters, explains gap, asks verification Q | **ENTER** event |
| Turn N+1 | TEACHER → TEACHER | Teacher continues, re-explains/adapts, asks new verification Q | **CONTINUE** event |
| Turn N+2 | TEACHER → TEACHER | Clarification/readiness — no new attempt consumed | **CONTINUE** (no attempt increment) |
| Turn N+3 | TEACHER → STUDENT | Verification passed → restore interrupted question | **EXIT** event (verification_passed=1) |
| Turn N+3 | TEACHER → STUDENT | Max attempts (3) reached → fallback to simpler difficulty | **LIMIT_FALLBACK** event (verification_passed=0) |

**Granularity Decision**: **One AI turn in Teacher Mode = One intervention log row**, but with nuance:
- **Entry turn** (STUDENT→TEACHER): Creates log with `intervention_type="enter"`, includes `teacher_explanation` and `verification_question` from AI response
- **Continuation turns** (TEACHER→TEACHER): Creates log with `intervention_type="continue"`, includes updated explanation/question
- **Exit turn** (TEACHER→STUDENT with `should_restore_interrupted_question=True`): **Updates the most recent open intervention log** with `verification_answer` (from user message), `verification_passed` (from evaluation), and `intervention_type="exit"` or `"limit_fallback"`

**Why Not One Log Per Turn?** The verification answer and pass/fail result belong to the **same intervention episode** as the explanation and question. Creating separate rows would fragment a single pedagogical intervention across multiple rows.

**Implementation Pattern**: 
- On **entry/continue**: `INSERT` new `TeacherInterventionLog`
- On **exit/fallback**: `UPDATE` the latest open log for this session (where `verification_passed IS NULL`)

---

### 7. Duplicate / Idempotency Analysis

**Current Identifiers Available**:
| Identifier | Source | Stability |
|------------|--------|-----------|
| `user_msg.id` | User message (persisted first) | ✅ Stable per turn |
| `ai_msg.id` | AI message (persisted second) | ✅ Stable per turn |
| `turn_eval.message_id` | Links to user_msg.id | ✅ Stable |
| `turn_assessment.message_id` | Links to user_msg.id | ✅ Stable |
| `session_state.current_question_id` | Points to AI message | ✅ Stable |
| `session_state.interrupted_question_id` | Points to prior AI message | ✅ Stable |

**No existing per-intervention identifier**. The `TeacherInterventionLog` has its own UUID PK.

**Idempotency Strategy**:
1. **Entry/Continue**: Use `(session_id, user_id, attempt_count, intervention_type IN ('enter','continue'))` as natural key. Before INSERT, check if a log with same session+attempt+type exists.
2. **Exit/Fallback**: Find latest log for session where `verification_passed IS NULL` and UPDATE it.
3. **Transaction boundary**: All within the same `ChatService.send_message()` transaction — no race conditions from concurrent requests (sessions are single-threaded per user).

**Safest Design**: 
```python
# On entry/continue: check for existing open intervention at this attempt
existing = db.query(TeacherInterventionLog).filter(
    TeacherInterventionLog.session_id == session_id,
    TeacherInterventionLog.user_id == user_id,
    TeacherInterventionLog.attempt_count == attempt_count,
    TeacherInterventionLog.intervention_type.in_(('enter', 'continue')),
    TeacherInterventionLog.verification_passed.is_(None)
).first()
if existing:
    # Update existing (idempotent)
else:
    # Create new
```

---

### 8. Transaction Boundary

**Current `ChatService.send_message()` Transaction Order** (lines 214-673):
1. Load session + ownership check
2. **Persist user message** (`message_repo.create_message`) — COMMIT
3. Build AIContext
4. **Invoke AI Engine** (`ai_engine.process`)
5. **Persist AI message** (`message_repo.create_message`) — COMMIT
6. **Persist TurnEvaluation** (`message_repo.create_evaluation`) — COMMIT
7. **Persist TurnAssessment** (`turn_assessment_repo.create_assessment`) — COMMIT
8. **Update SessionState** (`session_repo.update_state`) — COMMIT
9. Return response

**Problem**: Each repository method calls `db.commit()` independently (see `message_repo.py`, `turn_assessment_repo.py`, `session_repo.py`). This means **multiple transactions per turn**, not a single atomic transaction.

**For TeacherInterventionLog**:
- Should be created **after** AI message is persisted (so we have `ai_msg.id` for `message_id` FK if added)
- Should be created **after** TurnEvaluation is available (for `verification_passed` on exit turns)
- Should be in the **same transaction** as SessionState update for consistency

**Recommended Placement**: After line 657 (`session_repo.update_state`), before return. Use a **single transaction** for the entire turn by removing individual `commit()` calls from repositories and letting the service layer commit once. However, that's a larger refactor.

**Minimal Change**: Add `TeacherInterventionRepository.create()` call after SessionState update, within the same logical flow. Accept that it may be a separate commit (current architecture limitation). For exit/fallback updates, use the same session.

---

### 9. Ownership & IDOR Analysis

**Current ChatService Ownership** (lines 222-227):
```python
if user_id:
    db_session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
else:
    db_session = self.session_repo.get(db, session_id)
```

**Session Ownership Verified**: Yes, via `session_repo.get_by_id_and_user()` which filters by `Session.user_id == user_id`.

**TeacherInterventionRepository.create()** requires `user_id` and `session_id` — both available from `db_session.user_id` and `session_id` parameter.

**No Client-Supplied user_id**: The `user_id` comes from the authenticated request context (via FastAPI dependency), passed to `ChatService.send_message()`. The backend **derives ownership from `current_user.id`** — correct.

**Security Verification**: Automatic persistence cannot bypass ownership because:
1. Session ownership is verified before any persistence
2. `user_id` for intervention log comes from `db_session.user_id` (trusted)
3. `session_id` is the same session already verified

---

### 10. SessionEvidenceBuilder Integration

**Current Integration** (`session_evidence.py:178-211`):
```python
if db is not None and user_id is not None:
    repo = TeacherInterventionRepository()
    intervention_logs = repo.get_by_session(db, session_uuid, user_uuid)
    for log in intervention_logs:
        teacher_interventions.append(TeacherInterventionEvidence(...))
```

**Status**: **Already fully integrated**. The evidence builder reads from `teacher_intervention_logs` table when `db` and `user_id` are provided (which `ReportService._build_report_data()` passes at line 139-148).

**No Changes Needed**: Once `ChatService` auto-persists to `teacher_intervention_logs`, reports and evidence will automatically include them.

---

### 11. Timeline Integration

**Current Integration** (`timeline_repository.py:85-99`):
```sql
-- 5. teacher_intervention
SELECT
    'teacher_intervention' AS event_type,
    i.created_at AS timestamp,
    i.session_id AS session_id,
    CAST(NULL AS uuid) AS message_id,
    i.id AS entity_id,
    jsonb_build_object(
        'intervention_type', i.intervention_type,
        'gap', left(coalesce(i.gap, ''), 500),
        'attempt_count', i.attempt_count,
        'verification_passed', i.verification_passed
    ) AS metadata
FROM teacher_intervention_logs i
WHERE i.user_id = CAST(:user_id AS uuid)
```

**Status**: **Already fully integrated**. The timeline UNION query includes `teacher_intervention_logs` as an event source.

**No Changes Needed**: Auto-persisted logs will automatically appear as `teacher_intervention` timeline events.

---

### 12. TurnAssessment Relationship

**Current TurnAssessment** (`turn_assessment.py`):
- Links to `message_id` (user message), `session_id`, `user_id`
- Stores `learning_assessment`, `turn_interpretation`, `learning_objective`, `question_specification` as JSON

**Relationship Options**:
| Option | Pros | Cons |
|--------|------|------|
| `TeacherInterventionLog.message_id` → AI message | Links intervention to teacher's explanation/question | AI message created after user message |
| `TeacherInterventionLog.message_id` → user message | Consistent with TurnAssessment | Less semantically accurate |
| No FK, only session_id | Simpler | Less traceability |

**Recommendation**: Add `message_id` FK to **AI message** (the teacher's response). This requires the AI message to be persisted first (which it is, at line 412-417). The `message_id` would allow tracing: "Which AI message delivered this explanation/question?"

**No FK to TurnAssessment**: Unnecessary coupling. Session + message_id is sufficient for traceability.

---

### 13. Multi-Turn Teacher Mode Analysis

**State Machine** (from `decision_engine.py` and `student_nodes.py`):

```
STUDENT --(trigger)--> TEACHER (attempt=1, enter)
    │
    ├─ Learner answers verification → PASS → STUDENT (exit, verification_passed=1)
    ├─ Learner answers verification → PARTIAL → TEACHER (attempt=2, continue)
    ├─ Learner asks clarification → TEACHER (attempt=1 or 2, continue, no increment)
    ├─ Learner fails → TEACHER (attempt+1, continue)
    └─ attempt >= 3 → STUDENT (limit_fallback, verification_passed=0)
```

**Persistence Mapping**:
| Turn | AIResult.state_updates | Action |
|------|------------------------|--------|
| Enter | `teacher_intervention.active=True, attempt_count=1` | INSERT log (type=enter, explanation=AI.content, question=extract from AI.content) |
| Continue (failed answer) | `teacher_intervention.active=True, attempt_count=2` | INSERT log (type=continue, explanation=AI.content, question=extract from AI.content) |
| Continue (clarification) | `teacher_intervention.active=True, attempt_count=2` | INSERT log (type=continue, explanation=AI.content, question=extract from AI.content) |
| Exit (pass) | `should_restore_interrupted_question=True, next_mode=STUDENT` | UPDATE latest open log: verification_answer=user_msg.content, verification_passed=1, type=exit |
| Exit (limit_fallback) | `should_restore_interrupted_question=True, next_mode=STUDENT, reason contains "Maximum Teacher attempts"` | UPDATE latest open log: verification_answer=user_msg.content, verification_passed=0, type=limit_fallback |

**Critical**: The `verification_answer` and `verification_passed` are only known on the **exit turn** (user's response + evaluation). The entry/continue turns only have the teacher's explanation and question.

---

### 14. Failure / Rollback Behavior

| Failure Scenario | Current Behavior | Recommended Behavior |
|------------------|------------------|----------------------|
| AI falls back to MockProvider | Returns valid AIResult (may lack teacher data) | Only persist if `state_updates.teacher_intervention` is present and valid |
| AIResult missing Teacher Mode data | `state_updates.teacher_intervention = None` | No log created (Student Mode) |
| AI call fails (exception) | Propagates up, no persistence | No log created (transaction rolls back if using single transaction) |
| AI returns Student Mode result | `next_mode=STUDENT`, no teacher_intervention | No log created |
| AI returns Teacher Mode state without event | `teacher_intervention` present but same as before | No new log (only on state change) |
| Intervention persistence fails | N/A (not implemented) | **Roll back entire turn** (user msg, AI msg, evaluation, session state) — requires single transaction |

**Rollback Recommendation**: Since current architecture uses per-repository commits, full rollback isn't possible without refactoring. **Minimal approach**: Log the error, don't crash the turn, but mark intervention persistence as failed. **Proper approach**: Refactor to single transaction (out of scope for 4.5).

---

### 15. Performance Analysis

**Impact of Auto-Persistence**:
- **One additional INSERT** per Teacher Mode entry/continue turn
- **One additional UPDATE** per Teacher Mode exit/fallback turn
- **No additional SELECTs** during normal chat (only on entry/continue to check for duplicates)
- **Indexes sufficient**: `teacher_intervention_logs` has indexes on `session_id`, `user_id`, `created_at`
- **No N+1 queries**: Intervention history only loaded by `SessionEvidenceBuilder` (report generation) and Timeline API — not during chat
- **Normal chat unaffected**: Student Mode turns create zero intervention logs

**Performance Verdict**: Negligible impact. Single-row INSERT/UPDATE per Teacher Mode turn.

---

### 16. Database / Migration Requirement

**Current Schema Sufficient?** **Mostly Yes** for basic implementation.

**Required for Full Implementation**:
| Change | Required? | Reason |
|--------|-----------|--------|
| Add `message_id` FK to messages | **Recommended** | Traceability to AI message that delivered intervention |
| Add `intervention_type` CHECK constraint | **Recommended** | Data integrity (enter/continue/exit/limit_fallback) |
| Add unique index on (session_id, attempt_count, intervention_type) | **Optional** | Idempotency enforcement at DB level |

**Migration Required for 4.5?** **No** for minimal implementation. **Yes** for recommended traceability (add `message_id` column).

---

### 17. Backward Compatibility Analysis

| Component | Impact | Mitigation |
|-----------|--------|------------|
| Existing ChatService behavior | None | Only adds INSERT/UPDATE when teacher_intervention present |
| Student Mode | None | `teacher_intervention` is None → no log created |
| Teacher Mode | Enhanced | Logs now persisted automatically |
| AIResult handling | None | Reads existing fields only |
| StateUpdates | None | Continues to update SessionState JSON |
| SessionState persistence | None | Unchanged |
| TurnEvaluation persistence | None | Unchanged |
| TurnAssessment persistence | None | Unchanged |
| Report generation | Enhanced | Automatically includes new logs via EvidenceBuilder |
| Report versioning | None | Unchanged |
| Timeline | Enhanced | Automatically includes new logs via TimelineRepository |
| Intervention APIs | Enhanced | Now return auto-persisted logs |
| Phase 3 integration tests | None | Should continue passing |

**Student Mode Protection**: `state_updates.teacher_intervention` is `None` in Student Mode (see `student_nodes.py:808-816`). No accidental logs.

---

### 18. AI Boundary Verification

**Backend Responsibility (Confirmed)**:
- ✅ Inspect structured `AIResult.state_updates.teacher_intervention`
- ✅ Persist intervention information to `TeacherInterventionLog`
- ✅ Return normal response

**Backend Does NOT** (Correct):
- ❌ Teacher Mode detection (done in `DecisionEngine.decide()`)
- ❌ Struggle detection (done in `DecisionEngine.decide()`)
- ❌ Gap detection (done in `AIEvaluator` + `DecisionEngine`)
- ❌ Intervention decision-making (done in `DecisionEngine.decide()`)
- ❌ Explanation generation (done in `TeacherModeHandler` → LLM)
- ❌ Verification question generation (done in `TeacherModeHandler` + LLM)
- ❌ Verification decision-making (done in `DecisionEngine.decide()`)
- ❌ Mastery decisions (done in `DecisionEngine` + `LearnerModelManager`)
- ❌ Verification thresholds (constants in `DecisionEngine`)
- ❌ Mode switching logic (done in `DecisionEngine.decide()`)
- ❌ Teacher exit decisions (done in `DecisionEngine.decide()`)
- ❌ Pedagogical strategy selection (done in `DecisionEngine.decide()`)

**Boundary Intact**: The backend only persists what the AI engine explicitly provides in structured output.

---

### 19. Required Implementation Changes

**Files to Modify**:

| File | Change |
|------|--------|
| `backend/app/services/chat_service.py` | Add `TeacherInterventionRepository` import and instantiation; add persistence logic after SessionState update |
| `backend/app/repositories/teacher_intervention_repository.py` | Add `get_latest_open_by_session()` method for exit/fallback updates; add `create_or_update()` for idempotent entry/continue |

**Logic to Add in `ChatService.send_message()`** (after line 657, before return):

```python
# 8. Persist Teacher Intervention Log (if Teacher Mode event occurred)
if user_id and updates.teacher_intervention is not None and updates.teacher_intervention.active:
    ti = updates.teacher_intervention
    attempt = updates.teacher_attempt_count or ti.attempt_count
    
    # Determine intervention type from mode transition
    prev_mode = db_session.state.current_mode.value if hasattr(db_session.state.current_mode, 'value') else str(db_session.state.current_mode)
    new_mode = updates.current_mode.value if updates.current_mode and hasattr(updates.current_mode, 'value') else (str(updates.current_mode) if updates.current_mode else prev_mode)
    
    if prev_mode != "TEACHER" and new_mode == "TEACHER":
        intervention_type = "enter"
    elif prev_mode == "TEACHER" and new_mode == "TEACHER":
        intervention_type = "continue"
    elif prev_mode == "TEACHER" and new_mode == "STUDENT" and decision.should_restore_interrupted_question:
        intervention_type = "limit_fallback" if "Maximum Teacher attempts" in (decision.reason or "") else "exit"
    else:
        intervention_type = None
    
    if intervention_type in ("enter", "continue"):
        # Idempotent create
        existing = self.teacher_intervention_repo.get_latest_open_by_session(db, session_id, user_id, attempt)
        if existing:
            # Update explanation/question if changed
            pass
        else:
            self.teacher_intervention_repo.create(
                db=db,
                session_id=session_id,
                user_id=user_id,
                gap=ti.gap,
                attempt_count=attempt,
                teacher_explanation=ai_msg.content,  # AI response contains explanation
                verification_question=extract_verification_question(ai_msg.content),
                intervention_type=intervention_type,
            )
    elif intervention_type in ("exit", "limit_fallback"):
        # Update latest open log with verification result
        open_log = self.teacher_intervention_repo.get_latest_open_by_session(db, session_id, user_id)
        if open_log:
            verification_passed = 1 if evaluation.correctness >= 0.7 and evaluation.stuck_probability < 0.35 and len(evaluation.misconceptions) == 0 else 0
            open_log.verification_answer = message_in.content  # User's answer
            open_log.verification_passed = verification_passed
            open_log.intervention_type = intervention_type
            db.commit()
```

**Helper Function Needed**: `extract_verification_question(ai_content: str) -> str` — extract the last question from AI response (the verification question).

---

### 20. Required Test Cases

| # | Test Case | File |
|---|-----------|------|
| 1 | Student Mode turn creates no intervention log | `test_chat_service.py` |
| 2 | Teacher Mode entry creates intervention log (type=enter) | `test_chat_service.py` / new `test_teacher_intervention_persistence.py` |
| 3 | Teacher Mode continuation creates intervention log (type=continue) | new test file |
| 4 | Teacher explanation preserved in log | new test file |
| 5 | Verification question preserved in log | new test file |
| 6 | Verification answer preserved on exit turn | new test file |
| 7 | Verification result (pass/fail) preserved | new test file |
| 8 | Teacher Mode exit (pass) updates log with type=exit | new test file |
| 9 | Teacher Mode exit (limit_fallback) updates log with type=limit_fallback | new test file |
| 10 | Multiple Teacher Mode turns create correct number of logs | new test file |
| 11 | Intervention logs survive across requests (DB persistence) | new test file |
| 12 | Intervention logs included in report evidence | `test_report_service.py` / integration |
| 13 | Intervention logs appear in timeline | `test_timeline.py` / integration |
| 14 | Cross-user intervention data isolated | `test_teacher_intervention_api.py` (existing) |
| 15 | Unauthenticated requests protected | `test_teacher_intervention_api.py` (existing) |
| 16 | AI fallback (MockProvider) does not create fabricated logs | new test file |
| 17 | Intervention persistence failure handling | new test file |
| 18 | Existing ChatService tests remain compatible | `test_chat_service.py` (run existing) |
| 19 | Existing Teacher Mode tests remain compatible | `test_teacher_mode_persistence.py` (run existing) |
| 20 | Existing Phase 3 intervention API tests remain compatible | `test_teacher_intervention_api.py` (run existing) |
| 21 | Existing report tests remain compatible | `test_report_versioning.py` (run existing) |

**Test File Recommendation**: Create `backend/tests/services/test_teacher_intervention_persistence.py` for new persistence tests.

---

### 21. Exact Files Expected to Change

| File | Change Type |
|------|-------------|
| `backend/app/services/chat_service.py` | **MODIFY** — Add TeacherInterventionRepository, add persistence logic |
| `backend/app/repositories/teacher_intervention_repository.py` | **MODIFY** — Add `get_latest_open_by_session()`, `create_or_update()` |
| `backend/app/ai/schemas.py` | **POTENTIAL** — Add `intervention_type` to `TeacherIntervention` if AI should emit it (but per boundary, AI shouldn't decide persistence types) |
| `backend/alembic/versions/xxxx_add_message_id_to_teacher_intervention.py` | **NEW (optional)** — Migration for `message_id` FK |

**Files NOT to Change**:
- `backend/app/ai/engine.py` — AI boundary
- `backend/app/ai/graph.py` — Internal AI
- `backend/app/ai/nodes/student_nodes.py` — AI internal
- `backend/app/ai/decision_engine.py` — AI internal
- `backend/app/ai/teacher.py` — AI internal
- `backend/app/ai/session_evidence.py` — Already reads from logs
- `backend/app/services/report_service.py` — Already uses EvidenceBuilder
- `backend/app/services/timeline_service.py` — Already uses TimelineRepository
- `backend/app/api/v1/teacher_interventions.py` — Already reads from logs

---

### 22. Recommended Implementation Order

1. **Add repository methods** (`teacher_intervention_repository.py`):
   - `get_latest_open_by_session(db, session_id, user_id, attempt_count=None)`
   - `create_or_update_entry_continue(db, session_id, user_id, gap, attempt_count, explanation, question, type)`

2. **Add helper** in `chat_service.py`: `extract_verification_question(content: str) -> str`

3. **Add persistence logic** in `ChatService.send_message()` after SessionState update

4. **Write unit tests** for new repository methods

5. **Write integration tests** for auto-persistence scenarios (new test file)

6. **Run existing test suites** to verify backward compatibility:
   - `test_chat_service.py`
   - `test_teacher_mode_persistence.py`
   - `test_teacher_intervention_api.py`
   - `test_report_versioning.py`
   - `test_timeline.py`

7. **(Optional) Create migration** for `message_id` FK if traceability required

---

### 23. Risks / Edge Cases

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Duplicate logs on retry | Medium | Data pollution | Idempotency check by (session, attempt, type) |
| Verification answer from wrong turn | Low | Incorrect data | Only update on exit turn with `should_restore_interrupted_question` |
| Missing verification_question extraction | Medium | Incomplete logs | Robust extraction (last question mark in AI response) |
| Partial AI results (fallback) | Low | Missing logs | Guard: only persist if `teacher_intervention.active == True` |
| Transaction inconsistency | Medium | Orphaned logs | Accept current multi-commit; log errors |
| Student Mode accidentally creating logs | Low | Data pollution | Guard: `teacher_intervention.active` must be True |
| Multi-user session (not supported) | N/A | N/A | Sessions are single-user |

---

### 24. Final Recommendation

**Proceed with Implementation** using the following approach:

1. **Minimal Viable Implementation**: 
   - Persist `enter` and `continue` events on Teacher Mode turns
   - Update latest open log on exit/fallback turns
   - Use existing `TeacherInterventionRepository.create()` with idempotency check in service layer

2. **No Schema Migration Required** for MVP — current schema sufficient

3. **No AI Contract Changes** — backend derives `intervention_type` from mode transitions

4. **Extract Verification Question** from AI response content (last sentence ending in `?`)

5. **Leverage Existing Infrastructure** — EvidenceBuilder, Timeline, APIs already integrated

6. **Test Thoroughly** — Focus on multi-turn Teacher Mode flows, exit scenarios, and Student Mode isolation

**Architecture Decision**: One `TeacherInterventionLog` row per intervention **episode** (enter → continue* → exit/fallback), not per turn. Entry/continue create new rows; exit/fallback updates the latest open row. This preserves the pedagogical unity of a single intervention while maintaining append-only audit trail for entry/continue phases.

---

This audit confirms that Task 4.5 is **architecturally sound, low-risk, and builds cleanly on existing Phase 3 infrastructure**. The implementation requires only `ChatService` and `TeacherInterventionRepository` modifications, with no AI boundary violations.