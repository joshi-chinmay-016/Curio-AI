# Curio AI — Phase 1: Core Adaptive Student Mode

## 1. Overview

Phase 1 implements the first genuinely adaptive **Student Mode** learning engine for Curio AI, adhering strictly to the Feynman Learning Technique and the frozen Phase 0 contracts.

In this phase, Curio embodies an inquisitive student who probes the learner's understanding. The learner acts as the teacher, explaining concepts in their own words while Curio analyzes their responses, identifies knowledge gaps and misconceptions, selects pedagogical strategies, adjusts difficulty, and formulates focused Socratic questions.

---

## 2. Architectural Flow

```
[ Learner Input / Topic ]
           ↓
     AIContext (Input)
           ↓
 CurioEngine.process() (Public Boundary)
           ↓
    LangGraph Workflow (Internal):
    ┌─────────────────────────────┐
    │ START                       │
    │   ↓                         │
    │ run_evaluation (Phase 1A)   │
    │   ↓                         │
    │ run_decision (Phase 1B)     │
    │   ↓                         │
    │ run_response (Phase 1C & 1D)│
    │   ↓                         │
    │ run_state_updates (Phase 1E)│
    │   ↓                         │
    │ END                         │
    └─────────────────────────────┘
           ↓
      AIResult (Output)
           ↓
  Backend (ChatService)
  Validates & Persists StateUpdates
```

---

## 3. Component Details

### 3.1 Phase 1A — TurnEvaluator (`backend/app/ai/evaluator.py`)
- **Role**: Evaluates the learner's explanation for the **current turn only**.
- **Contract**: Produces `TurnEvaluation` conforming to `backend/app/ai/schemas.py`.
- **Metrics** (0.0 to 1.0):
  - `correctness`: Accuracy of the explanation.
  - `clarity`: Precision and expressiveness.
  - `completeness`: Component coverage.
  - `depth`: Underlying mechanisms and reasoning.
  - `relevance`: Topical alignment.
  - `stuck_probability`: Confusion or explicit "I don't know" cues.
- **Categorical Extraction**:
  - `undefined_terms`: Jargon introduced without definition.
  - `misconceptions`: Erroneous assumptions or false beliefs.
  - `missing_concepts`: Key components omitted.
  - `mastered_concepts`: Concepts clearly understood.
  - `knowledge_gap`: Diagnostic explanation of the gap.
  - `recommended_strategy` & `recommended_difficulty`.

### 3.2 Phase 1B — DecisionEngine (`backend/app/ai/decision_engine.py`)
- **Role**: Deterministic pedagogical policy engine. The LLM does not arbitrarily dictate state transitions.
- **Strategy Priority**:
  1. `undefined_terms` present $\rightarrow$ `CLARIFY_TERM`
  2. `misconceptions` present $\rightarrow$ `CHALLENGE_MISCONCEPTION`
  3. `missing_concepts` present $\rightarrow$ `PROBE_MISSING_CONCEPT`
  4. Mechanism gap $\rightarrow$ `PROBE_HOW`
  5. Reasoning gap $\rightarrow$ `PROBE_WHY`
  6. Strong understanding $\rightarrow$ `INCREASE_DIFFICULTY`
  7. Normal follow-up $\rightarrow$ `VERIFY_UNDERSTANDING` or `PROBE_WHY`
- **Difficulty Transitions** (1–5 clamped):
  - 1 = FOUNDATION, 2 = MECHANISM, 3 = APPLICATION, 4 = EDGE_CASE, 5 = SYNTHESIS.
  - Strong understanding: `current + 1` (clamped to 5).
  - Partial understanding: remain at `current`.
  - Major gap: remain or decrease by 1 (`max(1, current - 1)`).
  - Misconception: remain at `current` (challenge first).
  - Invariant: Maximum delta of 1 per turn ($|\Delta| \le 1$).
- **Bounded Confidence**:
  - Strong answer: increases ($+0.08$, clamped to $1.0$).
  - Partial answer: remains stable ($\pm 0.00$).
  - Major gap: decreases ($-0.08$, clamped to $0.0$).
  - Misconception: decreases ($-0.10$, clamped to $0.0$).
  - No 75% termination in Phase 1 (`should_offer_termination = False`).
- **Mode Invariant**: `next_mode = Mode.STUDENT` across all turns in Phase 1.

### 3.3 Phase 1C & 1D — Student Mode & Question Generation (`backend/app/ai/student.py`)
- **Persona**: Curious, respectful, intelligent student who asks questions to learn.
- **Initial Turn**: When no learner answer exists yet, generates a foundational question (`ASK_FOUNDATION`, difficulty 1).
- **Follow-Up Turns**: Formulates questions matching the selected strategy, concept, and difficulty.
- **Misconception Handling**: Does not lecture. Uses probing questions and counterexamples to let the learner discover contradictions.
- **HARD ONE-QUESTION RULE**:
  - Every response must contain **exactly ONE primary learning question**.
  - At most one short conversational lead-in sentence is permitted.
  - Compound or multi-part questions are strictly prohibited.
  - Post-processing enforces a single question mark in the final output.

### 3.4 Phase 1E — LangGraph Integration (`backend/app/ai/graph.py` & `backend/app/ai/nodes/student_nodes.py`)
- Encapsulated within `CurioEngine`. Backend code interacts solely via `CurioEngine.process(context: AIContext) -> AIResult`.
- Graph flow: `START -> evaluation_node -> decision_node -> response_node -> state_updates_node -> END`.
- Emits `StateUpdates` recommending updates to `current_mode`, `difficulty`, `confidence`, `active_concept`, `current_question`, `mastered_concepts`, and `unresolved_misconceptions`.

---

## 4. Test Verification Summary

Phase 1 implementation is thoroughly validated via deterministic unit, contract, and end-to-end tests:
- **`backend/tests/ai/test_phase1_student_mode.py`**:
  - 8 TurnEvaluator cases (strong, partial, incorrect, misconception, missing concept, undefined term, irrelevant, weak/uncertain).
  - Exact strategy priority ordering.
  - Difficulty increments and clamping (1–5).
  - Confidence bounding and direction.
  - Hard one-question rule enforcement.
  - CurioEngine initial turn and follow-up turns.
- **Zero API calls**: All 1A–1F tests execute using `MockLLMProvider` without network access or API credentials.
- **Full suite passing**: 67/67 AI tests and 21/21 API/service tests pass cleanly.

---

## 5. Strict Phase 1 Boundaries & Exclusions

The following capabilities are deliberately excluded from Phase 1 and reserved for subsequent phases:
- Teacher Mode intelligence and interventions.
- Evaluator Mode and session reports.
- 75% confidence termination triggers.
- RAG, embeddings, pgvector retrieval, and document ingestion.
- Voice, STT, and TTS.
- Dynamic mistake injection.
