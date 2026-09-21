"""
Comprehensive Phase 2 Test Suite for Teacher Mode, Gap-Specific Teaching,
Stuck Detection, Verification, Attempt Limits, and Interrupted Question Restoration.

Validates:
1. Stuck Detection Tests (10 cases):
   - Explicit "I don't know" -> Teacher
   - Explicit "I'm stuck" -> Teacher
   - Explicit "I don't understand" -> Teacher
   - High stuck_probability + weak correctness -> Teacher
   - Repeated same gap -> Teacher
   - Strong answer -> Student
   - Normal misconception -> Student
   - Normal missing concept -> Student
   - Low confidence alone -> Student
   - Borderline stuck_probability -> deterministic expected result
2. Teacher Response & Verification Tests:
   - Correct gap selected
   - Teacher addresses only the gap
   - Teacher response contains explanation
   - Teacher response contains exactly one verification question
   - Verification targets the same gap
   - Teacher attempt count increments
   - Failed verification keeps Teacher Mode active
   - Second explanation differs/adapts appropriately (attempt-aware)
   - Successful verification exits Teacher Mode
3. Restoration Tests:
   - Student question is saved before Teacher Mode
   - Interrupted question remains unchanged through Teacher turns
   - Verification success restores the exact question
   - Restored question has the original concept
   - Restored question has the original difficulty
   - Teacher intervention is cleared after success
   - No unrelated question is generated during restoration
4. Loop Prevention & Fallback Tests:
   - Teacher attempts increment
   - Maximum attempt limit (3) is respected
   - Teacher cannot loop indefinitely
   - Fallback behavior occurs after max attempts (exit to Student with simpler difficulty)
   - Student Mode resumes correctly
5. End-to-End Binary Search Scenario:
   - Complete multi-turn deterministic flow
"""
import pytest
from backend.app.ai.decision_engine import DecisionEngine, MAX_TEACHER_ATTEMPTS
from backend.app.ai.engine import CurioEngine
from backend.app.ai.evaluator import AIEvaluator
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    LearningContext,
    LearningDecision,
    Mode,
    ModeTransition,
    Role,
    SessionInfo,
    SessionState,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
)
from backend.app.ai.teacher import TeacherModeHandler


def _make_context(
    user_msg: str = "A function calls itself.",
    topic: str = "Recursion",
    mode: Mode = Mode.STUDENT,
    difficulty: int = 2,
    confidence: float = 0.5,
    active_concept: str = "Recursion Definition",
    current_q_content: str = "Why is a base case required in recursion?",
    interrupted_q: CurrentQuestion = None,
    teacher_intervention: TeacherIntervention = None,
    teacher_attempt_count: int = 0,
    consecutive_failures: int = 0,
) -> AIContext:
    session_info = SessionInfo(session_id="phase2_test_sess", topic=topic)
    curr_q = CurrentQuestion(
        id="q_curr_123",
        content=current_q_content,
        concept=active_concept,
        difficulty=difficulty,
    )
    current_state = SessionState(
        session_id="phase2_test_sess",
        current_mode=mode,
        current_difficulty=difficulty,
        understanding_confidence=confidence,
        active_concept=active_concept,
        current_question=curr_q,
        interrupted_question=interrupted_q,
        teacher_intervention=teacher_intervention,
        teacher_attempt_count=teacher_attempt_count,
        consecutive_failures=consecutive_failures,
    )
    messages = [
        ChatMessage(role=Role.ASSISTANT, content=current_q_content),
        ChatMessage(role=Role.USER, content=user_msg),
    ]
    conversation = ConversationContext(recent_messages=messages, message_count=len(messages))
    return AIContext(session=session_info, current_state=current_state, conversation=conversation)


# =====================================================================
# 1. STUCK DETECTION TESTS (10 Cases)
# =====================================================================

class TestStuckDetectionPolicy:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = DecisionEngine()

    def test_1_explicit_idk_triggers_teacher(self):
        """Explicit 'I don't know' triggers Teacher Mode."""
        ctx = _make_context(user_msg="I don't know how this works.")
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.5,
            stuck_probability=0.9, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Does not understand base cases", recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert "explicit stuck signal" in decision.reason

    def test_2_explicit_stuck_triggers_teacher(self):
        """Explicit 'I'm stuck' triggers Teacher Mode."""
        ctx = _make_context(user_msg="I'm stuck, can you explain?")
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.5, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.85, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Stuck on mechanism", recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_3_explicit_dont_understand_triggers_teacher(self):
        """Explicit 'I don't understand' triggers Teacher Mode."""
        ctx = _make_context(user_msg="I don't understand why sorting is required.")
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.6, completeness=0.1, depth=0.0, relevance=0.8,
            stuck_probability=0.8, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Does not see why sorting allows half-array elimination",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_4_high_stuck_prob_plus_weak_correctness_triggers_teacher(self):
        """stuck_probability >= 0.75 and correctness < 0.5 triggers Teacher Mode without exact phrase."""
        ctx = _make_context(user_msg="Maybe it loops or something, completely lost.")
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.3, completeness=0.1, depth=0.0, relevance=0.4,
            stuck_probability=0.80, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Missing execution model", recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_5_repeated_same_gap_triggers_teacher(self):
        """Repeated failure on the same knowledge gap triggers Teacher Mode (Trigger C)."""
        ctx = _make_context(
            user_msg="I think it still just checks every element.",
            consecutive_failures=1,
        )
        ctx.learning_context.recent_evaluations = [
            TurnEvaluation(
                correctness=0.3, clarity=0.5, completeness=0.2, depth=0.1, relevance=0.8,
                stuck_probability=0.4, misconceptions=[], missing_concepts=[], undefined_terms=[],
                knowledge_gap="Why sorting is required", recommended_strategy=Strategy.PROBE_WHY,
                recommended_difficulty=2
            )
        ]
        eval_turn = TurnEvaluation(
            correctness=0.3, clarity=0.5, completeness=0.2, depth=0.1, relevance=0.8,
            stuck_probability=0.5, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Why sorting is required", recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_6_strong_answer_stays_in_student(self):
        """Strong answer remains in Student Mode."""
        ctx = _make_context(user_msg="The base case provides a termination condition so the function returns.")
        eval_turn = TurnEvaluation(
            correctness=0.95, clarity=0.9, completeness=0.9, depth=0.85, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap=None, recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=3
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy in (Strategy.INCREASE_DIFFICULTY, Strategy.PROBE_WHY)

    def test_7_normal_misconception_stays_in_student(self):
        """Single normal misconception does NOT trigger Teacher Mode; stays in Student Mode."""
        ctx = _make_context(user_msg="Binary search works on any array because it checks the middle.")
        eval_turn = TurnEvaluation(
            correctness=0.4, clarity=0.8, completeness=0.5, depth=0.4, relevance=0.9,
            stuck_probability=0.1, misconceptions=["Binary search works on unsorted arrays"],
            missing_concepts=[], undefined_terms=[], knowledge_gap="Belief that unsorted data can be binary searched",
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.CHALLENGE_MISCONCEPTION

    def test_8_normal_missing_concept_stays_in_student(self):
        """Single missing concept does NOT trigger Teacher Mode; stays in Student Mode."""
        ctx = _make_context(user_msg="A recursive function calls itself to break down the task.")
        eval_turn = TurnEvaluation(
            correctness=0.7, clarity=0.8, completeness=0.5, depth=0.4, relevance=1.0,
            stuck_probability=0.1, misconceptions=[], missing_concepts=["base case"],
            undefined_terms=[], knowledge_gap="Omitted termination condition",
            recommended_strategy=Strategy.PROBE_MISSING_CONCEPT, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.PROBE_MISSING_CONCEPT

    def test_9_low_confidence_alone_stays_in_student(self):
        """Low confidence alone does NOT trigger Teacher Mode."""
        ctx = _make_context(user_msg="It divides the problem in half.", confidence=0.1)
        eval_turn = TurnEvaluation(
            correctness=0.65, clarity=0.7, completeness=0.6, depth=0.5, relevance=0.9,
            stuck_probability=0.2, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap=None, recommended_strategy=Strategy.PROBE_HOW,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy in (Strategy.PROBE_HOW, Strategy.PROBE_WHY, Strategy.VERIFY_UNDERSTANDING)

    def test_10_borderline_stuck_probability_deterministic_result(self):
        """stuck_probability = 0.74 (below 0.75 threshold) without explicit phrase does not trigger Teacher Mode."""
        ctx = _make_context(user_msg="I'm somewhat unsure about the details.")
        eval_turn = TurnEvaluation(
            correctness=0.55, clarity=0.5, completeness=0.4, depth=0.3, relevance=0.8,
            stuck_probability=0.74, misconceptions=[], missing_concepts=["mechanism"],
            undefined_terms=[], knowledge_gap="Partial mechanism gap",
            recommended_strategy=Strategy.PROBE_MISSING_CONCEPT, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.PROBE_MISSING_CONCEPT


# =====================================================================
# 2. TEACHER RESPONSE & VERIFICATION TESTS
# =====================================================================

class TestTeacherResponseAndVerification:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.provider = MockLLMProvider()
        self.teacher = TeacherModeHandler(self.provider)
        self.engine = DecisionEngine()

    def test_teacher_response_contains_explanation_and_single_verification_question(self):
        """Teacher response must explain only the gap and end with exactly one verification question."""
        ctx = _make_context(
            topic="Binary Search",
            active_concept="Sorting Requirement",
            current_q_content="Why does binary search require a sorted array?",
        )
        gap = "Ordering allows elimination of half the search space"
        response_text = self.teacher.generate_teacher_response(
            context=ctx,
            gap=gap,
            attempt_count=1,
            interrupted_question=ctx.current_question,
        )

        assert len(response_text) > 0
        assert response_text.count("?") == 1
        # Contains explanation
        assert "sorting" in response_text.lower() or "ordering" in response_text.lower()
        # Contains verification question
        assert "why can we ignore" in response_text.lower() or "?" in response_text

    def test_teacher_attempt_adaptation(self):
        """Teacher adapts explanation across attempts (attempt 1 vs attempt 2 vs attempt 3)."""
        ctx = _make_context(topic="Binary Search")
        gap = "Ordering allows elimination of half the search space"

        resp_1 = self.teacher.generate_teacher_response(ctx, gap, attempt_count=1)
        resp_2 = self.teacher.generate_teacher_response(ctx, gap, attempt_count=2)
        resp_3 = self.teacher.generate_teacher_response(ctx, gap, attempt_count=3)

        # Responses should be different and adapted
        assert resp_1 != resp_2
        assert resp_2 != resp_3
        assert "dictionary" in resp_2.lower() or "analogy" in resp_2.lower() or "apple" in resp_2.lower()
        assert "[" in resp_3 or "micro" in resp_3.lower() or "5" in resp_3

    def test_failed_verification_keeps_teacher_mode(self):
        """When in Teacher Mode and verification fails, remain in Teacher Mode and increment attempts."""
        int_q = CurrentQuestion(id="q_orig", content="Why does binary search require sorted data?", concept="Binary Search", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="Ordering elimination", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="I still don't understand why we can ignore values after 10.",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_fail = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.2, depth=0.1, relevance=0.7,
            stuck_probability=0.85, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Still does not understand why ordering eliminates half the search space.",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_fail)

        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_successful_verification_exits_teacher_mode(self):
        """When in Teacher Mode and verification passes, exit to Student Mode and restore interrupted question."""
        int_q = CurrentQuestion(id="q_orig", content="Why does binary search require sorted data?", concept="Binary Search", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="Ordering elimination", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Because the array is sorted, every number after 10 is greater than 10, so 7 cannot be there.",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_pass = TurnEvaluation(
            correctness=0.9, clarity=0.9, completeness=0.85, depth=0.8, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap=None, recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_pass)

        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.RESTORE_INTERRUPTED_QUESTION
        assert decision.should_restore_interrupted_question is True
        assert decision.difficulty == 2
        assert decision.active_concept == "Binary Search"


# =====================================================================
# 3. RESTORATION TESTS
# =====================================================================

class TestInterruptedQuestionRestoration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = CurioEngine()

    def test_student_question_snapshot_on_entering_teacher(self):
        """When transitioning from Student to Teacher, current_question is saved into interrupted_question."""
        ctx = _make_context(
            user_msg="I don't know, I'm completely stuck.",
            topic="Recursion",
            current_q_content="What stops a recursive function from running forever?",
            difficulty=2,
        )
        result = self.engine.process(ctx)

        assert result.decision.next_mode == Mode.TEACHER
        assert result.state_updates.current_mode == Mode.TEACHER
        assert result.state_updates.interrupted_question is not None
        assert result.state_updates.interrupted_question.content == "What stops a recursive function from running forever?"
        assert result.state_updates.interrupted_question.difficulty == 2
        assert result.state_updates.teacher_intervention.active is True
        assert result.state_updates.teacher_attempt_count == 1

    def test_interrupted_question_preserved_across_teacher_turns(self):
        """During multiple Teacher Mode turns, interrupted_question is preserved unchanged."""
        int_q = CurrentQuestion(id="q_orig", content="Original question: explain base case.", concept="Recursion", difficulty=3)
        intervention = TeacherIntervention(active=True, gap="Base case purpose", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Still confused about how base cases stop the function.",
            mode=Mode.TEACHER,
            difficulty=3,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        result = self.engine.process(ctx)

        assert result.decision.next_mode == Mode.TEACHER
        assert result.state_updates.interrupted_question is not None
        assert result.state_updates.interrupted_question.id == "q_orig"
        assert result.state_updates.interrupted_question.content == "Original question: explain base case."
        assert result.state_updates.teacher_attempt_count == 2

    def test_restoration_restores_exact_question_concept_and_difficulty(self):
        """On successful verification, the exact question, concept, and difficulty are restored."""
        int_q = CurrentQuestion(id="q_orig", content="Original question: explain base case.", concept="Recursion Concept", difficulty=3)
        intervention = TeacherIntervention(active=True, gap="Base case purpose", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Without base case it runs forever, stops the loop.",
            mode=Mode.TEACHER,
            difficulty=3,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        result = self.engine.process(ctx)

        assert result.decision.next_mode == Mode.STUDENT
        assert result.decision.should_restore_interrupted_question is True
        assert result.state_updates.current_mode == Mode.STUDENT
        assert result.state_updates.current_question.content == int_q.content
        assert result.state_updates.current_question.difficulty == 3
        assert result.state_updates.current_question.concept == "Recursion Concept"
        assert result.state_updates.interrupted_question is None
        assert result.state_updates.teacher_intervention.active is False
        assert result.state_updates.teacher_attempt_count == 0


# =====================================================================
# 4. LOOP PREVENTION & FALLBACK TESTS
# =====================================================================

class TestTeacherLoopPreventionAndFallback:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.decision_engine = DecisionEngine()
        self.curio_engine = CurioEngine()

    def test_max_attempts_exits_teacher_mode_to_simpler_difficulty(self):
        """When teacher_attempt_count reaches MAX_TEACHER_ATTEMPTS (3), fallback to Student Mode at simpler difficulty."""
        int_q = CurrentQuestion(id="q_orig", content="Complex problem.", concept="Advanced Recursion", difficulty=3)
        intervention = TeacherIntervention(active=True, gap="Difficult gap", attempt_count=2, verification_required=True)
        ctx = _make_context(
            user_msg="I still don't understand, still confused.",
            mode=Mode.TEACHER,
            difficulty=3,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=2,
        )
        # Attempt 3 fails verification
        eval_fail = TurnEvaluation(
            correctness=0.1, clarity=0.3, completeness=0.1, depth=0.0, relevance=0.6,
            stuck_probability=0.85, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Still stuck on difficult gap", recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=3
        )
        decision = self.decision_engine.decide(ctx, eval_fail)

        assert decision.next_mode == Mode.STUDENT
        assert decision.should_restore_interrupted_question is True
        # Simpler difficulty (3 - 1 = 2)
        assert decision.difficulty == 2
        assert "Maximum Teacher attempts (3) reached" in decision.reason

    def test_loop_prevention_end_to_end_in_engine(self):
        """End-to-end CurioEngine verify that max attempts cannot loop indefinitely."""
        int_q = CurrentQuestion(id="q_orig", content="Original hard question.", concept="Hard Concept", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="Hard gap", attempt_count=2, verification_required=True)
        ctx = _make_context(
            user_msg="still don't understand",
            mode=Mode.TEACHER,
            difficulty=2,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=2,
        )
        result = self.curio_engine.process(ctx)

        assert result.decision.next_mode == Mode.STUDENT
        assert result.state_updates.current_mode == Mode.STUDENT
        assert result.state_updates.difficulty == 1  # Decreased from 2 to 1
        assert result.state_updates.teacher_intervention.active is False


# =====================================================================
# 5. COMPLETE END-TO-END BINARY SEARCH SCENARIO
# =====================================================================

class TestBinarySearchEndToEndScenario:
    def test_complete_binary_search_teacher_mode_flow(self):
        """
        End-to-End Scenario:
        1. Student Mode: AI asked "Why does binary search require a sorted array?"
        2. Learner: "I don't understand why sorting matters." (Genuinely stuck)
        3. Transition to Teacher Mode:
           - Interrupted question saved
           - Exact gap identified ("Ordering allows elimination of half the search space")
           - Teacher explanation + 1 verification question generated
        4. Learner answers verification question:
           "Because the array is sorted, every number after 10 is greater than 10, so 7 cannot be after 10."
        5. Verification evaluated: PASS
        6. Return to Student Mode:
           - Original question restored exactly
           - Student Mode continues
        """
        engine = CurioEngine()

        # Step 1 & 2: Learner gets stuck on binary search question
        ctx_turn_1 = _make_context(
            user_msg="I don't understand why sorting matters.",
            topic="Binary Search",
            current_q_content="Why does binary search require a sorted array?",
            difficulty=2,
        )
        result_turn_1 = engine.process(ctx_turn_1)

        # Step 3: Transition to Teacher Mode
        assert result_turn_1.decision.next_mode == Mode.TEACHER
        assert result_turn_1.response.mode == Mode.TEACHER
        assert result_turn_1.state_updates.current_mode == Mode.TEACHER
        assert result_turn_1.state_updates.interrupted_question.content == "Why does binary search require a sorted array?"
        assert result_turn_1.response.content.count("?") == 1
        assert "why can we ignore" in result_turn_1.response.content.lower() or "?" in result_turn_1.response.content

        # Step 4: Learner answers verification question
        ctx_turn_2 = _make_context(
            user_msg="Because the array is sorted, every number after 10 is greater than 10, so 7 cannot be there.",
            topic="Binary Search",
            mode=Mode.TEACHER,
            difficulty=2,
            current_q_content=result_turn_1.response.content,
            interrupted_q=result_turn_1.state_updates.interrupted_question,
            teacher_intervention=result_turn_1.state_updates.teacher_intervention,
            teacher_attempt_count=1,
        )
        result_turn_2 = engine.process(ctx_turn_2)

        # Step 5 & 6: Verification PASSED -> Student Mode restored
        assert result_turn_2.decision.next_mode == Mode.STUDENT
        assert result_turn_2.decision.should_restore_interrupted_question is True
        assert result_turn_2.state_updates.current_mode == Mode.STUDENT
        assert result_turn_2.state_updates.current_question.content == "Why does binary search require a sorted array?"
        assert result_turn_2.state_updates.interrupted_question is None
        assert result_turn_2.state_updates.teacher_intervention.active is False
        assert result_turn_2.state_updates.teacher_attempt_count == 0
        assert "Why does binary search require a sorted array?" in result_turn_2.response.content


# =====================================================================
# 6. ADAPTIVE MODE TRANSITIONS & DECISION HIERARCHY TESTS
# =====================================================================

class TestCurioAdaptiveModeTransitions:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = DecisionEngine()

    def test_adaptive_1_strongly_correct_answer_stays_student_increases_difficulty(self):
        """Test 1: Strongly correct answer demonstrates understanding -> Student Mode + difficulty increase."""
        ctx = _make_context(
            user_msg="Because after checking the middle element, we need to know whether to search the left or right half. Sorting gives us the ordering needed to eliminate half of the search space.",
            topic="Binary Search",
            difficulty=2,
            confidence=0.6,
        )
        eval_turn = TurnEvaluation(
            correctness=0.95, clarity=0.95, completeness=0.9, depth=0.85, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["search space elimination", "sorted ordering invariant"],
            knowledge_gap=None, recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=3
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.difficulty >= 2
        assert decision.strategy in (Strategy.INCREASE_DIFFICULTY, Strategy.PROBE_WHY)

    def test_adaptive_2_partially_correct_probes_reasoning_in_student(self):
        """Test 2: Partially correct answer probes missing reasoning without switching to Teacher Mode."""
        ctx = _make_context(
            user_msg="Because otherwise we can't find the value efficiently.",
            topic="Binary Search",
            difficulty=2,
            confidence=0.5,
        )
        eval_turn = TurnEvaluation(
            correctness=0.6, clarity=0.7, completeness=0.5, depth=0.4, relevance=0.9,
            stuck_probability=0.1, misconceptions=[], missing_concepts=["halving search space"],
            undefined_terms=[], knowledge_gap="Does not explain how sorting enables halving",
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy in (Strategy.PROBE_WHY, Strategy.PROBE_HOW, Strategy.PROBE_MISSING_CONCEPT, Strategy.VERIFY_UNDERSTANDING)

    def test_adaptive_3_completely_wrong_triggers_teacher_mode(self):
        """Test 3: Completely wrong answer / major misconception triggers Teacher Mode."""
        ctx = _make_context(
            user_msg="Because binary search checks every element one by one.",
            topic="Binary Search",
            difficulty=2,
            confidence=0.5,
        )
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.7, completeness=0.2, depth=0.1, relevance=0.7,
            stuck_probability=0.2, misconceptions=["Binary search is linear search"],
            missing_concepts=["divide and conquer", "middle element comparison"],
            undefined_terms=[], knowledge_gap="Confusing binary search with linear search",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert "teacher intervention" in decision.reason or "clear major misconception" in decision.reason

    def test_adaptive_4_explicit_stuck_triggers_teacher_mode(self):
        """Test 4: Explicit 'I don't know' triggers Teacher Mode."""
        ctx = _make_context(
            user_msg="I don't know.",
            topic="Binary Search",
            difficulty=2,
        )
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.5,
            stuck_probability=0.95, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="Does not know why sorting is required",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_adaptive_5_repeated_incorrect_answers_triggers_teacher_mode(self):
        """Test 5: Repeated failures on same concept trigger Teacher Mode."""
        ctx = _make_context(
            user_msg="Because it has to search everywhere.",
            topic="Binary Search",
            difficulty=2,
            consecutive_failures=2,
        )
        eval_turn = TurnEvaluation(
            correctness=0.3, clarity=0.4, completeness=0.2, depth=0.1, relevance=0.6,
            stuck_probability=0.3, misconceptions=[], missing_concepts=["halving search space"],
            undefined_terms=[], knowledge_gap="Unable to explain sorting requirement",
            recommended_strategy=Strategy.PROBE_HOW,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_adaptive_6_weak_answer_followed_by_correct_reasoning_remains_student(self):
        """Test 6: Learner who previously gave weak answer now answers with valid reasoning remains in Student Mode."""
        ctx = _make_context(
            user_msg="The sorted order means comparing with the middle element tells us which half the target must be in, so we can discard the other half.",
            topic="Binary Search",
            difficulty=2,
            consecutive_failures=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.85, clarity=0.9, completeness=0.8, depth=0.75, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["search space elimination"],
            knowledge_gap=None, recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT

    def test_adaptive_7_teacher_verification_passes_restores_student(self):
        """Test 7: Successful verification in Teacher Mode restores interrupted question and returns to Student Mode."""
        interrupted_q = CurrentQuestion(
            id="q_int_1",
            content="Why does binary search require a sorted array?",
            concept="Binary Search Invariant",
            difficulty=2,
        )
        ctx = _make_context(
            user_msg="Because all elements to the right of the middle are greater than the middle element, so if our target is smaller, it cannot possibly be on the right.",
            topic="Binary Search",
            mode=Mode.TEACHER,
            difficulty=2,
            interrupted_q=interrupted_q,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.9, clarity=0.9, completeness=0.85, depth=0.8, relevance=1.0,
            stuck_probability=0.0, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["half space elimination"], knowledge_gap=None,
            recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.should_restore_interrupted_question is True

    def test_adaptive_8_teacher_verification_fails_remains_teacher(self):
        """Test 8: Failed verification in Teacher Mode remains in Teacher Mode for adapted explanation."""
        interrupted_q = CurrentQuestion(
            id="q_int_1",
            content="Why does binary search require a sorted array?",
            concept="Binary Search Invariant",
            difficulty=2,
        )
        intervention = TeacherIntervention(
            active=True,
            gap="half space elimination",
            attempt_count=1,
            verification_required=True,
        )
        ctx = _make_context(
            user_msg="I still don't get it. Does it just jump around randomly?",
            topic="Binary Search",
            mode=Mode.TEACHER,
            difficulty=2,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.8, misconceptions=["Random jumping in binary search"],
            missing_concepts=["monotonic ordering"], undefined_terms=[],
            knowledge_gap="half space elimination", recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_adaptive_9_teacher_retry_limit_exits_to_student(self):
        """Test 9: Teacher Mode respects MAX_TEACHER_ATTEMPTS (3) and exits to Student Mode at simpler difficulty."""
        interrupted_q = CurrentQuestion(
            id="q_int_1",
            content="Why does binary search require a sorted array?",
            concept="Binary Search Invariant",
            difficulty=3,
        )
        intervention = TeacherIntervention(
            active=True,
            gap="half space elimination",
            attempt_count=2,
            verification_required=True,
        )
        ctx = _make_context(
            user_msg="I really don't understand this.",
            topic="Binary Search",
            mode=Mode.TEACHER,
            difficulty=3,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=2,
        )
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.9, misconceptions=[], missing_concepts=[], undefined_terms=[],
            knowledge_gap="half space elimination", recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.should_restore_interrupted_question is True
        assert decision.difficulty < 3  # Fallback to simpler difficulty


# =====================================================================
# 7. 17 DETERMINISTIC STATE-MACHINE SPECIFICATION TESTS
# =====================================================================

class TestCurioTeacherModeStateRefinement:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = DecisionEngine()

    def test_1_student_plus_explicit_teach_me(self):
        """TEST 1: Student + explicit 'teach me' -> Teacher Mode."""
        ctx = _make_context(user_msg="I don't know about the mechanism. can you teach me?", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.8, completeness=0.0, depth=0.0, relevance=0.9,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["FastAPI request mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert "explicit stuck signal" in decision.reason

    def test_2_student_plus_dont_understand_this(self):
        """TEST 2: Student + 'I don't understand this' -> Teacher Mode."""
        ctx = _make_context(user_msg="I don't understand this mechanism at all.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.05, clarity=0.7, completeness=0.0, depth=0.0, relevance=0.9,
            stuck_probability=0.9, misconceptions=[], missing_concepts=["FastAPI request flow"],
            undefined_terms=[], knowledge_gap="FastAPI request flow",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_3_student_plus_clearly_wrong_answer(self):
        """TEST 3: Student + clearly wrong answer -> Teacher Mode when major misconception/stuck criteria met."""
        ctx = _make_context(user_msg="Because FastAPI is a database.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.8, completeness=0.1, depth=0.0, relevance=0.8,
            stuck_probability=0.75, misconceptions=["FastAPI is a database"],
            missing_concepts=["ASGI framework"], undefined_terms=[],
            knowledge_gap="Confusing web framework with database",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=1
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_4_student_plus_partial_answer(self):
        """TEST 4: Student + partial answer -> Student Mode + probe."""
        ctx = _make_context(user_msg="Because ASGI makes it faster.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.55, clarity=0.7, completeness=0.5, depth=0.4, relevance=0.9,
            stuck_probability=0.1, misconceptions=[], missing_concepts=["ASGI server role"],
            undefined_terms=[], knowledge_gap="Does not explain how ASGI connects to FastAPI",
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy in (Strategy.PROBE_WHY, Strategy.PROBE_HOW, Strategy.PROBE_MISSING_CONCEPT)

    def test_5_student_plus_partial_then_correct(self):
        """TEST 5: Student + partial -> correct: Student remains active."""
        ctx = _make_context(
            user_msg="Uvicorn is an ASGI server that manages sockets and passes requests to FastAPI.",
            topic="FastAPI",
            consecutive_failures=0,
        )
        eval_turn = TurnEvaluation(
            correctness=0.9, clarity=0.9, completeness=0.85, depth=0.8, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["ASGI server role"], knowledge_gap=None,
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT

    def test_6_student_plus_partial_then_repeated_wrong(self):
        """TEST 6: Student + partial -> repeated wrong: Eventually Teacher Mode."""
        ctx = _make_context(
            user_msg="It uses magic to connect.",
            topic="FastAPI",
            consecutive_failures=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.6, misconceptions=["Magic connection"],
            missing_concepts=["ASGI interface"], undefined_terms=[],
            knowledge_gap="Cannot explain ASGI server connection",
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_7_teacher_plus_user_asks_teach_me(self):
        """TEST 7: Teacher + user asks 'teach me' -> Remain Teacher."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="can you teach me?",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.8, completeness=0.0, depth=0.0, relevance=0.8,
            stuck_probability=0.9, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_8_teacher_plus_user_asks_clarification(self):
        """TEST 8: Teacher + user asks clarification/question -> Remain Teacher."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Why is middleware involved in this process?",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.8, completeness=0.1, depth=0.1, relevance=0.9,
            stuck_probability=0.8, misconceptions=[], missing_concepts=["Middleware"],
            undefined_terms=[], knowledge_gap="Middleware in request pipeline",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_9_teacher_plus_wrong_verification_answer(self):
        """TEST 9: Teacher + wrong verification answer -> Remain Teacher."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Because FastAPI directly opens the TCP connection itself.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.7, completeness=0.2, depth=0.1, relevance=0.8,
            stuck_probability=0.8, misconceptions=["FastAPI opens TCP directly"],
            missing_concepts=["ASGI server role"], undefined_terms=[],
            knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_10_teacher_plus_partial_verification_answer(self):
        """TEST 10: Teacher + partial verification answer -> Remain Teacher + probe."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Because it handles the requests.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.5, clarity=0.7, completeness=0.4, depth=0.3, relevance=0.8,
            stuck_probability=0.3, misconceptions=[], missing_concepts=["Specific ASGI server responsibilities"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.PROBE_WHY
        assert decision.should_restore_interrupted_question is False

    def test_11_teacher_plus_correct_verification_answer(self):
        """TEST 11: Teacher + correct verification answer -> PASS -> restore interrupted question -> Student."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Because FastAPI is an ASGI application and the server, such as Uvicorn, handles the actual network communication and passes requests to the application.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.95, clarity=0.95, completeness=0.9, depth=0.85, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["FastAPI request handling mechanism"], knowledge_gap=None,
            recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.RESTORE_INTERRUPTED_QUESTION
        assert decision.should_restore_interrupted_question is True
        assert decision.active_concept == "FastAPI"

    def test_12_teacher_plus_i_dont_know(self):
        """TEST 12: Teacher + 'I don't know' -> Remain Teacher."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="I don't know.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.5,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_13_teacher_plus_i_still_dont_understand(self):
        """TEST 13: Teacher + 'I still don't understand' -> Remain Teacher + adapt explanation."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="I still don't understand.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.5,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_14_teacher_plus_yes_not_automatically_pass(self):
        """TEST 14: Teacher + 'yes' -> NOT automatically PASS."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="yes",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.6, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False

    def test_15_teacher_plus_okay_not_automatically_pass(self):
        """TEST 15: Teacher + 'okay' -> NOT automatically PASS."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="okay",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.6, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False

    def test_16_teacher_plus_teach_me_about_the_mechanism(self):
        """TEST 16: Teacher + 'ok teach me about the mechanism' -> NOT PASS. Expected: Explain mechanism -> ask verification -> remain Teacher."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="ok teach me about the mechanism",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.8, completeness=0.1, depth=0.0, relevance=0.8,
            stuck_probability=0.85, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        # MUST REMAIN IN TEACHER MODE - NOT PASS!
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_17_teacher_max_attempts_reached_without_understanding(self):
        """TEST 17: Teacher max attempts reached without understanding -> Do NOT mark mastered."""
        interrupted_q = CurrentQuestion(id="q_orig", content="How does FastAPI handle an incoming HTTP request?", concept="FastAPI", difficulty=3)
        intervention = TeacherIntervention(active=True, gap="FastAPI request handling mechanism", attempt_count=2, verification_required=True)
        ctx = _make_context(
            user_msg="I still don't get it at all.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            difficulty=3,
            interrupted_q=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=2,
        )
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.6,
            stuck_probability=0.9, misconceptions=[], missing_concepts=["FastAPI request handling mechanism"],
            undefined_terms=[], knowledge_gap="FastAPI request handling mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.should_restore_interrupted_question is True
        assert decision.difficulty < 3
        # Must not falsely claim mastery
        assert "mastered" not in decision.reason.lower()
        assert "without demonstrated understanding" in decision.reason or "maximum teacher attempts" in decision.reason.lower()


# =====================================================================
# 8. LEGACY BEHAVIORAL RECOVERY & ACCEPTANCE CRITERIA TESTS (27 Cases)
# =====================================================================

class TestLegacyBehavioralRecoveryAndAcceptanceCriteria:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.decision_engine = DecisionEngine()
        self.curio_engine = CurioEngine()

    def test_1_strong_answer_to_student(self):
        """1. Strong answer -> Student Mode."""
        ctx = _make_context(user_msg="FastAPI uses ASGI because ASGI provides an asynchronous standard interface allowing non-blocking I/O.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.95, clarity=0.9, completeness=0.9, depth=0.85, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["ASGI Interface"], knowledge_gap=None,
            recommended_strategy=Strategy.INCREASE_DIFFICULTY, recommended_difficulty=3
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT

    def test_2_partial_answer_to_student_probe(self):
        """2. Partial answer -> Student + probe."""
        ctx = _make_context(user_msg="Because it makes things faster.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.55, clarity=0.7, completeness=0.5, depth=0.4, relevance=0.8,
            stuck_probability=0.1, misconceptions=[], missing_concepts=["ASGI role"], undefined_terms=[],
            knowledge_gap="Missing async mechanism", recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy in (Strategy.PROBE_WHY, Strategy.PROBE_HOW, Strategy.PROBE_MISSING_CONCEPT)

    def test_3_partial_then_improved_to_student(self):
        """3. Partial answer -> improved answer -> Student."""
        ctx = _make_context(
            user_msg="The ASGI server handles socket connections and passes request dictionaries to FastAPI.",
            topic="FastAPI",
            consecutive_failures=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.9, clarity=0.9, completeness=0.85, depth=0.8, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["ASGI server role"], knowledge_gap=None,
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT

    def test_4_partial_then_repeated_failure_to_teacher(self):
        """4. Partial answer -> repeated failure -> Teacher."""
        ctx = _make_context(
            user_msg="I still have no clue how sockets connect.",
            topic="FastAPI",
            consecutive_failures=2,
        )
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.6, misconceptions=[], missing_concepts=["ASGI server"], undefined_terms=[],
            knowledge_gap="Cannot explain ASGI server connection",
            recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_5_clearly_wrong_to_teacher(self):
        """5. Clearly wrong answer / major misconception -> Teacher."""
        ctx = _make_context(user_msg="FastAPI is a database engine.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.8, completeness=0.1, depth=0.0, relevance=0.8,
            stuck_probability=0.75, misconceptions=["FastAPI is a database"], missing_concepts=["Web framework"], undefined_terms=[],
            knowledge_gap="Confusing web framework with database",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=1
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_6_idk_to_teacher(self):
        """6. 'I don't know' -> Teacher."""
        ctx = _make_context(user_msg="I don't know.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.5,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="Does not know ASGI mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_7_im_stuck_to_teacher(self):
        """7. 'I'm stuck' -> Teacher."""
        ctx = _make_context(user_msg="I'm stuck, help me.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.5,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="Stuck on ASGI mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_8_can_you_teach_me_to_teacher(self):
        """8. 'Can you teach me?' -> Teacher."""
        ctx = _make_context(user_msg="Can you teach me?", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.8, completeness=0.0, depth=0.0, relevance=0.8,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="Requested teaching on ASGI",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_9_explain_this_to_teacher(self):
        """9. 'Explain this' / 'Explain the mechanism' -> Teacher."""
        ctx = _make_context(user_msg="Explain the mechanism to me please.", topic="FastAPI")
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.8, completeness=0.0, depth=0.0, relevance=0.8,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="Requested explanation of mechanism",
            recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_10_teacher_plus_teach_me_again(self):
        """10. Teacher + 'teach me again' -> Teacher."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="Teach me again.", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.8,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP
        assert decision.should_restore_interrupted_question is False

    def test_11_teacher_plus_dont_understand(self):
        """11. Teacher + 'I don't understand' -> Teacher."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="I don't understand.", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.0, clarity=0.5, completeness=0.0, depth=0.0, relevance=0.8,
            stuck_probability=0.95, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False

    def test_12_teacher_plus_wrong_verification(self):
        """12. Teacher + wrong verification -> Teacher."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="Because FastAPI directly handles the TCP socket.", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.1, clarity=0.7, completeness=0.1, depth=0.0, relevance=0.8,
            stuck_probability=0.8, misconceptions=["FastAPI handles TCP"], missing_concepts=["ASGI server"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False

    def test_13_teacher_plus_partial_verification(self):
        """13. Teacher + partial verification -> Teacher + probe."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="Because it handles requests.", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.5, clarity=0.7, completeness=0.4, depth=0.3, relevance=0.8,
            stuck_probability=0.3, misconceptions=[], missing_concepts=["Server details"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.PROBE_WHY
        assert decision.should_restore_interrupted_question is False

    def test_14_teacher_plus_yes_not_verified(self):
        """14. Teacher + 'yes' -> NOT verified."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="yes", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.5, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False

    def test_15_teacher_plus_okay_not_verified(self):
        """15. Teacher + 'okay' -> NOT verified."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="okay", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.4, completeness=0.1, depth=0.0, relevance=0.5,
            stuck_probability=0.5, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False

    def test_16_teacher_plus_i_understand_not_verified(self):
        """16. Teacher + 'I understand now. Let me explain.' -> NOT verified until explanation demonstrated."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(user_msg="I understand now. Let me explain.", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        eval_turn = TurnEvaluation(
            correctness=0.2, clarity=0.6, completeness=0.1, depth=0.0, relevance=0.7,
            stuck_probability=0.4, misconceptions=[], missing_concepts=["ASGI mechanism"], undefined_terms=[],
            knowledge_gap="ASGI mechanism", recommended_strategy=Strategy.PROBE_WHY, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False
        assert "readiness" in decision.reason.lower() or "prompting" in decision.reason.lower()

    def test_17_teacher_plus_correct_explanation_to_student(self):
        """17. Teacher + correct explanation -> Student."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="The ASGI server manages the network connections and hands incoming HTTP events to the FastAPI application via ASGI.",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        eval_turn = TurnEvaluation(
            correctness=0.95, clarity=0.95, completeness=0.9, depth=0.85, relevance=1.0,
            stuck_probability=0.05, misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["ASGI mechanism"], knowledge_gap=None,
            recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION, recommended_difficulty=2
        )
        decision = self.decision_engine.decide(ctx, eval_turn)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy == Strategy.RESTORE_INTERRUPTED_QUESTION
        assert decision.should_restore_interrupted_question is True

    def test_18_interrupted_question_restored_only_after_pass(self):
        """18. Interrupted question restored only after PASS."""
        int_q = CurrentQuestion(id="q_int", content="Original question: Why FastAPI ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)

        # Turn with non-answer
        ctx_non_answer = _make_context(user_msg="okay", mode=Mode.TEACHER, interrupted_q=int_q, teacher_intervention=intervention, teacher_attempt_count=1)
        res_non_answer = self.curio_engine.process(ctx_non_answer)
        assert res_non_answer.decision.should_restore_interrupted_question is False
        assert res_non_answer.state_updates.interrupted_question is not None

        # Turn with correct answer
        ctx_pass = _make_context(
            user_msg="The asgi server handles incoming network communication and passes the request to the fastapi application.",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        res_pass = self.curio_engine.process(ctx_pass)
        assert res_pass.decision.should_restore_interrupted_question is True
        assert res_pass.state_updates.interrupted_question is None
        assert res_pass.state_updates.current_mode == Mode.STUDENT

    def test_19_teacher_state_survives_multiple_turns(self):
        """19. Teacher state survives multiple turns."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)

        # Turn 1: User asks a clarification question in Teacher Mode
        ctx_turn_1 = _make_context(
            user_msg="Can you explain that again?",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        res_turn_1 = self.curio_engine.process(ctx_turn_1)
        assert res_turn_1.decision.next_mode == Mode.TEACHER
        assert res_turn_1.state_updates.interrupted_question is not None
        assert res_turn_1.state_updates.teacher_intervention.active is True
        # Clarification turn does not consume an attempt limit
        assert res_turn_1.state_updates.teacher_attempt_count == 1

        # Turn 2: User provides correct verification
        ctx_turn_2 = _make_context(
            user_msg="The asgi server handles incoming network communication and passes the request to the fastapi app.",
            mode=Mode.TEACHER,
            interrupted_q=res_turn_1.state_updates.interrupted_question,
            teacher_intervention=res_turn_1.state_updates.teacher_intervention,
            teacher_attempt_count=res_turn_1.state_updates.teacher_attempt_count,
        )
        res_turn_2 = self.curio_engine.process(ctx_turn_2)
        assert res_turn_2.decision.next_mode == Mode.STUDENT
        assert res_turn_2.decision.should_restore_interrupted_question is True

    def test_20_teacher_state_survives_session_restoration(self):
        """20. Teacher state survives session restoration / persistence simulation."""
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        history = [
            ModeTransition(from_mode=Mode.STUDENT, to_mode=Mode.TEACHER, reason="Stuck signal", timestamp="2026-09-21T12:00:00Z", active_concept="ASGI mechanism")
        ]

        # Simulate state saved in DB
        saved_state_dict = {
            "session_id": "sess_restore_01",
            "current_mode": Mode.TEACHER,
            "current_difficulty": 2,
            "understanding_confidence": 0.5,
            "active_concept": "ASGI mechanism",
            "interrupted_question": int_q,
            "teacher_intervention": intervention,
            "teacher_attempt_count": 1,
            "mode_switch_history": history,
        }
        restored_state = SessionState(**saved_state_dict)

        ctx = AIContext(
            session=SessionInfo(session_id="sess_restore_01", topic="FastAPI"),
            current_state=restored_state,
            conversation=ConversationContext(recent_messages=[ChatMessage(role=Role.USER, content="Still confused.")]),
        )
        res = self.curio_engine.process(ctx)
        assert res.decision.next_mode == Mode.TEACHER
        assert res.state_updates.interrupted_question.content == "Why does FastAPI use ASGI?"
        assert res.state_updates.teacher_intervention.active is True
        assert len(res.state_updates.mode_switch_history) >= 1

    def test_21_mode_transition_history_recorded(self):
        """21. Mode transition history is recorded."""
        ctx = _make_context(user_msg="I don't know about the mechanism. Can you teach me?", topic="FastAPI")
        result = self.curio_engine.process(ctx)

        assert result.state_updates.mode_switch_history is not None
        assert len(result.state_updates.mode_switch_history) >= 1
        transition = result.state_updates.mode_switch_history[-1]
        assert transition.from_mode == Mode.STUDENT
        assert transition.to_mode == Mode.TEACHER
        assert len(transition.reason) > 0
        assert len(transition.timestamp) > 0

    def test_22_no_false_mastery_on_attempt_limit(self):
        """22. No false mastery on attempt limit fallback."""
        int_q = CurrentQuestion(id="q_orig", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=3)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=2, verification_required=True)
        ctx = _make_context(
            user_msg="I still have no idea, still completely stuck.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            difficulty=3,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=2,
        )
        result = self.curio_engine.process(ctx)

        assert result.decision.next_mode == Mode.STUDENT
        assert result.state_updates.current_mode == Mode.STUDENT
        assert "without demonstrated understanding" in result.decision.reason or "maximum teacher attempts" in result.decision.reason.lower()
        # Must not add to mastered concepts
        assert result.state_updates.mastered_concepts is None or "ASGI mechanism" not in result.state_updates.mastered_concepts

    def test_23_no_false_confidence(self):
        """23. No false confidence inflation on failed turns."""
        int_q = CurrentQuestion(id="q_orig", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="wrong answer, totally lost.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            confidence=0.5,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        result = self.curio_engine.process(ctx)
        assert result.decision.confidence <= 0.5

    def test_24_exact_acceptance_criteria_fastapi_dialogue(self):
        """
        24. Exact Acceptance Criteria Conversation:
        - AI asks "Why does FastAPI use ASGI?"
        - Learner: "I don't know about the mechanism. Can you teach me?" -> STUDENT -> TEACHER
        - AI teaches exact mechanism, asks one verification question.
        - Learner: "Can you explain that again?" -> TEACHER remains active, Curio explains/adapts, asks another verification question.
        - Learner: "I think the ASGI server handles the incoming network communication and passes the request to the FastAPI application through the ASGI interface."
          -> TEACHER -> STUDENT (restores original interrupted question).
        """
        engine = CurioEngine()

        # Step 1: Learner asks to be taught in Student Mode
        ctx_turn_1 = _make_context(
            user_msg="I don't know about the mechanism. Can you teach me?",
            topic="FastAPI",
            current_q_content="Why does FastAPI use ASGI?",
            difficulty=2,
        )
        res_turn_1 = engine.process(ctx_turn_1)

        assert res_turn_1.decision.next_mode == Mode.TEACHER
        assert res_turn_1.response.mode == Mode.TEACHER
        assert res_turn_1.state_updates.current_mode == Mode.TEACHER
        assert res_turn_1.state_updates.interrupted_question.content == "Why does FastAPI use ASGI?"
        assert res_turn_1.response.content.count("?") == 1
        assert "asgi" in res_turn_1.response.content.lower()

        # Step 2: Learner asks "Can you explain that again?" in Teacher Mode
        ctx_turn_2 = _make_context(
            user_msg="Can you explain that again?",
            topic="FastAPI",
            mode=Mode.TEACHER,
            difficulty=2,
            current_q_content=res_turn_1.response.content,
            interrupted_q=res_turn_1.state_updates.interrupted_question,
            teacher_intervention=res_turn_1.state_updates.teacher_intervention,
            teacher_attempt_count=res_turn_1.state_updates.teacher_attempt_count,
        )
        res_turn_2 = engine.process(ctx_turn_2)

        # Expected: TEACHER remains active, Curio explains/adapts, asks verification question
        assert res_turn_2.decision.next_mode == Mode.TEACHER
        assert res_turn_2.response.mode == Mode.TEACHER
        assert res_turn_2.decision.should_restore_interrupted_question is False
        assert res_turn_2.state_updates.interrupted_question is not None
        assert res_turn_2.response.content.count("?") == 1

        # Step 3: Learner provides valid explanation
        ctx_turn_3 = _make_context(
            user_msg="I think the ASGI server handles the incoming network communication and passes the request to the FastAPI application through the ASGI interface.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            difficulty=2,
            current_q_content=res_turn_2.response.content,
            interrupted_q=res_turn_2.state_updates.interrupted_question,
            teacher_intervention=res_turn_2.state_updates.teacher_intervention,
            teacher_attempt_count=res_turn_2.state_updates.teacher_attempt_count,
        )
        res_turn_3 = engine.process(ctx_turn_3)

        # Expected: Evaluated PASS -> TEACHER -> STUDENT -> Restore original question
        assert res_turn_3.decision.next_mode == Mode.STUDENT
        assert res_turn_3.decision.should_restore_interrupted_question is True
        assert res_turn_3.state_updates.current_mode == Mode.STUDENT
        assert res_turn_3.state_updates.current_question.content == "Why does FastAPI use ASGI?"
        assert res_turn_3.state_updates.interrupted_question is None
        assert res_turn_3.state_updates.teacher_intervention.active is False
        assert "Why does FastAPI use ASGI?" in res_turn_3.response.content

    def test_25_teacher_asks_verification_learner_says_okay_teach_me(self):
        """25. Second Required Scenario: Teacher asks verification. Learner: 'Okay, teach me about the mechanism.' -> NOT verified, remain Teacher."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Okay, teach me about the mechanism.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        res = self.curio_engine.process(ctx)
        assert res.decision.next_mode == Mode.TEACHER
        assert res.decision.should_restore_interrupted_question is False
        assert res.state_updates.interrupted_question is not None

    def test_26_teacher_asks_verification_learner_gives_completely_wrong_answer(self):
        """26. Third Required Scenario: Teacher asks verification. Learner gives completely wrong answer -> NOT verified, remain Teacher."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Because FastAPI directly opens the TCP connection itself.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        res = self.curio_engine.process(ctx)
        assert res.decision.next_mode == Mode.TEACHER
        assert res.decision.should_restore_interrupted_question is False
        assert res.state_updates.interrupted_question is not None

    def test_27_teacher_asks_verification_learner_gives_partial_answer(self):
        """27. Fourth Required Scenario: Teacher asks verification. Learner gives partial answer -> NOT verified, remain Teacher + targeted probe."""
        int_q = CurrentQuestion(id="q_int", content="Why does FastAPI use ASGI?", concept="FastAPI", difficulty=2)
        intervention = TeacherIntervention(active=True, gap="ASGI mechanism", attempt_count=1, verification_required=True)
        ctx = _make_context(
            user_msg="Because it handles the requests.",
            topic="FastAPI",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            teacher_intervention=intervention,
            teacher_attempt_count=1,
        )
        res = self.curio_engine.process(ctx)
        assert res.decision.next_mode == Mode.TEACHER
        assert res.decision.should_restore_interrupted_question is False
        assert res.decision.strategy in (Strategy.PROBE_WHY, Strategy.PROBE_HOW)



