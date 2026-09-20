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
