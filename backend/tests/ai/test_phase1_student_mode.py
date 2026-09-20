"""
Comprehensive Phase 1 Test Suite for Core Adaptive Student Mode.
Validates:
- 17.1 Evaluator tests (8 cases)
- 17.2 Decision tests (strict strategy priority)
- 17.3 Difficulty tests (transitions and clamping 1-5)
- 17.4 Confidence tests (bounded range and update direction)
- 17.5 Question generation tests (single-question rule, persona)
- 17.6 CurioEngine end-to-end tests (initial turn and follow-up turns)
"""
import pytest
from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.engine import CurioEngine
from backend.app.ai.evaluator import AIEvaluator, TurnEvaluator
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    Difficulty,
    LearningContext,
    LearningDecision,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    SourceMode,
    StateUpdates,
    Strategy,
    TurnEvaluation,
)
from backend.app.ai.student import StudentModeHandler


def _make_context(
    user_msg: str = "A function calls itself.",
    topic: str = "Recursion",
    difficulty: int = 1,
    confidence: float = 0.5,
    active_concept: str = "recursion_definition",
    empty_history: bool = False,
) -> AIContext:
    session_info = SessionInfo(session_id="test_sess_01", topic=topic)
    current_state = SessionState(
        session_id="test_sess_01",
        current_mode=Mode.STUDENT,
        current_difficulty=difficulty,
        understanding_confidence=confidence,
        active_concept=active_concept,
        current_question=CurrentQuestion(
            id="q_prev", content="What is recursion?", concept=active_concept, difficulty=difficulty
        ),
    )
    if empty_history:
        messages = []
    else:
        messages = [
            ChatMessage(role=Role.ASSISTANT, content="What is recursion?"),
            ChatMessage(role=Role.USER, content=user_msg),
        ]
    conversation = ConversationContext(recent_messages=messages, message_count=len(messages))
    return AIContext(session=session_info, current_state=current_state, conversation=conversation)


# =====================================================================
# 17.1 Evaluator Tests (8 Cases)
# =====================================================================

class TestTurnEvaluator:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.provider = MockLLMProvider()
        self.evaluator = AIEvaluator(self.provider)

    def test_evaluator_alias(self):
        """Verify TurnEvaluator is exported and identical to AIEvaluator."""
        assert TurnEvaluator is AIEvaluator

    def test_case_1_strong_answer(self):
        """Case 1: Strong answer has high scores and mastered concepts."""
        ctx = _make_context(user_msg="A strong explanation: a base case provides a termination condition.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert 0.0 <= evaluation.correctness <= 1.0
        assert evaluation.correctness >= 0.8
        assert evaluation.clarity >= 0.8
        assert evaluation.completeness >= 0.8
        assert evaluation.depth >= 0.7
        assert evaluation.relevance >= 0.9
        assert evaluation.stuck_probability <= 0.2
        assert len(evaluation.mastered_concepts) > 0
        assert len(evaluation.misconceptions) == 0
        assert len(evaluation.undefined_terms) == 0

    def test_case_2_partial_answer(self):
        """Case 2: Partial answer has moderate correctness and missing concepts."""
        ctx = _make_context(user_msg="A partial answer: calls itself until done.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert 0.4 <= evaluation.correctness <= 0.8
        assert len(evaluation.missing_concepts) > 0
        assert evaluation.knowledge_gap is not None
        assert len(evaluation.misconceptions) == 0

    def test_case_3_incorrect_answer(self):
        """Case 3: Incorrect answer has low correctness and identifies gap."""
        ctx = _make_context(user_msg="An incorrect explanation: recursion is an iterative for loop.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert evaluation.correctness < 0.4
        assert evaluation.knowledge_gap is not None
        assert len(evaluation.mastered_concepts) == 0

    def test_case_4_likely_misconception(self):
        """Case 4: Misconception is populated in misconceptions list."""
        ctx = _make_context(user_msg="I have a misconception: binary search works on any array.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert len(evaluation.misconceptions) > 0
        assert any("binary search" in m.lower() or "unsorted" in m.lower() for m in evaluation.misconceptions)
        assert evaluation.recommended_strategy == Strategy.CHALLENGE_MISCONCEPTION

    def test_case_5_missing_concept(self):
        """Case 5: Missing concept is detected and identified."""
        ctx = _make_context(user_msg="explain recursion: a function calls itself.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert len(evaluation.missing_concepts) > 0
        assert "base case" in evaluation.missing_concepts
        assert evaluation.recommended_strategy == Strategy.PROBE_MISSING_CONCEPT

    def test_case_6_undefined_term(self):
        """Case 6: Undefined term is detected and placed in undefined_terms."""
        ctx = _make_context(user_msg="We optimize recursion using a trampoline undefined_term.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert len(evaluation.undefined_terms) > 0
        assert "trampoline" in evaluation.undefined_terms
        assert evaluation.recommended_strategy == Strategy.CLARIFY_TERM

    def test_case_7_irrelevant_answer(self):
        """Case 7: Irrelevant answer has low relevance."""
        ctx = _make_context(user_msg="irrelevant: the weather is nice today.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert evaluation.relevance < 0.3
        assert evaluation.correctness < 0.3
        assert evaluation.knowledge_gap is not None

    def test_case_8_weak_uncertain_answer(self):
        """Case 8: Weak/uncertain answer has high stuck_probability."""
        ctx = _make_context(user_msg="I don't know, I'm completely stuck.")
        evaluation = self.evaluator.evaluate_turn(ctx)

        assert evaluation.stuck_probability >= 0.7
        assert evaluation.correctness == 0.0


# =====================================================================
# 17.2 Decision Tests (Strategy Priority)
# =====================================================================

class TestDecisionEnginePolicy:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = DecisionEngine()

    def test_priority_1_undefined_term_overrides_misconception_and_missing_concept(self):
        """Priority 1: Undefined term has highest priority -> CLARIFY_TERM."""
        ctx = _make_context()
        evaluation = TurnEvaluation(
            correctness=0.6,
            clarity=0.5,
            completeness=0.5,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.1,
            misconceptions=["Belief stack is infinite"],
            missing_concepts=["base case"],
            undefined_terms=["tail-call accumulator"],
            recommended_strategy=Strategy.CLARIFY_TERM,
            recommended_difficulty=1,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.CLARIFY_TERM
        assert decision.active_concept == "tail-call accumulator"

    def test_priority_2_misconception_overrides_missing_concept(self):
        """Priority 2: Misconception has second priority -> CHALLENGE_MISCONCEPTION."""
        ctx = _make_context()
        evaluation = TurnEvaluation(
            correctness=0.5,
            clarity=0.7,
            completeness=0.5,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.1,
            misconceptions=["Binary search works on unsorted arrays"],
            missing_concepts=["sorted order"],
            undefined_terms=[],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION
        assert decision.active_concept == "Binary search works on unsorted arrays"

    def test_priority_3_missing_concept_selected(self):
        """Priority 3: Missing concept without undefined terms or misconceptions -> PROBE_MISSING_CONCEPT."""
        ctx = _make_context()
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
            recommended_strategy=Strategy.PROBE_MISSING_CONCEPT,
            recommended_difficulty=1,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.PROBE_MISSING_CONCEPT
        assert decision.active_concept == "base case"

    def test_priority_4_mechanism_gap_selects_probe_how(self):
        """Priority 4: Mechanism gap -> PROBE_HOW."""
        ctx = _make_context()
        evaluation = TurnEvaluation(
            correctness=0.7,
            clarity=0.7,
            completeness=0.6,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            recommended_strategy=Strategy.PROBE_HOW,
            recommended_difficulty=2,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.PROBE_HOW

    def test_priority_5_reasoning_gap_selects_probe_why(self):
        """Priority 5: Reasoning gap -> PROBE_WHY."""
        ctx = _make_context()
        evaluation = TurnEvaluation(
            correctness=0.75,
            clarity=0.7,
            completeness=0.7,
            depth=0.6,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=2,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.PROBE_WHY

    def test_priority_6_strong_understanding_increases_difficulty(self):
        """Priority 6: Strong understanding -> INCREASE_DIFFICULTY."""
        ctx = _make_context(difficulty=2)
        evaluation = TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=["Recursion"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=3,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.INCREASE_DIFFICULTY
        assert decision.difficulty == 3


# =====================================================================
# 17.3 Difficulty Tests (1-5 Bounds and Clamping)
# =====================================================================

class TestDifficultyTransitions:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = DecisionEngine()

    @pytest.mark.parametrize("start_diff, expected_next", [
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 5),  # Clamped at 5
    ])
    def test_strong_understanding_increments_by_at_most_one(self, start_diff, expected_next):
        """Verify difficulty progression: 1->2, 2->3, 3->4, 4->5, never > 5."""
        ctx = _make_context(difficulty=start_diff)
        evaluation = TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=["Recursion"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=min(5, start_diff + 1),
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.difficulty == expected_next
        assert 1 <= decision.difficulty <= 5
        assert abs(decision.difficulty - start_diff) <= 1

    def test_major_gap_decrements_by_at_most_one_clamped_at_one(self):
        """Verify major gap decreases difficulty by at most 1, never < 1."""
        # From 3 to 2
        ctx3 = _make_context(difficulty=3)
        eval_gap = TurnEvaluation(
            correctness=0.1,
            clarity=0.3,
            completeness=0.1,
            depth=0.1,
            relevance=0.8,
            stuck_probability=0.8,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            knowledge_gap="Completely stuck",
            recommended_strategy=Strategy.ASK_FOUNDATION,
            recommended_difficulty=1,
        )
        decision3 = self.engine.decide(ctx3, eval_gap)
        assert decision3.difficulty == 2
        assert abs(decision3.difficulty - 3) <= 1

        # From 1 to 1 (never < 1)
        ctx1 = _make_context(difficulty=1)
        decision1 = self.engine.decide(ctx1, eval_gap)
        assert decision1.difficulty == 1

    def test_misconception_maintains_difficulty(self):
        """Misconception challenges at current difficulty level without jumping."""
        ctx = _make_context(difficulty=3)
        evaluation = TurnEvaluation(
            correctness=0.35,
            clarity=0.8,
            completeness=0.4,
            depth=0.3,
            relevance=0.9,
            stuck_probability=0.1,
            misconceptions=["Binary search works on unsorted arrays"],
            missing_concepts=[],
            undefined_terms=[],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=3,
        )
        decision = self.engine.decide(ctx, evaluation)
        assert decision.difficulty == 3


# =====================================================================
# 17.4 Confidence Tests
# =====================================================================

class TestConfidenceUpdates:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = DecisionEngine()

    def test_strong_answer_increases_confidence(self):
        """Strong answer increases confidence and stays <= 1.0."""
        ctx = _make_context(confidence=0.5)
        evaluation = TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=["Recursion"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.confidence > 0.5
        assert decision.confidence <= 1.0

    def test_confidence_clamped_at_max(self):
        """Confidence never exceeds 1.0 even with maximum starting confidence."""
        ctx = _make_context(confidence=0.98)
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
            mastered_concepts=["Recursion"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        )
        decision = self.engine.decide(ctx, evaluation)
        assert decision.confidence <= 1.0

    def test_major_gap_decreases_confidence(self):
        """Major gap decreases confidence and stays >= 0.0."""
        ctx = _make_context(confidence=0.5)
        evaluation = TurnEvaluation(
            correctness=0.1,
            clarity=0.3,
            completeness=0.1,
            depth=0.1,
            relevance=0.8,
            stuck_probability=0.85,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            knowledge_gap="Completely stuck",
            recommended_strategy=Strategy.ASK_FOUNDATION,
            recommended_difficulty=1,
        )
        decision = self.engine.decide(ctx, evaluation)

        assert decision.confidence < 0.5
        assert decision.confidence >= 0.0

    def test_misconception_decreases_confidence(self):
        """Misconception decreases confidence."""
        ctx = _make_context(confidence=0.6)
        evaluation = TurnEvaluation(
            correctness=0.3,
            clarity=0.8,
            completeness=0.4,
            depth=0.3,
            relevance=0.9,
            stuck_probability=0.1,
            misconceptions=["Binary search works on unsorted arrays"],
            missing_concepts=[],
            undefined_terms=[],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        )
        decision = self.engine.decide(ctx, evaluation)
        assert decision.confidence < 0.6

    def test_confidence_clamped_at_zero(self):
        """Confidence never goes below 0.0."""
        ctx = _make_context(confidence=0.02)
        evaluation = TurnEvaluation(
            correctness=0.0,
            clarity=0.0,
            completeness=0.0,
            depth=0.0,
            relevance=0.0,
            stuck_probability=0.95,
            misconceptions=["Severe misconception"],
            missing_concepts=[],
            undefined_terms=[],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        )
        decision = self.engine.decide(ctx, evaluation)
        assert decision.confidence >= 0.0


# =====================================================================
# 17.5 Question Generation Tests (Hard One-Question Rule)
# =====================================================================

class TestQuestionGeneration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.provider = MockLLMProvider()
        self.handler = StudentModeHandler(self.provider)

    def test_initial_question_generation(self):
        """Initial turn generates foundational question with exactly one question mark."""
        ctx = _make_context(topic="Operating Systems", empty_history=True)
        question = self.handler.generate_initial_question(ctx)

        assert len(question) > 0
        assert question.count("?") == 1
        assert "operating system" in question.lower()

    def test_followup_question_clarify_term(self):
        """CLARIFY_TERM generates question targeting the undefined term."""
        ctx = _make_context()
        decision = LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.CLARIFY_TERM,
            difficulty=1,
            confidence=0.5,
            reason="Clarify term",
            active_concept="trampoline",
        )
        question = self.handler.generate_followup_question(ctx, TurnEvaluation(
            correctness=0.6, clarity=0.5, completeness=0.5, depth=0.5, relevance=1.0, stuck_probability=0.0,
            recommended_strategy=Strategy.CLARIFY_TERM, recommended_difficulty=1
        ), decision)

        assert len(question) > 0
        assert question.count("?") == 1

    def test_followup_question_challenge_misconception(self):
        """CHALLENGE_MISCONCEPTION generates a probing question, not a lecture."""
        ctx = _make_context()
        decision = LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.CHALLENGE_MISCONCEPTION,
            difficulty=2,
            confidence=0.4,
            reason="Challenge misconception",
            active_concept="Binary search works on unsorted arrays",
        )
        question = self.handler.generate_followup_question(ctx, TurnEvaluation(
            correctness=0.35, clarity=0.8, completeness=0.4, depth=0.3, relevance=0.9, stuck_probability=0.1,
            misconceptions=["Binary search works on unsorted arrays"],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION, recommended_difficulty=2
        ), decision)

        assert len(question) > 0
        assert question.count("?") == 1
        assert "unsorted" in question.lower() or "discard" in question.lower()

    def test_hard_one_question_enforcement_truncates_compound_questions(self):
        """Ensures post-processing strips secondary questions to satisfy the one-question rule."""
        raw_bad = "What is a base case? Why does it stop recursion? Can you give an example?"
        cleaned = StudentModeHandler._enforce_single_question(raw_bad)

        assert cleaned.count("?") == 1
        assert cleaned == "What is a base case?"


# =====================================================================
# 17.6 CurioEngine End-to-End Tests
# =====================================================================

class TestCurioEngineEndToEnd:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.provider = MockLLMProvider()
        self.engine = CurioEngine(provider=self.provider)

    def test_initial_turn_flow(self):
        """
        Initial turn test:
        No learner answer exists yet.
        Verifies:
        - strategy = ASK_FOUNDATION
        - difficulty = 1
        - mode = STUDENT
        - response contains exactly one foundational question
        - current_question is created in StateUpdates
        """
        context = _make_context(topic="Operating Systems", empty_history=True)
        result = self.engine.process(context)

        assert isinstance(result, AIResult)
        assert result.evaluation is not None
        assert result.decision is not None
        assert result.response is not None
        assert result.state_updates is not None

        # Mode invariant
        assert result.decision.next_mode == Mode.STUDENT
        assert result.response.mode == Mode.STUDENT
        assert result.state_updates.current_mode == Mode.STUDENT

        # Strategy and difficulty
        assert result.decision.strategy == Strategy.ASK_FOUNDATION
        assert result.decision.difficulty == 1
        assert result.response.difficulty == 1

        # Single question rule
        assert result.response.requires_single_question is True
        assert result.response.content.count("?") == 1
        assert len(result.response.content) > 0

        # State updates
        assert result.state_updates.current_question is not None
        assert result.state_updates.current_question.content == result.response.content
        assert result.state_updates.current_question.difficulty == 1

    def test_followup_turn_flow(self):
        """
        Follow-up turn test:
        Learner provides an answer.
        Verifies:
        - evaluation metrics are bounded [0.0, 1.0]
        - decision is made deterministically
        - exactly one question is generated
        - StateUpdates captures new question and updated difficulty/confidence
        """
        context = _make_context(
            user_msg="A strong explanation: a base case provides a termination condition.",
            difficulty=1,
            confidence=0.5,
        )
        result = self.engine.process(context)

        assert isinstance(result, AIResult)

        # Evaluation validation
        eval_res = result.evaluation
        assert 0.0 <= eval_res.correctness <= 1.0
        assert 0.0 <= eval_res.clarity <= 1.0
        assert 0.0 <= eval_res.completeness <= 1.0
        assert 0.0 <= eval_res.depth <= 1.0
        assert 0.0 <= eval_res.relevance <= 1.0
        assert 0.0 <= eval_res.stuck_probability <= 1.0

        # Decision validation
        dec_res = result.decision
        assert dec_res.next_mode == Mode.STUDENT
        assert 1 <= dec_res.difficulty <= 5
        assert 0.0 <= dec_res.confidence <= 1.0
        assert dec_res.difficulty == 2  # Incremented from 1
        assert dec_res.confidence > 0.5  # Increased

        # Response validation
        resp_res = result.response
        assert resp_res.mode == Mode.STUDENT
        assert resp_res.requires_single_question is True
        assert resp_res.content.count("?") == 1

        # StateUpdates validation
        updates = result.state_updates
        assert updates.current_mode == Mode.STUDENT
        assert updates.difficulty == 2
        assert updates.confidence == dec_res.confidence
        assert updates.current_question is not None
        assert updates.current_question.content == resp_res.content
        assert updates.current_question.difficulty == 2
        assert updates.consecutive_successes >= 1
