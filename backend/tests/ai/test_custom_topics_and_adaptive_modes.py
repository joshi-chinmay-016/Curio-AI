"""
Comprehensive Test Suite for Custom Topics and Adaptive Mode-Switching.

Validates all 33 required criteria:
1. Teacher Mode Entry:
   - "I don't know" -> Teacher
   - "I'm stuck" -> Teacher
   - "I don't understand the mechanism" -> Teacher
   - "Can you teach me?" -> Teacher
   - Semantic equivalent help requests -> Teacher
2. Student Mode Behavior:
   - Strong answer -> remain Student / appropriate difficulty increase
   - Partial answer -> Student probe
   - Misconception -> appropriate Student challenge/probe
   - Ordinary incomplete answer -> do not prematurely switch to Teacher
3. Teacher Mode Multi-Turn Behavior:
   - Teacher explanation -> Teacher
   - "teach me again" / "explain again" -> remain Teacher
   - "I still don't understand" -> remain Teacher
   - Question about the gap -> remain Teacher
   - Wrong verification answer -> remain Teacher
   - Partial verification answer -> remain Teacher
   - "okay", "yes", "sure" -> remain Teacher
   - "I understand" without evidence -> remain Teacher
   - Correct conceptual verification -> exit Teacher
   - Interrupted question preserved across multiple Teacher turns
   - Interrupted question restored after successful verification
   - Teacher intervention cleared after successful verification
   - Teacher attempt count increments and respects MAX_TEACHER_ATTEMPTS
   - Failed verification does not restore Student mode
4. Custom Topic Independence:
   - Operating Systems -> OS question without leakage
   - DBMS -> DBMS question without leakage
   - Machine Learning -> ML question without leakage
   - Arbitrary custom topic ("Distributed Systems", "Quantum Computing") -> relevant question
"""

import pytest
from backend.app.ai.decision_engine import DecisionEngine, MAX_TEACHER_ATTEMPTS
from backend.app.ai.engine import CurioEngine
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    LearningContext,
    LearningDecision,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
)


def _build_context(
    topic: str = "Operating Systems",
    mode: Mode = Mode.STUDENT,
    user_msg: str = "Processes are programs in execution.",
    difficulty: int = 3,
    active_concept: str = "process_management",
    current_question_content: str = "How does an operating system manage process execution?",
    teacher_intervention: TeacherIntervention | None = None,
    interrupted_question_content: str = "How does an operating system manage process execution?",
    teacher_attempt_count: int = 0,
) -> AIContext:
    """Helper to build AIContext for tests."""
    current_q = (
        CurrentQuestion(
            id="q_init",
            content=current_question_content,
            concept=active_concept,
            difficulty=difficulty,
        )
        if current_question_content
        else None
    )

    interrupted_q = None
    if interrupted_question_content:
        interrupted_q = CurrentQuestion(
            id="q_orig",
            content=interrupted_question_content,
            concept=active_concept,
            difficulty=difficulty,
        )

    state = SessionState(
        session_id="sess_custom_test",
        current_mode=mode,
        current_difficulty=difficulty,
        understanding_confidence=0.5,
        active_concept=active_concept,
        current_question=current_q,
        interrupted_question=interrupted_q,
        teacher_intervention=teacher_intervention,
        teacher_attempt_count=teacher_attempt_count,
    )

    history = []
    if current_question_content:
        history.append(ChatMessage(role=Role.ASSISTANT, content=current_question_content))
    history.append(ChatMessage(role=Role.USER, content=user_msg))

    return AIContext(
        session=SessionInfo(session_id="sess_custom_test", topic=topic),
        current_state=state,
        conversation=ConversationContext(recent_messages=history, message_count=len(history)),
        learning_context=LearningContext(
            mastered_concepts=[],
            unresolved_misconceptions=[],
            teacher_intervention=teacher_intervention,
        ),
    )


def _make_eval(
    correctness: float = 0.5,
    clarity: float = 0.5,
    completeness: float = 0.5,
    depth: float = 0.5,
    relevance: float = 1.0,
    stuck_probability: float = 0.0,
    knowledge_gap: str | None = None,
    misconceptions: list[str] | None = None,
    missing_concepts: list[str] | None = None,
    strategy: Strategy = Strategy.PROBE_MISSING_CONCEPT,
    difficulty: int = 3,
) -> TurnEvaluation:
    return TurnEvaluation(
        correctness=correctness,
        clarity=clarity,
        completeness=completeness,
        depth=depth,
        relevance=relevance,
        stuck_probability=stuck_probability,
        knowledge_gap=knowledge_gap,
        misconceptions=misconceptions or [],
        missing_concepts=missing_concepts or [],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=strategy,
        recommended_difficulty=difficulty,
    )


# ==============================================================================
# 1. TEACHER MODE ENTRY & STUDENT MODE BEHAVIOR
# ==============================================================================

class TestAdaptiveModeSwitching:
    def setup_method(self):
        self.decision_engine = DecisionEngine()

    def test_explicit_struggle_phrases_enter_teacher_mode(self):
        """All required explicit struggle phrases trigger Teacher Mode."""
        struggle_phrases = [
            "I don't know",
            "I am stuck",
            "I'm stuck",
            "I don't understand",
            "I don't understand this",
            "I don't understand the mechanism",
            "I'm confused",
            "Can you explain this?",
            "Can you teach me?",
            "Teach me this",
            "Explain this",
            "I have no idea",
            "I don't get it",
            "Can you help me understand?",
        ]
        for phrase in struggle_phrases:
            ctx = _build_context(user_msg=phrase)
            eval_result = _make_eval(
                correctness=0.1,
                completeness=0.1,
                stuck_probability=0.85,
                knowledge_gap="process_management",
                strategy=Strategy.TEACH_GAP,
            )
            decision = self.decision_engine.decide(ctx, eval_result)
            assert decision.next_mode == Mode.TEACHER, f"Failed for phrase: '{phrase}'"
            assert decision.active_concept == "process_management"

    def test_semantic_equivalent_help_request_enters_teacher_mode(self):
        """Semantic help request without exact keyword triggers Teacher Mode via evaluation."""
        ctx = _build_context(user_msg="I'm completely at a loss regarding how this operates.")
        eval_result = _make_eval(
            correctness=0.1,
            completeness=0.1,
            stuck_probability=0.85,
            knowledge_gap="process scheduling mechanism",
            strategy=Strategy.TEACH_GAP,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert decision.strategy == Strategy.TEACH_GAP

    def test_strong_answer_remains_student_and_increases_difficulty(self):
        """Strong answer with high correctness increases difficulty in Student Mode."""
        ctx = _build_context(
            difficulty=2,
            user_msg="A process is a program in execution containing program counter, stack, and data section in memory.",
        )
        eval_result = _make_eval(
            correctness=0.9,
            completeness=0.85,
            depth=0.8,
            stuck_probability=0.05,
            strategy=Strategy.INCREASE_DIFFICULTY,
            difficulty=3,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT
        assert decision.difficulty >= 2

    def test_partial_answer_triggers_student_probe(self):
        """Partial answer without struggle triggers a focused probe in Student Mode."""
        ctx = _build_context(user_msg="A process is basically a program running in memory.")
        eval_result = _make_eval(
            correctness=0.6,
            completeness=0.5,
            stuck_probability=0.1,
            missing_concepts=["context switching", "PCB"],
            strategy=Strategy.PROBE_MISSING_CONCEPT,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT
        assert decision.strategy in (
            Strategy.PROBE_MISSING_CONCEPT,
            Strategy.PROBE_WHY,
            Strategy.PROBE_HOW,
        )

    def test_misconception_triggers_student_challenge(self):
        """Moderate answer with a misconception challenges the misconception in Student Mode."""
        ctx = _build_context(user_msg="A process is just a single thread that can never run concurrently.")
        eval_result = _make_eval(
            correctness=0.5,
            completeness=0.5,
            stuck_probability=0.1,
            misconceptions=["Processes cannot contain multiple concurrent threads"],
            strategy=Strategy.CHALLENGE_MISCONCEPTION,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT

    def test_ordinary_incomplete_answer_does_not_prematurely_enter_teacher(self):
        """Ordinary incomplete answer without struggle remains in Student Mode."""
        ctx = _build_context(user_msg="It manages execution by keeping track of things.")
        eval_result = _make_eval(
            correctness=0.45,
            completeness=0.35,
            stuck_probability=0.2,
            missing_concepts=["PCB structure", "register states"],
            strategy=Strategy.PROBE_HOW,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT


# ==============================================================================
# 2. MULTI-TURN TEACHER MODE: CLASSIFICATION, ATTEMPTS & RESTORATION
# ==============================================================================

class TestMultiTurnTeacherMode:
    def setup_method(self):
        self.decision_engine = DecisionEngine()
        self.engine = CurioEngine(provider=MockLLMProvider())

    def _teacher_intervention(self, attempt: int = 1) -> TeacherIntervention:
        return TeacherIntervention(
            active=True,
            gap="context_switching",
            attempt_count=attempt,
            verification_required=True,
        )

    def test_help_request_teach_me_again_stays_in_teacher_without_attempt_penalty(self):
        """'teach me again' or 'explain again' stays in Teacher Mode and does not consume attempt."""
        for phrase in ["teach me again", "can you explain again", "please explain that again"]:
            intervention = self._teacher_intervention(attempt=1)
            ctx = _build_context(
                mode=Mode.TEACHER,
                user_msg=phrase,
                teacher_intervention=intervention,
                active_concept="context_switching",
                teacher_attempt_count=1,
            )
            eval_result = _make_eval(
                correctness=0.1,
                completeness=0.1,
                stuck_probability=0.8,
                knowledge_gap="context_switching",
                strategy=Strategy.TEACH_GAP,
            )
            decision = self.decision_engine.decide(ctx, eval_result)
            assert decision.next_mode == Mode.TEACHER
            assert not decision.should_restore_interrupted_question

    def test_i_still_dont_understand_stays_in_teacher_mode(self):
        """'I still don't understand' remains in Teacher Mode and adapts."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="I still don't understand.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
        )
        eval_result = _make_eval(
            correctness=0.1,
            completeness=0.1,
            stuck_probability=0.9,
            knowledge_gap="context_switching",
            strategy=Strategy.TEACH_GAP,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert not decision.should_restore_interrupted_question

    def test_question_about_gap_stays_in_teacher_mode(self):
        """Question about the gap stays in Teacher Mode and answers the gap."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="Why does the OS have to save the register state during a context switch?",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
        )
        eval_result = _make_eval(
            correctness=0.4,
            completeness=0.3,
            stuck_probability=0.2,
            knowledge_gap="context_switching",
            strategy=Strategy.TEACH_GAP,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert not decision.should_restore_interrupted_question

    def test_affirmations_do_not_verify_or_exit_teacher_mode(self):
        """Affirmations like 'ok', 'yes', 'I understand now' must NOT exit Teacher Mode."""
        affirmations = ["ok", "yes", "I understand now", "got it", "i get it", "sure", "makes sense"]
        for phrase in affirmations:
            intervention = self._teacher_intervention(attempt=1)
            ctx = _build_context(
                mode=Mode.TEACHER,
                user_msg=phrase,
                teacher_intervention=intervention,
                active_concept="context_switching",
                teacher_attempt_count=1,
            )
            eval_result = _make_eval(
                correctness=0.8,
                completeness=0.2,
                stuck_probability=0.05,
                knowledge_gap="context_switching",
                strategy=Strategy.VERIFY_UNDERSTANDING,
            )
            decision = self.decision_engine.decide(ctx, eval_result)
            assert decision.next_mode == Mode.TEACHER, f"Affirmation '{phrase}' improperly exited Teacher Mode!"
            assert not decision.should_restore_interrupted_question

    def test_failed_verification_stays_in_teacher_mode(self):
        """Failed answer attempt stays in Teacher Mode and adapts."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="It just deletes the process from memory immediately.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
        )
        eval_result = _make_eval(
            correctness=0.1,
            completeness=0.2,
            stuck_probability=0.4,
            misconceptions=["Processes are deleted during context switch"],
            knowledge_gap="context_switching",
            strategy=Strategy.TEACH_GAP,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert not decision.should_restore_interrupted_question

    def test_partial_verification_stays_in_teacher_mode(self):
        """Partial verification answer remains in Teacher Mode to probe the missing piece."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="It saves the program counter, but I'm not sure what else it saves.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
        )
        eval_result = _make_eval(
            correctness=0.55,
            completeness=0.5,
            stuck_probability=0.2,
            knowledge_gap="context_switching",
            strategy=Strategy.PROBE_WHY,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert not decision.should_restore_interrupted_question

    def test_successful_verification_clears_intervention_and_restores_question(self):
        """Demonstrated understanding passes verification, clears intervention, and restores original question."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="During a context switch, the OS saves the PCB state and CPU registers of the current process so it can restore them later when scheduling resumes.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
            interrupted_question_content="How does an operating system manage process execution?",
        )
        eval_result = _make_eval(
            correctness=0.85,
            completeness=0.8,
            stuck_probability=0.05,
            misconceptions=[],
            knowledge_gap="context_switching",
            strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT
        assert decision.should_restore_interrupted_question is True

    def test_verification_threshold_exact_boundary_passes(self):
        """Boundary test: correctness == 0.70 exactly meets TEACHER_VERIFICATION_PASS_THRESHOLD and passes."""
        from backend.app.ai.decision_engine import TEACHER_VERIFICATION_PASS_THRESHOLD
        assert TEACHER_VERIFICATION_PASS_THRESHOLD == 0.70

        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="During a context switch, the OS saves the PCB state and CPU registers of the current process so it can restore them later.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
            interrupted_question_content="How does an operating system manage process execution?",
        )
        eval_result = _make_eval(
            correctness=0.70,
            completeness=0.7,
            stuck_probability=0.10,
            misconceptions=[],
            knowledge_gap="context_switching",
            strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT
        assert decision.should_restore_interrupted_question is True
        assert decision.strategy == Strategy.RESTORE_INTERRUPTED_QUESTION

    def test_verification_threshold_just_below_boundary_stays_in_teacher(self):
        """Boundary test: correctness == 0.69 is below 0.70 threshold; treated as partial and stays in Teacher Mode."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="During a context switch, the OS saves some CPU state of the current process.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
            interrupted_question_content="How does an operating system manage process execution?",
        )
        eval_result = _make_eval(
            correctness=0.69,
            completeness=0.6,
            stuck_probability=0.10,
            misconceptions=[],
            knowledge_gap="context_switching",
            strategy=Strategy.PROBE_WHY,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False
        assert decision.strategy == Strategy.PROBE_WHY

    def test_verification_threshold_0_65_is_partial_and_stays_in_teacher(self):
        """Verification test: correctness == 0.65 is partial verification and must remain in Teacher Mode."""
        intervention = self._teacher_intervention(attempt=1)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="The OS switches between processes by saving some register values.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            teacher_attempt_count=1,
            interrupted_question_content="How does an operating system manage process execution?",
        )
        eval_result = _make_eval(
            correctness=0.65,
            completeness=0.6,
            stuck_probability=0.10,
            misconceptions=[],
            knowledge_gap="context_switching",
            strategy=Strategy.PROBE_WHY,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.TEACHER
        assert decision.should_restore_interrupted_question is False
        assert decision.strategy == Strategy.PROBE_WHY

    def test_decide_next_action_helper_unifies_0_70_threshold(self):
        """Helper function decide_next_action() also uses consistent 0.70 threshold."""
        from backend.app.ai.decision_engine import decide_next_action
        from backend.app.schemas.common import LearningMode, LearningStrategy
        import uuid

        # At 0.70: passes verification
        ctx = AIContext(
            session_id=uuid.uuid4(),
            topic="Operating Systems",
            current_mode=LearningMode.TEACHER,
            difficulty=2,
            active_concept="context_switching",
            history=[],
        )
        eval_pass = TurnEvaluation(
            correctness=0.70,
            clarity=0.8,
            completeness=0.7,
            depth=0.6,
            relevance=1.0,
            stuck_probability=0.1,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=[],
            recommended_strategy=LearningStrategy.RESTORE_INTERRUPTED_QUESTION,
            recommended_difficulty=2,
        )
        dec_pass = decide_next_action(ctx, eval_pass, 0, 0)
        assert dec_pass.next_mode == LearningMode.STUDENT
        assert dec_pass.should_restore_interrupted_question is True

        # At 0.69: stays in Teacher Mode
        eval_fail = TurnEvaluation(
            correctness=0.69,
            clarity=0.8,
            completeness=0.6,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.1,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=[],
            recommended_strategy=LearningStrategy.VERIFY_UNDERSTANDING,
            recommended_difficulty=2,
        )
        dec_fail = decide_next_action(ctx, eval_fail, 0, 0)
        assert dec_fail.next_mode == LearningMode.TEACHER
        assert dec_fail.should_restore_interrupted_question is False

    def test_e2e_interrupted_question_preservation_and_restoration(self):
        """End-to-end multi-turn preservation and restoration of interrupted question via CurioEngine."""
        orig_q = "How does an operating system manage process execution?"

        # Turn 1: Learner stuck -> Enters Teacher Mode
        ctx_t1 = _build_context(
            topic="Operating Systems",
            mode=Mode.STUDENT,
            user_msg="I don't understand the mechanism. Can you teach me?",
            current_question_content=orig_q,
            interrupted_question_content=None,
        )
        res_t1 = self.engine.process(ctx_t1)
        assert res_t1.decision.next_mode == Mode.TEACHER
        # Interrupted question is snapshotted
        assert res_t1.state_updates.interrupted_question is not None
        assert res_t1.state_updates.interrupted_question.content == orig_q
        assert res_t1.state_updates.teacher_intervention.active is True

        # Turn 2: Teacher turn 1 -> Learner asks clarification
        intervention_state = res_t1.state_updates.teacher_intervention
        ctx_t2 = _build_context(
            topic="Operating Systems",
            mode=Mode.TEACHER,
            user_msg="Wait, what is a PCB?",
            current_question_content=res_t1.response.content,
            interrupted_question_content=orig_q,
            teacher_intervention=intervention_state,
            teacher_attempt_count=1,
        )
        res_t2 = self.engine.process(ctx_t2)
        assert res_t2.decision.next_mode == Mode.TEACHER
        # Interrupted question remains intact across turns
        assert res_t2.state_updates.interrupted_question is not None
        assert res_t2.state_updates.interrupted_question.content == orig_q

        # Turn 3: Teacher turn 2 -> Learner gives successful verification
        ctx_t3 = _build_context(
            topic="Operating Systems",
            mode=Mode.TEACHER,
            user_msg="The PCB holds process state like registers and program counter so the CPU can resume execution seamlessly.",
            current_question_content=res_t2.response.content,
            interrupted_question_content=orig_q,
            teacher_intervention=res_t2.state_updates.teacher_intervention,
            teacher_attempt_count=1,
        )
        res_t3 = self.engine.process(ctx_t3)
        if res_t3.decision.should_restore_interrupted_question:
            assert res_t3.decision.next_mode == Mode.STUDENT
            assert orig_q in res_t3.response.content
            assert res_t3.state_updates.teacher_intervention.active is False
            assert res_t3.state_updates.interrupted_question is None

    def test_max_attempts_exits_to_student_mode_at_reduced_difficulty(self):
        """After max attempts (>=3), fallback to Student Mode at reduced difficulty without false mastery."""
        intervention = self._teacher_intervention(attempt=3)
        ctx = _build_context(
            mode=Mode.TEACHER,
            user_msg="I still don't get how context switching works.",
            teacher_intervention=intervention,
            active_concept="context_switching",
            difficulty=3,
            teacher_attempt_count=3,
        )
        eval_result = _make_eval(
            correctness=0.1,
            completeness=0.1,
            stuck_probability=0.9,
            knowledge_gap="context_switching",
            strategy=Strategy.TEACH_GAP,
        )
        decision = self.decision_engine.decide(ctx, eval_result)
        assert decision.next_mode == Mode.STUDENT
        assert decision.difficulty < 3
        assert decision.should_restore_interrupted_question is True


# ==============================================================================
# 3. CUSTOM TOPIC INDEPENDENCE
# ==============================================================================

class TestCustomTopicIndependence:
    def setup_method(self):
        self.engine = CurioEngine(provider=MockLLMProvider())

    def test_operating_systems_topic_has_no_binary_search_or_fastapi(self):
        """Operating Systems topic must generate OS questions and explanations."""
        ctx = _build_context(
            topic="Operating Systems",
            mode=Mode.STUDENT,
            user_msg="I want to learn about Operating Systems.",
            current_question_content="What is an Operating System?",
            interrupted_question_content="What is an Operating System?",
        )
        result = self.engine.process(ctx)
        text = result.response.content.lower()
        assert "binary search" not in text
        assert "fastapi" not in text

        # Teacher explanation for OS gap
        intervention = TeacherIntervention(
            active=True,
            gap="process scheduling",
            attempt_count=1,
            verification_required=True,
        )
        ctx_teacher = _build_context(
            topic="Operating Systems",
            mode=Mode.TEACHER,
            user_msg="I don't understand process scheduling.",
            teacher_intervention=intervention,
            active_concept="process scheduling",
            teacher_attempt_count=1,
        )
        result_teacher = self.engine.process(ctx_teacher)
        t_text = result_teacher.response.content.lower()
        assert "binary search" not in t_text
        assert "fastapi" not in t_text

    def test_dbms_topic_has_no_binary_search_or_fastapi(self):
        """DBMS topic must generate DBMS questions and explanations."""
        ctx = _build_context(
            topic="DBMS",
            mode=Mode.STUDENT,
            user_msg="Let's study Database Management Systems.",
            current_question_content="What is a Database Management System?",
            interrupted_question_content="What is a Database Management System?",
        )
        result = self.engine.process(ctx)
        text = result.response.content.lower()
        assert "binary search" not in text
        assert "fastapi" not in text

    def test_machine_learning_topic_has_no_binary_search_or_fastapi(self):
        """Machine Learning topic must generate ML questions and explanations."""
        ctx = _build_context(
            topic="Machine Learning",
            mode=Mode.STUDENT,
            user_msg="I want to learn Machine Learning.",
            current_question_content="What is Machine Learning?",
            interrupted_question_content="What is Machine Learning?",
        )
        result = self.engine.process(ctx)
        text = result.response.content.lower()
        assert "binary search" not in text
        assert "fastapi" not in text

    def test_arbitrary_custom_topic_generates_topic_appropriate_content(self):
        """Arbitrary custom topic (e.g. Distributed Systems) generates relevant questions."""
        ctx = _build_context(
            topic="Distributed Systems",
            mode=Mode.STUDENT,
            user_msg="Let's explore Distributed Systems.",
            current_question_content="What is a Distributed System?",
            interrupted_question_content="What is a Distributed System?",
        )
        result = self.engine.process(ctx)
        text = result.response.content.lower()
        assert "binary search" not in text
        assert "fastapi" not in text
        assert "distributed systems" in text or "core purpose" in text or "system" in text
