# Curio AI - AI Engine Contracts

This document contains the internal definitions, input requirements, and output schemas for the AI Engine (`backend/app/ai/`). Both the AI sub-modules and the service layers calling the AI engine must adhere to these schemas.

---

## AI Module Boundary

The AI Engine does **not** communicate with the database. The database is queried in the service layer (e.g. `chat_service.py`), mapped into an `AIContext` object, and passed directly into the AI orchestrator.

```
+---------------------+
|    Chat Service     | <--- DB / SQLAlchemy Models
+---------------------+
           |  (Maps state to AIContext)
           v
+---------------------+
|   AI Orchestrator   |
+---------------------+
           |
           +---> Evaluate Answer -> TurnEvaluation
           |
           +---> Make Decision   -> LearningDecision
           |
           +---> Gen Response    -> AIResponse
           v
+---------------------+
|    Chat Service     | ---> (Persist outputs to DB)
+---------------------+
```

---

## Data Models (Pydantic / TS Interfaces)

### 1. `AIContext`
Input provided to the AI Engine for evaluation. Contains the session history, active topic, and state parameters.

```python
class AIContext(BaseModel):
    session_id: UUID
    topic: str
    current_mode: str  # STUDENT, TEACHER, EVALUATOR
    difficulty: int    # 1 to 5
    active_concept: str
    current_question: Optional[str]
    interrupted_question: Optional[str]
    document_context: Optional[str]
    history: List[ChatMessage]
```

### 2. `TurnEvaluation`
Calculated by `evaluator.py`. Evaluates the user's latest response.

```python
class TurnEvaluation(BaseModel):
    correctness: float       # 0.0 to 1.0
    clarity: float           # 0.0 to 1.0
    completeness: float      # 0.0 to 1.0
    depth: float             # 0.0 to 1.0
    relevance: float         # 0.0 to 1.0
    stuck_probability: float  # 0.0 to 1.0
    misconceptions: List[str]
    missing_concepts: List[str]
    undefined_terms: List[str]
    mastered_concepts: List[str]
    knowledge_gap: Optional[str]
    recommended_strategy: str
    recommended_difficulty: int
```

### 3. `LearningDecision`
Calculated by `decision_engine.py` deterministically. Determines mode transition, strategy, and parameter updates.

```python
class LearningDecision(BaseModel):
    next_mode: str          # STUDENT, TEACHER, EVALUATOR, COMPLETED
    strategy: str           # ASK_FOUNDATION, PROBE_WHY, TEACH_GAP, etc.
    difficulty: int         # 1 to 5
    confidence: float       # 0.0 to 1.0
    reason: str
    active_concept: str
    should_offer_termination: bool
    should_restore_interrupted_question: bool
```

### 4. `AIResponse`
Returned by the AI Engine to the service layer.

```python
class AIResponse(BaseModel):
    content: str
    mode: str
    strategy: str
    difficulty: int
    confidence: float
    metadata: Dict[str, Any]
```

### 5. `SessionState`
Maintained internally and in the database to track learning progress.

```python
class SessionState(BaseModel):
    session_id: UUID
    current_mode: str
    difficulty: int
    confidence: float
    active_concept: str
    current_question_id: Optional[UUID]
    interrupted_question_id: Optional[UUID]
    consecutive_strong_answers: int
    consecutive_weak_answers: int
    unresolved_misconceptions: List[str]
    mastered_concepts: List[str]
```
