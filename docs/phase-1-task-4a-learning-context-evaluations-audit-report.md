# Phase 1, Task 4A: Learning Context Evaluations Hydration Audit Report

**Date**: 2026-09-21  
**Author**: Backend Infrastructure Engineer (Pair Programming with AI Assistant)  
**Scope**: Read-Only Audit for Hydrating Recent Turn Evaluations from PostgreSQL into `AIContext.learning_context.recent_evaluations`.  
**Boundary**: Backend infrastructure only. Zero code modifications, no migrations, no Groq API calls, no AI heuristic changes.

---

## 1. Executive Summary & Current Findings

In `ChatService.send_message()`, the backend persists turn evaluations to the PostgreSQL database after each turn:
```python
self.message_repo.create_evaluation(db, user_msg.id, turn_eval_in)
```
However, during context compilation at the beginning of each turn (`chat_service.py:233-237`), `learning_context` is constructed without `recent_evaluations`:
```python
learning_context = LearningContext(
    mastered_concepts=db_session.state.mastered_concepts or [],
    unresolved_misconceptions=db_session.state.unresolved_misconceptions or [],
    teacher_intervention=teacher_intervention_obj,
)
```
Because `recent_evaluations` is omitted, it defaults to an empty list (`[]`).

### Impact on AI Engine
1. **DecisionEngine Trigger C Failure**: In `backend/app/ai/decision_engine.py:159-165`, Trigger C (transitioning from Student Mode to Teacher Mode upon repeated failure on the same knowledge gap) checks:
   ```python
   elif context.learning_context and context.learning_context.recent_evaluations:
       for prev_eval in reversed(context.learning_context.recent_evaluations):
           if prev_eval.knowledge_gap:
               prev_gap = prev_eval.knowledge_gap.strip().lower()
               if prev_gap in current_gap_lower or current_gap_lower in prev_gap:
                   trigger_c = True
                   break
   ```
   Because `recent_evaluations` is always empty in production, Trigger C cannot inspect past evaluations across turns.
2. **Evaluator Mode Session Evidence**: When `student_nodes.py:47` constructs session evidence via `SessionEvidenceBuilder.build_from_history()`, passing an empty evaluations list forces the builder to synthesize default neutral fallback evaluations rather than using the learner's actual historical evaluations.

---

## 2. Database Model & Relationship Architecture

### Model Definition: `backend/app/models/evaluation.py`
```python
class TurnEvaluation(Base):
    __tablename__ = "turn_evaluations"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True, index=True)
    correctness = Column(Float, default=0.0, nullable=False)
    clarity = Column(Float, default=0.0, nullable=False)
    completeness = Column(Float, default=0.0, nullable=False)
    depth = Column(Float, default=0.0, nullable=False)
    relevance = Column(Float, default=0.0, nullable=False)
    stuck_probability = Column(Float, default=0.0, nullable=False)
    misconceptions = Column(JSON, default=list, nullable=False)
    missing_concepts = Column(JSON, default=list, nullable=False)
    undefined_terms = Column(JSON, default=list, nullable=False)
    mastered_concepts = Column(JSON, default=list, nullable=False)
    knowledge_gap = Column(Text, nullable=True)
    recommended_strategy = Column(String, nullable=False)
    recommended_difficulty = Column(Integer, default=1, nullable=False)

    message = relationship("Message", back_populates="evaluation")
```

### Relational Hierarchy
- **No Direct `session_id` Column on `turn_evaluations`**: The `turn_evaluations` table is indexed and keyed solely on `message_id`.
- **Foreign Key**: `message_id → messages.id`.
- **Session Association**: `messages.session_id → sessions.id`.
- **One-to-One with Message**: In `backend/app/models/message.py:18`:
  ```python
  evaluation = relationship("TurnEvaluation", uselist=False, back_populates="message", cascade="all, delete-orphan")
  ```
- **Turn Ownership**: In Curio AI, turn evaluations are created exclusively for `USER` messages (`m.sender == "USER"`). AI messages do not have evaluations.

---

## 3. Schema Contract Alignment: Database vs AI Model

The schema mapping between the SQLAlchemy DB model and the AI domain model `backend/app/ai/schemas.py:125-139` is an exact 1:1 match:

| Field | DB Column Type (`models.evaluation`) | AI Schema Type (`ai.schemas.TurnEvaluation`) | Mapping / Conversion Requirement |
| :--- | :--- | :--- | :--- |
| `correctness` | `Float` | `float` (bounded `0.0`..`1.0`) | Clamp to `[0.0, 1.0]` |
| `clarity` | `Float` | `float` (bounded `0.0`..`1.0`) | Clamp to `[0.0, 1.0]` |
| `completeness` | `Float` | `float` (bounded `0.0`..`1.0`) | Clamp to `[0.0, 1.0]` |
| `depth` | `Float` | `float` (bounded `0.0`..`1.0`) | Clamp to `[0.0, 1.0]` |
| `relevance` | `Float` | `float` (bounded `0.0`..`1.0`) | Clamp to `[0.0, 1.0]` |
| `stuck_probability`| `Float` | `float` (bounded `0.0`..`1.0`) | Clamp to `[0.0, 1.0]` |
| `misconceptions` | `JSON` | `List[str]` | Default to `[]` if `None` |
| `missing_concepts` | `JSON` | `List[str]` | Default to `[]` if `None` |
| `undefined_terms` | `JSON` | `List[str]` | Default to `[]` if `None` |
| `mastered_concepts`| `JSON` | `List[str]` | Default to `[]` if `None` |
| `knowledge_gap` | `Text` | `Optional[str]` | Pass as-is or `None` |
| `recommended_strategy`| `String` | `Strategy` (Enum) | `Strategy(val)` with fallback to `Strategy.PROBE_WHY` |
| `recommended_difficulty`| `Integer` | `int` (bounded `1`..`5`) | Clamp to `[1, 5]` |

---

## 4. Ordering Analysis: Chronological vs. Newest-First

### Critical Discrepancy Identified
While the user prompt suggests *"preferably newest first"*, inspection of Chinmay's AI engine reveals that **the AI code explicitly assumes chronological ordering (oldest $\rightarrow$ newest)**:

1. **`DecisionEngine` (`decision_engine.py:160`)**:
   ```python
   for prev_eval in reversed(context.learning_context.recent_evaluations):
   ```
   `DecisionEngine` calls `reversed()` on `recent_evaluations` so that it starts at the *end* of the list (the most recent turn) and works backward towards earlier turns. If `recent_evaluations` were pre-sorted newest-first, `reversed()` would inspect the *oldest* turn first and the newest turn last.
2. **`SessionEvidenceBuilder` (`session_evidence.py:96-110`)**:
   ```python
   for turn_idx, u_idx in enumerate(user_msg_indices):
       if evaluations and eval_idx < len(evaluations):
           turn_eval = evaluations[eval_idx]
           eval_idx += 1
   ```
   `SessionEvidenceBuilder` iterates through user message indices in chronological order (turn 0, turn 1, ...) and pairs each turn with `evaluations[eval_idx]`. If `evaluations` were newest-first, turn 0 would incorrectly receive the newest turn evaluation.

### Conclusion on Ordering
- To maintain seamless contract compatibility without breaking `DecisionEngine` or `SessionEvidenceBuilder`, the list passed to `LearningContext.recent_evaluations` **must be chronologically ordered** (matching `messages.created_at.asc()`).
- If a query fetches the last $N$ turns using `DESC` with a `LIMIT`, the backend should reverse the slice before populating `recent_evaluations` so the resulting list ends with the most recent turn.

---

## 5. Safe Sliding Window Limit

1. **Memory & Token Context**:
   - In a long session (e.g., 40+ turns), passing 40 full evaluation objects into every turn's context adds unnecessary serialization and memory overhead.
2. **Pedagogical Requirement**:
   - `DecisionEngine` Trigger C only needs recent turns to detect *immediate repeated failure* on the same knowledge gap.
   - 5 to 10 turns provide ample lookback for pedagogy without bloat.
3. **Established Pattern**:
   - Prior audit recommendation: limit lookback to the **last 10 evaluated turns** (`limit=10`).
   - If total session evaluations $< 10$, all existing evaluations are included.

---

## 6. Session Ownership & Filtering Guarantees

Because `turn_evaluations` lacks a `session_id` column, the query must guarantee strict session isolation:
```sql
SELECT te.* 
FROM turn_evaluations te
JOIN messages m ON te.message_id = m.id
WHERE m.session_id = :session_id AND m.sender = 'USER'
ORDER BY m.created_at ASC;
```

### Preventing N+1 Query Performance Degradation
In `chat_service.py:135`, messages are loaded via:
```python
db_history = self.message_repo.list_by_session(db, session_id)
```
If `ChatService` iterates over `m.evaluation` on each message in `db_history`, SQLAlchemy will emit a separate `SELECT` query for every message (N+1 query issue).
**Solution**:
Add a dedicated query method in `MessageRepository`:
- `get_recent_evaluations_by_session(db, session_id, limit=10)`
- Executes a single joined query, preventing N+1 overhead while strictly isolating by `session_id`.

---

## 7. Defensive Deserialization Strategy

To ensure zero crashes from corrupted or legacy database rows:
1. **Enum Safety**: Convert `recommended_strategy` string via:
   ```python
   try:
       strategy_obj = Strategy(db_ev.recommended_strategy)
   except (ValueError, KeyError):
       strategy_obj = Strategy.PROBE_WHY
   ```
2. **Bounds Clamping**:
   - `correctness`, `clarity`, `completeness`, `depth`, `relevance`, `stuck_probability`: clamp to `max(0.0, min(1.0, float(val)))`.
   - `recommended_difficulty`: clamp to `max(1, min(5, int(val)))`.
3. **JSON List Safety**:
   - `misconceptions`, `missing_concepts`, `undefined_terms`, `mastered_concepts`: coerce `None` or non-list to `list(val)` or `[]`.
4. **Validation Isolation**:
   - Wrap each record conversion in `try...except Exception`. If an unrecoverable schema error occurs, log a warning and skip that single evaluation rather than crashing the chat turn.

---

## 8. Alignment Questions for Chinmay

1. **Ordering Confirmation**:
   - Does Chinmay's AI logic explicitly depend on `recent_evaluations` ending with the most recent evaluation (as evidenced by `for prev_eval in reversed(...)` in `decision_engine.py`)?
   - *Recommendation*: Backend will hydrate in chronological order (`created_at ASC`), ending with the latest turn.
2. **Lookback Window Size**:
   - Is a 10-turn lookback window (`limit=10`) sufficient for pedagogical decision-making, or is an unbounded history required for specific evaluator scenarios?
   - *Recommendation*: Default to the last 10 turns.

---

## 9. Recommended Minimal Backend Implementation Plan

### Step 1: Add Repository Query in `backend/app/repositories/message_repository.py`
Add a dedicated method that queries `turn_evaluations` joined with `messages`, filtered by `session_id`, limited to the last 10 user turns, and sorted chronologically:
```python
def get_recent_evaluations_by_session(
    self, db: SQLAlchemySession, session_id: UUID, limit: int = 10
) -> List[TurnEvaluation]:
    # Query newest first to apply limit, then reverse to return chronologically
    subquery = (
        db.query(TurnEvaluation)
        .join(Message, TurnEvaluation.message_id == Message.id)
        .filter(Message.session_id == session_id, Message.sender == "USER")
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(subquery))
```

### Step 2: Implement Defensive Mapper in `backend/app/services/chat_service.py`
Add a helper method `_to_ai_turn_evaluation(db_eval)` mirroring the proven pattern in `report_service.py:74-88`.

### Step 3: Populate `recent_evaluations` in `ChatService.send_message()`
```python
recent_db_evals = self.message_repo.get_recent_evaluations_by_session(db, session_id, limit=10)
hydrated_evals = [
    eval_obj for db_ev in recent_db_evals
    if (eval_obj := self._to_ai_turn_evaluation(db_ev)) is not None
]

learning_context = LearningContext(
    mastered_concepts=db_session.state.mastered_concepts or [],
    unresolved_misconceptions=db_session.state.unresolved_misconceptions or [],
    recent_evaluations=hydrated_evals,
    teacher_intervention=teacher_intervention_obj,
)
```

---

## 10. Required Tests for Validation

1. **Unit Tests (`test_chat_service.py`)**:
   - `test_send_message_hydrates_recent_evaluations_into_aicontext`: Verify past turn evaluations are extracted from the DB and populated into `AIContext.learning_context.recent_evaluations`.
   - `test_send_message_handles_malformed_turn_evaluation_gracefully`: Verify invalid strategy strings, out-of-bound float values, or `None` lists do not crash `send_message`.
   - `test_send_message_recent_evaluations_ordering_and_limit`: Verify evaluations are chronologically ordered and capped at the configured limit (e.g. 10).
2. **Database Integration Tests (`test_database_integration.py`)**:
   - `test_get_recent_evaluations_by_session_isolation`: Verify that querying recent evaluations strictly filters by `session_id` and does not leak evaluations across different sessions or users.

---

## 11. Files Requiring Changes (When Approved)

1. `backend/app/repositories/message_repository.py`: Add `get_recent_evaluations_by_session()` method.
2. `backend/app/services/chat_service.py`: Add defensive mapper and populate `learning_context.recent_evaluations`.
3. `backend/tests/services/test_chat_service.py`: Add hydration and defensive parsing unit tests.
4. `backend/tests/integration/test_database_integration.py`: Add database-backed query and session-isolation tests.
