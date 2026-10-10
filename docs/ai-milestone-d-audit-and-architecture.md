# AI Milestone D: Concept Modeling Architecture Audit & Discovery

**Document Version:** 1.0.0  
**Milestone:** AI Milestone D — Concept Model, Learning Objectives & Dynamic Knowledge Representation  
**Date:** October 10, 2026  
**Status:** Completed  
**Branch:** `feature/ai`  

---

## 1. Executive Summary & Objective

The primary objective of Milestone D is to build a generic, validated, topic-independent concept representation that enables Curio AI to understand:
1. What a learner should learn (Concepts & Learning Objectives).
2. What evidence demonstrates genuine understanding (Expected Evidence & Constraints).
3. How concepts relate to one another (Prerequisites, Specialization, Generalization, Causal/Mechanistic Dependencies).

This bridges the gap:
$$\text{Topic} \longrightarrow \text{Concept Model} \longrightarrow \text{Learning Objectives} \longrightarrow \text{Expected Evidence} \longrightarrow \text{Assessment Context}$$

Milestone D ensures Curio AI can teach and assess arbitrary domains (computer science, economics, biology, physics, mathematics, philosophy) without hardcoded topic branches or manually maintained question banks.

---

## 2. Existing Repository State & Baseline Findings

### 2.1 Git & Branch Verification
- **Branch:** `feature/ai` (synchronized with `origin/feature/ai` and merged `dev` branch PR #14).
- **Working Tree:** Clean, 0 uncommitted changes.
- **Test Baseline:** 316 passing tests in `backend/tests/ai` with 100% pass rate.

### 2.2 Existing Concept Implementations
1. **Schemas (`backend/app/ai/schemas.py`)**:
   - `ConceptNode`: Contains basic fields (`id`, `name`, `definition`, `prerequisites`, `sub_concepts`, `applications`, `constraints`, `common_misconceptions`, `edge_cases`, `difficulty_level`).
   - `ConceptRelationship`: Contains `source_concept_id`, `target_concept_id`, `relation_type`, `description`.
   - `ConceptModel`: Top-level container (`topic`, `concepts`, `relationships`, `metadata`) with basic `get_concept()` and `get_prerequisites()`.
   - `LearnerModel` & `ConceptState`: Tracks per-concept mastery and evidence count.
2. **Concept Builder (`backend/app/ai/concept_model.py`)**:
   - `ConceptModelBuilder`: Uses `provider.generate_structured(prompt, ConceptModel)`.
   - Sanitizes duplicate IDs and removes phantom prerequisites.
   - Provides a basic 4-tier fallback model (`fundamentals`, `mechanism`, `applications`, `edge_cases`).
3. **Existing Question Selector (`backend/app/ai/question_selector.py`)**:
   - Evaluates prerequisites and gap nodes using `concept_model.get_concept()`.

---

## 3. Gap Analysis: What is Missing for Milestone D

While the baseline contains foundational data structures, several essential capabilities are absent:

| Requirement | Baseline Status | Milestone D Plan |
| :--- | :--- | :--- |
| **TopicModel Contract** | Only basic `ConceptModel` with `topic: str` exists. | Introduce `TopicModel` (inheriting/aliasing `ConceptModel` for backward compatibility) with `topic_id`, `topic_title`, `topic_description`, `learning_objectives`, `validation_status`, `model_version`, `limitations`. |
| **Learning Objectives** | Absent. Concepts only have definitions and sub-concepts. | Create `LearningObjective` with `objective_id`, `concept_id`, `description`, `cognitive_action` enum, `difficulty`, `essential`, `prerequisite_objective_ids`, `expected_evidence`, `success_criteria`. |
| **Cognitive Actions** | Absent. | Define `CognitiveAction` enum (`DEFINE`, `EXPLAIN`, `COMPARE`, `APPLY`, `DERIVE`, `ANALYZE`, `PREDICT`, `JUSTIFY`, `EVALUATE`, `SYNTHESIZE`). |
| **Typed Relationships** | Only raw string `"PREREQUISITE_OF"`. | Define `RelationshipType` enum (`PREREQUISITE_OF`, `DEPENDS_ON`, `PART_OF`, `RELATED_TO`, `CONTRASTS_WITH`, `GENERALIZES_TO`, `SPECIALIZES_TO`, `CAUSES`, `REQUIRES`, `EXAMPLE_OF`). |
| **Expected Evidence Requirements** | Unstructured strings in test fixtures. | Introduce `ExpectedEvidenceRequirement` with `evidence_id`, `objective_id`, `description`, `evidence_type` (`DEFINITION`, `MECHANISM`, `REASONING`, `EXAMPLE`, `APPLICATION`, etc.), `essential`, `acceptance_criteria`. |
| **Concept Constraints** | Raw strings only. | Introduce `ConceptConstraint` specifying conditions, invariants, and boundaries. |
| **Graph Validation & Cycle Detection** | Only strips self-loops; fails to detect multi-node prerequisite cycles. | Implement rigorous Tarjan's / Kahn's algorithm cycle detection on prerequisite DAG, topological sorting, transitive prerequisite computation. |
| **Token-Efficient Context Extraction** | Sends whole model or minimal node. | Implement `extract_assessment_subgraph(concept_id)` and `summarize_for_prompt()` extracting compact relevant subgraphs without full graph token bloat. |
| **Answer Intelligence Integration** | Answer Intelligence constructs expected evidence ad-hoc. | Wire active concept's `LearningObjective` and `ExpectedEvidenceRequirement` directly into `ExpectedEvidence(core_components=..., common_misconceptions=...)`. |
| **Arbitrary Topic Support** | Verified only on standard CS topics. | Add test suites covering Non-CS topics (Economics, Biology, Physics, Philosophy, Medicine). |

---

## 4. Architectural Boundaries & Non-Goals

1. **`LearningAssessment` Remains Canonical:** The Concept Model specifies *what* to assess; Answer Intelligence evaluates *how well* the learner understands it.
2. **`MasteryGate` Remains Sole Authority:** The Concept Model never grants mastery. Mastery requires evidence verified through `MasteryGate`.
3. **No Database Coupling:** Zero ORM models or database sessions in `backend/app/ai`. Persistence is handled cleanly via `StateUpdates` in `engine.py`.
4. **Provider Abstraction:** Dynamic model generation uses `BaseAIProvider.generate_structured()`, mockable and testable offline.

---

## 5. Implementation Roadmap & Commit Boundaries

- **Commit 1:** `docs(ai): audit concept modeling architecture` (This document)
- **Commit 2:** `feat(ai): define concept model and learning objective contracts` (Pydantic schemas, enums, backward compatibility)
- **Commit 3:** `feat(ai): add dynamic topic concept model generation` (Prompt engineering, provider-independent generator, fallback)
- **Commit 4:** `feat(ai): validate concept relationships and prerequisites` (Structural validation, prerequisite cycle detection, topological sort, graph traversal utilities)
- **Commit 5:** `feat(ai): integrate concept models with learning assessment` (Objective-to-evidence wiring, question context integration)
- **Commit 6:** `feat(ai): add concept model session lifecycle support` (Sub-graph context extraction, session state reuse, token efficiency)
- **Commit 7:** `test(ai): validate concept model generation and assessment integration` (Comprehensive unit, graph, mock LLM, Non-CS topics, and regression tests)
- **Commit 8:** `docs(ai): document milestone d concept model` (Final report & representative outputs)
