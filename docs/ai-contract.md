# Curio AI Engine & Backend Contract Specification

This document defines the architectural boundary, data contracts, and integration protocols between the **Curio Backend** (FastAPI / PostgreSQL / SQLAlchemy, owned by Vishal) and the **Curio AI Engine** (LangGraph / Python, owned by Chinmay).

---

## 1. Purpose of the AI Layer

Curio AI is an adaptive learning system modeled on the Feynman Technique. The learner acts as the teacher, and the AI acts primarily as a curious student who probes for explanations, detects gaps and misconceptions, adjusts difficulty progressively, and temporarily transitions to Teacher Mode only when necessary to unblock specific knowledge gaps.

The AI layer is responsible for:
- Evaluating learner explanations across correctness, clarity, completeness, depth, relevance, and stuck probability.
- Maintaining pedogogical strategy transitions (Student $\leftrightarrow$ Teacher $\leftrightarrow$ Evaluator).
- Selecting the next instructional move (probe why, probe how, clarify term, increase difficulty, teach gap, etc.).
- Formulating learner-facing single questions.
- Recommending state mutations based on mastery.

The AI layer is **stateless across network invocations**: all persistent context is provided in the input payload, and all state mutations are returned as recommendations in the output payload.

---

## 2. AI / Backend Separation & Architectural Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│   (Auth, DB, Sessions, Persistence, API Controllers)    │
└────────────────────────────┬────────────────────────────┘
                             │ Builds AIContext
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 CurioEngine.process()                   │
│          (Public Interface Boundary of AI Layer)        │
└────────────────────────────┬────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            │   LangGraph Workflow (Internal) │
            │                                 │
            │   START                         │
            │     ↓                           │
            │   Evaluation Node               │
            │     ↓                           │
            │   Decision Node                 │
            │     ↓                           │
            │   Response Node                 │
            │     ↓                           │
            │   END                           │
            └────────────────┬────────────────┘
                             │
                             ▼ Emits AIResult
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│       (Validates AIResult, Persists to PostgreSQL)      │
└─────────────────────────────────────────────────────────┘
```

### Core Separation Rules:
1. **Zero Database Access in AI Engine**: The AI engine **never** imports SQLAlchemy, database sessions, database models, Alembic, or PostgreSQL drivers.
2. **Zero Framework Dependencies in AI Engine**: The AI engine does not depend on FastAPI or HTTP request contexts.
3. **Backend Owns Persistence**: The backend loads session state from the database, constructs `AIContext`, invokes the AI engine, validates the resulting `AIResult`, and writes updates to the database.
4. **AI Recommends, Backend Persists**: The AI engine produces `StateUpdates` recommendations. The backend validates these updates and performs atomic transactions.
5. **LangGraph Is An Internal Implementation Detail**: LangGraph classes (`StateGraph`, `START`, `END`, internal node states) must **never** be exposed to or imported by the backend.

---

## 3. Input Contract: `AIContext`

Constructed by the backend service layer before invoking `CurioEngine.process()`.

```python
class AIContext(BaseModel):
    session: SessionInfo
    current_state: SessionState
    conversation: ConversationContext
    learning_context: LearningContext = Field(default_factory=LearningContext)
    source_context: Optional[Dict[str, Any]] = None
```

### Sub-Models:
```python
class SessionInfo(BaseModel):
    session_id: str
    topic: str
    source_mode: SourceMode = SourceMode.GENERAL  # GENERAL | DOCUMENT | MIXED

class ConversationContext(BaseModel):
    recent_messages: List[ChatMessage] = Field(default_factory=list)
    message_count: int = 0

class LearningContext(BaseModel):
    mastered_concepts: List[str] = Field(default_factory=list)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    recent_evaluations: List[TurnEvaluation] = Field(default_factory=list)
    teacher_intervention: Optional[TeacherIntervention] = None

class ChatMessage(BaseModel):
    role: Role  # USER | ASSISTANT | SYSTEM
    content: str
    input_type: InputType = InputType.TEXT  # TEXT | VOICE
```

*Note: `AIContext` supports property accessors (`session_id`, `topic`, `current_mode`, `difficulty`, `active_concept`, `history`) and flat initialization for full backward compatibility.*

---

## 4. Output Contract: `AIResult`

Returned by `CurioEngine.process()` to the backend.

```python
class AIResult(BaseModel):
    evaluation: TurnEvaluation
    decision: LearningDecision
    response: AIResponse
    state_updates: StateUpdates
```

---

## 5. State Models: `SessionState` & `CurrentQuestion`

### `CurrentQuestion`
Represents the rich semantic representation of the active question:
```python
class CurrentQuestion(BaseModel):
    id: str
    content: str
    concept: str
    difficulty: int = Field(ge=1, le=5)
```

### `TeacherIntervention`
Tracks teacher-led mini-interventions:
```python
class TeacherIntervention(BaseModel):
    active: bool = False
    gap: str = ""
    attempt_count: int = Field(default=0, ge=0)
    verification_required: bool = True
```

### `SessionState`
Persistent learning state:
```python
class SessionState(BaseModel):
    session_id: str
    current_mode: Mode = Mode.STUDENT            # STUDENT | TEACHER | EVALUATOR
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
    concept_mastery: Dict[str, float] = Field(default_factory=dict)  # values 0.0..1.0
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    teacher_intervention: Optional[TeacherIntervention] = None
```

---

## 6. Evaluation Contract: `TurnEvaluation`

Answers: **"What did the learner demonstrate in their latest response?"**

```python
class TurnEvaluation(BaseModel):
    correctness: float = Field(ge=0.0, le=1.0)
    clarity: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    depth: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    stuck_probability: float = Field(ge=0.0, le=1.0)
    misconceptions: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    undefined_terms: List[str] = Field(default_factory=list)
    mastered_concepts: List[str] = Field(default_factory=list)
    knowledge_gap: Optional[str] = None
    recommended_strategy: Strategy
    recommended_difficulty: int = Field(ge=1, le=5)
```

---

## 7. Decision Contract: `LearningDecision`

Answers: **"What pedagogical action should Curio take next?"**

```python
class LearningDecision(BaseModel):
    next_mode: Mode                          # STUDENT | TEACHER | EVALUATOR
    strategy: Strategy                       # ASK_FOUNDATION | PROBE_WHY | ...
    difficulty: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    active_concept: str
    should_offer_termination: bool = False
    should_restore_interrupted_question: bool = False
```

---

## 8. Response & State Updates Contracts

### `AIResponse`
Contains the generated interaction content:
```python
class AIResponse(BaseModel):
    content: str = Field(min_length=1)
    mode: Mode
    strategy: Strategy
    difficulty: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_single_question: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### `StateUpdates`
Recommended mutations for the backend to persist:
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

## 9. Public AI Engine Interface: `CurioEngine`

The backend interacts exclusively with `CurioEngine`:

```python
from backend.app.ai import CurioEngine, AIContext, AIResult

engine = CurioEngine()
result: AIResult = engine.process(context)
```

### LangGraph Encapsulation Boundary:
The backend **must never** import:
- `backend.app.ai.graph`
- `backend.app.ai.nodes.*`
- `langgraph.*`

All internal workflow orchestration happens behind `CurioEngine.process()`.

---

## 10. Code & Responsibility Ownership Matrix

| Responsibility Area | Owner | Location | Details |
|---|---|---|---|
| User Authentication & Auth Tokens | Vishal | `backend/app/api/` | JWT / OAuth verification |
| Database Persistence & Migrations | Vishal | `backend/app/db/`, `models/`, `alembic/` | PostgreSQL tables & schema |
| Repositories & CRUD | Vishal | `backend/app/repositories/` | SQLAlchemy queries |
| API Service Layer | Vishal | `backend/app/services/` | Assembles context, orchestrates persistence |
| AI Context Construction | Vishal | `backend/app/services/` | Converts DB records to `AIContext` |
| AI Reasoning & Evaluation | Chinmay | `backend/app/ai/` | Evaluates learner responses |
| Pedagogical Decisions | Chinmay | `backend/app/ai/` | Mode switches, difficulty & strategy |
| Socratic Question Formulation | Chinmay | `backend/app/ai/nodes/` | Generates next inquiry |
| State Updates Application | Vishal | `backend/app/services/` | Validates and commits `StateUpdates` to DB |

---

## 11. Complete Example Execution Flow

### Input `AIContext`:
```json
{
  "session": {
    "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "topic": "Recursion",
    "source_mode": "GENERAL"
  },
  "current_state": {
    "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "current_mode": "STUDENT",
    "current_difficulty": 3,
    "understanding_confidence": 0.68,
    "active_concept": "base_case",
    "current_question": {
      "id": "q_123",
      "content": "Why is a base case necessary in recursion?",
      "concept": "base_case",
      "difficulty": 3
    },
    "consecutive_failures": 0,
    "consecutive_successes": 2,
    "teacher_attempt_count": 0,
    "recent_strategy_history": ["PROBE_WHY"],
    "concept_mastery": {
      "recursion_definition": 0.85
    }
  },
  "conversation": {
    "recent_messages": [
      {
        "role": "ASSISTANT",
        "content": "Why is a base case necessary in recursion?",
        "input_type": "TEXT"
      },
      {
        "role": "USER",
        "content": "It stops the function from calling itself forever.",
        "input_type": "TEXT"
      }
    ],
    "message_count": 2
  },
  "learning_context": {
    "mastered_concepts": ["recursion_definition"],
    "unresolved_misconceptions": []
  }
}
```

### Output `AIResult`:
```json
{
  "evaluation": {
    "correctness": 0.85,
    "clarity": 0.78,
    "completeness": 0.72,
    "depth": 0.65,
    "relevance": 0.95,
    "stuck_probability": 0.15,
    "misconceptions": [],
    "missing_concepts": ["Stack memory during recursion"],
    "undefined_terms": [],
    "mastered_concepts": ["Purpose of a base case"],
    "knowledge_gap": null,
    "recommended_strategy": "PROBE_WHY",
    "recommended_difficulty": 4
  },
  "decision": {
    "next_mode": "STUDENT",
    "strategy": "PROBE_WHY",
    "difficulty": 4,
    "confidence": 0.68,
    "reason": "The learner understands the definition but has not explained the underlying mechanism.",
    "active_concept": "base_case",
    "should_offer_termination": false,
    "should_restore_interrupted_question": false
  },
  "response": {
    "content": "What would happen if the recursive function did not contain a base case?",
    "mode": "STUDENT",
    "strategy": "PROBE_WHY",
    "difficulty": 4,
    "confidence": 0.68,
    "requires_single_question": true,
    "metadata": {
      "placeholder": true,
      "phase": "0"
    }
  },
  "state_updates": {
    "active_concept": "base_case",
    "current_mode": "STUDENT",
    "difficulty": 4,
    "confidence": 0.68,
    "mastered_concepts": ["Purpose of a base case"],
    "unresolved_misconceptions": [],
    "current_question": {
      "id": "q_gen_placeholder",
      "content": "What would happen if the recursive function did not contain a base case?",
      "concept": "base_case",
      "difficulty": 4
    }
  }
}
```

---

## 12. Rules for Changing the Contract

1. **Additive Changes First**: New optional fields may be added to `AIContext` or `StateUpdates` without breaking existing consumers.
2. **Never Remove or Rename Core Fields**: Fields such as `session_id`, `current_mode`, `difficulty`, `confidence`, `evaluation`, `decision`, and `response` must not be renamed without written agreement between Chinmay and Vishal.
3. **No Database Leakage**: Any new field added must be serializable to pure JSON without requiring database-specific types (e.g. use `str` or standard `UUID`, not SQLAlchemy models).
4. **Contract Updates Require Documentation Updates**: Any changes to `schemas.py` must be immediately reflected in `docs/ai-contract.md` and validated with unit tests in `backend/tests/ai/`.
