"""
Phase 4.1 End-to-End Difficulty Pipeline Regression Tests.
Exercises the actual runtime integration boundary through decision_node()
in backend/app/ai/nodes/student_nodes.py to guarantee:
1. abs(final_difficulty - starting_difficulty) <= 1 per turn.
2. decision.difficulty and question_specification.difficulty always agree and lie in [1, 5].
3. Evaluation evidence drives single authoritative transition via DecisionEngine without double transition in QuestionSelector.
4. Strategy, objective, concept targeting, and standalone selector compatibility are preserved.
"""
import uuid
import pytest
from typing import List, Optional

from backend.app.ai.nodes.student_nodes import decision_node
from backend.app.ai.learner_model import LearnerModel
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.schemas import (
    AIContext,
    ChatMessage,
    ConceptModel,
    ConceptNode,
    ConceptRelationship,
    LearningDecision,
    LearningObjective,
    Mode,
    ObjectiveType,
    Role,
    SessionState,
    Strategy,
    TurnEvaluation,
    TurnInterpretation,
    TurnIntent,
)
from backend.app.schemas.common import InputType


def make_pipeline_context(
    difficulty: int = 1,
    topic: str = "binary_search",
    active_concept: str = "binary_search",
    user_msg: Optional[str] = "Let me explain the algorithm.",
    recent_strategies: Optional[List[Strategy]] = None,
) -> AIContext:
    history = (
        [ChatMessage(role=Role.USER, sender="USER", content=user_msg, input_type=InputType.TEXT)]
        if user_msg is not None
        else []
    )
    state = SessionState(
        session_id="pipeline-session",
        current_mode=Mode.STUDENT,
        current_difficulty=difficulty,
        understanding_confidence=0.5,
        active_concept=active_concept,
        recent_strategy_history=recent_strategies or [],
    )
    return AIContext(
        session_id=uuid.uuid4(),
        topic=topic,
        current_mode=Mode.STUDENT,
        difficulty=difficulty,
        active_concept=active_concept,
        current_state=state,
        history=history,
    )


def make_pipeline_eval(
    correctness: float = 0.5,
    clarity: float = 0.7,
    completeness: float = 0.5,
    depth: float = 0.5,
    relevance: float = 1.0,
    stuck_prob: float = 0.0,
    misconceptions: Optional[List[str]] = None,
    missing_concepts: Optional[List[str]] = None,
    undefined_terms: Optional[List[str]] = None,
    recommended_strategy: Optional[Strategy] = None,
    recommended_difficulty: Optional[int] = None,
    knowledge_gap: Optional[str] = None,
) -> TurnEvaluation:
    return TurnEvaluation(
        correctness=correctness,
        clarity=clarity,
        completeness=completeness,
        depth=depth,
        relevance=relevance,
        stuck_probability=stuck_prob,
        misconceptions=misconceptions or [],
        missing_concepts=missing_concepts or [],
        undefined_terms=undefined_terms or [],
        mastered_concepts=[],
        recommended_strategy=recommended_strategy or Strategy.VERIFY_UNDERSTANDING,
        recommended_difficulty=recommended_difficulty or 1,
        knowledge_gap=knowledge_gap,
    )


def make_pipeline_model() -> tuple[ConceptModel, LearnerModel]:
    c1 = ConceptNode(id="bs_definition", name="Binary Search Definition", difficulty_level=1, prerequisites=[])
    c2 = ConceptNode(id="middle_element", name="Middle Element Comparison", difficulty_level=2, prerequisites=["bs_definition"])
    c3 = ConceptNode(id="half_elimination", name="Halving Elimination Mechanism", difficulty_level=3, prerequisites=["middle_element"])
    c4 = ConceptNode(id="log_complexity", name="Logarithmic Time Complexity", difficulty_level=4, prerequisites=["half_elimination"])
    c5 = ConceptNode(id="trade_offs", name="Search Trade-offs and Constraints", difficulty_level=5, prerequisites=["log_complexity"])
    rels = [
        ConceptRelationship(source_concept_id="bs_definition", target_concept_id="middle_element"),
        ConceptRelationship(source_concept_id="middle_element", target_concept_id="half_elimination"),
        ConceptRelationship(source_concept_id="half_elimination", target_concept_id="log_complexity"),
        ConceptRelationship(source_concept_id="log_complexity", target_concept_id="trade_offs"),
    ]
    concept_model = ConceptModel(topic="binary_search", concepts=[c1, c2, c3, c4, c5], relationships=rels)
    learner_model = LearnerModel(session_id="pipeline-session")
    return concept_model, learner_model


def _run_decision_node(
    context: AIContext,
    evaluation: TurnEvaluation,
    concept_model: ConceptModel,
    learner_model: LearnerModel,
    interpretation: Optional[TurnInterpretation] = None,
):
    state = {
        "context": context,
        "evaluation": evaluation,
        "concept_model": concept_model,
        "learner_model": learner_model,
        "interpretation": interpretation or TurnInterpretation(intent=TurnIntent.UNKNOWN),
    }
    result = decision_node(state)
    return result["decision"], result.get("question_specification")


# =============================================================================
# Pipeline Integration Invariant Tests (Requirements 1-12)
# =============================================================================

def test_1_strong_answer_advances_at_most_one_level():
    """1. Strong answer: starting at difficulty 1, one turn can advance to at most 2; decision and spec agree."""
    start_diff = 1
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="Binary search repeatedly divides the search space in half by comparing the middle element.")
    ev = make_pipeline_eval(correctness=0.95, completeness=0.90, depth=0.85, stuck_prob=0.0)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1, f"Expected delta <= 1, got {decision.difficulty - start_diff}"
    assert decision.difficulty == 2
    assert spec is not None
    assert spec.difficulty == decision.difficulty
    assert 1 <= decision.difficulty <= 5
    assert 1 <= spec.difficulty <= 5


def test_2_weak_answer_regresses_at_most_one_level():
    """2. Weak answer: starting at difficulty 3, one turn can regress to at most 2; decision and spec agree."""
    start_diff = 3
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="I think it searches through elements and maybe halves something.")
    ev = make_pipeline_eval(correctness=0.35, completeness=0.35, depth=0.30, stuck_prob=0.30)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1, f"Expected delta <= 1, got {decision.difficulty - start_diff}"
    assert decision.difficulty == 2
    assert spec is not None
    assert spec.difficulty == decision.difficulty
    assert 1 <= decision.difficulty <= 5
    assert 1 <= spec.difficulty <= 5


def test_3_incomplete_answer_blocks_difficulty_increase():
    """3. Incomplete answer: difficulty does not increase when completeness fails advancement criteria (<0.70)."""
    start_diff = 2
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="It halves the list.")
    # High correctness but completeness 0.50 (< 0.70)
    ev = make_pipeline_eval(correctness=0.85, completeness=0.50, depth=0.70, stuck_prob=0.0)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1
    assert decision.difficulty == start_diff
    assert spec is not None
    assert spec.difficulty == decision.difficulty


def test_4_vague_answer_blocks_difficulty_increase():
    """4. Vague answer: difficulty does not increase when depth fails advancement criteria (<0.60)."""
    start_diff = 2
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="Binary search is fast and efficient for searching.")
    # High correctness and completeness, but depth 0.45 (< 0.60)
    ev = make_pipeline_eval(correctness=0.85, completeness=0.80, depth=0.45, stuck_prob=0.0)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1
    assert decision.difficulty == start_diff
    assert spec is not None
    assert spec.difficulty == decision.difficulty


def test_5_active_misconception_blocks_advancement():
    """5. Active misconception: difficulty does not increase while a blocking misconception remains unresolved."""
    start_diff = 2
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="It works on unsorted lists too.")
    ev = make_pipeline_eval(
        correctness=0.60,
        completeness=0.75,
        depth=0.70,
        stuck_prob=0.10,
        misconceptions=["Binary search does not require sorted data"],
    )
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1
    assert decision.difficulty <= start_diff
    assert spec is not None
    assert spec.difficulty == decision.difficulty
    assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION
    assert spec.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION


def test_6_off_topic_answer_no_unjustified_advancement():
    """6. Off-topic answer: no unjustified advancement occurs."""
    start_diff = 2
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="I enjoy eating pizza while coding.")
    ev = make_pipeline_eval(correctness=0.10, completeness=0.10, depth=0.10, relevance=0.10, stuck_prob=0.0)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1
    assert decision.difficulty == start_diff
    assert spec is not None
    assert spec.difficulty == decision.difficulty


def test_7_upper_boundary_clamping():
    """7. Upper boundary: difficulty cannot exceed 5 even on strong answers."""
    start_diff = 5
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="Comprehensive analysis of logarithmic trade-offs.")
    ev = make_pipeline_eval(correctness=0.95, completeness=0.95, depth=0.90, stuck_prob=0.0)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert abs(decision.difficulty - start_diff) <= 1
    assert decision.difficulty == 5
    assert spec is not None
    assert spec.difficulty == 5


def test_8_lower_boundary_clamping():
    """8. Lower boundary: difficulty cannot fall below 1 even on weak answers."""
    start_diff = 1
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="I don't know anything about this.")
    ev = make_pipeline_eval(correctness=0.10, completeness=0.10, depth=0.10, stuck_prob=0.80)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    # In student mode, if stuck_prob >= 0.75 and correctness < 0.5, DecisionEngine transitions to Teacher mode
    # In either mode, difficulty must be >= 1
    assert 1 <= decision.difficulty <= 5
    assert abs(decision.difficulty - start_diff) <= 1
    if spec is not None:
        assert spec.difficulty == decision.difficulty
        assert 1 <= spec.difficulty <= 5


def test_9_initial_turn_no_evaluation():
    """9. No-evaluation/initial turn: existing initial difficulty behavior remains correct (difficulty 1, ASK_FOUNDATION)."""
    ctx = make_pipeline_context(difficulty=1, user_msg=None)
    ev = make_pipeline_eval()
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert decision.difficulty == 1
    assert decision.strategy == Strategy.ASK_FOUNDATION
    assert spec is not None
    assert spec.difficulty == 1
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_DEFINITION


def test_10_strategy_preservation_and_objective_mapping():
    """10. Strategy preservation: intended strategy, rationale, and objective remain appropriate after fix."""
    start_diff = 1
    ctx = make_pipeline_context(difficulty=start_diff, user_msg="Binary search divides the sorted array at the midpoint.")
    ev = make_pipeline_eval(correctness=0.90, completeness=0.85, depth=0.80, stuck_prob=0.0)
    c_model, l_model = make_pipeline_model()

    decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

    assert decision.difficulty == 2
    assert decision.strategy == Strategy.PROBE_HOW
    assert spec is not None
    assert spec.difficulty == 2
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_MECHANISM
    assert "PROBE_HOW" in spec.reason or "demonstrated" in spec.reason


def test_11_question_selector_standalone_compatibility():
    """11. Selector compatibility: standalone use of QuestionSelector defaults to adjust_difficulty=True and preserves behavior."""
    selector = QuestionSelector()
    c_model, l_model = make_pipeline_model()
    node = c_model.concepts[0]
    state = l_model.get_or_create_concept(node.id)

    # Strong evaluation standalone
    ev_strong = make_pipeline_eval(correctness=0.95, completeness=0.90, depth=0.85, stuck_prob=0.0)
    spec_standalone = selector.select_question_specification(
        concept_model=c_model,
        learner_model=l_model,
        current_difficulty=1,
        latest_evaluation=ev_strong,
        target_concept_override=node.id,
    )
    # Default adjust_difficulty=True increments difficulty in standalone mode
    assert spec_standalone.difficulty == 2

    # With adjust_difficulty=False, difficulty stays at current_difficulty (1)
    spec_non_adjusted = selector.select_question_specification(
        concept_model=c_model,
        learner_model=l_model,
        current_difficulty=1,
        latest_evaluation=ev_strong,
        target_concept_override=node.id,
        adjust_difficulty=False,
    )
    assert spec_non_adjusted.difficulty == 1
    # Misconceptions from evaluation are still used even when adjust_difficulty=False
    ev_misc = make_pipeline_eval(correctness=0.5, misconceptions=["Midpoint formula overflow"])
    spec_misc = selector.select_question_specification(
        concept_model=c_model,
        learner_model=l_model,
        current_difficulty=2,
        latest_evaluation=ev_misc,
        target_concept_override=node.id,
        strategy=Strategy.CHALLENGE_MISCONCEPTION,
        adjust_difficulty=False,
    )
    assert spec_misc.difficulty == 2
    assert "Midpoint formula overflow" in spec_misc.evidence_expected


def test_12_multi_turn_progression_bounded_each_turn():
    """Multi-turn test: over 3 consecutive strong turns, difficulty advances exactly 1 level per turn (1 -> 2 -> 3 -> 4)."""
    c_model, l_model = make_pipeline_model()
    current_diff = 1
    recent_strats = []

    for expected_next_diff in [2, 3, 4]:
        ctx = make_pipeline_context(
            difficulty=current_diff,
            user_msg=f"Turn explanation at difficulty {current_diff}",
            recent_strategies=recent_strats,
        )
        ev = make_pipeline_eval(correctness=0.92, completeness=0.88, depth=0.80, stuck_prob=0.0)
        decision, spec = _run_decision_node(ctx, ev, c_model, l_model)

        assert abs(decision.difficulty - current_diff) <= 1, f"Failed at turn diff {current_diff}: jumped to {decision.difficulty}"
        assert decision.difficulty == expected_next_diff
        assert spec is not None
        assert spec.difficulty == expected_next_diff
        current_diff = decision.difficulty
        recent_strats.append(decision.strategy)
