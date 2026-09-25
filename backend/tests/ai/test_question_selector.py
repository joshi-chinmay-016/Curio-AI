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
