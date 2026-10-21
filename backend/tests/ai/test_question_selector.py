"""
Unit tests for QuestionSelector (Phase E & F).
Verifies:
- Weak concepts are prioritized
- Missing prerequisite intercepts advanced concept
- Active misconception yields RESOLVE_MISCONCEPTION objective
- Difficulty transitions are bounded to [1, 5] and max delta +-1
- Generation constraints and expected evidence are preserved
"""
import pytest
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.schemas import (
    ConceptModel,
    ConceptNode,
    ConceptRelationship,
    ObjectiveType,
    TurnEvaluation,
    Strategy,
)


def _sample_concept_model():
    c1 = ConceptNode(id="sorted_data", name="Sorted Data Requirement", difficulty_level=1)
    c2 = ConceptNode(
        id="middle_element",
        name="Middle Element Comparison",
        prerequisites=["sorted_data"],
        difficulty_level=2,
    )
    c3 = ConceptNode(
        id="half_elimination",
        name="Halving Elimination Mechanism",
        prerequisites=["middle_element"],
        difficulty_level=3,
    )
    c4 = ConceptNode(
        id="log_complexity",
        name="Logarithmic Time Complexity",
        prerequisites=["half_elimination"],
        difficulty_level=4,
    )
    rels = [
        ConceptRelationship(source_concept_id="sorted_data", target_concept_id="middle_element"),
        ConceptRelationship(source_concept_id="middle_element", target_concept_id="half_elimination"),
        ConceptRelationship(source_concept_id="half_elimination", target_concept_id="log_complexity"),
    ]
    return ConceptModel(topic="Binary Search", concepts=[c1, c2, c3, c4], relationships=rels)


def test_question_selector_initial_turn():
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        current_difficulty=1,
    )

    # Initial turn should target the foundational concept
    assert spec.target_concept == "sorted_data"
    assert spec.difficulty == 1
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_DEFINITION
    assert len(spec.generation_constraints) > 0


def test_question_selector_misconception_priority():
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    # Record a misconception on middle_element
    state = learner_mgr.get_or_create_concept_state("middle_element")
    state.active_misconceptions.append("Checks elements sequentially if middle fails")
    state.unresolved_gap = True
    learner_mgr.model.unresolved_gaps.append("middle_element")

    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        current_difficulty=2,
    )

    assert spec.target_concept == "middle_element"
    assert spec.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION
    assert "Checks elements sequentially" in spec.reason


def test_question_selector_prerequisite_gap_interception():
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    # Suppose learner attempted half_elimination, but prerequisite sorted_data is weak (< 0.60)
    elim_state = learner_mgr.get_or_create_concept_state("half_elimination")
    elim_state.attempt_count = 1

    sorted_state = learner_mgr.get_or_create_concept_state("sorted_data")
    sorted_state.mastery = 0.20  # Weak prerequisite

    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        current_difficulty=3,
    )

    # Must steer back to prerequisite
    assert spec.target_concept == "sorted_data"
    assert "Prerequisite concept" in spec.reason


def test_question_selector_bounded_difficulty_increase():
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    # Satisfy sorted_data
    s1 = learner_mgr.get_or_create_concept_state("sorted_data")
    s1.mastery = 0.90

    # Strong turn evaluation
    strong_eval = TurnEvaluation(
        correctness=0.95,
        clarity=0.9,
        completeness=0.9,
        depth=0.9,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["sorted_data"],
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=2,
    )

    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        current_difficulty=1,
        latest_evaluation=strong_eval,
    )

    # Difficulty increased by exactly 1 level (from 1 to 2)
    assert spec.difficulty == 2
    assert spec.target_concept == "middle_element"


def test_question_selector_strategies_produce_intended_objectives():
    """Verify each supported pedagogical strategy maps to the correct ObjectiveType."""
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    # 1. CLARIFY_TERM -> UNDERSTAND_DEFINITION
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.CLARIFY_TERM,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_DEFINITION

    # 2. PROBE_WHY -> UNDERSTAND_CAUSAL_RELATION
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.PROBE_WHY,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_CAUSAL_RELATION

    # 3. PROBE_HOW -> UNDERSTAND_MECHANISM
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.PROBE_HOW,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_MECHANISM

    # 4. CHALLENGE_MISCONCEPTION -> RESOLVE_MISCONCEPTION
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.CHALLENGE_MISCONCEPTION,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION

    # 5a. PROBE_MISSING_CONCEPT (unassessed / new gap) -> VERIFY_GAP
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.PROBE_MISSING_CONCEPT,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.VERIFY_GAP

    # 5b. PROBE_MISSING_CONCEPT (demonstrated weakness / failed attempts) -> REINFORCE_WEAK_CONCEPT
    weak_state = learner_mgr.get_or_create_concept_state("sorted_data")
    weak_state.attempt_count = 2
    weak_state.mastery = 0.30
    weak_state.unresolved_gap = True
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.PROBE_MISSING_CONCEPT,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.REINFORCE_WEAK_CONCEPT

    # 6. VERIFY_UNDERSTANDING -> EXPLAIN_IN_OWN_WORDS
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=Strategy.VERIFY_UNDERSTANDING,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.EXPLAIN_IN_OWN_WORDS


def test_question_selector_preserves_decision_reason():
    """Verify decision.reason is faithfully preserved in spec.reason."""
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    custom_reason = "Detailed reasoning: student showed slight confusion on invariant boundary."
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="middle_element",
        strategy=Strategy.PROBE_WHY,
        strategy_reason=custom_reason,
    )
    assert spec.reason == custom_reason
    assert spec.learning_objective.reason == custom_reason


def test_question_selector_targeted_selection_preserves_active_misconception_evidence():
    """Verify targeted selection does not accidentally bypass relevant misconception signals."""
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    state = learner_mgr.get_or_create_concept_state("middle_element")
    state.active_misconceptions.append("Always takes index len//2 without checking bounds")

    # Probing middle_element without explicit CHALLENGE_MISCONCEPTION still detects the misconception
    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="middle_element",
        strategy=Strategy.PROBE_HOW,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION
    assert "Always takes index len//2 without checking bounds" in spec.evidence_expected


def test_question_selector_fallback_when_strategy_absent_or_unknown():
    """Verify that absent strategy safely uses existing difficulty-based fallback."""
    selector = QuestionSelector()
    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    spec = selector.select_question_specification(
        concept_model=model,
        learner_model=learner_mgr.model,
        target_concept_override="sorted_data",
        strategy=None,
        current_difficulty=1,
    )
    # Default diff 1 -> UNDERSTAND_DEFINITION
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_DEFINITION
    assert "Probing understanding of 'Sorted Data Requirement' at difficulty 1." in spec.reason


def test_decision_node_wires_evaluation_and_strategy_to_selector():
    """Verify decision_node passes evaluation, strategy, reason, and preserves target concept for VERIFY_UNDERSTANDING."""
    import uuid
    from backend.app.ai.nodes.student_nodes import decision_node
    from backend.app.ai.schemas import AIContext, ChatMessage, Role, SessionState

    model = _sample_concept_model()
    learner_mgr = LearnerModelManager()

    sess_id = uuid.uuid4()
    context = AIContext(
        session_id=sess_id,
        topic="Binary Search",
        current_mode="STUDENT",
        difficulty=2,
        active_concept="middle_element",
        conversation={"recent_messages": [ChatMessage(role=Role.USER, content="I divide the list and check the middle.")]},
        history=[ChatMessage(role=Role.USER, content="I divide the list and check the middle.")],
        current_state=SessionState(session_id=sess_id, active_concept="middle_element", understanding_confidence=0.5),
    )

    evaluation = TurnEvaluation(
        correctness=0.6,
        clarity=0.7,
        completeness=0.75,
        depth=0.85,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=Strategy.VERIFY_UNDERSTANDING,
        recommended_difficulty=2,
    )

    state = {
        "context": context,
        "evaluation": evaluation,
        "concept_model": model,
        "learner_model": learner_mgr.model,
    }

    result = decision_node(state)
    spec = result["question_specification"]

    assert spec is not None
    # Concept target should be preserved
    assert spec.target_concept == "middle_element"
    # Objective should be EXPLAIN_IN_OWN_WORDS for VERIFY_UNDERSTANDING
    assert spec.learning_objective.objective_type == ObjectiveType.EXPLAIN_IN_OWN_WORDS
    # Reason should be preserved from DecisionEngine
    assert result["decision"].reason in spec.reason
