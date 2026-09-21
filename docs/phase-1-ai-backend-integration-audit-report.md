# Curio AI — Phase 1: AI–Backend Integration Compatibility Audit Report

**Author:** Senior Backend Architect  
**Project:** Curio AI (Feynman Role-Reversal Learning Platform)  
**Date:** September 21, 2026  
**Status:** Audit Complete — **ACTION ITEMS IDENTIFIED**  
**Repository:** `joshi-chinmay-016/Curio-AI`  
**Current Branch:** `backend` (synchronized with `dev`)  
**Architectural Contract:** `AIContext` $\rightarrow$ `CurioEngine.process()` $\rightarrow$ `AIResult`

---

## 1. Executive Summary

A comprehensive, read-only compatibility audit was performed on the Curio AI backend to evaluate the current state of integration between the backend infrastructure / service layer and the newly merged AI engine (`CurioEngine`, LangGraph state workflows, Student Mode, Teacher Mode, and Evaluator Mode).

### Key Audit Findings:
1. **Core Architectural Plumbing is Established**: The backend service layer ([`ChatService`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py)) interacts directly with [`CurioEngine.process()`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L38) using strongly-typed [`AIContext`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L450) and consuming [`AIResult`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L376). Unit tests for `ChatService` (11 tests) and core AI components (131 tests) pass cleanly.
2. **Provider Wiring Mismatch (P0 - Critical)**: `ChatService.__init__` instantiates `self.ai_provider = GroqLLMProvider()`, but does **not** pass it to `CurioEngine()`. Since `CurioEngine.__init__` defaults to `MockLLMProvider()`, the live application API (`chat_service = ChatService()`) defaults to mock AI inference rather than real Groq inference in production.
3. **Teacher Mode State Persistence Loss (P1 - High)**: The AI contract produces and requires `teacher_attempt_count: int` and `teacher_intervention: Optional[TeacherIntervention]`. However, the PostgreSQL database model `SessionState` and schema `SessionStateBase` have no columns/fields for these. As a result, `teacher_attempt_count` is lost on every turn and resets to `0`, preventing Teacher Mode from advancing past Attempt 1 (Conceptual $\rightarrow$ Analogy $\rightarrow$ Worked Example).
4. **Missing Prior Evaluations Hydration (P1 - High)**: `ChatService` does not populate `learning_context.recent_evaluations` from `turn_evaluations` in the database. Consequently, `DecisionEngine`'s Trigger C (repeated failure on the same knowledge gap) cannot evaluate past turn evaluations.
5. **Database Transaction / Error Recovery Gap (P2 - Medium)**: Incoming user messages are persisted to the database before calling `CurioEngine.process()`. If the AI engine fails or times out, the database transaction is not rolled back, leaving orphan user messages without AI responses.
6. **Overall Readiness**: **NOT FULLY READY** for Phase 1 sign-off until the P0 provider wiring and P1 Teacher Mode attempt/evaluations persistence issues are addressed.

---

## 2. Strict Responsibility Boundaries

- **Backend Responsibility**: Backend infrastructure, REST APIs, authentication, PostgreSQL database, Alembic migrations, persistence, transaction safety, security, and deployment.
- **AI Intelligence Responsibility (Chinmay)**: AI intelligence, system prompts, Socratic heuristics, decision trees, LangGraph nodes/workflows, Student/Teacher/Evaluator Mode logic, gap analysis, and report generation intelligence.

---

## 3. Detailed Audit Sections

### A. Files Inspected

#### 1. AI Schemas & Engine Interfaces
- [`backend/app/ai/schemas.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py): Definition of `AIContext`, `AIResult`, `SessionState`, `StateUpdates`, `TurnEvaluation`, `LearningDecision`, `AIResponse`, `CurrentQuestion`, `TeacherIntervention`, `SessionEvidence`, `SessionEvaluation`, and `LearningReport`.
- [`backend/app/ai/engine.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py): `CurioEngine` implementation, `process()` entry point, and session evaluation methods.
- [`backend/app/ai/graph.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/graph.py): LangGraph state machine definition (`START` $\rightarrow$ `evaluation` $\rightarrow$ `decision` $\rightarrow$ `response` $\rightarrow$ `state_updates` $\rightarrow$ `END`).
- [`backend/app/ai/nodes/student_nodes.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/nodes/student_nodes.py): Workflow nodes (`evaluation_node`, `decision_node`, `response_node`, `state_updates_node`).
- [`backend/app/ai/student.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/student.py): Socratic student persona handler and single-question enforcement.
- [`backend/app/ai/teacher.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/teacher.py): Teacher mode handler, gap-specific explanation, and verification questions.
- [`backend/app/ai/evaluator.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/evaluator.py): Semantic evaluator for learner turns.
- [`backend/app/ai/decision_engine.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/decision_engine.py): Deterministic pedagogical decision engine and mode/strategy transitions.
- [`backend/app/ai/session_evaluator.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/session_evaluator.py): Synthesis and scoring for Phase 3 evaluation.
- [`backend/app/ai/session_evidence.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/session_evidence.py): Structured evidence compilation from session turns.
- [`backend/app/ai/orchestrator.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/orchestrator.py): Legacy orchestrator.
- [`backend/app/ai/providers/groq_provider.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/groq_provider.py): Production Groq LLM provider.
- [`backend/app/ai/providers/mock_provider.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/mock_provider.py): Deterministic mock provider.
- [`backend/app/ai/prompts/evaluator_prompts.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/prompts/evaluator_prompts.py) & [`teacher_prompts.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/prompts/teacher_prompts.py): System prompts.

#### 2. Backend Services & Repositories
- [`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py): Primary interaction layer between API and `CurioEngine`.
- [`backend/app/services/session_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/session_service.py): Session lifecycle management.
- [`backend/app/services/report_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/report_service.py): Phase 3 report generation service.
- [`backend/app/repositories/session_repository.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py): Database operations for sessions and states.
- [`backend/app/repositories/message_repository.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/message_repository.py): Message and turn evaluation CRUD.
- [`backend/app/repositories/report_repository.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/report_repository.py): Report persistence.

#### 3. Database Models & Backend Schemas
- [`backend/app/models/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py): SQLAlchemy models `Session` and `SessionState`.
- [`backend/app/models/message.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/message.py): SQLAlchemy model `Message`.
- [`backend/app/models/evaluation.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/evaluation.py): SQLAlchemy model `TurnEvaluation`.
- [`backend/app/models/report.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/report.py): SQLAlchemy model `SessionReport`.
- [`backend/app/schemas/message.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py): `MessageCreate`, `MessageResponse`, `ChatTurnResponse`, `TurnEvaluationResponse`, `LearningDecisionResponse`.
- [`backend/app/schemas/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/session.py): `SessionStateBase`, `SessionStateResponse`, `SessionResponse`.
- [`backend/app/schemas/common.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/common.py): Shared backend enums (`LearningMode`, `LearningStrategy`, `InputType`, `SourceType`).

#### 4. API Routers
- [`backend/app/api/v1/messages.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/messages.py): Chat endpoints (`POST /sessions/{id}/messages`, `GET /sessions/{id}/messages`).
- [`backend/app/api/v1/sessions.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/sessions.py): Session lifecycle endpoints.
- [`backend/app/api/v1/reports.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/reports.py): Report retrieval endpoint.

#### 5. Test Suites
- [`backend/tests/services/test_chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/services/test_chat_service.py): 11 passing unit tests for ChatService.
- [`backend/tests/integration/test_teacher_mode_persistence.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/integration/test_teacher_mode_persistence.py): Teacher mode persistence tests.
- [`backend/tests/ai/test_phase1_student_mode.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_phase1_student_mode.py), [`test_phase2_teacher_mode.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_phase2_teacher_mode.py), [`test_engine.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_engine.py): 131 passing AI unit tests.

---

### B. Confirmed Integration Behavior

1. **Architectural Contract Boundary Adherence**:
   - `ChatService` invokes the canonical AI engine through `ai_result: AIResult = self.ai_engine.process(context)` at line 227 of [`chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L227).
   - The method accepts a strongly typed `AIContext` and returns an `AIResult`.
2. **AIContext Construction**:
   - `SessionInfo`: Constructed with `session_id` (stringified UUID), `topic`, and `source_mode` (derived from `session.source_type`).
   - `ConversationContext`: Compiled from database message history, correctly mapping database message sender (`AI` vs `USER`) to `Role.ASSISTANT` and `Role.USER`.
   - `InputType` Normalization: Safe normalization ensures lowercase or missing values cleanly default to `InputType.TEXT` without throwing validation errors.
   - `SessionState`: Hydrated with `current_mode`, `current_difficulty`, `understanding_confidence`, `active_concept`, and answer streak counters (`consecutive_strong_answers` $\rightarrow$ `consecutive_successes`, `consecutive_weak_answers` $\rightarrow$ `consecutive_failures`).
3. **Question Hydration**:
   - `current_question_id` and `interrupted_question_id` from PostgreSQL are looked up in the session's message history. When matching messages are found, rich `CurrentQuestion` objects (`id`, `content`, `concept`, `difficulty`) are constructed.
   - If IDs are `None` or refer to messages not in history, hydration safely leaves them as `None` without crashing.
4. **AIResult Consumption & Persistence**:
   - **User Message**: Created and committed prior to engine invocation.
   - **AI Response**: Created in the database with `sender="AI"` and content from `ai_result.response.content`.
   - **Turn Evaluation**: All 13 fields from `ai_result.evaluation` (correctness, clarity, depth, stuck_probability, misconceptions, etc.) are converted to `TurnEvaluationResponse` and persisted in `turn_evaluations` linked to `user_msg.id`.
   - **State Updates Merging**: `StateUpdates` from `ai_result` are merged defensively: `None` values in updates preserve existing database values; `mastered_concepts` and `unresolved_misconceptions` are deduplicated and merged with existing lists.
   - **API Return Contract**: `ChatService.send_message` returns a `ChatTurnResponse` matching all frontend Pydantic expectations.
5. **Question ID Tracking & Fallback**:
   - For newly generated questions (which carry non-UUID string IDs like `"q_a1b2c3d4"`), `ChatService` catches the `ValueError` and falls back to `ai_msg.id` (the persisted database message UUID).
   - When entering Teacher Mode, `interrupted_question_id` is snapshotted from the previous `current_question_id`.
   - When exiting Teacher Mode with `should_restore_interrupted_question=True`, `interrupted_question_id` is set to `None`.
6. **Separation of Concerns**:
   - The backend service layer does not contain prompts, pedagogical rules, or decision-making trees.
   - Report compilation is delegated cleanly to `ReportService` and `SessionEvidenceBuilder`.

---

### C. Contract Mismatches (Confirmed Issues)

#### 1. CurioEngine Provider Defaulting to Mock in Production Runtime (Critical)
- **Location:** [`backend/app/services/chat_service.py:44-47`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L44-L47) and [`backend/app/ai/engine.py:34-36`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L34-L36)
- **Detail:** In `ChatService.__init__`:
  ```python
  self.ai_provider = GroqLLMProvider()
  self.orchestrator = AIOrchestrator(self.ai_provider)
  self.ai_engine = ai_engine or CurioEngine()
  ```
  `CurioEngine.__init__` defaults to `MockLLMProvider()` if no provider is passed. `ChatService` does **not** pass `self.ai_provider` into `CurioEngine()`.
- **Impact:** In the actual production API endpoint ([`backend/app/api/v1/messages.py:10`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/messages.py#L10)), `chat_service = ChatService()` initializes `CurioEngine` with `MockLLMProvider()`. Real LLM inference via Groq is never invoked.

#### 2. Dropped Teacher Mode State (`teacher_attempt_count`, `teacher_intervention`)
- **Location:** [`backend/app/services/chat_service.py:196-207`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L196-L207) and [`backend/app/models/session.py:26-40`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L26-L40)
- **Detail:** The AI contract (`schemas.SessionState`) requires `teacher_attempt_count: int` and `teacher_intervention: Optional[TeacherIntervention]`. `StateUpdates` produces these values on every turn. However:
  - The PostgreSQL `session_states` table has **no columns** for `teacher_attempt_count` or `teacher_intervention`.
  - `SessionStateBase` backend schema has no fields for them.
  - `ChatService` drops them during persistence and does not populate them into `AIContext` (leaving them `0` and `None`).
- **Impact:** When a user is in Teacher Mode across multiple turns, `student_nodes.py` lines 179–183:
  ```python
  curr_attempts = context.current_state.teacher_attempt_count or 0
  attempt_count = curr_attempts + 1
  ```
  always evaluates `curr_attempts = 0`, resetting `attempt_count` to `1` on **every turn**. The Teacher never advances through the pedagogical stages (Attempt 1: Conceptual $\rightarrow$ Attempt 2: Analogy $\rightarrow$ Attempt 3: Worked Example).

#### 3. Missing Hydration of `learning_context.recent_evaluations`
- **Location:** [`backend/app/services/chat_service.py:214-217`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L214-L217)
- **Detail:** `LearningContext` defines `recent_evaluations: List[TurnEvaluation] = Field(default_factory=list)`. In `chat_service.py`, `learning_context` is constructed as:
  ```python
  learning_context = LearningContext(
      mastered_concepts=db_session.state.mastered_concepts or [],
      unresolved_misconceptions=db_session.state.unresolved_misconceptions or []
  )
  ```
  `recent_evaluations` is omitted and defaults to `[]`.
- **Impact:** In [`backend/app/ai/decision_engine.py:159-165`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/decision_engine.py#L159-L165), Trigger C (detecting repeated failure on the same knowledge gap to switch from Student Mode to Teacher Mode) checks `context.learning_context.recent_evaluations`. Because `ChatService` does not hydrate prior turn evaluations from the database, Trigger C cannot inspect past evaluations.

#### 4. Dropped Analytical State Fields (`concept_mastery`, `recent_strategy_history`, `misconception_counts`)
- **Location:** [`backend/app/models/session.py:26-40`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L26-L40) and [`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py)
- **Detail:** `StateUpdates` and `SessionState` declare `concept_mastery: Dict[str, float]`, `recent_strategy_history: List[Strategy]`, and `misconception_counts: Dict[str, int]`. The backend database model `SessionState` lacks columns for these, and `ChatService` neither persists nor hydrates them.

---

### D. Potential Risks

1. **Unprotected Database Writes Prior to Engine Invocation (Transaction / Rollback Gap)**:
   - In [`chat_service.py:129`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L129), `user_msg = self.message_repo.create_message(...)` persists the incoming user message to the database before calling `self.ai_engine.process(context)`.
   - If `CurioEngine.process()` raises an unhandled exception (e.g., Groq API network timeout, rate limit, JSON schema mismatch), the transaction is not rolled back. The orphan user message remains in the database without any corresponding AI response or turn evaluation.
2. **Missing Exception Handling & Graceful Degradation in ChatService**:
   - `ChatService.send_message()` has no `try/except` block wrapping `self.ai_engine.process(context)`. Any exception crashes through to FastAPI's generic HTTP 500 handler.
3. **Dead Code & Redundant Instantiations**:
   - In `ChatService.__init__`, `self.ai_provider = GroqLLMProvider()` and `self.orchestrator = AIOrchestrator(self.ai_provider)` are initialized on every service creation, but `self.orchestrator` is never invoked in any execution path.
4. **Unhandled Chat-Triggered Evaluator Mode**:
   - If `CurioEngine.process()` ever transitions to `Mode.EVALUATOR` or produces `session_evaluation` and `learning_report`, `ChatService.send_message()` ignores those fields and does not persist them into `session_reports` or mark the session as `COMPLETED`. Report generation is currently only wired through `POST /sessions/{id}/end` or `/evaluate`.

---

### E. Missing Test Coverage

1. **End-to-End ChatService $\leftrightarrow$ CurioEngine Integration**:
   - All 11 tests in [`backend/tests/services/test_chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/services/test_chat_service.py) mock `CurioEngine` with `MagicMock()`. There is **zero** test coverage executing `ChatService.send_message()` against a real `CurioEngine` instance (even with `MockLLMProvider`).
2. **Multi-Turn Teacher Mode Progression Test**:
   - There are no tests verifying that `teacher_attempt_count` increments across turns (Turn 1 $\rightarrow$ Turn 2 $\rightarrow$ Turn 3) in `ChatService`. Existing tests in `test_teacher_mode_persistence.py` mock the return value with static attempt counts.
3. **Engine Failure / Resilience Test**:
   - No test exists verifying how `ChatService` handles an engine crash, timeout, or invalid return value (and whether the database state rolls back cleanly).
4. **Recent Evaluations Hydration Test**:
   - No test verifies that past evaluations from `turn_evaluations` are hydrated into `context.learning_context.recent_evaluations`.
5. **Provider Configuration / Injection Test**:
   - No test verifies that `ChatService()` injects a production provider into `CurioEngine`.

---

### F. Recommended Fixes, Ordered by Severity

#### Priority 0 — Critical Functional Blocker
1. **Wire Real Provider to CurioEngine in `ChatService`**:
   - In `ChatService.__init__`, configure `self.ai_engine = ai_engine or CurioEngine(provider=self.ai_provider)`.
   - Remove unused `self.orchestrator = AIOrchestrator(self.ai_provider)`.

#### Priority 1 — High (Core Pedagogical Invariants Broken)
2. **Hydrate `learning_context.recent_evaluations`**:
   - In `ChatService.send_message()`, query recent turn evaluations from `turn_evaluations` (up to the last 5–10 turns) and populate `learning_context.recent_evaluations` so `DecisionEngine` Trigger C works across turns.
3. **Persist and Hydrate `teacher_attempt_count` and `teacher_intervention`**:
   - Ensure `teacher_attempt_count` and `teacher_intervention` are preserved in the backend state (e.g., via a JSON field or dedicated columns in `session_states`) and hydrated into `current_state` so the Teacher can progress through attempts 1, 2, and 3.

#### Priority 2 — Medium (Reliability & Robustness)
4. **Database Transaction Safety around Engine Invocation**:
   - Wrap user message persistence and state updates in a database transaction that only commits after `CurioEngine.process()` succeeds, preventing orphan user messages on engine failure.
5. **Graceful Engine Error Handling**:
   - Catch engine exceptions in `ChatService` with appropriate domain error handling or retry logic.
6. **Remove Legacy Orchestrator References**:
   - Remove imports and instantiations of `AIOrchestrator` in `chat_service.py`.

#### Priority 3 — Low (Longitudinal Tracking & Polish)
7. **Persist `concept_mastery`, `recent_strategy_history`, and `misconception_counts`**:
   - Store these in `session_states` for session history inspection.
8. **Add Live Integration Tests**:
   - Add unit/integration tests running `ChatService` directly against `CurioEngine(MockLLMProvider())`.

---

### G. Readiness Assessment

**Verdict: NOT FULLY READY for Phase 1 sign-off.**

While the structural pipeline (`AIContext` $\rightarrow$ `CurioEngine.process()` $\rightarrow$ `AIResult`) is clean and all 131 AI and service unit tests pass:
1. Production runs will execute purely in mock mode because `CurioEngine` is initialized without `self.ai_provider` (P0).
2. Multi-turn Teacher Mode cannot progress beyond Attempt 1 because `teacher_attempt_count` is dropped by the backend persistence layer (P1).
3. Pedagogical Trigger C cannot detect past failures because `learning_context.recent_evaluations` is not hydrated (P1).

Once these synchronization items are addressed, the backend will be ready for the next Phase 1 task.
