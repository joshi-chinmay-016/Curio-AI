# Phase 3 Learning Persistence — Architecture Audit Report

**Status**: READ-ONLY AUDIT — No modifications made  
**Date**: 2026-09-25  
**Phase 1 & 2**: Stable (369 tests passing)

---

## 1. Current Architecture Overview

### 1.1 Model Layer (Database Persistence)

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|
| **User** | `users` | id, email, hashed_password, is_active, created_at, updated_at | → sessions (1:N) |
| **Session** | `sessions` | id, user_id (FK), topic, source_type, document_id (FK), status, timestamps | → user (N:1), state (1:1), messages (1:N), report (1:1) |
| **SessionState** | `session_states` | session_id (PK, FK), current_mode, difficulty, confidence, active_concept, current_question_id, interrupted_question_id, consecutive_strong_answers, consecutive_weak_answers, unresolved_misconceptions (JSON), mastered_concepts (JSON), **teacher_attempt_count**, **teacher_intervention (JSON)** | → session (1:1) |
| **Message** | `messages` | id, session_id (FK), sender, content, input_type, created_at | → session (N:1), evaluation (1:1) |
| **TurnEvaluation** | `turn_evaluations` | message_id (PK, FK), correctness, clarity, completeness, depth, relevance, stuck_probability, misconceptions (JSON), missing_concepts (JSON), undefined_terms (JSON), mastered_concepts (JSON), knowledge_gap, recommended_strategy, recommended_difficulty | → message (1:1) |
| **SessionReport** | `session_reports` | session_id (PK, FK), understanding_score, mastery_level, strengths (JSON), learning_gaps (JSON), misconceptions_detected (JSON), concepts_mastered (JSON), teacher_interventions_required, difficulty_achieved, personalized_roadmap (JSON), recommended_exercises (JSON), evidence_confidence, concept_assessments (JSON), resolved/unresolved gaps/misconceptions (JSON), session_evaluation (JSON) | → session (1:1) |

### 1.2 Key Observations — Current Persistence

**✅ Already Persisted (Session-scoped):**
- Session metadata (topic, source_type, status, timestamps)
- **SessionState**: mode (STUDENT/TEACHER/EVALUATOR), difficulty (1-5), confidence (0-1), active_concept
- **Question Tracking**: `current_question_id` (FK to Message), `interrupted_question_id` (FK to Message)
- **Streaks**: consecutive_strong_answers, consecutive_weak_answers
- **Learning Lists**: unresolved_misconceptions (JSON list[str]), mastered_concepts (JSON list[str])
- **Teacher Mode**: teacher_attempt_count (int), teacher_intervention (JSON with active, gap, attempt_count, verification_required)
- **Messages**: Full conversation history with sender, content, input_type
- **TurnEvaluations**: Per-user-message evaluation (8 scoring dims + strategy + difficulty)
- **SessionReport**: Final report with mastery, gaps, misconceptions, roadmap, concept_assessments

**❌ NOT Persisted (Memory-only in AIContext):**
| AIContext Field | Current Location | Persistence Status |
|-----------------|------------------|-------------------|
| `SessionState.concept_mastery` (Dict[str, float]) | AI schema only | ❌ Not in DB |
| `SessionState.misconception_counts` (Dict[str, int]) | AI schema only | ❌ Not in DB |
| `SessionState.recent_strategy_history` (List[Strategy]) | AI schema only | ❌ Not in DB |
| `SessionState.mode_switch_history` (List[ModeTransition]) | AI schema only (partially in SessionState.mode_switch_history JSON) | ⚠️ Partial |
| `LearningContext.recent_evaluations` (List[TurnEvaluation]) | Built from TurnEvaluation table at runtime | ✅ Derived |
| `LearningContext.teacher_intervention` (TeacherIntervention) | Built from SessionState.teacher_intervention JSON | ✅ Derived |
| `LearningContext.mastered_concepts` (List[str]) | Built from SessionState.mastered_concepts JSON | ✅ Derived |
| `LearningContext.unresolved_misconceptions` (List[str]) | Built from SessionState.unresolved_misconceptions JSON | ✅ Derived |
| `CurrentQuestion` objects (id, content, concept, difficulty) | Hydrated from Message table via question_ids | ✅ Derived |
| `conversation.recent_messages` (List[ChatMessage]) | Built from Message table at runtime | ✅ Derived |

---

## 2. Chinmay's AI Layer — What Needs Backend Persistence

### 2.1 StateUpdates from AIResult (Returned by CurioEngine.process())

The AI layer returns `StateUpdates` containing fields that **must be persisted** to survive restarts and enable multi-session continuity:

```python
class StateUpdates(BaseModel):
    active_concept: Optional[str]
    interrupted_question: Optional[CurrentQuestion]  # → interrupted_question_id
    mastered_concepts: Optional[List[str]]           # → SessionState.mastered_concepts
    unresolved_misconceptions: Optional[List[str]]   # → SessionState.unresolved_misconceptions
    teacher_intervention: Optional[TeacherIntervention]  # → SessionState.teacher_intervention
    current_question: Optional[CurrentQuestion]      # → current_question_id
    current_mode: Optional[Mode]                     # → SessionState.current_mode
    difficulty: Optional[int]                        # → SessionState.difficulty
    confidence: Optional[float]                      # → SessionState.confidence
    concept_mastery: Optional[Dict[str, float]]      # ❌ NO DB COLUMN
    consecutive_failures: Optional[int]              # → consecutive_weak_answers
    consecutive_successes: Optional[int]             # → consecutive_strong_answers
    teacher_attempt_count: Optional[int]             # → SessionState.teacher_attempt_count
    recent_strategy_history: Optional[List[Strategy]]  # ❌ NO DB COLUMN
    misconception_counts: Optional[Dict[str, int]]   # ❌ NO DB COLUMN
    mode_switch_history: Optional[List[ModeTransition]]  # ❌ NO DB COLUMN (partial JSON)
```

**Critical Gap**: `concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history` exist in AI schema but **have no database columns**.

### 2.2 SessionEvidence (Built by SessionEvidenceBuilder for Report Generation)

`SessionEvidence` aggregates per-turn evidence for the `SessionEvaluator`:

```python
class SessionEvidence(BaseModel):
    session_id: str
    topic: str
    turns: List[TurnEvidence]                    # Built from Message + TurnEvaluation
    teacher_interventions: List[TeacherInterventionEvidence]  # Detected from transcript
    concepts_encountered: List[str]
    concept_evidence_map: Dict[str, ConceptEvidenceItem]  # Per-concept rollup
    difficulty_progression: List[int]
    confidence_progression: List[float]
    total_learner_turns: int
    successful_turns: int
    failed_turns: int
```

**Status**: Built **on-demand at report time** from existing tables (Message, TurnEvaluation, SessionState). No new persistence needed for report generation.

### 2.3 Teacher Mode — State Machine Requirements

From `decision_engine.py` and `student_nodes.py`:

| State | Persisted In | Notes |
|-------|-------------|-------|
| `teacher_attempt_count` | SessionState.teacher_attempt_count | ✅ Already |
| `teacher_intervention` (gap, attempt_count, verification_required) | SessionState.teacher_intervention (JSON) | ✅ Already |
| `interrupted_question_id` | SessionState.interrupted_question_id | ✅ Already |
| `current_question_id` | SessionState.current_question_id | ✅ Already |
| Mode transition history | ❌ Only in AIContext.mode_switch_history | **Missing** |
| Per-concept mastery scores (0.0-1.0) | ❌ Only in AIContext.concept_mastery | **Missing** |
| Per-misconception occurrence counts | ❌ Only in AIContext.misconception_counts | **Missing** |

---

## 3. AI / Backend Contract Boundary

### 3.1 Current Contract (Stable)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND SERVICE LAYER                           │
│  ChatService.send_message()                                         │
│  1. Load SessionState from DB (with ownership check)               │
│  2. Build AIContext from DB state:                                 │
│     - SessionState → current_state                                 │
│     - Message history → conversation.recent_messages               │
│     - TurnEvaluation → learning_context.recent_evaluations         │
│     - SessionState.mastered_concepts → learning_context.mastered   │
│     - SessionState.unresolved_misconceptions → learning_context... │
│     - SessionState.teacher_intervention → learning_context...      │
│     - SessionState.question_ids → CurrentQuestion hydration        │
│  3. Call: ai_result = ai_engine.process(ai_context)                │
│  4. Persist AIResult:                                               │
│     - User message + AI message → Message table                    │
│     - TurnEvaluation → TurnEvaluation table                        │
│     - StateUpdates → SessionState (via update_state)               │
│  5. Return ChatTurnResponse                                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        AI LAYER (Chinmay)                           │
│  CurioEngine.process(AIContext) → AIResult                          │
│  AIResult contains:                                                 │
│   - evaluation: TurnEvaluation                                      │
│   - decision: LearningDecision                                      │
│   - response: AIResponse                                            │
│   - state_updates: StateUpdates  ◄─── BACKEND MUST PERSIST         │
│   - session_evaluation: SessionEvaluation (optional)               │
│   - learning_report: LearningReport (optional)                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Contract Compliance — Current State

| AIResult Field | Backend Handles | Gap |
|----------------|-----------------|-----|
| `evaluation` | ✅ Persisted to TurnEvaluation | None |
| `decision` | ✅ Used for response, not persisted | Decision history not stored |
| `response` | ✅ Persisted as AI Message | None |
| `state_updates` | ⚠️ Partial (see below) | **concept_mastery, misconception_counts, recent_strategy_history, mode_switch_history missing** |
| `session_evaluation` | ✅ Persisted to SessionReport | None |
| `learning_report` | ✅ Persisted to SessionReport | None |

### 3.3 StateUpdates → SessionState Mapping (Current)

```python
# In ChatService.send_message() lines 410-545:
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
    teacher_intervention_data=new_ti_data,      # Legacy field
    mode_switch_history=new_msh,                # Written but NO DB COLUMN
    teacher_attempt_count=new_teacher_attempts,
    teacher_intervention=new_teacher_intervention,
)
self.session_repo.update_state(db, session_id, state_update)
```

**Repository.update_state()** (lines 68-94) writes `mode_switch_history` to `db_state.mode_switch_history` but **the SessionState model has no `mode_switch_history` column** — this data is silently dropped.

---

## 4. Missing Persistence — Summary

### 4.1 Database Columns Needed (SessionState table)

| Column | Type | Purpose | Source |
|--------|------|---------|--------|
| `concept_mastery` | JSON (Dict[str, float]) | Per-concept mastery scores 0.0-1.0 | StateUpdates.concept_mastery |
| `misconception_counts` | JSON (Dict[str, int]) | Occurrence count per misconception | StateUpdates.misconception_counts |
| `recent_strategy_history` | JSON (List[str]) | Last N strategies used | StateUpdates.recent_strategy_history |
| `mode_switch_history` | JSON (List[dict]) | Full mode transition audit trail | StateUpdates.mode_switch_history |

### 4.2 Concept-Level Persistence — Design Decision Needed

**Option A: Extend SessionState (Session-scoped)**
- Add JSON columns above to `session_states`
- Simple, no new tables
- **Limitation**: Mastery doesn't persist across sessions

**Option B: New `UserConceptProgress` Table (User-scoped)**
```sql
user_concept_progress (
    user_id UUID FK users,
    concept VARCHAR NOT NULL,
    mastery_score FLOAT DEFAULT 0.0,  -- 0.0-1.0
    total_attempts INT DEFAULT 0,
    successful_attempts INT DEFAULT 0,
    last_practiced_at TIMESTAMP,
    last_difficulty INT DEFAULT 1,
    misconception_count INT DEFAULT 0,
    PRIMARY KEY (user_id, concept)
)
```
- **Advantage**: Cross-session mastery tracking, adaptive difficulty per user
- **Required for**: "User A learns 'recursion' in Session 1 → Session 2 starts at appropriate level"

**Option C: Both** — SessionState for session-specific state, UserConceptProgress for long-term mastery

### 4.3 Teacher Mode Persistence — Current vs Required

| State | Current | Required |
|-------|---------|----------|
| `teacher_attempt_count` | ✅ Integer column | ✅ |
| `teacher_intervention` (gap, attempt_count, verification_required) | ✅ JSON column | ✅ |
| `interrupted_question_id` | ✅ UUID column | ✅ |
| `current_question_id` | ✅ UUID column | ✅ |
| Full intervention history (per-attempt explanations, verification Q&A) | ❌ | **New table `TeacherInterventionLog`** |
| Mode transition audit trail | ⚠️ Partial (dropped) | **mode_switch_history column** |

---

## 5. APIs Currently Available for Learning State

| Endpoint | Returns | Learning State Included |
|----------|---------|------------------------|
| `GET /sessions/{id}` | SessionResponse + SessionStateResponse | mode, difficulty, confidence, active_concept, question_ids, streaks, mastered_concepts, unresolved_misconceptions, teacher_attempt_count, teacher_intervention |
| `GET /sessions` | List[SessionSummaryResponse] | mode, difficulty, confidence (summary only) |
| `GET /sessions/{id}/messages` | List[MessageResponse] | Full conversation (no evaluations) |
| `GET /sessions/{id}/report` | SessionReportResponse | Final mastery, gaps, misconceptions, roadmap, concept_assessments |
| `POST /sessions/{id}/messages` | ChatTurnResponse | Current turn evaluation + decision (not historical) |

**Missing APIs:**
- `GET /users/me/concepts` — Cross-session concept mastery
- `GET /users/me/progress` — Learning trajectory over time
- `GET /sessions/{id}/evaluations` — Detailed turn-by-turn evaluation history
- `GET /sessions/{id}/teacher-interventions` — Teacher mode intervention log

---

## 6. Required Backend Changes

### 6.1 Database Migrations (Priority Order)

| # | Migration | Description | Risk |
|---|-----------|-------------|------|
| 1 | Add `concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history` to `session_states` | Session-scoped AI state persistence | Low (additive JSON columns) |
| 2 | Create `user_concept_progress` table | Cross-session user mastery tracking | Medium (new table, FK) |
| 3 | Create `teacher_intervention_log` table | Full teacher mode audit trail | Medium (new table) |

### 6.2 Repository Changes

| Repository | New Methods Needed |
|------------|-------------------|
| `SessionRepository` | `update_state()` already handles new JSON columns if model updated; `get_concept_mastery(user_id, concept)` |
| `MessageRepository` | `get_evaluations_by_session(session_id)` — already exists as `get_recent_evaluations_by_session` |
| **New: `ConceptProgressRepository`** | `get_by_user(user_id)`, `get_by_user_and_concept(user_id, concept)`, `upsert_progress(user_id, concept, mastery_delta, difficulty, misconception_delta)` |

### 6.3 Service Changes

| Service | Changes |
|---------|---------|
| `ChatService` | Update `send_message()` to persist new StateUpdates fields; hydrate `concept_mastery`, `misconception_counts`, `recent_strategy_history` into AIContext |
| `SessionService` | No breaking changes; may add `get_user_concept_progress(user_id)` |
| **New: `LearningProgressService`** | Aggregate cross-session progress; compute readiness for topics; recommend next concepts |

### 6.4 Schema Changes

| Schema | Changes |
|--------|---------|
| `SessionStateBase` | Add `concept_mastery`, `misconception_counts`, `recent_strategy_history`, `mode_switch_history` |
| `SessionStateResponse` | Include new fields |
| **New: `ConceptProgressResponse`** | User-facing concept mastery |
| **New: `LearningProgressResponse`** | Aggregated user progress |

### 6.5 API Changes

| Endpoint | Changes |
|----------|---------|
| `GET /sessions/{id}` | Include new SessionState fields |
| **New: `GET /api/v1/users/me/concepts`** | List user's concept mastery across sessions |
| **New: `GET /api/v1/users/me/progress`** | Aggregated learning progress |
| **New: `GET /api/v1/sessions/{id}/teacher-interventions`** | Teacher mode audit log |

---

## 7. Security & Ownership Considerations

### 7.1 Current Ownership Model (Enforced)
- **Session** owned by User (via `Session.user_id` FK)
- **All session operations** require `current_user.id` match (Phase 2 Task 5)
- **SessionReport** accessible only via Session ownership
- **Messages/Evaluations** accessible only via Session ownership

### 7.2 New Data Ownership

| New Data | Owner | Access Control |
|----------|-------|----------------|
| `user_concept_progress` | **User** (not Session) | `user_id` FK; user sees only own |
| `teacher_intervention_log` | **Session** → **User** | Via Session ownership |
| `concept_mastery` (SessionState) | **Session** → **User** | Via Session ownership |
| `mode_switch_history` | **Session** → **User** | Via Session ownership |

**Critical**: Concept mastery is **User-scoped**, not Session-scoped. A user's mastery of "recursion" persists across sessions. This requires `user_concept_progress` with `user_id` FK and RLS/policy enforcement.

### 7.3 No Cross-User Leakage
- All new queries must filter by `current_user.id` (User-scoped) or `session.user_id` (Session-scoped)
- `user_concept_progress` queries: `WHERE user_id = current_user.id`
- `teacher_intervention_log` queries: `JOIN sessions ON ... WHERE sessions.user_id = current_user.id`

---

## 8. Migration Requirements

### 8.1 Alembic Migrations (No Data Loss)

```python
# Migration 1: Extend session_states
op.add_column('session_states', sa.Column('concept_mastery', sa.JSON(), server_default='{}', nullable=False))
op.add_column('session_states', sa.Column('misconception_counts', sa.JSON(), server_default='{}', nullable=False))
op.add_column('session_states', sa.Column('recent_strategy_history', sa.JSON(), server_default='[]', nullable=False))
op.add_column('session_states', sa.Column('mode_switch_history', sa.JSON(), server_default='[]', nullable=False))

# Migration 2: Create user_concept_progress
op.create_table('user_concept_progress',
    sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    sa.Column('concept', sa.String(), primary_key=True),
    sa.Column('mastery_score', sa.Float(), server_default='0.0', nullable=False),
    sa.Column('total_attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('successful_attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_practiced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_difficulty', sa.Integer(), server_default='1', nullable=False),
    sa.Column('misconception_count', sa.Integer(), server_default='0', nullable=False),
)
op.create_index('ix_user_concept_progress_user_id', 'user_concept_progress', ['user_id'])

# Migration 3: Create teacher_intervention_log
op.create_table('teacher_intervention_log',
    sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
    sa.Column('session_id', sa.UUID(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
    sa.Column('intervention_index', sa.Integer(), nullable=False),
    sa.Column('gap', sa.String(), nullable=False),
    sa.Column('attempt_count', sa.Integer(), nullable=False),
    sa.Column('teacher_explanation', sa.Text(), nullable=False),
    sa.Column('verification_question', sa.Text(), nullable=False),
    sa.Column('verification_answer', sa.Text(), nullable=True),
    sa.Column('verification_passed', sa.Boolean(), nullable=False),
    sa.Column('related_concept', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
)
op.create_index('ix_teacher_intervention_log_session_id', 'teacher_intervention_log', ['session_id'])
```

### 8.2 Backward Compatibility

- All new columns have `server_default` — existing rows get sensible defaults
- No `NOT NULL` without default on existing tables
- New tables are additive — no impact on existing queries
- API responses include new fields as optional (default empty)

---

## 9. Testing Requirements

### 9.1 Unit Tests (Mock-based, No DB)

| Test Target | Scenarios |
|-------------|-----------|
| `SessionRepository.update_state()` | Persists all new JSON fields correctly |
| `ConceptProgressRepository.upsert_progress()` | Increments mastery, attempts, difficulty |
| `LearningProgressService.get_user_progress()` | Aggregates across sessions correctly |
| `ChatService.send_message()` | Hydrates new fields into AIContext; persists StateUpdates fully |

### 9.2 Integration Tests (DB Required)

| Test File | New Tests |
|-----------|-----------|
| `test_database_integration.py` | `test_user_concept_progress_crud`, `test_concept_mastery_cross_session` |
| `test_teacher_mode_persistence.py` | `test_teacher_intervention_log_persisted`, `test_mode_switch_history_persisted` |
| `test_api_integration.py` | `test_get_user_concepts_endpoint`, `test_get_user_progress_endpoint` |
| `test_session_idor.py` | Cross-user isolation for new endpoints |

### 9.3 Regression Tests (Must Continue Passing)

All 369 existing tests must pass. Key areas:
- Session CRUD + ownership (41 IDOR tests)
- Teacher mode persistence (14 tests)
- Chat service hydration (22 tests)
- Report generation (6 tests)
- Auth endpoints (15 tests)

---

## 10. Recommended Phase 3 Implementation Tasks (Dependency Order)

| Task | Description | Dependencies | Est. Effort |
|------|-------------|--------------|-------------|
| **3.1** | **Extend SessionState model + migration** (add 4 JSON columns) | None | 1 day |
| **3.2** | **Update ChatService to persist/fetch new StateUpdates fields** | 3.1 | 1 day |
| **3.3** | **Create UserConceptProgress model + migration + repository** | 3.1 | 2 days |
| **3.4** | **Implement LearningProgressService** (cross-session aggregation) | 3.3 | 2 days |
| **3.5** | **Add User Concept Progress API** (`GET /users/me/concepts`, `GET /users/me/progress`) | 3.4 | 1 day |
| **3.6** | **Create TeacherInterventionLog model + migration + repository** | 3.1 | 1 day |
| **3.7** | **Update SessionEvidenceBuilder to use TeacherInterventionLog** | 3.6 | 1 day |
| **3.8** | **Add Teacher Intervention API** (`GET /sessions/{id}/teacher-interventions`) | 3.7 | 0.5 day |
| **3.9** | **Full integration test suite + regression validation** | All above | 2 days |

**Total Estimated**: ~11.5 days

---

## 11. Regression Risk Assessment

| Area | Risk | Mitigation |
|------|------|------------|
| Session CRUD | Low | Additive columns only; no schema breaking changes |
| Teacher Mode | Low | Existing fields unchanged; new fields optional |
| ChatService | Medium | Large function; add tests for new field hydration/persistence |
| Report Generation | Low | Uses SessionEvidenceBuilder (on-demand); no schema dependency |
| Auth/Ownership | None | New tables follow same FK patterns |
| AI Engine | None | Contract unchanged (AIContext/AIResult stable) |

---

## 12. AI Logic Duplication — What to Avoid

| AI Logic | Current Location | Backend Should NOT |
|----------|------------------|-------------------|
| Strategy selection | DecisionEngine | Re-implement strategy priority |
| Difficulty transitions | DecisionEngine | Calculate difficulty deltas |
| Confidence updates | DecisionEngine + ScoringEngine | Recalculate confidence |
| Teacher verification thresholds | DecisionEngine constants | Hardcode 0.70/0.40/0.35 |
| Misconception detection | AIEvaluator (LLM) | Parse evaluations for misconceptions |
| Gap analysis | GapAnalyzer | Re-implement gap lifecycle |
| Mastery level determination | ScoringEngine | Calculate mastery from scores |
| Roadmap generation | ReportBuilder | Generate roadmap items |

**Backend Responsibility**: Persistence, hydration, aggregation, API exposure  
**AI Responsibility**: All pedagogical reasoning, scoring, decision-making

---

## 13. Clear Recommendation — Next Implementation Task

### **Start with Task 3.1: Extend SessionState Model + Migration**

**Rationale**:
1. **Lowest risk** — additive JSON columns with defaults
2. **Unblocks everything** — ChatService can immediately persist the 4 missing StateUpdates fields
3. **No new tables** — avoids FK complexity initially
4. **Immediate value** — mode_switch_history, concept_mastery, misconception_counts, recent_strategy_history survive restarts
5. **Backward compatible** — existing sessions get empty defaults

**Implementation Steps**:
1. Add 4 columns to `SessionState` SQLAlchemy model
2. Create Alembic migration with `server_default`
3. Update `SessionStateBase` / `SessionStateResponse` schemas
4. Verify `SessionRepository.update_state()` handles new fields (already uses dynamic `hasattr` checks)
5. Update `ChatService.send_message()` to populate new fields from `StateUpdates`
6. Update `ChatService.send_message()` to hydrate new fields into `AIContext.current_state`
7. Run full test suite (369 tests) — zero regressions expected

**Deliverable**: SessionState persists full AIStateUpdates round-trip; AIContext hydrated with complete learning state.

---

## Appendix: File Inventory for Phase 3 Changes

### Models (Modify)
- `backend/app/models/session.py` — Add 4 JSON columns to SessionState

### Schemas (Modify)
- `backend/app/schemas/session.py` — Add fields to SessionStateBase, SessionStateResponse

### Repositories (Modify)
- `backend/app/repositories/session_repository.py` — update_state() already compatible

### Services (Modify)
- `backend/app/services/chat_service.py` — Hydrate + persist new fields

### Migrations (New)
- `backend/alembic/versions/xxx_extend_session_state_phase3.py`

### New Models (Task 3.3+)
- `backend/app/models/concept_progress.py` — UserConceptProgress
- `backend/app/models/teacher_intervention_log.py` — TeacherInterventionLog

### New Repositories (Task 3.3+)
- `backend/app/repositories/concept_progress_repository.py`
- `backend/app/repositories/teacher_intervention_repository.py`

### New Services (Task 3.4+)
- `backend/app/services/learning_progress_service.py`

### New API Routes (Task 3.5+)
- `backend/app/api/v1/progress.py` — User progress endpoints

### Tests (New)
- `backend/tests/integration/test_concept_progress.py`
- `backend/tests/integration/test_teacher_intervention_log.py`
- `backend/tests/api/test_progress_api.py`