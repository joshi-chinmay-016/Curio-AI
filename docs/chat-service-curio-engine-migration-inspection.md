# Technical Inspection: ChatService Migration to CurioEngine

This document provides a comprehensive technical inspection of [`CurioEngine`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py#L25), AI schemas, [`ChatService`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py#L13), [`SessionRepository`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py#L7), and identified compatibility problems prior to performing the migration.

---

## 1. CurioEngine Class Inspection

* **File**: [`backend/app/ai/engine.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/engine.py)

### 1.1 `__init__` Signature
```python
def __init__(self, provider: Optional[BaseAIProvider] = None, graph: Any = None):
    self.provider = provider
    self._graph = graph or build_curio_graph()
```
* **Parameters**:
  - `provider`: Optional instance conforming to [`BaseAIProvider`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/base.py#L8). Defaults to `None`.
  - `graph`: Optional pre-compiled LangGraph runnable. Defaults to [`build_curio_graph()`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/graph.py#L34).

### 1.2 `process()` Signature & Return Type
```python
def process(self, context: AIContext) -> AIResult:
```
* **Input**: [`context: AIContext`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L277) (strongly-typed Pydantic model).
* **Return Type**: [`AIResult`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L205).

### 1.3 Required Dependencies
* `backend.app.ai.graph.build_curio_graph`
* `backend.app.ai.providers.base.BaseAIProvider`
* `backend.app.ai.schemas` (`AIContext`, `AIResponse`, `AIResult`, `LearningDecision`, `Mode`, `StateUpdates`, `Strategy`, `TurnEvaluation`)

### 1.4 How the Compiled LangGraph is Invoked
1. **Initial State Packaging**:
   ```python
   initial_state = {
       "context": context,
   }
   ```
2. **Execution**:
   ```python
   final_state = self._graph.invoke(initial_state)
   ```
3. **Extraction & Default Resolution**:
   - Extracts `evaluation: TurnEvaluation`, `decision: LearningDecision`, `response: AIResponse`, and `state_updates: Optional[StateUpdates]` from `final_state`.
   - Fallback: If `state_updates is None`, constructs default `StateUpdates` from `decision` and `evaluation`.
4. **Validation & Return**:
   - Constructs and validates `AIResult(evaluation=..., decision=..., response=..., state_updates=...)`.

---

## 2. AIResult and StateUpdates Schemas

* **File**: [`backend/app/ai/schemas.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py)

### 2.1 `AIResult` Schema
```python
class AIResult(BaseModel):
    evaluation: TurnEvaluation
    decision: LearningDecision
    response: AIResponse
    state_updates: StateUpdates
```
* **Fields**:
  - `evaluation` ([`TurnEvaluation`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L125)): Required. Turn scoring and pedagogical evaluation.
  - `decision` ([`LearningDecision`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L145)): Required. Next pedagogical strategy, difficulty, and mode.
  - `response` ([`AIResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L160)): Required. Generated learner-facing content.
  - `state_updates` ([`StateUpdates`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L174)): Required. Recommended state mutations for persistence.
* **Validation**: Standard Pydantic V2 validation; all four top-level fields are mandatory.

### 2.2 `StateUpdates` Schema
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
* **Field Summary**:
  | Field | Type | Default | Validation Rule |
  | :--- | :--- | :--- | :--- |
  | `active_concept` | `Optional[str]` | `None` | Optional string |
  | `interrupted_question`| `Optional[CurrentQuestion]`| `None` | Validated via `CurrentQuestion` model |
  | `mastered_concepts` | `Optional[List[str]]` | `None` | List of concept strings |
  | `unresolved_misconceptions` | `Optional[List[str]]` | `None` | List of misconception strings |
  | `teacher_intervention`| `Optional[TeacherIntervention]`| `None` | Validated via `TeacherIntervention` model |
  | `current_question` | `Optional[CurrentQuestion]`| `None` | Validated via `CurrentQuestion` model |
  | `current_mode` | `Optional[Mode]` | `None` | Valid enum: `STUDENT`, `TEACHER`, `EVALUATOR` |
  | `difficulty` | `Optional[int]` | `None` | `1 <= difficulty <= 5` |
  | `confidence` | `Optional[float]` | `None` | `0.0 <= confidence <= 1.0` |
  | `concept_mastery` | `Optional[Dict[str, float]]` | `None` | Each score in dict must satisfy `0.0 <= score <= 1.0` |
  | `consecutive_failures`| `Optional[int]` | `None` | `>= 0` |
  | `consecutive_successes`| `Optional[int]` | `None` | `>= 0` |
  | `teacher_attempt_count`| `Optional[int]` | `None` | `>= 0` |
  | `recent_strategy_history`| `Optional[List[Strategy]]`| `None` | List of valid `Strategy` enums |
  | `misconception_counts`| `Optional[Dict[str, int]]` | `None` | Map of concept to integer count |

---

## 3. Current ChatService Implementation

* **File**: [`backend/app/services/chat_service.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/services/chat_service.py)

### 3.1 Constructor Dependencies
```python
def __init__(self):
    self.session_repo = SessionRepository()
    self.message_repo = MessageRepository()
    self.ai_provider = GroqLLMProvider()
    self.orchestrator = AIOrchestrator(self.ai_provider)
```
- Instantiates repository singletons directly.
- Initializes [`GroqLLMProvider`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/providers/groq_provider.py#L9) and passes it to the legacy [`AIOrchestrator`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/orchestrator.py#L13).

### 3.2 `send_message()` Flow
1. **Fetch Session**: Queries `db_session = self.session_repo.get(db, session_id)`.
2. **Persist User Message**: Calls `self.message_repo.create_message(db, session_id, "USER", message_in)`.
3. **Compile Context**:
   - Queries historical messages: `self.message_repo.list_by_session(db, session_id)`.
   - Inspects history to find last question content string: `active_question`.
   - Instantiates `AIContext` using flat parameters (omitting `confidence`, `mastered_concepts`, `unresolved_misconceptions`, and hardcoding `interrupted_question=None`).
4. **Invoke Legacy Orchestrator**:
   ```python
   ai_response = self.orchestrator.process_turn(
       context,
       consecutive_strong=db_session.state.consecutive_strong_answers,
       consecutive_weak=db_session.state.consecutive_weak_answers
   )
   ```
5. **Extract Metadata**: Reads raw dicts `ai_response.metadata["evaluation"]` and `ai_response.metadata["decision"]`.
6. **Persist AI Message**: Calls `self.message_repo.create_message(db, session_id, "AI", ...)`.
7. **Persist Evaluation**: Calls `self.message_repo.create_evaluation(db, user_msg.id, TurnEvaluationResponse(...))`.
8. **Manual State Math & Persistence**:
   - Re-computes consecutive answer streaks in Python.
   - Unions lists for `mastered_concepts` and `unresolved_misconceptions`.
   - Calls `self.session_repo.update_state(db, session_id, state_update)`.
9. **Return DTO**: Serializes and returns `ChatTurnResponse`.

### 3.3 Database Transaction Boundaries
* There is **no single atomic transaction**.
* Every repository mutation triggers an independent `db.commit()`:
  - User message: `create_message` commits immediately.
  - AI message: `create_message` commits immediately.
  - Turn evaluation: `create_evaluation` commits immediately.
  - State updates: `update_state` commits immediately.
* **Risk**: If the AI engine or a subsequent repository call fails, partial data remains permanently committed in PostgreSQL.

### 3.4 Response Serialization
* Serializes into [`ChatTurnResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py#L50):
  - `user_message`: [`MessageResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py#L11)
  - `ai_message`: [`MessageResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py#L11)
  - `evaluation`: [`TurnEvaluationResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py#L22)
  - `decision`: [`LearningDecisionResponse`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/message.py#L40)

---

## 4. SessionRepository.update_state() Inspection

* **File**: [`backend/app/repositories/session_repository.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/repositories/session_repository.py)

### 4.1 Accepted Input Type
```python
def update_state(self, db: SQLAlchemySession, session_id: UUID, state_in: SessionStateBase) -> SessionState:
```
* Accepts `state_in: SessionStateBase` defined in [`backend/app/schemas/session.py`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/schemas/session.py#L7).

### 4.2 Supported Fields
* `current_mode: LearningMode`
* `difficulty: int`
* `confidence: float`
* `active_concept: str`
* `current_question_id: Optional[UUID]`
* `interrupted_question_id: Optional[UUID]`
* `consecutive_strong_answers: int`
* `consecutive_weak_answers: int`
* `unresolved_misconceptions: List[str]`
* `mastered_concepts: List[str]`

### 4.3 How Partial Updates are Handled
* **Partial updates are NOT supported.**
* The method unconditionally writes every field from `state_in` directly onto `db_state`:
  ```python
  db_state.current_mode = state_in.current_mode.value ...
  db_state.difficulty = state_in.difficulty
  db_state.confidence = state_in.confidence
  db_state.active_concept = state_in.active_concept
  db_state.current_question_id = state_in.current_question_id
  db_state.interrupted_question_id = state_in.interrupted_question_id
  db_state.consecutive_strong_answers = state_in.consecutive_strong_answers
  db_state.consecutive_weak_answers = state_in.consecutive_weak_answers
  db_state.unresolved_misconceptions = state_in.unresolved_misconceptions
  db_state.mastered_concepts = state_in.mastered_concepts
  ```
* **Implication**: Any caller must provide a fully populated `SessionStateBase` instance. If `StateUpdates` from `CurioEngine` leaves certain fields as `None`, the caller must retain the previous values from `db_session.state` to prevent overwriting with defaults.

---

## 5. Compatibility Problems & Integration Mismatches

| # | Problem Area | Existing Implementation in `ChatService` | Requirement in `CurioEngine` | Impact / Failure Mode |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Return Object Structure** | Expects `AIResponse` with dicts in `.metadata["evaluation"]` and `.metadata["decision"]`. | Returns [`AIResult`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L205) with strongly-typed attributes (`evaluation`, `decision`, `response`, `state_updates`). | Direct substitution causes `KeyError: 'evaluation'` on `.metadata`. |
| **2** | **State Mutation Ownership** | Ad-hoc threshold math in service layer (`if correctness > 0.7: consecutive_strong += 1`). | Contract Rule #4 (*"AI Recommends, Backend Persists"*): Mutations emitted in [`StateUpdates`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L174). | Business logic duplication; state machine decisions ignored. |
| **3** | **Question Representation (UUID vs Semantic Object)** | Database stores UUIDs (`current_question_id`, `interrupted_question_id`). | `AIContext` and `StateUpdates` expect [`CurrentQuestion`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L67) (`id`, `content`, `concept`, `difficulty`). | Context passes plain string for `current_question` and `None` for `interrupted_question`. |
| **4** | **Dropped Learning Context** | `confidence`, `mastered_concepts`, `unresolved_misconceptions` omitted from `AIContext` constructor. | Canonical [`AIContext`](file:///c:/Users/Vishal%20S%20Naik/MyProjects/Curio-AI/backend/app/ai/schemas.py#L277) requires `understanding_confidence`, `LearningContext.mastered_concepts`, and `LearningContext.unresolved_misconceptions`. | AI context resets confidence to `0.0` on every turn; cannot evaluate mastery or prevent loops. |
| **5** | **Enum Identity Mismatch** | `ChatService` uses `LearningMode` and `LearningStrategy` from `backend.app.schemas.common`. | `CurioEngine` uses `Mode` and `Strategy` from `backend.app.ai.schemas`. | Although string representations match (`"STUDENT"`), enum classes differ across schemas. |
| **6** | **Partial State Merging** | `SessionRepository.update_state` requires all fields; overwrites if missing. | `StateUpdates` has all fields defaulted to `None`. | Service must explicitly merge `ai_result.state_updates` onto `db_session.state`. |
| **7** | **Non-Atomic DB Writes** | 4 separate commits per turn. | Engine turn execution can fail after user message is committed. | Database state inconsistency on exceptions. |
