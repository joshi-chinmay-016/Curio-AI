# Curio AI — Phase 3: Evaluator Mode + Learning Report

## 1. Phase 3 Goal

Phase 3 addresses the session-level evaluation question:
> *"Based on everything that happened during this learning session, how well does this learner actually understand the topic, what are their strengths, what gaps remain, which misconceptions were resolved or remain unresolved, and what should they learn next?"*

The system produces a machine-readable `SessionEvaluation` and a UI-agnostic `LearningReport`. The frontend report UI and visualization remain strictly deferred to a future phase.

---

## 2. TurnEvaluator vs. SessionEvaluator

| Dimension | TurnEvaluator (Phase 1) | SessionEvaluator (Phase 3) |
| :--- | :--- | :--- |
| **Scope** | Single learner turn | Complete session history |
| **Question** | "How good was *this* particular explanation?" | "What does the *entire session* tell us about the learner?" |
| **Inputs** | Current question + latest learner answer | All messages, turn evaluations, teacher interventions, and state progression |
| **Output** | `TurnEvaluation` | `SessionEvaluation` + `LearningReport` |
| **Role** | Immediate tactical pedagogical decisions | Longitudinal assessment and actionable roadmap |

---

## 3. Architecture & Evidence Pipeline

```
Raw Session Interaction (DB / Context)
           ↓
SessionEvidenceBuilder (3B)
           ↓
Structured SessionEvidence
           ↓
      ┌────┴────────────────────────┐
      ↓                             ↓
ScoringEngine (3D)           GapAnalyzer (3E)
- Deterministic 0-100 score  - Lifecycle: DETECTED/RESOLVED/UNRESOLVED
- Evidence confidence        - Misconception resolution tracking
- Concept assessments        - Evidence-backed strengths
      └────┬────────────────────────┘
           ↓
SessionEvaluator (3C)
           ↓
SessionEvaluation (Machine-readable)
           ↓
ReportBuilder (3F)
           ↓
LearningReport (UI-Agnostic Structured Data)
           ↓
ReportService & Persistence Layer (3G)
```

---

## 4. Evaluation Contracts

### 4.1 SessionEvidence
- `turns: List[TurnEvidence]`: Complete sequence of evaluated learner answers paired with preceding questions.
- `teacher_interventions: List[TeacherInterventionEvidence]`: Tracks teacher explanations, verification questions, and verification outcomes (`passed: bool`).
- `concept_evidence_map: Dict[str, ConceptEvidenceItem]`: Aggregated concept turns, scores, gaps, and assistance markers.
- `difficulty_progression: List[int]`: Difficulty levels traversed.
- `confidence_progression: List[float]`: Confidence levels across turns.
- `total_learner_turns`, `successful_turns`, `failed_turns`.

### 4.2 ConceptAssessment
- `concept: str`
- `understanding_score: float` (0.0 to 100.0)
- `confidence: float` (0.0 to 1.0)
- `mastery_level: MasteryLevel`
- `strengths: List[str]`
- `gaps: List[str]`
- `misconceptions: List[str]`
- `evidence_references: List[str]` (e.g., `["turn_0", "turn_2"]`)

### 4.3 SessionEvaluation
- `session_id: str`
- `topic: str`
- `understanding_score: float` (0.0 to 100.0)
- `mastery_level: MasteryLevel`
- `evidence_confidence: float` (0.0 to 1.0)
- `strengths: List[str]`
- `knowledge_gaps: List[GapAnalysisItem]`
- `misconceptions: List[MisconceptionAnalysisItem]`
- `resolved_gaps: List[str]`
- `unresolved_gaps: List[str]`
- `resolved_misconceptions: List[str]`
- `unresolved_misconceptions: List[str]`
- `concept_assessments: List[ConceptAssessment]`
- `difficulty_progression: List[int]`
- `teacher_intervention_summary: Dict[str, Any]`
- `recommended_next_steps: List[RoadmapItem]`

### 4.4 LearningReport
UI-agnostic user-facing data model consumed by future frontend components:
- `understanding_score`, `mastery_level`, `evidence_confidence`
- `strengths`, `knowledge_gaps`, `resolved_gaps`, `unresolved_gaps`
- `misconceptions`, `resolved_misconceptions`, `unresolved_misconceptions`
- `concept_assessments`, `difficulty_achieved`, `teacher_interventions_required`
- `recommended_next_steps: List[RoadmapItem]`

---

## 5. Scoring Architecture & Mastery Levels

### 5.1 Deterministic Turn Scoring
Dimensions weighted transparently:
- **Correctness**: 35%
- **Completeness**: 20%
- **Depth**: 20%
- **Clarity**: 15%
- **Relevance**: 10%
- Difficulty scaling factor rewards higher difficulty successfully handled.
- Stuck penalty caps scores for turns with high stuck probability (> 0.6).

### 5.2 Evidence Confidence & Insufficient Evidence Guard
A high score on minimal evidence does not justify a high-confidence mastery claim:
- `turns == 1`: Confidence is strictly capped at `0.25`.
- `turns == 2`: Confidence is capped at `0.48`.
- Higher confidence requires repeated turns, multi-concept coverage, and score consistency.

### 5.3 Mastery Thresholds
- **MASTERY**: Score >= 85.0 and `evidence_confidence >= 0.70`
- **PROFICIENT**: Score >= 70.0 and `evidence_confidence >= 0.50`
- **DEVELOPING**: Score >= 45.0
- **BEGINNER**: Score < 45.0, or insufficient evidence guard triggered.

---

## 6. Gap & Misconception Lifecycle

### 6.1 Knowledge Gaps
1. **DETECTED**: Identified via `TurnEvaluation.knowledge_gap` or `missing_concepts`.
2. **CHALLENGED**: Targeted by subsequent Socratic probe or Teacher Mode intervention.
3. **RESOLVED**: Teacher verification passed or later turns demonstrated high correctness without the gap.
4. **UNRESOLVED**: Persistence of the gap without subsequent successful verification.

### 6.2 Misconceptions
1. **DETECTED**: Identified in `TurnEvaluation.misconceptions`.
2. **CHALLENGED**: Strategy `CHALLENGE_MISCONCEPTION` or Teacher Mode triggered.
3. **RESOLVED**: Teacher verification passed or subsequent turns showed clear, correct explanations omitting the misconception.
4. **UNRESOLVED**: Misconception persisted or was unaddressed.

---

## 7. Roadmap Generation

Roadmap items (`RoadmapItem`) are derived strictly from session evidence:
1. **Priority 1 (`RESOLVE_MISCONCEPTION`)**: Critical unresolved misconceptions.
2. **Priority 2 (`FILL_GAP`)**: Major unresolved knowledge gaps.
3. **Priority 3 (`PRACTICE`)**: Concepts with understanding scores below 70%.
4. **Priority 4 (`ADVANCED` / `PRACTICE`)**: Mastery consolidation and real-world synthesis.

---

## 8. Evaluator Mode Lifecycle & LangGraph Flow

Evaluator Mode is **read-only** with respect to the active learning state:
- Does not overwrite `current_question`, `interrupted_question`, or `active_concept`.
- Does not continue Student Mode questioning.
- Public interface remains strictly `CurioEngine.process(AIContext) -> AIResult`.
- Evaluator flow in LangGraph:
  `START -> evaluation_node (evaluates session) -> decision_node (Strategy.GENERATE_REPORT) -> response_node -> state_updates_node (read-only) -> END`.

---

## 9. Backend Persistence & APIs

### 9.1 Database Migration
Migration `a1b2c3d4e5f6_add_phase3_evaluation_fields.py` adds the following columns to `session_reports`:
- `evidence_confidence: Float`
- `concept_assessments: JSON`
- `resolved_gaps: JSON`
- `unresolved_gaps: JSON`
- `resolved_misconceptions: JSON`
- `unresolved_misconceptions: JSON`
- `session_evaluation: JSON`

### 9.2 Endpoints
- `POST /api/v1/sessions/{id}/evaluate`: Explicitly triggers session evaluation and generates structured learning report. Idempotent: returns existing report if already compiled.
- `POST /api/v1/sessions/{id}/end`: Completes session and returns learning report.
- `GET /api/v1/sessions/{id}/report`: Retrieves compiled report (404 if not yet evaluated).

---

## 10. Verification & Test Baseline

- **Phase 1 Baseline**: 67/67 passed.
- **Phase 2 Baseline**: 87/87 passed.
- **Phase 3 New Tests**: 30 new tests added:
  - Contracts: 7 passed (`test_phase3_contracts.py`)
  - Evidence Builder: 6 passed (`test_phase3_evidence.py`)
  - Scoring & Gaps: 6 passed (`test_phase3_scoring.py`)
  - Evaluator & Report: 5 passed (`test_phase3_evaluator.py`)
  - API & Persistence: 6 passed (`test_phase3_api.py`)
- **Full Backend Suite**: 175/175 passed (0 failures, 0 errors).
- **Live Groq Smoke Test**: Validated on real provider (`openai/gpt-oss-120b`).

---

## 11. Explicitly Deferred

- **3H**: Frontend report UI, cards, layout, charts.
- **3I**: Frontend report integration.
- PDF generation and export.
- Automatic 75% mastery termination.
- Cross-session global mastery graph.
- RAG / Document learning.
- Voice mode.
