# Curio AI — Phase 0 Contract Synchronization Audit Report

**Author:** Senior Backend Architect  
**Project:** Curio AI (Feynman Role-Reversal Learning Platform)  
**Date:** September 19, 2026  
**Status:** Audit Complete — **NOT READY TO FREEZE**  
**Repository:** `joshi-chinmay-016/Curio-AI`  
**Current Working Branch:** `backend`  

---

## 1. Executive Summary

A comprehensive, read-only contract synchronization audit was conducted between the Phase 0 AI contracts introduced in PR #1 (`joshi-chinmay-016/feature/ai`, merged into `dev` via commit `eecf629`, and merged into `backend` via commit `e8889af`) and the current backend implementation across database models, Pydantic schemas, services, repositories, API routers, and test suites.

### Key Audit Findings:
1. **Critical Packaging Blocker (`ModuleNotFoundError: No module named 'langgraph'`)**: PR #1 introduced `backend/app/ai/graph.py` which depends on `langgraph`, and eagerly imported `CurioEngine` in `backend/app/ai/__init__.py`. However, `langgraph` was **never declared** in [backend/requirements.txt](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/requirements.txt). As a consequence, `backend/app/main.py` and the entire test suite fail during module collection.
2. **AI Layer Disconnection / Engine Bypass**: The active backend service layer ([ChatService](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L13-L20)) completely bypasses the new [CurioEngine](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L25) boundary. Instead, it still calls the legacy `AIOrchestrator(self.ai_provider).process_turn(...)`, discarding the newly established [AIResult](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L205-L210) and [StateUpdates](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L174-L190) contracts.
3. **Severe Data Loss in Context Building**: In [chat_service.py:51-61](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L51-L61), `AIContext` is constructed via flat legacy arguments where `confidence` is omitted (resetting to `0.0` every turn), `unresolved_misconceptions` and `mastered_concepts` are omitted (resetting to empty lists), and `interrupted_question` is hardcoded to `None` (dropping the saved database state).
4. **Teacher Mode Persistence Breakdown**: The PostgreSQL `session_states` table only records foreign UUIDs (`current_question_id`, `interrupted_question_id`), whereas the Phase 0 contract requires semantic [CurrentQuestion](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L67-L77) objects (`id`, `content`, `concept`, `difficulty`). Furthermore, [TeacherIntervention](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L79-L84) has **no representation** in PostgreSQL or backend schemas.
5. **Freeze Verdict**: **NOT READY TO FREEZE**. Immediate, non-breaking synchronization fixes are required in backend service wiring and context construction before freezing the Phase 0 baseline.

---

## 2. Repository and Branches Inspected

### Git History and Commit Audit
- **Current Local Branch**: `backend` (clean working tree).
- **Target Comparison Commit**: `826d6086dba17257a16f46fc3dc15884e89d2b60` (`feat: define Curio AI contracts`).
- **PR Merge Commit into `dev`**: `eecf629` (`Merge pull request #1 from joshi-chinmay-016/feature/ai`).
- **Sync Merge Commit into `backend`**: `e8889af` (`Merge branch 'dev' into backend`).
- **Additional Backend Commits Inspected**:
  - `c977008` (`compute dynamic confidence metrics in decision engine and add threshold tests`)
  - `4bc4965` (`add Phase 0 project preparation and environment audit report`)

### Files and Components Inspected:
| Layer | File Path | Primary Entities Inspected |
|---|---|---|
| **Contract Spec** | [docs/ai-contract.md](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/ai-contract.md) | Architectural rules, JSON payloads, ownership matrix |
| **AI Schemas** | [backend/app/ai/schemas.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py) | `SessionState`, `AIContext`, `AIResult`, `CurrentQuestion`, `TeacherIntervention`, `StateUpdates`, `TurnEvaluation`, `LearningDecision`, `AIResponse` |
| **AI Engine Boundary** | [backend/app/ai/engine.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py) | `CurioEngine.process()` |
| **AI Internal Workflow** | [backend/app/ai/graph.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/graph.py), [placeholder.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/nodes/placeholder.py) | LangGraph compilation, placeholder nodes |
| **Database Models** | [backend/app/models/session.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py), [message.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/message.py), [evaluation.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/evaluation.py) | `Session`, `SessionState`, `Message`, `TurnEvaluation` |
| **Backend Schemas** | [backend/app/schemas/session.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/session.py), [message.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py), [common.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/common.py) | `SessionStateBase`, `ChatTurnResponse`, `TurnEvaluationResponse`, `LearningDecisionResponse` |
| **Backend Services** | [backend/app/services/chat_service.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py), [session_service.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/session_service.py) | Context compilation, AI invocation, persistence update |
| **Repositories** | [backend/app/repositories/session_repository.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py), [message_repository.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/message_repository.py) | CRUD queries, state updates |
| **API Endpoints** | [backend/app/api/v1/messages.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/messages.py), [sessions.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/api/v1/sessions.py) | FastAPI routes |
| **Test Suites** | [backend/tests/ai/test_schemas.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_schemas.py), [test_engine.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_engine.py), [test_decision_engine.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/ai/test_decision_engine.py), [test_health.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/tests/api/test_health.py) | Contract verification, test collection status |

---

## 3. Phase 0 Contract Definitions

As defined in [docs/ai-contract.md](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/ai-contract.md) and implemented in [backend/app/ai/schemas.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py):

### A. State Schemas
```python
class CurrentQuestion(BaseModel):
    id: str
    content: str
    concept: str
    difficulty: int = Field(ge=1, le=5)

class TeacherIntervention(BaseModel):
    active: bool = False
    gap: str = ""
    attempt_count: int = Field(default=0, ge=0)
    verification_required: bool = True

class SessionState(BaseModel):
    session_id: str
    current_mode: Mode = Mode.STUDENT
    current_difficulty: int = Field(default=1, ge=1, le=5)
    understanding_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    active_concept: str = ""
    current_question: Optional[CurrentQuestion] = None
    interrupted_question: Optional[CurrentQuestion] = None
    consecutive_failures: int = Field(default=0, ge=0)
    consecutive_successes: int = Field(default=0, ge=0)
    teacher_attempt_count: int = Field(default=0, ge=0)
    recent_strategy_history: List[Strategy] = Field(default_factory=list)
    misconception_counts: Dict[str, int] = Field(default_factory=dict)
    concept_mastery: Dict[str, float] = Field(default_factory=dict)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    teacher_intervention: Optional[TeacherIntervention] = None
```

### B. Input Contract: `AIContext`
```python
class AIContext(BaseModel):
    session: SessionInfo
    current_state: SessionState
    conversation: ConversationContext
    learning_context: LearningContext = Field(default_factory=LearningContext)
    source_context: Optional[Dict[str, Any]] = None
```
*Note: Supports backward-compatibility properties (`session_id`, `topic`, `current_mode`, `difficulty`, `active_concept`, `history`, `current_question`, `interrupted_question`) and flat dict initialization via `@model_validator(mode="before") adapt_legacy_or_flat_inputs`.*

### C. Output Contract: `AIResult`
```python
class AIResult(BaseModel):
    evaluation: TurnEvaluation
    decision: LearningDecision
    response: AIResponse
    state_updates: StateUpdates
```

### D. Mutation Contract: `StateUpdates`
```python
class StateUpdates(BaseModel):
    active_concept: Optional[str] = None
    interrupted_question: Optional[CurrentQuestion] = None
    mastered_concepts: Optional[List[str]] = None
    unresolved_misconceptions: Optional[List[str]] = None
    teacher_intervention: Optional[TeacherIntervention] = None
    current_question: Optional[CurrentQuestion] = None
    current_mode: Optional[Mode] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    concept_mastery: Optional[Dict[str, float]] = None
    consecutive_failures: Optional[int] = Field(default=None, ge=0)
    consecutive_successes: Optional[int] = Field(default=None, ge=0)
    teacher_attempt_count: Optional[int] = Field(default=None, ge=0)
    recent_strategy_history: Optional[List[Strategy]] = None
    misconception_counts: Optional[Dict[str, int]] = None
```

---

## 4. Current Backend Implementation

### A. Database Models (`SQLAlchemy`)
Defined in [backend/app/models/session.py:26-41](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L26-L41):
```python
class SessionState(Base):
    __tablename__ = "session_states"

    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    current_mode = Column(String, default="STUDENT", nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    active_concept = Column(String, default="Core Definition", nullable=False)
    current_question_id = Column(UUID(as_uuid=True), nullable=True)
    interrupted_question_id = Column(UUID(as_uuid=True), nullable=True)
    consecutive_strong_answers = Column(Integer, default=0, nullable=False)
    consecutive_weak_answers = Column(Integer, default=0, nullable=False)
    unresolved_misconceptions = Column(JSON, default=list, nullable=False)
    mastered_concepts = Column(JSON, default=list, nullable=False)
```

### B. Backend Pydantic Schemas
Defined in [backend/app/schemas/session.py:7-18](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/session.py#L7-L18):
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
```

### C. Context Construction & Execution in `ChatService`
Defined in [backend/app/services/chat_service.py:51-68](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L51-L68):
```python
context = AIContext(
    session_id=session_id,
    topic=db_session.topic,
    current_mode=LearningMode(db_session.state.current_mode),
    difficulty=db_session.state.difficulty,
    active_concept=db_session.state.active_concept,
    current_question=active_question,
    interrupted_question=None,  # Hardcoded None!
    document_context=None,
    history=ai_history
)

# Still invokes legacy AIOrchestrator, not CurioEngine!
ai_response = self.orchestrator.process_turn(
    context,
    consecutive_strong=db_session.state.consecutive_strong_answers,
    consecutive_weak=db_session.state.consecutive_weak_answers
)
```

---

## 5. Schema Comparison

### 1. `SessionState` Schema vs Database Table vs Backend Schema
| Feature / Field | Phase 0 AI Contract (`schemas.py`) | Backend DB Model (`models/session.py`) | Backend API Schema (`schemas/session.py`) | Status |
|---|---|---|---|---|
| Session ID | `session_id: str` | `session_id: UUID(as_uuid=True)` | `session_id: UUID` | Compatible via serializer |
| Mode | `current_mode: Mode` (Enum) | `current_mode: String` | `current_mode: LearningMode` | Compatible (Identical strings) |
| Difficulty | `current_difficulty: int (1..5)` | `difficulty: Integer (1..5)` | `difficulty: int` | Naming discrepancy |
| Confidence | `understanding_confidence: float` | `confidence: Float` | `confidence: float` | Naming discrepancy |
| Active Concept | `active_concept: str` | `active_concept: String` | `active_concept: str` | Compatible |
| Current Question | `current_question: Optional[CurrentQuestion]` | `current_question_id: UUID` | `current_question_id: Optional[UUID]` | **Type Mismatch** (Object vs UUID) |
| Interrupted Question | `interrupted_question: Optional[CurrentQuestion]` | `interrupted_question_id: UUID` | `interrupted_question_id: Optional[UUID]` | **Type Mismatch** (Object vs UUID) |
| Consecutive Successes | `consecutive_successes: int` | `consecutive_strong_answers: Integer` | `consecutive_strong_answers: int` | Naming discrepancy |
| Consecutive Failures | `consecutive_failures: int` | `consecutive_weak_answers: Integer` | `consecutive_weak_answers: int` | Naming discrepancy |
| Unresolved Misconceptions | `unresolved_misconceptions: List[str]` | `unresolved_misconceptions: JSON` | `unresolved_misconceptions: List[str]` | Compatible |
| Mastered Concepts | `mastered_concepts: List[str]` (in `LearningContext`) | `mastered_concepts: JSON` | `mastered_concepts: List[str]` | Stored in DB, omitted in builder |
| Teacher Intervention | `teacher_intervention: Optional[TeacherIntervention]` | **Not Present** | **Not Present** | **Missing from Backend** |
| Teacher Attempt Count | `teacher_attempt_count: int` | **Not Present** | **Not Present** | **Missing from Backend** |
| Concept Mastery Map | `concept_mastery: Dict[str, float]` | **Not Present** | **Not Present** | **Missing from Backend** |
| Strategy History | `recent_strategy_history: List[Strategy]` | **Not Present** | **Not Present** | **Missing from Backend** |
| Misconception Counts | `misconception_counts: Dict[str, int]` | **Not Present** | **Not Present** | **Missing from Backend** |

---

## 6. Mismatch Classification Table

Each mismatch identified is recorded below with complete evidence, impact analysis, and category:
- **MUST CHANGE**: Essential for contract compatibility, core Feynman pedagogical flow, or preventing data corruption.
- **BACKEND IMPLEMENTATION DETAIL**: Internal backend abstraction differences that do not require changing the AI contract.
- **CAN DEFER**: Future enhancement that can be handled in Phase 1 without breaking Phase 0 contracts.

| ID | Component | Mismatch | Classification |
|---|---|---|---|
| **M-01** | Dependencies | Missing `langgraph` in `backend/requirements.txt` breaks all test collection and backend startup | **MUST CHANGE** |
| **M-02** | Service Layer | `ChatService` invokes legacy `AIOrchestrator` instead of `CurioEngine.process()` | **MUST CHANGE** |
| **M-03** | Service Layer | `ChatService` discards `AIResult` and `StateUpdates`, calculating state manually | **MUST CHANGE** |
| **M-04** | Context Builder | `understanding_confidence` is omitted during `AIContext` creation (resets to `0.0`) | **MUST CHANGE** |
| **M-05** | Context Builder | `interrupted_question` is hardcoded to `None` in `ChatService` | **MUST CHANGE** |
| **M-06** | Context Builder | `unresolved_misconceptions` and `mastered_concepts` are omitted from `AIContext` | **MUST CHANGE** |
| **M-07** | State / DB | DB stores `current_question_id` (UUID), AI contract requires `CurrentQuestion` object | **MUST CHANGE** |
| **M-08** | Teacher Mode | `TeacherIntervention` object is not persisted in DB or restored | **MUST CHANGE** |
| **M-09** | SessionState | Naming differences (`difficulty` vs `current_difficulty`, `confidence` vs `understanding_confidence`) | **BACKEND IMPLEMENTATION DETAIL** |
| **M-10** | SessionState | Answer streak naming (`consecutive_strong_answers` vs `consecutive_successes`) | **BACKEND IMPLEMENTATION DETAIL** |
| **M-11** | Context Adapter | `adapt_legacy_or_flat_inputs` accepts `source_context`, but `ChatService` passed `document_context` | **BACKEND IMPLEMENTATION DETAIL** |
| **M-12** | Database Model | `concept_mastery: Dict[str, float]` not persisted in DB | **CAN DEFER** |
| **M-13** | Database Model | `recent_strategy_history: List[Strategy]` not persisted in DB | **CAN DEFER** |
| **M-14** | Database Model | `misconception_counts: Dict[str, int]` not persisted in DB | **CAN DEFER** |

---

### Detailed Mismatch Analysis

#### M-01: Missing `langgraph` Dependency
- **Schema/Component**: Package Dependencies & `backend/app/ai/__init__.py`.
- **Phase 0 Contract**: [engine.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L9) and [graph.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/graph.py#L7) require `langgraph.graph.StateGraph`.
- **Current Backend**: [backend/requirements.txt](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/requirements.txt) does not declare `langgraph`.
- **Exact Mismatch**: Running `pytest` or importing `backend.app.main` raises `ModuleNotFoundError: No module named 'langgraph'`.
- **Impact**: Backend cannot run, build, or pass CI.
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Add `langgraph>=0.0.20` to `backend/requirements.txt`. Protect [backend/app/ai/__init__.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/__init__.py) with defensive loading.
- **Evidence**: [backend/requirements.txt:1-12](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/requirements.txt#L1-L12), [backend/app/ai/graph.py:7](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/graph.py#L7).

#### M-02: `ChatService` Bypasses `CurioEngine`
- **Schema/Component**: `backend/app/services/chat_service.py`.
- **Phase 0 Contract**: Section 2 & 9 of [docs/ai-contract.md](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/ai-contract.md#L32-L34) specifies that `CurioEngine.process()` is the **exclusive** public interface.
- **Current Backend**: `ChatService.__init__` instantiates `self.orchestrator = AIOrchestrator(self.ai_provider)` and invokes `self.orchestrator.process_turn(...)`.
- **Exact Mismatch**: The backend invokes legacy code instead of the LangGraph-based `CurioEngine`.
- **Impact**: PR #1's workflow, nodes, and graph routing are completely ignored in production runtime.
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Refactor `ChatService` to initialize and call `CurioEngine().process(context)`.
- **Evidence**: [backend/app/services/chat_service.py:19](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L19), [chat_service.py:64](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L64).

#### M-03: Discarding `AIResult` and `StateUpdates`
- **Schema/Component**: `backend/app/services/chat_service.py`.
- **Phase 0 Contract**: The engine outputs `AIResult` containing `StateUpdates` (recommended mutations). The backend validates and applies `StateUpdates`.
- **Current Backend**: `ChatService` parses `ai_response.metadata["evaluation"]` and `ai_response.metadata["decision"]`, and executes custom counter updates (`if evaluation_data["correctness"] > 0.7: consecutive_strong += 1`).
- **Exact Mismatch**: The backend does not consume `AIResult.state_updates`.
- **Impact**: Violates Contract Separation Rule #4 ("AI Recommends, Backend Persists").
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Update `ChatService` to consume `ai_result.state_updates` to drive `SessionStateBase` persistence.
- **Evidence**: [backend/app/services/chat_service.py:104-128](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L104-L128).

#### M-04: Confidence Dropped During Context Building
- **Schema/Component**: `backend/app/services/chat_service.py` -> `AIContext`.
- **Phase 0 Contract**: `SessionState.understanding_confidence` is a float (0.0 to 1.0) indicating learner mastery.
- **Current Backend**: `ChatService.send_message` does not pass `confidence` or `understanding_confidence` when instantiating `AIContext`.
- **Exact Mismatch**: Flat validator `adapt_legacy_or_flat_inputs` defaults `understanding_confidence` to `0.0`.
- **Impact**: Every chat turn resets the AI's understanding confidence to `0.0`, crippling termination decisions (`confidence >= 0.75`).
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Pass `understanding_confidence=db_session.state.confidence` when constructing `AIContext`.
- **Evidence**: [backend/app/services/chat_service.py:51-61](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L51-L61), [backend/app/ai/schemas.py:323-330](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L323-L330).

#### M-05: Interrupted Question Hardcoded to `None`
- **Schema/Component**: `backend/app/services/chat_service.py`.
- **Phase 0 Contract**: `AIContext.current_state.interrupted_question` must carry the question paused during Teacher Mode.
- **Current Backend**: `ChatService` explicitly sets `interrupted_question=None` (line 58).
- **Exact Mismatch**: Although `db_session.state.interrupted_question_id` exists in the database, it is never read to populate the contract.
- **Impact**: Socratic role-reversal cannot resume the interrupted inquiry after a Teacher Mode intervention concludes.
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Query the message content for `interrupted_question_id` and construct a `CurrentQuestion` instance to supply to `AIContext`.
- **Evidence**: [backend/app/services/chat_service.py:58](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L58).

#### M-06: Learning Context (Misconceptions & Mastered Concepts) Dropped
- **Schema/Component**: `backend/app/services/chat_service.py`.
- **Phase 0 Contract**: `AIContext.learning_context` contains `unresolved_misconceptions` and `mastered_concepts`.
- **Current Backend**: `ChatService` does not pass `unresolved_misconceptions` or `mastered_concepts` from `db_session.state` into `AIContext`.
- **Exact Mismatch**: Active misconceptions recorded in the database are omitted from the input to the AI engine.
- **Impact**: AI repeats the same misconceptions or assumes zero prior mastery.
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Construct `LearningContext(unresolved_misconceptions=db_session.state.unresolved_misconceptions, mastered_concepts=db_session.state.mastered_concepts)` and pass it into `AIContext`.
- **Evidence**: [backend/app/services/chat_service.py:51-61](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L51-L61).

#### M-07: Current Question Representation (UUID vs Semantic Object)
- **Schema/Component**: `backend/app/models/session.py` vs `backend/app/ai/schemas.py`.
- **Phase 0 Contract**: `CurrentQuestion` contains `id: str`, `content: str`, `concept: str`, and `difficulty: int`.
- **Current Backend**: DB table `session_states` only contains `current_question_id: Column(UUID)` and `interrupted_question_id: Column(UUID)`.
- **Exact Mismatch**: Database stores only a UUID pointer to a message, while the AI contract expects the full semantic text and metadata.
- **Impact**: The context builder must execute secondary database queries against the `messages` table to reconstruct `CurrentQuestion`, or risk passing empty strings.
- **Classification**: **MUST CHANGE** (in Backend service reconstruction logic; database schema can remain normalized UUID pointers with joined loading).
- **Recommended Action**: In `ChatService`, resolve `current_question_id` and `interrupted_question_id` against `db_session.messages` to produce `CurrentQuestion` instances.
- **Evidence**: [backend/app/models/session.py:34-35](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L34-L35), [backend/app/ai/schemas.py:67-77](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L67-L77).

#### M-08: Teacher Intervention State Lost on Persistence
- **Schema/Component**: `backend/app/models/session.py` vs `backend/app/ai/schemas.py`.
- **Phase 0 Contract**: `SessionState.teacher_intervention: Optional[TeacherIntervention]` tracks active status, knowledge gap, attempt count, and verification requirements.
- **Current Backend**: `session_states` table has no column for `teacher_intervention`.
- **Exact Mismatch**: When the AI enters Teacher Mode, its internal state machine intervention context cannot be saved in PostgreSQL.
- **Impact**: If a session pauses or receives a subsequent message while in Teacher Mode, the intervention progress is wiped.
- **Classification**: **MUST CHANGE**.
- **Recommended Action**: Add a JSON column `teacher_intervention` to `session_states` table and `SessionStateBase` Pydantic schema.
- **Evidence**: [backend/app/models/session.py:26-41](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L26-L41), [backend/app/ai/schemas.py:79-84](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L79-L84).

#### M-09: Field Naming Differences (`difficulty` vs `current_difficulty`, `confidence` vs `understanding_confidence`)
- **Schema/Component**: `SessionState` naming conventions.
- **Phase 0 Contract**: Named `current_difficulty` and `understanding_confidence`.
- **Current Backend**: DB and API schemas name them `difficulty` and `confidence`.
- **Exact Mismatch**: Field names differ between backend persistence models and AI contract.
- **Impact**: Managed cleanly via Pydantic property aliases, serialization validators, or explicit mapping in the repository layer.
- **Classification**: **BACKEND IMPLEMENTATION DETAIL**.
- **Recommended Action**: Keep backend DB column names as `difficulty` and `confidence` to avoid unnecessary migrations; map them explicitly when constructing `AIContext` and persisting `StateUpdates`.
- **Evidence**: [backend/app/models/session.py:31-32](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L31-L32), [backend/app/ai/schemas.py:93-94](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L93-L94).

#### M-10: Answer Streak Naming (`consecutive_strong_answers` vs `consecutive_successes`)
- **Schema/Component**: `SessionState` streak counters.
- **Phase 0 Contract**: `consecutive_successes: int` and `consecutive_failures: int`.
- **Current Backend**: `consecutive_strong_answers: int` and `consecutive_weak_answers: int`.
- **Exact Mismatch**: Semantic synonym naming difference.
- **Impact**: No contract breach if mapped cleanly in the backend adapter layer.
- **Classification**: **BACKEND IMPLEMENTATION DETAIL**.
- **Recommended Action**: Map `consecutive_strong_answers` $\leftrightarrow$ `consecutive_successes` in `ChatService`.
- **Evidence**: [backend/app/models/session.py:36-37](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py#L36-L37), [backend/app/ai/schemas.py:98-99](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L98-L99).

#### M-11: Context Source Parameter (`document_context` vs `source_context`)
- **Schema/Component**: `ChatService` vs `AIContext`.
- **Phase 0 Contract**: `AIContext` defines `source_context: Optional[Dict[str, Any]] = None`.
- **Current Backend**: `chat_service.py:59` passes `document_context=None`.
- **Exact Mismatch**: Keyword argument name mismatch in legacy call.
- **Impact**: Ignored by `adapt_legacy_or_flat_inputs` because `document_context` is not recognized, defaulting `source_context` to `None`.
- **Classification**: **BACKEND IMPLEMENTATION DETAIL**.
- **Recommended Action**: Change `document_context=None` to `source_context=None` in `chat_service.py`.
- **Evidence**: [backend/app/services/chat_service.py:59](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L59), [backend/app/ai/schemas.py:282](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L282).

#### M-12, M-13, M-14: Granular Metrics Omitted from DB Persistence
- **Schema/Component**: `concept_mastery`, `recent_strategy_history`, `misconception_counts`.
- **Phase 0 Contract**: Present in `SessionState` with validation rules.
- **Current Backend**: Neither PostgreSQL `session_states` nor backend Pydantic models contain these fields.
- **Exact Mismatch**: The AI contract schema supports granular analytics, but the backend storage does not persist them.
- **Impact**: These are supplementary analytics. Their absence does not break the core Phase 0 Feynman interaction loop.
- **Classification**: **CAN DEFER**.
- **Recommended Action**: Defer database column additions for these three fields to Phase 1 Alembic migration.
- **Evidence**: [backend/app/ai/schemas.py:101-103](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L101-L103).

---

## 7. Teacher Mode Persistence Audit

The Feynman technique relies on seamless transitions: when a learner exhibits repeated confusion, Curio transitions from Student Mode to Teacher Mode, explains the concept gap, verifies the learner's understanding, and then returns to Student Mode to resume the interrupted question.

### Verification Matrix
| Field | Schema Support | Populated in Run | Persisted in DB | Restored on Resume | Passed to Context | Consumed by AI | Covered by Tests |
|---|---|---|---|---|---|---|---|
| **1. Current question** | ✅ Yes (`CurrentQuestion`) | ⚠️ Partial (string only) | ⚠️ Partial (UUID only) | ❌ No | ⚠️ Partial (string text) | ✅ Yes | ❌ No |
| **2. Interrupted question** | ✅ Yes (`CurrentQuestion`) | ⚠️ Partial (UUID only) | ⚠️ Partial (UUID only) | ❌ No | ❌ No (`None` hardcoded) | ❌ No | ❌ No |
| **3. Active concept** | ✅ Yes (`str`) | ✅ Yes | ✅ Yes (`String`) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **4. Current mode** | ✅ Yes (`Mode`) | ✅ Yes | ✅ Yes (`String`) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **5. Teacher intervention state** | ✅ Yes (`TeacherIntervention`) | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **6. Unresolved misconceptions** | ✅ Yes (`List[str]`) | ✅ Yes (Evaluation) | ✅ Yes (`JSON`) | ✅ Yes | ❌ No (Omitted in builder) | ❌ No | ❌ No |
| **7. Difficulty** | ✅ Yes (`int 1..5`) | ✅ Yes | ✅ Yes (`Integer`) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **8. Confidence** | ✅ Yes (`float 0..1`) | ✅ Yes | ✅ Yes (`Float`) | ✅ Yes | ❌ No (Omitted in builder) | ❌ No | ❌ No |

### Detailed Gaps Identified in Teacher Mode Flow:

1. **Current Question**:
   - In DB, `current_question_id` stores the UUID of the assistant message.
   - When constructing `AIContext` in [chat_service.py:44-50](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L44-L50), the code extracts the message content of the last AI message as a plain string.
   - It passes `current_question=active_question` to `AIContext`.
   - `adapt_legacy_or_flat_inputs` converts this string into a synthesized `CurrentQuestion(id="curr_q", content=active_question, concept=active_concept, difficulty=difficulty)`.
   - *Gap*: The true question ID is lost and replaced with the dummy string `"curr_q"`.

2. **Interrupted Question**:
   - When switching from Student to Teacher mode, [chat_service.py:133](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L133) records `state_update.interrupted_question_id = db_session.state.current_question_id`.
   - This UUID is saved in PostgreSQL `session_states.interrupted_question_id`.
   - However, during context compilation on line 58:
     ```python
     interrupted_question=None,  # Handled in decision if restored
     ```
   - *Critical Failure*: The saved `interrupted_question_id` is completely ignored. The AI never receives the interrupted question. When Teacher Mode verifies understanding and emits `should_restore_interrupted_question=True`, Curio has no record of what question was interrupted!

3. **Teacher Intervention State**:
   - The Phase 0 contract specifies `TeacherIntervention(active=bool, gap=str, attempt_count=int, verification_required=bool)`.
   - The backend has **zero database columns** and **zero schema fields** for this object.
   - *Critical Failure*: Multi-turn teacher interventions cannot track how many times the teacher has attempted to explain the gap, risking infinite teaching loops or premature exit.

4. **Missing / Null Behavior**:
   - If `interrupted_question` is null, the AI assumes no prior question was pending and generates a new foundation question.
   - If `teacher_intervention` is null, the AI assumes no intervention is in progress.

---

## 8. End-to-End Contract Flow

### Flow Architecture Diagram

```
[Client / User]
       │
       ▼  POST /api/v1/sessions/{id}/messages
┌─────────────────────────────────────────────────────────────┐
│ 1. API Route Layer (messages.py)                            │
│    Receives MessageCreate, validates session_id             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Backend Service Layer (ChatService.send_message)         │
│    Loads Session & SessionState from DB                     │
│    Saves User Message to DB (MessageRepository)             │
│                                                             │
│    [CRITICAL DEFECT HERE]:                                  │
│    - Omits confidence -> defaults to 0.0                    │
│    - Omits misconceptions -> defaults to []                 │
│    - Hardcodes interrupted_question -> None                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ Constructs AIContext
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AI Contract Boundary (CurioEngine.process)               │
│    [CRITICAL DEFECT HERE]:                                  │
│    ChatService calls legacy AIOrchestrator, Bypassing Engine│
└──────────────────────────────┬──────────────────────────────┘
                               │ Executes LangGraph
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LangGraph State Machine (Evaluation -> Decision -> Resp) │
│    Evaluates answer, decides mode/difficulty/strategy       │
│    Emits AIResult (Evaluation, Decision, Resp, StateUpdates)│
└──────────────────────────────┬──────────────────────────────┘
                               │ Emits AIResult
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Backend Persistence & State Mutation                     │
│    [CRITICAL DEFECT HERE]:                                  │
│    ChatService ignores StateUpdates, manually updates DB    │
│    Persists ai_message & turn_evaluation                    │
│    Updates session_states table                             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Response Formatter & Client Delivery                     │
│    Returns ChatTurnResponse to User                         │
└─────────────────────────────────────────────────────────────┘
```

### Trace of Contract Deficiencies:
- **Lost Between Layers**:
  - `SessionState.confidence` $\rightarrow$ Lost when building `AIContext` (resets to `0.0`).
  - `SessionState.unresolved_misconceptions` $\rightarrow$ Lost when building `AIContext`.
  - `SessionState.interrupted_question_id` $\rightarrow$ Lost when building `AIContext`.
  - `AIResult.state_updates` $\rightarrow$ Discarded by `ChatService`.
- **Renamed Inconsistently**:
  - `understanding_confidence` (Contract) $\leftrightarrow$ `confidence` (DB & API).
  - `current_difficulty` (Contract) $\leftrightarrow$ `difficulty` (DB & API).
  - `consecutive_successes` (Contract) $\leftrightarrow$ `consecutive_strong_answers` (DB).
  - `consecutive_failures` (Contract) $\leftrightarrow$ `consecutive_weak_answers` (DB).
- **Incompatible Types**:
  - `CurrentQuestion` (Pydantic model in Contract) $\leftrightarrow$ `UUID` (PostgreSQL foreign key).
- **Never Persisted**:
  - `teacher_intervention` (contract object with `attempt_count`, `gap`, etc.).
  - `concept_mastery` dictionary.
  - `recent_strategy_history` list.
- **Persisted But Never Restored**:
  - `interrupted_question_id` (written to DB on Student $\rightarrow$ Teacher switch, but passed as `None` to AI).

---

## 9. Critical Compatibility Issues

These issues break functionality or violate contracts and **must be fixed**:

1. **Dependency Packaging Failure (`langgraph`)**:
   - `backend/requirements.txt` is missing `langgraph`.
   - In Python environments without `langgraph`, importing `backend.app.ai` crashes with `ModuleNotFoundError`.
   - Because `backend/app/main.py` imports `api_router`, which imports `reports.py`, which imports `report_service.py`, which imports `backend/app/ai`, **the entire FastAPI backend fails to start**.
2. **AI Layer Decoupling Violated by Non-Use**:
   - While `CurioEngine` cleanly encapsulates LangGraph without leaking it to the backend, `ChatService` never invokes `CurioEngine`. It still instantiates `AIOrchestrator`.
   - The contract specified in [docs/ai-contract.md](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/docs/ai-contract.md) is effectively a dead letter in production code until `ChatService` is rewired.
3. **State Erasure During Interaction Turns**:
   - A learning platform cannot function if the student's confidence score resets to zero every time they submit an explanation. This breaks the termination threshold logic (`confidence >= 0.75`).

---

## 10. Backend-Only Implementation Details

These items represent internal architectural decisions and do **not** require changing the public AI contract:

1. **Database Column Naming vs Contract Naming**:
   - Keeping `difficulty`, `confidence`, `consecutive_strong_answers`, and `consecutive_weak_answers` in PostgreSQL is acceptable and standard practice.
   - The backend service layer acts as the anti-corruption layer, mapping DB model attributes to `AIContext` parameters and unpacking `StateUpdates` into DB model attributes.
2. **Normalized Foreign Keys vs Embedded Objects**:
   - PostgreSQL stores `current_question_id: UUID` and `interrupted_question_id: UUID` pointing to the `messages` table. This is good relational database design.
   - The backend service is responsible for hydrating those UUIDs into `CurrentQuestion` objects when building `AIContext`.
3. **Message Input Types & Roles**:
   - The database stores `sender: "USER" | "AI"`. The AI contract uses `Role.USER`, `Role.ASSISTANT`, and `Role.SYSTEM`.
   - [ChatMessage](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L221-L239) already includes an automatic adapter for `sender="AI"` $\rightarrow$ `role=Role.ASSISTANT`.

---

## 11. Deferred Improvements

The following improvements are non-blocking for Phase 0 and can be scheduled for Phase 1:

1. **Per-Concept Mastery Matrix (`concept_mastery: Dict[str, float]`)**:
   - Storing a granular float score for every individual concept can be persisted in a future JSONB column in PostgreSQL during Phase 1.
2. **Rolling Strategy History (`recent_strategy_history: List[Strategy]`)**:
   - Tracking the last 5 strategies in PostgreSQL can be deferred. Currently, recent strategies can be inferred from recent messages.
3. **Misconception Frequency Aggregator (`misconception_counts: Dict[str, int]`)**:
   - Cumulative misconception frequency mapping can be deferred to Phase 1 analytics.

---

## 12. Missing Test Coverage

The following tests are currently missing and must be added to ensure contract integrity:

| Test Name | File Location | Purpose | Expected Behavior |
|---|---|---|---|
| `test_session_state_db_to_ai_context_mapping` | `backend/tests/services/test_chat_service.py` | Verify that DB `SessionState` fields (confidence, difficulty, active concept) accurately populate `AIContext` | All numeric and string state values must match DB record exactly; confidence must not default to 0.0 |
| `test_context_builder_interrupted_question_hydration` | `backend/tests/services/test_chat_service.py` | Verify that when `interrupted_question_id` exists in DB, `AIContext.current_state.interrupted_question` is hydrated | Returns `CurrentQuestion` with content of the interrupted message |
| `test_chat_service_engine_invocation_and_state_updates` | `backend/tests/services/test_chat_service.py` | Verify `ChatService.send_message` invokes `CurioEngine.process()` and saves `AIResult.state_updates` to DB | Database `SessionState` reflects values recommended by `StateUpdates` |
| `test_teacher_mode_interrupted_question_persistence` | `backend/tests/services/test_chat_service.py` | Verify Student $\rightarrow$ Teacher transition preserves `interrupted_question_id` in DB | `interrupted_question_id` equals previous question ID |
| `test_teacher_mode_restoration_clears_interrupted` | `backend/tests/services/test_chat_service.py` | Verify Teacher $\rightarrow$ Student transition with `should_restore_interrupted_question=True` restores question | `interrupted_question_id` cleared to `None` in DB |
| `test_ai_context_flat_adapter_confidence_preservation` | `backend/tests/ai/test_schemas.py` | Verify `adapt_legacy_or_flat_inputs` retains `confidence` argument if passed | `context.current_state.understanding_confidence == passed_confidence` |
| `test_unresolved_misconceptions_roundtrip` | `backend/tests/services/test_chat_service.py` | Verify misconceptions in DB are sent to AI and new misconceptions are appended | Active misconceptions persist across multiple turns |

---

## 13. Recommended Changes Before Contract Freeze

### For Vishal (Backend Lead):
1. **Declare Dependency**:
   - Add `langgraph>=0.0.20` to [backend/requirements.txt](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/requirements.txt).
2. **Rewire `ChatService` to use `CurioEngine`**:
   - Replace `AIOrchestrator` with `CurioEngine`.
   - In `send_message()`, invoke `ai_result = self.engine.process(context)`.
   - Consume `ai_result.state_updates` to drive `SessionStateBase` updates.
3. **Fix Context Compilation in `ChatService`**:
   - Pass `confidence=db_session.state.confidence`.
   - Pass `unresolved_misconceptions=db_session.state.unresolved_misconceptions`.
   - Pass `mastered_concepts=db_session.state.mastered_concepts`.
   - Hydrate `interrupted_question` by querying the message for `db_session.state.interrupted_question_id`.
4. **Database Schema Addition for Teacher Intervention**:
   - Add a nullable JSON column `teacher_intervention = Column(JSON, nullable=True)` to `SessionState` model in [backend/app/models/session.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/models/session.py).

### For Chinmay (AI Lead):
1. **Defensive Package Imports**:
   - In [backend/app/ai/__init__.py](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/__init__.py), wrap the `from backend.app.ai.engine import CurioEngine` in a `try...except ImportError` or use lazy importing so importing schema classes does not crash if `langgraph` is not yet installed in a lightweight client environment.
2. **Enhance `adapt_legacy_or_flat_inputs`**:
   - In [backend/app/ai/schemas.py:300-330](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L300-L330), read `confidence` or `understanding_confidence` from `data`:
     ```python
     confidence = float(data.get("understanding_confidence", data.get("confidence", 0.0)))
     ```
   - Also read `unresolved_misconceptions` and `mastered_concepts` if provided in flat kwargs.

---

## 14. Contract Freeze Readiness

### Verdict: **NOT READY TO FREEZE**

### Concrete Justification:
1. **Runtime Inoperability**: The repository cannot run tests or boot FastAPI because `langgraph` is missing from `requirements.txt`.
2. **Complete AI Layer Disconnection**: The backend service layer does not yet use the Phase 0 AI contracts (`CurioEngine`, `AIResult`, `StateUpdates`), executing dead legacy code instead.
3. **Pedagogical State Corruption**: Context building drops the student's confidence and misconceptions on every interaction, making it impossible to evaluate or freeze state machine behavior.
4. **Teacher Mode Inoperability**: The interrupted question is hardcoded to `None`, breaking the core Feynman role-reversal loop.

---

## 15. Final Action Items

### Immediate Step-by-Step Resolution Plan:

```
[Phase 0 Sync Action Checklist]
├── 1. Add `langgraph>=0.0.20` to backend/requirements.txt
├── 2. Update backend/app/ai/__init__.py to lazily or safely import CurioEngine
├── 3. Update backend/app/ai/schemas.py adapt_legacy_or_flat_inputs to read confidence & misconceptions
├── 4. Add `teacher_intervention` column to backend/app/models/session.py & session schemas
├── 5. Refactor backend/app/services/chat_service.py:
│     ├── Replace AIOrchestrator with CurioEngine
│     ├── Hydrate current_question and interrupted_question from message history
│     ├── Pass understanding_confidence, unresolved_misconceptions, mastered_concepts
│     └── Apply ai_result.state_updates directly to SessionState persistence
├── 6. Run pytest backend/tests to verify all AI and API tests collect and pass
└── 7. Formally freeze Phase 0 contracts
```
