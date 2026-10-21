import uuid
from backend.app.ai.schemas import AIContext, ChatMessage, TurnEvaluation
from backend.app.schemas.common import LearningMode, LearningStrategy, InputType
from backend.app.ai.decision_engine import decide_next_action

def create_context(mode: LearningMode, diff: int, user_msg: str) -> AIContext:
    history = [ChatMessage(sender="USER", content=user_msg, input_type=InputType.TEXT)]
    return AIContext(
        session_id=uuid.uuid4(),
        topic="Recursion",
        current_mode=mode,
        difficulty=diff,
        active_concept="Core Definition",
        history=history
    )

def test_scenario_1_correct_but_incomplete():
    # Topic = Recursion, Answer = A function calls itself.
    context = create_context(LearningMode.STUDENT, 1, "A function calls itself.")
    evaluation = TurnEvaluation(
        correctness=0.7,
        clarity=0.8,
        completeness=0.5,
        depth=0.5,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=["base case"],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.PROBE_MISSING_CONCEPT,
        recommended_difficulty=1
    )
    
    decision = decide_next_action(context, evaluation, 0, 1)
    
    # Expected: Stay in STUDENT, Probe missing concept
    assert decision.next_mode == LearningMode.STUDENT
    assert decision.strategy == LearningStrategy.PROBE_MISSING_CONCEPT
    assert decision.active_concept == "base case"

def test_scenario_2_user_stuck():
    # Answer = I don't know.
    context = create_context(LearningMode.STUDENT, 1, "I don't know.")
    evaluation = TurnEvaluation(
        correctness=0.0,
        clarity=0.0,
        completeness=0.0,
        depth=0.0,
        relevance=0.0,
        stuck_probability=0.9,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.TEACH_GAP,
        recommended_difficulty=1
    )
    
    decision = decide_next_action(context, evaluation, 0, 2)
    
    # Expected: Switch to TEACHER
    assert decision.next_mode == LearningMode.TEACHER
    assert decision.strategy == LearningStrategy.TEACH_GAP

def test_scenario_3_teacher_verified():
    # Teacher explained gap, user understood.
    context = create_context(LearningMode.TEACHER, 1, "The base case stops the loop.")
    evaluation = TurnEvaluation(
        correctness=0.9,
        clarity=0.9,
        completeness=0.9,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["base case"],
        recommended_strategy=LearningStrategy.RESTORE_INTERRUPTED_QUESTION,
        recommended_difficulty=1
    )
    
    decision = decide_next_action(context, evaluation, 1, 0)
    
    # Expected: Switch back to STUDENT, restore interrupted question
    assert decision.next_mode == LearningMode.STUDENT
    assert decision.should_restore_interrupted_question is True

def test_scenario_4_confidence_limit():
    # Confidence >= 0.75
    context = create_context(LearningMode.STUDENT, 3, "Detailed explanation...")
    evaluation = TurnEvaluation(
        correctness=1.0,
        clarity=1.0,
        completeness=1.0,
        depth=1.0,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.INCREASE_DIFFICULTY,
        recommended_difficulty=4
    )
    
    # Force confidence to be > 0.75 by passing high strong count
    decision = decide_next_action(context, evaluation, 10, 0)
    
    assert decision.confidence > 0.75
    assert decision.should_offer_termination is True
    assert decision.strategy == LearningStrategy.OFFER_TERMINATION


def test_confidence_below_threshold_does_not_offer_termination():
    # Confidence should be well below 0.75
    context = create_context(LearningMode.STUDENT, 1, "Basic answer.")
    evaluation = TurnEvaluation(
        correctness=0.7,
        clarity=0.7,
        completeness=0.5,
        depth=0.5,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.PROBE_WHY,
        recommended_difficulty=1
    )

    decision = decide_next_action(context, evaluation, 1, 0)

    assert decision.confidence < 0.75
    assert decision.should_offer_termination is False
    assert decision.strategy != LearningStrategy.OFFER_TERMINATION
    assert decision.next_mode == LearningMode.STUDENT


def test_confidence_exactly_at_threshold_offers_termination():
    # Construct exact 0.75 score:
    # concept_coverage (0.30 * 0.6) = 0.18
    # recent_answer_quality (0.25 * 0.8) = 0.20
    # difficulty_achievement (0.20 * (3 / 5.0)) = 0.12 (initial diff 2 + 1 = 3)
    # consistency (0.15 * 1.0) = 0.15 (streak of 5 gives consistency 1.0)
    # independent_correction (0.10 * 1.0) = 0.10
    # Total = 0.18 + 0.20 + 0.12 + 0.15 + 0.10 = 0.75
    context = create_context(LearningMode.STUDENT, 2, "A well-structured explanation.")
    evaluation = TurnEvaluation(
        correctness=0.8,
        clarity=1.0,
        completeness=0.6,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.INCREASE_DIFFICULTY,
        recommended_difficulty=3
    )

    decision = decide_next_action(context, evaluation, 5, 0)

    assert decision.confidence == 0.75
    assert decision.next_mode == LearningMode.STUDENT
    assert decision.should_offer_termination is True
    assert decision.strategy == LearningStrategy.OFFER_TERMINATION
    assert decision.reason == "Confidence reached 75% or higher. Offering session termination."


def test_student_mode_termination_behavior():
    # Verifies full decision contract when termination condition is met in STUDENT mode
    context = create_context(LearningMode.STUDENT, 4, "Comprehensive synthesis answer.")
    evaluation = TurnEvaluation(
        correctness=1.0,
        clarity=1.0,
        completeness=1.0,
        depth=1.0,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["recursion", "base case", "call stack"],
        recommended_strategy=LearningStrategy.INCREASE_DIFFICULTY,
        recommended_difficulty=5
    )

    decision = decide_next_action(context, evaluation, 6, 0)

    assert decision.next_mode == LearningMode.STUDENT
    assert decision.confidence >= 0.75
    assert decision.should_offer_termination is True
    assert decision.strategy == LearningStrategy.OFFER_TERMINATION
    assert "Confidence reached 75%" in decision.reason


def test_non_student_mode_does_not_offer_termination_teacher():
    # Even if answer quality was historically high, transitioning to TEACHER mode must never offer termination
    context = create_context(LearningMode.STUDENT, 3, "I don't know how this works, can you explain?")
    evaluation = TurnEvaluation(
        correctness=0.0,
        clarity=0.0,
        completeness=0.0,
        depth=0.0,
        relevance=0.0,
        stuck_probability=0.9,
        misconceptions=[],
        missing_concepts=["mechanism"],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.TEACH_GAP,
        recommended_difficulty=3
    )

    # Previously had strong answers, but now stuck
    decision = decide_next_action(context, evaluation, 8, 1)

    assert decision.next_mode == LearningMode.TEACHER
    assert decision.should_offer_termination is False
    assert decision.strategy == LearningStrategy.TEACH_GAP


def test_non_student_mode_does_not_offer_termination_evaluator():
    # EVALUATOR mode should compile report and never offer termination
    context = create_context(LearningMode.EVALUATOR, 3, "Session ended.")
    evaluation = TurnEvaluation(
        correctness=1.0,
        clarity=1.0,
        completeness=1.0,
        depth=1.0,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=LearningStrategy.GENERATE_REPORT,
        recommended_difficulty=3
    )

    decision = decide_next_action(context, evaluation, 10, 0)

    assert decision.next_mode == LearningMode.EVALUATOR
    assert decision.should_offer_termination is False
    assert decision.strategy == LearningStrategy.GENERATE_REPORT


def test_anti_repetition_alternates_repeated_probe_why():
    """Verify repeated PROBE_WHY shifts to PROBE_HOW when recent strategy history contains PROBE_WHY."""
    from backend.app.ai.decision_engine import DecisionEngine
    from backend.app.ai.schemas import SessionState, Strategy

    engine = DecisionEngine()
    context = create_context(LearningMode.STUDENT, 2, "It works because of caching.")
    context.current_state.recent_strategy_history = [Strategy.PROBE_WHY]

    evaluation = TurnEvaluation(
        correctness=0.75,
        clarity=0.8,
        completeness=0.7,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=2,
    )

    decision = engine.decide(context, evaluation)
    # Consecutive PROBE_WHY must shift to PROBE_HOW
    assert decision.strategy == Strategy.PROBE_HOW
    assert "avoid consecutive strategy repetition" in decision.reason


def test_anti_repetition_alternates_repeated_probe_how():
    """Verify repeated PROBE_HOW shifts to VERIFY_UNDERSTANDING."""
    from backend.app.ai.decision_engine import DecisionEngine
    from backend.app.ai.schemas import Strategy

    engine = DecisionEngine()
    context = create_context(LearningMode.STUDENT, 2, "It steps through line by line.")
    context.current_state.recent_strategy_history = [Strategy.PROBE_HOW]

    evaluation = TurnEvaluation(
        correctness=0.75,
        clarity=0.8,
        completeness=0.7,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=Strategy.PROBE_HOW,
        recommended_difficulty=2,
    )

    decision = engine.decide(context, evaluation)
    assert decision.strategy == Strategy.VERIFY_UNDERSTANDING
    assert "avoid consecutive strategy repetition" in decision.reason


def test_anti_repetition_alternates_repeated_verify_understanding():
    """Verify repeated VERIFY_UNDERSTANDING shifts to PROBE_WHY."""
    from backend.app.ai.decision_engine import DecisionEngine
    from backend.app.ai.schemas import Strategy

    engine = DecisionEngine()
    context = create_context(LearningMode.STUDENT, 2, "For example in web servers.")
    context.current_state.recent_strategy_history = [Strategy.VERIFY_UNDERSTANDING]

    # Partial answer that defaults to VERIFY_UNDERSTANDING
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

    decision = engine.decide(context, evaluation)
    assert decision.strategy == Strategy.PROBE_WHY
    assert "avoid consecutive strategy repetition" in decision.reason


def test_anti_repetition_never_suppresses_clarify_term():
    """Verify CLARIFY_TERM is retained even if the previous strategy was also CLARIFY_TERM."""
    from backend.app.ai.decision_engine import DecisionEngine
    from backend.app.ai.schemas import Strategy

    engine = DecisionEngine()
    context = create_context(LearningMode.STUDENT, 1, "The buffer is volatile.")
    context.current_state.recent_strategy_history = [Strategy.CLARIFY_TERM]

    evaluation = TurnEvaluation(
        correctness=0.5,
        clarity=0.5,
        completeness=0.5,
        depth=0.4,
        relevance=1.0,
        stuck_probability=0.1,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=["volatile"],
        mastered_concepts=[],
        recommended_strategy=Strategy.CLARIFY_TERM,
        recommended_difficulty=1,
    )

    decision = engine.decide(context, evaluation)
    assert decision.strategy == Strategy.CLARIFY_TERM
    assert decision.active_concept == "volatile"


def test_anti_repetition_never_suppresses_challenge_misconception():
    """Verify CHALLENGE_MISCONCEPTION is retained even if the previous strategy was also CHALLENGE_MISCONCEPTION."""
    from backend.app.ai.decision_engine import DecisionEngine
    from backend.app.ai.schemas import Strategy

    engine = DecisionEngine()
    context = create_context(LearningMode.STUDENT, 2, "It searches sequentially.")
    context.current_state.recent_strategy_history = [Strategy.CHALLENGE_MISCONCEPTION]

    evaluation = TurnEvaluation(
        correctness=0.4,
        clarity=0.6,
        completeness=0.4,
        depth=0.3,
        relevance=1.0,
        stuck_probability=0.1,
        misconceptions=["Linear search on binary tree"],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
        recommended_difficulty=2,
    )

    decision = engine.decide(context, evaluation)
    assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION
    assert decision.active_concept == "Linear search on binary tree"


def test_anti_repetition_empty_history_preserves_standard_strategy():
    """Verify empty recent_strategy_history does not alter strategy selection."""
    from backend.app.ai.decision_engine import DecisionEngine
    from backend.app.ai.schemas import Strategy

    engine = DecisionEngine()
    context = create_context(LearningMode.STUDENT, 2, "Because of the pointer dereference.")
    context.current_state.recent_strategy_history = []

    evaluation = TurnEvaluation(
        correctness=0.75,
        clarity=0.8,
        completeness=0.7,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=2,
    )

    decision = engine.decide(context, evaluation)
    assert decision.strategy == Strategy.PROBE_WHY
    assert "avoid consecutive strategy repetition" not in decision.reason


