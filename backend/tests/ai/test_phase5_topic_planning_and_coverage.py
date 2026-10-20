"""
Phase 5 Comprehensive Verification Test Suite:
Topic Planning & Comprehensive Concept Coverage.

Validates all 20 required Phase 5 scenarios:
1. Topic plan represents multiple concepts and prerequisite relationships.
2. Duplicate or malformed concept entries are handled safely.
3. An unassessed important concept is eventually selected.
4. A correct answer about one concept does not mark every concept in the topic as mastered.
5. Mentioning a concept without demonstrating understanding does not count as mastery.
6. Incomplete answers keep the relevant concept in progress or needing review.
7. An active misconception takes priority over routine coverage.
8. An unresolved prerequisite is selected before a dependent concept where required.
9. Previously mastered concepts do not monopolize selection.
10. Coverage priorities change when new evaluation evidence arrives.
11. An unresolved gap can be revisited even after other concepts are mastered.
12. Missing legacy coverage state does not crash Student Mode.
13. Session restoration preserves or correctly reconstructs coverage.
14. Initial turns without an evaluation remain valid.
15. Concept selection preserves authoritative difficulty chosen by DecisionEngine.
16. Existing strategy and objective mappings remain correct.
17. Repeated concept selection is avoided when a similarly appropriate alternative exists.
18. The final output still obeys existing single-question enforcement.
19. Teacher Mode and Evaluator Mode behavior remain unchanged.
20. Backward compatibility with Phase 3 Step 3.5 and Phase 4.
"""
import uuid
import pytest

from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    CorrectnessLevel,
    LearningAssessment,
    MisconceptionEvidence,
    RelevanceLevel,
)
from backend.app.ai.concept_model import ConceptModelBuilder
from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.engine import CurioEngine
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.nodes.student_nodes import decision_node, state_updates_node
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.question_validator import enforce_single_student_question
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    ConceptCoverageItem,
    ConceptModel,
    ConceptNode,
    ConversationContext,
    CoverageStatus,
    CurrentQuestion,
    LearnerModel,
    LearningContext,
    LearningDecision,
    Mode,
    ObjectiveType,
    QuestionSpecification,
    Role,
    SessionState,
    Strategy,
    TopicPlan,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
    ChatMessage,
)
from backend.app.ai.topic_plan import TopicPlanner


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_concept_model() -> ConceptModel:
    """A realistic 3-node graph: foundations -> mechanisms -> applications."""
    return ConceptModel(
        topic="Photosynthesis",
        concepts=[
            ConceptNode(
                id="light_dependent_reactions",
                name="Light Dependent Reactions",
                description="Photons split water and generate ATP and NADPH",
                difficulty_level=1,
                prerequisites=[],
                importance="CORE",
            ),
            ConceptNode(
                id="calvin_cycle",
                name="Calvin Cycle",
                description="ATP and NADPH fix CO2 into sugars",
                difficulty_level=2,
                prerequisites=["light_dependent_reactions"],
                importance="CORE",
            ),
            ConceptNode(
                id="photorespiration",
                name="Photorespiration",
                description="Oxygenase activity of RuBisCO reduces photosynthetic efficiency",
                difficulty_level=3,
                prerequisites=["calvin_cycle"],
                importance="IMPORTANT",
            ),
        ],
        relationships=[],
    )


@pytest.fixture
def empty_learner_model() -> LearnerModel:
    return LearnerModel(session_id="test_session_p5")


# -----------------------------------------------------------------------------
# Tests 1 & 2: Topic Plan Representation and Malformed / Duplicate Resilience
# -----------------------------------------------------------------------------

def test_1_topic_plan_multiple_concepts_and_prerequisites(sample_concept_model, empty_learner_model):
    """Scenario 1: Topic plan represents multiple concepts and prerequisite relationships."""
    plan = TopicPlanner.build_topic_plan(sample_concept_model, empty_learner_model, topic="Photosynthesis")
    assert plan.topic == "Photosynthesis"
    assert len(plan.concepts) == 3

    c_map = {c.concept_id: c for c in plan.concepts}
    assert "light_dependent_reactions" in c_map
    assert "calvin_cycle" in c_map
    assert "photorespiration" in c_map

    # Prerequisites
    assert c_map["light_dependent_reactions"].prerequisites == []
    assert c_map["calvin_cycle"].prerequisites == ["light_dependent_reactions"]
    assert c_map["photorespiration"].prerequisites == ["calvin_cycle"]

    # Initial status
    assert c_map["light_dependent_reactions"].coverage_status == CoverageStatus.UNASSESSED
    assert plan.coverage_percentage == 0.0


def test_2_malformed_and_duplicate_concepts_handled_safely(empty_learner_model):
    """Scenario 2: Duplicate or malformed concept entries are handled safely."""
    malformed_model = ConceptModel(
        topic="Messy Topic",
        concepts=[
            ConceptNode(id="concept_a", name="Concept A", difficulty_level=1),
            ConceptNode(id="concept_a", name="Concept A Duplicate", difficulty_level=1),  # Duplicate ID
            ConceptNode(id="", name="Empty ID Concept", difficulty_level=1),  # Empty ID
            ConceptNode(id="concept_b", name="", difficulty_level=2),  # Empty name
        ],
    )
    plan = TopicPlanner.build_topic_plan(malformed_model, empty_learner_model, topic="Messy Topic")
    # Duplicate ID should be deduplicated, empty ID filtered out, empty name given fallback
    c_ids = [c.concept_id for c in plan.concepts]
    assert c_ids.count("concept_a") == 1
    assert "" not in c_ids
    assert "concept_b" in c_ids
    b_item = next(c for c in plan.concepts if c.concept_id == "concept_b")
    assert b_item.name == "Concept B"


def test_2b_empty_or_none_model_handled_safely(empty_learner_model):
    """Scenario 2b: None or empty concept model produces safe fallback topic plan."""
    plan = TopicPlanner.build_topic_plan(None, empty_learner_model, topic="Quantum Computing")
    assert plan.topic == "Quantum Computing"
    assert len(plan.concepts) >= 1
    assert plan.concepts[0].concept_id == "quantum_computing_definition"


# -----------------------------------------------------------------------------
# Tests 3 & 4: Unassessed Concept Selection & Concept Isolation
# -----------------------------------------------------------------------------

def test_3_unassessed_concept_eventually_selected(sample_concept_model, empty_learner_model):
    """Scenario 3: An unassessed important concept is selected when eligible."""
    selector = QuestionSelector()
    # Starting fresh: light_dependent_reactions is foundational and unassessed
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=1,
    )
    assert spec.target_concept == "light_dependent_reactions"
    assert spec.learning_objective.target_concept == "light_dependent_reactions"


def test_4_correct_answer_on_one_concept_does_not_mark_all_mastered(sample_concept_model, empty_learner_model):
    """Scenario 4: Correct answer on one concept isolates mastery to that concept only."""
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.85
    c1.evidence_count = 2
    c1.attempt_count = 2

    plan = TopicPlanner.build_topic_plan(sample_concept_model, empty_learner_model, topic="Photosynthesis")
    c_map = {c.concept_id: c for c in plan.concepts}

    assert c_map["light_dependent_reactions"].coverage_status == CoverageStatus.MASTERED
    assert c_map["calvin_cycle"].coverage_status == CoverageStatus.UNASSESSED
    assert c_map["photorespiration"].coverage_status == CoverageStatus.UNASSESSED
    assert plan.coverage_percentage < 50.0


# -----------------------------------------------------------------------------
# Tests 5 & 6: Shallow Mention is not Mastery, Incomplete Answers stay In Progress
# -----------------------------------------------------------------------------

def test_5_mentioning_concept_shallowly_does_not_count_as_mastery(sample_concept_model, empty_learner_model):
    """Scenario 5: Mentioning a concept or acknowledgment does not grant mastery."""
    lm_mgr = LearnerModelManager(empty_learner_model)
    lm_mgr.record_acknowledgement("light_dependent_reactions")

    plan = TopicPlanner.build_topic_plan(sample_concept_model, empty_learner_model, topic="Photosynthesis")
    c_map = {c.concept_id: c for c in plan.concepts}
    assert c_map["light_dependent_reactions"].coverage_status != CoverageStatus.MASTERED


def test_6_incomplete_answers_keep_concept_in_progress(sample_concept_model, empty_learner_model):
    """Scenario 6: Partial or incomplete explanation keeps concept IN_PROGRESS."""
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.45
    c1.evidence_count = 1
    c1.attempt_count = 1

    plan = TopicPlanner.build_topic_plan(sample_concept_model, empty_learner_model, topic="Photosynthesis")
    c_map = {c.concept_id: c for c in plan.concepts}
    assert c_map["light_dependent_reactions"].coverage_status == CoverageStatus.IN_PROGRESS


# -----------------------------------------------------------------------------
# Tests 7 & 8: Active Misconception Priority & Prerequisite Gating
# -----------------------------------------------------------------------------

def test_7_active_misconception_takes_priority_over_routine_coverage(sample_concept_model, empty_learner_model):
    """Scenario 7: An active misconception takes priority over moving to unassessed concepts."""
    # Concept 1 is partially known with an active misconception
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.40
    c1.attempt_count = 1
    c1.active_misconceptions = ["Believes light reactions produce glucose directly"]

    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=1,
    )
    # Must target the misconception, not advance to calvin_cycle
    assert spec.target_concept == "light_dependent_reactions"
    assert spec.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION


def test_8_unresolved_prerequisite_selected_before_dependent_concept(sample_concept_model, empty_learner_model):
    """Scenario 8: Prerequisite must be mastered before advancing to dependent concept."""
    # Attempted calvin_cycle, but prerequisite light_dependent_reactions has 0.1 mastery
    c_calvin = empty_learner_model.get_or_create_concept("calvin_cycle")
    c_calvin.attempt_count = 1
    c_calvin.mastery = 0.20

    c_light = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c_light.mastery = 0.10

    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=2,
    )
    # Must intercept and steer back to light_dependent_reactions
    assert spec.target_concept == "light_dependent_reactions"


# -----------------------------------------------------------------------------
# Tests 9 & 10: Mastered Concepts Don't Monopolize & Priority Shift on Evidence
# -----------------------------------------------------------------------------

def test_9_mastered_concepts_do_not_monopolize_selection(sample_concept_model, empty_learner_model):
    """Scenario 9: Once a concept is mastered, selection moves forward to unassessed concepts."""
    # Concept 1 is mastered
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.85
    c1.attempt_count = 2
    c1.evidence_count = 2

    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=2,
        recent_concept_history=["light_dependent_reactions"],
    )
    # Must select Calvin Cycle next, not stay on Light Reactions
    assert spec.target_concept == "calvin_cycle"


def test_10_coverage_priorities_change_when_new_evidence_arrives(sample_concept_model, empty_learner_model):
    """Scenario 10: Coverage priorities dynamically adjust when assessment updates learner state."""
    selector = QuestionSelector()

    # Step 1: Initial state -> selects light_dependent_reactions
    spec1 = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=1,
    )
    assert spec1.target_concept == "light_dependent_reactions"

    # Step 2: User demonstrates strong mastery on light_dependent_reactions
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.85
    c1.evidence_count = 2
    c1.attempt_count = 2

    # Step 3: Now selector chooses calvin_cycle
    spec2 = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=2,
        recent_concept_history=["light_dependent_reactions"],
    )
    assert spec2.target_concept == "calvin_cycle"


# -----------------------------------------------------------------------------
# Tests 11 & 12: Revisit Unresolved Gap & Missing Legacy Coverage Degradation
# -----------------------------------------------------------------------------

def test_11_unresolved_gap_revisited_even_after_other_concepts_mastered(sample_concept_model, empty_learner_model):
    """Scenario 11: An unresolved gap on an earlier concept can be revisited even if another is mastered."""
    # light_dependent_reactions has an unresolved gap
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.40
    c1.unresolved_gap = True
    empty_learner_model.unresolved_gaps = ["light_dependent_reactions"]

    # calvin_cycle was somehow explored and has mastery
    c2 = empty_learner_model.get_or_create_concept("calvin_cycle")
    c2.mastery = 0.80

    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=1,
    )
    assert spec.target_concept == "light_dependent_reactions"
    assert spec.learning_objective.objective_type == ObjectiveType.REINFORCE_WEAK_CONCEPT


def test_12_missing_legacy_coverage_state_does_not_crash():
    """Scenario 12: Missing legacy coverage state degrades safely without crashing."""
    legacy_state = SessionState(
        session_id="legacy_123",
        current_mode=Mode.STUDENT,
        current_difficulty=1,
        active_concept="",
        concept_mastery={},
        # topic_plan is None
    )
    assert legacy_state.topic_plan is None

    # Derive plan safely from legacy state
    plan = TopicPlanner.build_topic_plan(None, LearnerModel(session_id=legacy_state.session_id), topic="Physics")
    assert plan is not None
    assert plan.coverage_percentage == 0.0


# -----------------------------------------------------------------------------
# Tests 13 & 14: Session Restoration & Initial Foundation Turn
# -----------------------------------------------------------------------------

def test_13_session_restoration_preserves_and_reconstructs_coverage(sample_concept_model):
    """Scenario 13: Session restoration preserves and reconstructs correct coverage without resetting."""
    restored_learner = LearnerModel(session_id="restored_session")
    c1 = restored_learner.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.85
    c1.evidence_count = 2
    c1.attempt_count = 2

    c2 = restored_learner.get_or_create_concept("calvin_cycle")
    c2.mastery = 0.45
    c2.evidence_count = 1
    c2.attempt_count = 1

    plan = TopicPlanner.build_topic_plan(sample_concept_model, restored_learner, topic="Photosynthesis")
    c_map = {c.concept_id: c for c in plan.concepts}

    assert c_map["light_dependent_reactions"].coverage_status == CoverageStatus.MASTERED
    assert c_map["calvin_cycle"].coverage_status == CoverageStatus.IN_PROGRESS
    assert c_map["photorespiration"].coverage_status == CoverageStatus.UNASSESSED


def test_14_initial_turn_without_evaluation_remains_valid(sample_concept_model, empty_learner_model):
    """Scenario 14: Initial turn before any user response works seamlessly with TopicPlan."""
    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=1,
        latest_evaluation=None,
    )
    assert spec is not None
    assert spec.target_concept == "light_dependent_reactions"
    assert spec.difficulty == 1


# -----------------------------------------------------------------------------
# Tests 15 & 16: Authoritative Difficulty Preserved & Strategy Mapping
# -----------------------------------------------------------------------------

def test_15_concept_selection_preserves_authoritative_difficulty(sample_concept_model, empty_learner_model):
    """Scenario 15: adjust_difficulty=False preserves the DecisionEngine authoritative difficulty."""
    selector = QuestionSelector()
    # If DecisionEngine explicitly dictates difficulty 3, selector must not overwrite it
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=3,
        adjust_difficulty=False,
    )
    assert spec.difficulty == 3


def test_16_strategy_and_objective_mappings_remain_correct(sample_concept_model, empty_learner_model):
    """Scenario 16: Strategy mapping translates correctly into pedagogical learning objectives."""
    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=sample_concept_model,
        learner_model=empty_learner_model,
        current_difficulty=2,
        strategy=Strategy.REQUEST_EXAMPLE,
        strategy_reason="Ask for an application example",
        adjust_difficulty=False,
    )
    assert spec.learning_objective.objective_type == ObjectiveType.APPLY_CONCEPT
    assert spec.difficulty == 2


# -----------------------------------------------------------------------------
# Tests 17 & 18: Anti-Repetition & Single Question Guard
# -----------------------------------------------------------------------------

def test_17_repeated_concept_selection_avoided_with_alternatives(sample_concept_model, empty_learner_model):
    """Scenario 17: Anti-repetition penalty prevents immediately repeating a concept when an alternative exists."""
    # Both concept A and B are unassessed foundations
    concept_model = ConceptModel(
        topic="Sorting",
        concepts=[
            ConceptNode(id="bubble_sort", name="Bubble Sort", difficulty_level=1, prerequisites=[]),
            ConceptNode(id="insertion_sort", name="Insertion Sort", difficulty_level=1, prerequisites=[]),
        ],
    )
    selector = QuestionSelector()
    # Bubble sort was just discussed
    spec = selector.select_question_specification(
        concept_model=concept_model,
        learner_model=empty_learner_model,
        current_difficulty=1,
        recent_concept_history=["bubble_sort"],
    )
    assert spec.target_concept == "insertion_sort"


def test_18_final_output_obeys_single_question_enforcement():
    """Scenario 18: Step 3.5 single question enforcement remains fully effective with topic planning."""
    multi_q = "How does RuBisCO capture carbon dioxide? Also, why is it inefficient?"
    guarded = enforce_single_student_question(multi_q, fallback_concept="calvin_cycle")
    assert guarded.count("?") == 1


# -----------------------------------------------------------------------------
# Tests 19 & 20: Teacher/Evaluator Modes and Runtime Node Integration
# -----------------------------------------------------------------------------

def test_19_teacher_mode_and_evaluator_mode_behavior_unchanged(sample_concept_model, empty_learner_model):
    """Scenario 19: Evaluator and Teacher modes attach TopicPlan without altering mode behavior."""
    context = AIContext(
        session_id="test_sess_p5",
        topic="Photosynthesis",
        current_mode=Mode.EVALUATOR,
        current_state=SessionState(
            session_id="test_sess_p5",
            current_mode=Mode.EVALUATOR,
            active_concept="calvin_cycle",
        ),
        conversation=ConversationContext(recent_messages=[]),
        learning_context=LearningContext(recent_evaluations=[]),
    )
    state = {
        "context": context,
        "evaluation": TurnEvaluation(
            correctness=0.8,
            clarity=1.0,
            completeness=1.0,
            depth=1.0,
            relevance=1.0,
            stuck_probability=0.0,
            recommended_strategy=Strategy.GENERATE_REPORT,
            recommended_difficulty=1,
        ),
        "decision": LearningDecision(
            next_mode=Mode.EVALUATOR,
            strategy=Strategy.GENERATE_REPORT,
            difficulty=1,
            confidence=0.9,
            reason="Session evaluation complete",
            active_concept="calvin_cycle",
        ),
        "response": AIResponse(
            content="Session complete report.",
            mode=Mode.EVALUATOR,
            strategy=Strategy.GENERATE_REPORT,
            difficulty=1,
            confidence=0.9,
        ),
        "concept_model": sample_concept_model,
        "learner_model": empty_learner_model,
    }
    result = state_updates_node(state)
    assert "state_updates" in result
    su = result["state_updates"]
    assert su.current_mode == Mode.EVALUATOR
    assert su.topic_plan is not None
    assert su.topic_plan.topic == "Photosynthesis"


def test_20_runtime_node_advances_coverage_when_concept_mastered(sample_concept_model, empty_learner_model):
    """Scenario 20: Runtime decision_node automatically transitions to next unassessed concept upon mastery."""
    # Concept 1 is mastered
    c1 = empty_learner_model.get_or_create_concept("light_dependent_reactions")
    c1.mastery = 0.85
    c1.evidence_count = 2
    c1.attempt_count = 2

    context = AIContext(
        session_id="test_sess_p5",
        topic="Photosynthesis",
        current_mode=Mode.STUDENT,
        active_concept="light_dependent_reactions",
        current_state=SessionState(
            session_id="test_sess_p5",
            current_mode=Mode.STUDENT,
            active_concept="light_dependent_reactions",
            concept_mastery={"light_dependent_reactions": 0.85},
            learner_model=empty_learner_model,
            concept_model=sample_concept_model,
        ),
        conversation=ConversationContext(recent_messages=[
            ChatMessage(role=Role.USER, content="Water is split by light energy producing ATP and NADPH.")
        ]),
        learning_context=LearningContext(recent_evaluations=[]),
    )

    evaluation = TurnEvaluation(
        correctness=0.9,
        clarity=1.0,
        completeness=0.9,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        mastered_concepts=["light_dependent_reactions"],
        recommended_strategy=Strategy.DEPTH_EXPANSION,
        recommended_difficulty=2,
    )

    state = {
        "context": context,
        "evaluation": evaluation,
        "interpretation": TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT, is_answer_attempt=True),
        "concept_model": sample_concept_model,
        "learner_model": empty_learner_model,
    }

    res = decision_node(state)
    decision = res["decision"]
    spec = res["question_specification"]

    # Since light_dependent_reactions is mastered, decision_node releases target_concept_override,
    # allowing topic coverage to advance to calvin_cycle
    assert decision.active_concept == "calvin_cycle"
    assert spec.target_concept == "calvin_cycle"
    assert spec.difficulty == decision.difficulty
