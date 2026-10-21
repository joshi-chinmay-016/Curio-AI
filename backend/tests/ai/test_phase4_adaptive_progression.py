"""
Phase 4 Deterministic Test Suite: Adaptive Difficulty Progression & Evidence-Driven Question Strategies.
Tests Scenarios 1-22 and Multi-Turn Sequences A, B, C, D without live LLM or external databases.
"""
from typing import List, Optional
import uuid
import pytest

from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.learner_model import LearnerModel
from backend.app.ai.question_generator import QuestionGenerator
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.question_validator import enforce_single_student_question
from backend.app.ai.answer_intelligence.schemas import (
    CorrectnessLevel,
    LearningAssessment,
    RelevanceLevel,
)
from backend.app.ai.schemas import (
    AIContext,
    ChatMessage,
    ConceptModel,
    ConceptNode,
    LearningDecision,
    LearningObjective,
    Mode,
    ObjectiveType,
    QuestionCandidate,
    QuestionSpecification,
    SessionState,
    Strategy,
    TurnEvaluation,
)
from backend.app.schemas.common import InputType, LearningMode


def make_context(
    mode: Mode = Mode.STUDENT,
    difficulty: int = 1,
    topic: str = "binary_search",
    active_concept: str = "binary_search",
    recent_strategies: Optional[List[Strategy]] = None,
    user_msg: str = "Hello",
) -> AIContext:
    history = (
        [ChatMessage(sender="USER", content=user_msg, input_type=InputType.TEXT)]
        if user_msg
        else []
    )
    state = SessionState(
        session_id="test-session",
        current_mode=mode,
        current_difficulty=difficulty,
        understanding_confidence=0.5,
        active_concept=active_concept,
        recent_strategy_history=recent_strategies or [],
    )
    return AIContext(
        session_id=uuid.uuid4(),
        topic=topic,
        current_mode=mode,
        difficulty=difficulty,
        active_concept=active_concept,
        current_state=state,
        history=history,
    )


def make_eval(
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
    )


def make_model() -> tuple[ConceptModel, LearnerModel]:
    concepts = [
        ConceptNode(id="bs_definition", name="Binary Search Definition", difficulty_level=1, prerequisites=[]),
        ConceptNode(id="bs_mechanism", name="Two Pointer Mechanism", difficulty_level=2, prerequisites=["bs_definition"]),
        ConceptNode(id="bs_application", name="Searching Rotated Array", difficulty_level=3, prerequisites=["bs_mechanism"]),
        ConceptNode(id="bs_edge_case", name="Integer Overflow Midpoint", difficulty_level=4, prerequisites=["bs_mechanism"]),
        ConceptNode(id="bs_synthesis", name="Comparison with Hash Tables", difficulty_level=5, prerequisites=["bs_application", "bs_edge_case"]),
    ]
    c_model = ConceptModel(topic="binary_search", concepts=concepts)
    l_model = LearnerModel(session_id="test-session", user_id="u1", topic="binary_search")
    return c_model, l_model


# ==============================================================================
# SECTION 9: DIFFICULTY PROGRESSION (Scenarios 1 - 8)
# ==============================================================================

def test_scenario_1_unassessed_concept_starts_at_foundation():
    """1. A new or unassessed concept starts with an appropriate foundational question."""
    engine = DecisionEngine()
    context = make_context(difficulty=1, user_msg="")
    evaln = make_eval()
    decision = engine.decide(context, evaln)
    assert decision.strategy == Strategy.ASK_FOUNDATION
    assert decision.difficulty == 1

    selector = QuestionSelector()
    c_model, l_model = make_model()
    spec = selector.select_question_specification(
        concept_model=c_model,
        learner_model=l_model,
        current_difficulty=decision.difficulty,
        current_objective=None,
        latest_interpretation=None,
        latest_evaluation=None,
        strategy=decision.strategy,
    )
    assert spec.difficulty == 1
    assert spec.learning_objective.objective_type == ObjectiveType.UNDERSTAND_DEFINITION


def test_scenario_2_correct_but_incomplete_blocks_progression():
    """2. A correct but incomplete answer (completeness < 0.70) does not cause unjustified progression."""
    engine = DecisionEngine()
    context = make_context(difficulty=2, user_msg="You divide the array in half.")
    # High correctness, but low completeness (0.50)
    evaln = make_eval(correctness=0.85, completeness=0.50, depth=0.65)
    decision = engine.decide(context, evaln)

    # Difficulty must remain 2 (not advance to 3)
    assert decision.difficulty == 2
    assert decision.strategy == Strategy.DEPTH_EXPANSION


def test_scenario_3_vague_answer_triggers_focused_followup():
    """3. A vague answer triggers a focused follow-up and blocks progression."""
    engine = DecisionEngine()
    context = make_context(difficulty=2, user_msg="It just searches things fast.")
    # Vague explanation: depth < 0.60
    evaln = make_eval(correctness=0.60, completeness=0.40, depth=0.35)
    decision = engine.decide(context, evaln)

    assert decision.difficulty == 2
    assert decision.strategy == Strategy.PROBE_HOW
    assert "mechanism" in decision.reason.lower() or "how" in decision.reason.lower()


def test_scenario_4_clear_mechanism_explanation_justifies_progression():
    """4. A clear explanation of a mechanism justifies bounded progression (+1)."""
    engine = DecisionEngine()
    context = make_context(difficulty=2, user_msg="We compute mid = low + (high-low)//2, compare, and adjust bounds.")
    # Strong answer: high correctness, completeness, and depth with no misconceptions
    evaln = make_eval(correctness=0.90, completeness=0.85, depth=0.80, stuck_prob=0.0)
    decision = engine.decide(context, evaln)

    assert decision.difficulty == 3
    assert decision.strategy == Strategy.REQUEST_EXAMPLE
    assert "application" in decision.reason.lower() or "example" in decision.reason.lower()


def test_scenario_5_misconception_blocks_progression():
    """5. A misconception blocks premature advancement and triggers targeted resolution."""
    engine = DecisionEngine()
    context = make_context(difficulty=2, user_msg="It works on any random unsorted list.")
    evaln = make_eval(
        correctness=0.45,
        completeness=0.70,
        depth=0.60,
        misconceptions=["binary search operates on unsorted collections"],
    )
    decision = engine.decide(context, evaln)

    # Difficulty must not increase
    assert decision.difficulty == 2
    assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION
    assert "misconception" in decision.reason.lower()


def test_scenario_6_strong_explanation_advances_through_tiers():
    """6. A strong explanation can lead to application, edge cases, or synthesis at the appropriate tier."""
    engine = DecisionEngine()

    # Tier 2 -> 3
    ctx2 = make_context(difficulty=2, user_msg="Mechanism explained thoroughly.")
    dec2 = engine.decide(ctx2, make_eval(correctness=0.90, completeness=0.85, depth=0.85))
    assert dec2.difficulty == 3
    assert dec2.strategy == Strategy.REQUEST_EXAMPLE

    # Tier 3 -> 4
    ctx3 = make_context(difficulty=3, user_msg="Applied to log file search successfully.")
    dec3 = engine.decide(ctx3, make_eval(correctness=0.92, completeness=0.88, depth=0.85))
    assert dec3.difficulty == 4
    assert dec3.strategy == Strategy.TEST_EDGE_CASE

    # Tier 4 -> 5 (Probing edge cases at level 4)
    ctx4 = make_context(difficulty=4, user_msg="Handled duplicates and overflow bounds cleanly.")
    dec4 = engine.decide(ctx4, make_eval(correctness=0.95, completeness=0.90, depth=0.90))
    assert dec4.difficulty == 5
    assert dec4.strategy == Strategy.TEST_EDGE_CASE

    # Tier 5 (Probing synthesis at level 5)
    ctx5 = make_context(difficulty=5, user_msg="Comparison with hash tables and trade-offs.")
    dec5 = engine.decide(ctx5, make_eval(correctness=0.95, completeness=0.90, depth=0.90))
    assert dec5.difficulty == 5
    assert dec5.strategy == Strategy.CONNECT_CONCEPTS


def test_scenario_7_missing_or_contradictory_evidence_is_conservative():
    """7. Missing or contradictory assessment evidence results in a conservative decision."""
    engine = DecisionEngine()
    context = make_context(difficulty=3, user_msg="Um maybe?")
    # Contradictory: high stuck probability with nominal correctness
    evaln = make_eval(correctness=0.65, completeness=0.30, depth=0.30, stuck_prob=0.80)
    decision = engine.decide(context, evaln)

    # Conservative: difficulty drops or stays bounded, does NOT advance
    assert decision.difficulty <= 3
    assert decision.difficulty == 2  # Regresses due to stuck/weak evidence


def test_scenario_8_irrelevant_answer_does_not_falsely_increase_mastery():
    """8. An unrelated or irrelevant user answer does not falsely increase mastery."""
    engine = DecisionEngine()
    context = make_context(difficulty=2, user_msg="I like pizza.")
    evaln = make_eval(correctness=0.10, completeness=0.0, depth=0.0, relevance=0.0)
    decision = engine.decide(context, evaln)

    # Master/difficulty must NOT increase on irrelevant answers
    assert decision.difficulty <= context.difficulty
    assert decision.confidence <= context.current_state.understanding_confidence


# ==============================================================================
# SECTION 9: STRATEGY SELECTION (Scenarios 9 - 15)
# ==============================================================================

def test_scenario_9_all_eight_strategies_selectable_by_evidence():
    """9. Each of the eight strategies can be selected when its intended evidence is present."""
    engine = DecisionEngine()

    # 1. CLARIFY_TERM
    d1 = engine.decide(make_context(difficulty=1), make_eval(undefined_terms=["monotonicity"]))
    assert d1.strategy == Strategy.CLARIFY_TERM

    # 2. PROBE_WHY
    d2 = engine.decide(make_context(difficulty=2), make_eval(correctness=0.75, completeness=0.75, depth=0.65, recommended_strategy=Strategy.PROBE_WHY))
    assert d2.strategy == Strategy.PROBE_WHY

    # 3. PROBE_HOW
    d3 = engine.decide(make_context(difficulty=1), make_eval(correctness=0.55, completeness=0.45, depth=0.40, recommended_strategy=Strategy.PROBE_HOW))
    assert d3.strategy == Strategy.PROBE_HOW

    # 4. REQUEST_EXAMPLE
    d4 = engine.decide(make_context(difficulty=2), make_eval(correctness=0.88, completeness=0.80, depth=0.75))
    assert d4.strategy == Strategy.REQUEST_EXAMPLE

    # 5. TEST_EDGE_CASE
    d5 = engine.decide(make_context(difficulty=3), make_eval(correctness=0.90, completeness=0.85, depth=0.80))
    assert d5.strategy == Strategy.TEST_EDGE_CASE

    # 6. CHALLENGE_ASSUMPTION
    d6 = engine.decide(make_context(difficulty=3), make_eval(recommended_strategy=Strategy.CHALLENGE_ASSUMPTION))
    assert d6.strategy == Strategy.CHALLENGE_ASSUMPTION

    # 7. CONNECT_CONCEPTS
    d7 = engine.decide(make_context(difficulty=5), make_eval(correctness=0.92, completeness=0.88, depth=0.85))
    assert d7.strategy == Strategy.CONNECT_CONCEPTS

    # 8. DEPTH_EXPANSION
    d8 = engine.decide(make_context(difficulty=2), make_eval(correctness=0.72, completeness=0.55, depth=0.60))
    assert d8.strategy == Strategy.DEPTH_EXPANSION


def test_scenario_10_selected_strategy_changes_downstream_objective_meaningfully():
    """10. Each selected strategy changes the downstream objective or question specification meaningfully."""
    selector = QuestionSelector()
    c_model, l_model = make_model()

    mappings = [
        (Strategy.CLARIFY_TERM, ObjectiveType.UNDERSTAND_DEFINITION),
        (Strategy.PROBE_HOW, ObjectiveType.UNDERSTAND_MECHANISM),
        (Strategy.PROBE_WHY, ObjectiveType.UNDERSTAND_CAUSAL_RELATION),
        (Strategy.REQUEST_EXAMPLE, ObjectiveType.APPLY_CONCEPT),
        (Strategy.TEST_EDGE_CASE, ObjectiveType.HANDLE_EDGE_CASE),
        (Strategy.CHALLENGE_ASSUMPTION, ObjectiveType.HANDLE_EDGE_CASE),
        (Strategy.CONNECT_CONCEPTS, ObjectiveType.SYNTHESIZE_CONCEPTS),
        (Strategy.DEPTH_EXPANSION, ObjectiveType.UNDERSTAND_MECHANISM),
    ]

    for strat, expected_obj in mappings:
        spec = selector.select_question_specification(
            concept_model=c_model,
            learner_model=l_model,
            current_difficulty=3,
            current_objective=None,
            latest_interpretation=None,
            latest_evaluation=None,
            strategy=strat,
            strategy_reason=f"Testing {strat.value}",
        )
        assert spec.learning_objective.objective_type == expected_obj, f"Failed for {strat}"
        assert strat.value in spec.reason or "Testing" in spec.reason


def test_scenario_11_clarify_term_preserved_despite_repetition_history():
    """11. An undefined term is clarified even when recent strategy history contains CLARIFY_TERM."""
    engine = DecisionEngine()
    context = make_context(difficulty=1, recent_strategies=[Strategy.CLARIFY_TERM])
    evaln = make_eval(undefined_terms=["invariance"])
    decision = engine.decide(context, evaln)

    # Must NOT suppress CLARIFY_TERM while terms remain undefined
    assert decision.strategy == Strategy.CLARIFY_TERM
    assert decision.active_concept == "invariance"


def test_scenario_12_active_misconception_not_ignored_for_variety():
    """12. An active misconception is not ignored merely to vary strategies."""
    engine = DecisionEngine()
    context = make_context(difficulty=2, recent_strategies=[Strategy.CHALLENGE_MISCONCEPTION])
    evaln = make_eval(misconceptions=["binary search operates on unsorted lists"])
    decision = engine.decide(context, evaln)

    assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION
    assert "misconception" in decision.reason.lower()


def test_scenario_13_strategy_anti_repetition_avoids_consecutive_probe():
    """13. Strategy anti-repetition avoids consecutive repetition of probing strategies."""
    engine = DecisionEngine()

    # Repeated PROBE_WHY shifts to PROBE_HOW
    ctx_why = make_context(difficulty=2, recent_strategies=[Strategy.PROBE_WHY])
    d_why = engine.decide(ctx_why, make_eval(correctness=0.75, completeness=0.75, depth=0.65, recommended_strategy=Strategy.PROBE_WHY))
    assert d_why.strategy == Strategy.PROBE_HOW

    # Repeated PROBE_HOW shifts to VERIFY_UNDERSTANDING
    ctx_how = make_context(difficulty=2, recent_strategies=[Strategy.PROBE_HOW])
    d_how = engine.decide(ctx_how, make_eval(correctness=0.60, completeness=0.50, depth=0.45, recommended_strategy=Strategy.PROBE_HOW))
    assert d_how.strategy == Strategy.VERIFY_UNDERSTANDING


def test_scenario_14_repeated_strategy_allowed_for_unresolved_need():
    """14. Repeated use of a strategy is allowed when justified by an unresolved critical need."""
    engine = DecisionEngine()
    # Misconception remains unresolved
    ctx = make_context(difficulty=2, recent_strategies=[Strategy.CHALLENGE_MISCONCEPTION])
    evaln = make_eval(misconceptions=["still believes it works on unsorted lists"])
    decision = engine.decide(ctx, evaln)
    assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION


def test_scenario_15_strategy_reason_agrees_with_action():
    """15. The selected strategy's reason agrees with the evidence and actual action taken."""
    engine = DecisionEngine()
    ctx = make_context(difficulty=3)
    evaln = make_eval(correctness=0.90, completeness=0.85, depth=0.85)
    decision = engine.decide(ctx, evaln)
    assert decision.strategy == Strategy.TEST_EDGE_CASE
    assert "edge case" in decision.reason.lower() or "boundary" in decision.reason.lower()


# ==============================================================================
# SECTION 9: QUESTION INTEGRITY & COMPATIBILITY (Scenarios 16 - 22)
# ==============================================================================

def test_scenario_16_single_question_invariant_enforced():
    """16. Student Mode still returns exactly one independently answerable question per turn."""
    candidate_text = "I see! What is the time complexity of binary search? Also how does it work?"
    obj = LearningObjective(
        concept_id="binary_search",
        objective_type=ObjectiveType.UNDERSTAND_MECHANISM,
        difficulty=2,
        reason="Check mechanism",
        evidence_expected="Explains mechanism",
    )
    spec = QuestionSpecification(
        target_concept="binary_search",
        learning_objective=obj,
        difficulty=2,
        reason="Check mechanism",
        evidence_expected="Explains mechanism",
        generation_constraints=[],
    )
    res = enforce_single_student_question(candidate_text, spec)
    assert res.count("?") == 1


def test_scenario_17_no_answer_leakage():
    """17. No answer leakage or lecturing in generated fallback questions."""
    for obj_type in ObjectiveType:
        obj = LearningObjective(
            concept_id="binary_search",
            objective_type=obj_type,
            difficulty=3,
            reason="Check objective",
            evidence_expected="Learner explains",
        )
        spec = QuestionSpecification(
            target_concept="binary_search",
            learning_objective=obj,
            difficulty=3,
            reason="Check objective",
            evidence_expected="Learner explains",
            generation_constraints=[],
        )
        fallback = QuestionGenerator.construct_specification_fallback(spec)
        assert fallback.question_text.count("?") == 1
        # Student voice check
        assert not any(lecture_word in fallback.question_text.lower() for lecture_word in ["remember that", "you must know that", "the answer is"])


def test_scenario_18_fallback_questions_relevant_to_selected_objective():
    """18. Generated and fallback questions remain relevant to the selected objective."""
    obj = LearningObjective(
        concept_id="hash_table",
        objective_type=ObjectiveType.SYNTHESIZE_CONCEPTS,
        difficulty=5,
        reason="Compare trade-offs",
        evidence_expected="Analyzes trade-offs",
    )
    spec = QuestionSpecification(
        target_concept="hash_table",
        learning_objective=obj,
        difficulty=5,
        reason="Compare trade-offs",
        evidence_expected="Analyzes trade-offs",
        generation_constraints=[],
    )
    fallback = QuestionGenerator.construct_specification_fallback(spec)
    assert "hash table" in fallback.question_text.lower()
    assert "trade-off" in fallback.question_text.lower() or "coordinate" in fallback.question_text.lower()


def test_scenario_19_assessment_propagation_and_misconception_count_sync():
    """19. Assessment propagation and misconception count synchronization continue to work."""
    from backend.app.ai.learner_model import LearnerModelManager
    l_model = LearnerModel(session_id="test-session", user_id="u1", topic="binary_search")
    lm_mgr = LearnerModelManager(l_model)
    evaln = make_eval(misconceptions=["unsorted array supported"])

    # Update misconception counts
    lm_mgr.update_from_evaluation("binary_search", evaln)
    counts = lm_mgr.export_misconception_counts_dict()
    assert counts.get("binary_search", 0) >= 1


def test_scenario_20_session_restoration_and_legacy_state_safe():
    """20. Session restoration and legacy state inputs remain safe."""
    engine = DecisionEngine()
    legacy_state = SessionState(
        session_id="legacy-session",
        current_mode=Mode.STUDENT,
        current_difficulty=1,
    )
    ctx = AIContext(
        session_id=uuid.uuid4(),
        topic="binary_search",
        current_mode=Mode.STUDENT,
        difficulty=1,
        active_concept=None,
        current_state=legacy_state,
        history=[],
    )
    evaln = make_eval()
    decision = engine.decide(ctx, evaln)
    assert decision.next_mode == Mode.STUDENT
    assert decision.difficulty >= 1


def test_scenario_21_teacher_and_evaluator_regression():
    """21. Teacher Mode and Evaluator Mode behavior unchanged."""
    engine = DecisionEngine()
    # Teacher mode: explicit stuck signal triggers TEACH_GAP
    ctx_teacher = make_context(mode=Mode.TEACHER, difficulty=2, user_msg="I don't know, please teach me.")
    evaln = make_eval(correctness=0.0, completeness=0.0, depth=0.0, stuck_prob=0.9)
    dec_teacher = engine.decide(ctx_teacher, evaln)
    assert dec_teacher.next_mode == Mode.TEACHER
    assert dec_teacher.strategy == Strategy.TEACH_GAP


def test_scenario_22_termination_and_interruption_intact():
    """22. Existing termination and interruption behavior remains intact."""
    engine = DecisionEngine()
    ctx = make_context(difficulty=3, user_msg="Understood completely.")
    ctx.current_state.understanding_confidence = 0.85
    evaln = make_eval(correctness=0.95, completeness=0.90, depth=0.90)
    decision = engine.decide(ctx, evaln)
    assert decision.should_offer_termination is True


# ==============================================================================
# SECTION 10: SIMULATED MULTI-TURN SEQUENCES (Sequences A, B, C, D)
# ==============================================================================

def test_sequence_a_progressive_understanding():
    """
    Sequence A — Progressive understanding:
    1. Initial definition turn (difficulty 1, ASK_FOUNDATION).
    2. Partial answer triggers focused follow-up (PROBE_HOW / VERIFY).
    3. Improved mechanism explanation recognized -> difficulty advances to 2/3.
    4. Strong application answer advances to application/edge case.
    """
    engine = DecisionEngine()
    c_model, l_model = make_model()
    selector = QuestionSelector()

    # Turn 1: Initial definition
    ctx1 = make_context(difficulty=1, user_msg="")
    d1 = engine.decide(ctx1, make_eval())
    assert d1.strategy == Strategy.ASK_FOUNDATION
    assert d1.difficulty == 1

    spec1 = selector.select_question_specification(
        concept_model=c_model,
        learner_model=l_model,
        current_difficulty=d1.difficulty,
        current_objective=None,
        latest_interpretation=None,
        latest_evaluation=None,
        strategy=d1.strategy,
    )
    assert spec1.learning_objective.objective_type == ObjectiveType.UNDERSTAND_DEFINITION

    # Turn 2: Partial answer
    ctx2 = make_context(difficulty=1, recent_strategies=[d1.strategy], user_msg="It finds items by halving.")
    eval2 = make_eval(correctness=0.65, completeness=0.50, depth=0.45)
    d2 = engine.decide(ctx2, eval2)
    assert d2.difficulty == 1  # Cannot advance on incomplete/partial
    assert d2.strategy in (Strategy.PROBE_HOW, Strategy.DEPTH_EXPANSION)

    # Turn 3: Mechanism explained clearly
    ctx3 = make_context(difficulty=1, recent_strategies=[d1.strategy, d2.strategy], user_msg="It checks array[mid]. If key < mid, high=mid-1; else low=mid+1.")
    eval3 = make_eval(correctness=0.88, completeness=0.80, depth=0.75)
    d3 = engine.decide(ctx3, eval3)
    assert d3.difficulty == 2  # Advances boundedly by 1
    assert d3.strategy in (Strategy.PROBE_HOW, Strategy.REQUEST_EXAMPLE)

    # Turn 4: Application scenario explained clearly
    ctx4 = make_context(difficulty=2, recent_strategies=[d1.strategy, d2.strategy, d3.strategy], user_msg="In a dictionary search or sorted log file timestamp lookup.")
    eval4 = make_eval(correctness=0.90, completeness=0.85, depth=0.80)
    d4 = engine.decide(ctx4, eval4)
    assert d4.difficulty == 3  # Advances to 3
    assert d4.strategy == Strategy.REQUEST_EXAMPLE


def test_sequence_b_persistent_misconception():
    """
    Sequence B — Persistent misconception:
    1. Student expresses a misconception.
    2. Curio selects CHALLENGE_MISCONCEPTION.
    3. Student repeats or fails to resolve the misconception.
    4. Curio persists in challenging/clarifying without premature advancement or suppression.
    """
    engine = DecisionEngine()

    # Turn 1: Misconception introduced
    ctx1 = make_context(difficulty=2, user_msg="We can just run binary search on any linked list or unsorted data.")
    eval1 = make_eval(correctness=0.40, completeness=0.50, depth=0.40, misconceptions=["binary search works on unsorted collections"])
    d1 = engine.decide(ctx1, eval1)
    assert d1.strategy == Strategy.CHALLENGE_MISCONCEPTION
    assert d1.difficulty == 2

    # Turn 2: Misconception persists despite challenge
    ctx2 = make_context(
        difficulty=2,
        recent_strategies=[d1.strategy],
        user_msg="Yeah, it just jumps to the middle element regardless of order.",
    )
    eval2 = make_eval(correctness=0.35, completeness=0.50, depth=0.40, misconceptions=["binary search works on unsorted collections"])
    d2 = engine.decide(ctx2, eval2)
    # Anti-repetition MUST NOT suppress active misconception!
    assert d2.strategy == Strategy.CHALLENGE_MISCONCEPTION
    assert d2.difficulty <= 2  # Difficulty strictly does not advance


def test_sequence_c_strong_but_incomplete_explanation():
    """
    Sequence C — Strong but incomplete explanation:
    1. Student gives a confident, largely correct answer that lacks an example or is incomplete.
    2. Curio selects REQUEST_EXAMPLE or DEPTH_EXPANSION.
    3. Curio does not jump to advanced synthesis solely because the answer sounds confident.
    """
    engine = DecisionEngine()
    ctx = make_context(difficulty=2, user_msg="Binary search operates in O(log n) time complexity by eliminating half the search space at each iteration.")
    # High correctness and depth, but lacks example (needs application)
    evaln = make_eval(correctness=0.82, completeness=0.65, depth=0.70)
    decision = engine.decide(ctx, evaln)

    # Incompleteness blocks jumping difficulty!
    assert decision.difficulty == 2
    assert decision.strategy in (Strategy.DEPTH_EXPANSION, Strategy.REQUEST_EXAMPLE)


def test_sequence_d_repetition_and_recovery():
    """
    Sequence D — Repetition and recovery:
    1. Strategy history contains a recent strategy.
    2. Curio avoids pointless consecutive repetition when an alternative exists.
    3. Final question validation enforces the hard one-question invariant.
    """
    engine = DecisionEngine()
    ctx = make_context(difficulty=2, recent_strategies=[Strategy.PROBE_WHY], user_msg="Because halving the range cuts it down exponentially.")
    # Candidate decision would naturally pick PROBE_WHY again for causal explanation
    evaln = make_eval(correctness=0.75, completeness=0.75, depth=0.65, recommended_strategy=Strategy.PROBE_WHY)
    decision = engine.decide(ctx, evaln)

    # Shifted away from PROBE_WHY to avoid consecutive repetition
    assert decision.strategy != Strategy.PROBE_WHY
    assert decision.strategy == Strategy.PROBE_HOW
    assert "consecutive strategy repetition" in decision.reason

    # Final enforcement validation
    obj = LearningObjective(
        concept_id="binary_search",
        objective_type=ObjectiveType.UNDERSTAND_MECHANISM,
        difficulty=2,
        reason=decision.reason,
        evidence_expected="Walks through steps",
    )
    spec = QuestionSpecification(
        target_concept="binary_search",
        learning_objective=obj,
        difficulty=2,
        reason=decision.reason,
        evidence_expected="Walks through steps",
        generation_constraints=[],
    )
    raw_response = "Great explanation! What is the exact loop condition? And what happens when low exceeds high?"
    cleaned = enforce_single_student_question(raw_response, spec)
    assert cleaned.count("?") == 1
