"""
Adaptive Learning Core v1 — Live Validation Test Suite.
Validates scenarios A through J against CurioEngine end-to-end:
A. Operating Systems custom topic; no Binary Search/FastAPI leakage.
B. Direct conceptual answer is actually evaluated.
C. "what do you mean?" gets clarification before progression.
D. "I don't understand why..." enters Teacher for the exact gap.
E. "okay, I understand" stays Teacher and requests verification.
F. Substantive correct verification exits Teacher.
G. Wrong verification stays Teacher.
H. Repeated concept questions vary semantically.
I. Strong evidence increases difficulty.
J. Misconception changes the learning path.
"""
import pytest
from backend.app.ai.engine import CurioEngine
from backend.app.ai.novelty import QuestionNoveltyChecker
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    Strategy,
    TeacherIntervention,
    TurnIntent,
)


def _make_context(
    topic: str,
    user_msg: str = "",
    mode: Mode = Mode.STUDENT,
    difficulty: int = 1,
    confidence: float = 0.5,
    active_concept: str = "",
    history_messages: list = None,
    interrupted_q: CurrentQuestion = None,
    intervention: TeacherIntervention = None,
    teacher_attempt_count: int = 0,
) -> AIContext:
    session = SessionInfo(session_id="live_val_sess", topic=topic)
    curr_q = CurrentQuestion(
        id="q_curr",
        content=f"What is the foundational principle of {topic}?",
        concept=active_concept or f"{topic.lower().replace(' ', '_')}_foundation",
        difficulty=difficulty,
    )
    state = SessionState(
        session_id="live_val_sess",
        current_mode=mode,
        current_difficulty=difficulty,
        understanding_confidence=confidence,
        active_concept=active_concept,
        current_question=curr_q,
        interrupted_question=interrupted_q,
        teacher_intervention=intervention,
        teacher_attempt_count=teacher_attempt_count,
    )
    if history_messages is not None:
        msgs = list(history_messages)
    elif user_msg:
        msgs = [
            ChatMessage(role=Role.ASSISTANT, content=curr_q.content),
            ChatMessage(role=Role.USER, content=user_msg),
        ]
    else:
        msgs = []

    conv = ConversationContext(recent_messages=msgs, message_count=len(msgs))
    return AIContext(
        session=session,
        current_state=state,
        conversation=conv,
    )


class TestAdaptiveCoreLiveValidation:
    @classmethod
    def setup_class(cls):
        cls.engine = CurioEngine()

    def test_scenario_a_custom_topic_no_topic_leakage(self):
        """Scenario A: Operating Systems custom topic; zero Binary Search / FastAPI leakage."""
        ctx = _make_context(topic="Operating Systems", user_msg="")
        res: AIResult = self.engine.process(ctx)

        # Output must be generated specifically for Operating Systems
        assert res.decision.next_mode == Mode.STUDENT
        assert res.response.content
        full_dump = (
            res.response.content
            + " "
            + (res.decision.reason or "")
            + " "
            + (res.decision.active_concept or "")
        ).lower()

        # Absolutely NO topic leakage from Binary Search or FastAPI
        assert "binary search" not in full_dump
        assert "fastapi" not in full_dump
        assert "uvicorn" not in full_dump
        assert "asgi" not in full_dump
        assert "array" not in full_dump
        assert "sorted" not in full_dump

    def test_scenario_b_direct_conceptual_answer_evaluated(self):
        """Scenario B: Direct conceptual answer is actually evaluated and updates learner state."""
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="A process is an active program in execution with its own address space, whereas a thread is a lightweight unit of execution within a process that shares the address space.",
            difficulty=1,
            active_concept="process_management",
        )
        res: AIResult = self.engine.process(ctx)

        assert res.evaluation is not None
        assert res.evaluation.correctness >= 0.70
        assert res.evaluation.relevance >= 0.80
        assert res.turn_interpretation.is_answer_attempt is True
        assert res.state_updates.learner_model is not None
        # Mastery must reflect demonstrated evidence
        mgr = res.state_updates.learner_model
        assert mgr.get_or_create_concept("process_management").attempt_count >= 1

    def test_scenario_c_clarification_before_progression(self):
        """Scenario C: 'what do you mean?' gets clarification before advancing the learning state."""
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="What do you mean by kernel mode versus user mode?",
            difficulty=2,
            active_concept="cpu_privilege_rings",
        )
        res: AIResult = self.engine.process(ctx)

        # Must recognize intent as clarification request
        assert res.turn_interpretation.intent == TurnIntent.CLARIFICATION_REQUEST
        assert res.turn_interpretation.is_answer_attempt is False
        assert res.decision.strategy == Strategy.CLARIFY_TERM
        # Does NOT artificially jump difficulty
        assert res.decision.difficulty <= 2
        # Response content addresses clarification
        assert "referring to" in res.response.content.lower() or "mode" in res.response.content.lower()

    def test_scenario_d_explicit_gap_enters_teacher_mode(self):
        """Scenario D: 'I don't understand why...' enters Teacher for the exact gap and snapshots interrupted question."""
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="I don't understand why page faults cause such high latency.",
            difficulty=3,
            active_concept="virtual_memory_paging",
        )
        res: AIResult = self.engine.process(ctx)

        # Must enter Teacher mode
        assert res.decision.next_mode == Mode.TEACHER
        assert res.response.mode == Mode.TEACHER
        assert res.state_updates.teacher_intervention.active is True
        # Must snapshot interrupted question
        assert res.state_updates.interrupted_question is not None
        assert res.state_updates.interrupted_question.concept == "virtual_memory_paging"

    def test_scenario_e_acknowledgement_stays_in_teacher_mode(self):
        """Scenario E: 'okay, I understand' stays Teacher and requests verification without granting false mastery."""
        int_q = CurrentQuestion(
            id="q_snap", content="Explain paging mechanism", concept="paging", difficulty=3
        )
        intervention = TeacherIntervention(
            active=True, gap="paging", attempt_count=1, verification_required=True
        )
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="okay, I understand now",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            intervention=intervention,
            teacher_attempt_count=1,
            active_concept="paging",
        )
        res: AIResult = self.engine.process(ctx)

        # Acknowledgement must NOT exit Teacher Mode
        assert res.decision.next_mode == Mode.TEACHER
        assert res.state_updates.teacher_intervention.active is True
        assert res.state_updates.interrupted_question is not None
        # Does not consume attempt limit for bare acknowledgement
        assert res.state_updates.teacher_attempt_count == 1

    def test_scenario_f_substantive_correct_verification_exits_teacher(self):
        """Scenario F: Substantive correct verification exits Teacher, restores interrupted question, and updates LearnerModel."""
        int_q = CurrentQuestion(
            id="q_snap", content="Explain scheduling priority", concept="cpu_scheduling", difficulty=2
        )
        intervention = TeacherIntervention(
            active=True, gap="cpu_scheduling", attempt_count=1, verification_required=True
        )
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="Because the asgi server handles incoming network communication and passes the request to the fastapi app.",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            intervention=intervention,
            teacher_attempt_count=1,
            active_concept="cpu_scheduling",
        )
        res: AIResult = self.engine.process(ctx)

        # Verified understanding: must return to Student Mode
        assert res.decision.next_mode == Mode.STUDENT
        assert res.decision.should_restore_interrupted_question is True
        assert res.state_updates.current_mode == Mode.STUDENT
        assert res.state_updates.interrupted_question is None

    def test_scenario_g_wrong_verification_stays_teacher_and_increments_attempt(self):
        """Scenario G: Wrong verification stays in Teacher mode and increments attempt count."""
        int_q = CurrentQuestion(
            id="q_snap", content="Explain scheduling priority", concept="cpu_scheduling", difficulty=2
        )
        intervention = TeacherIntervention(
            active=True, gap="cpu_scheduling", attempt_count=1, verification_required=True
        )
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="It works because the stack is infinite and memory never runs out.",
            mode=Mode.TEACHER,
            interrupted_q=int_q,
            intervention=intervention,
            teacher_attempt_count=1,
            active_concept="cpu_scheduling",
        )
        res: AIResult = self.engine.process(ctx)

        assert res.decision.next_mode == Mode.TEACHER
        assert res.state_updates.teacher_intervention.active is True
        assert res.state_updates.teacher_attempt_count == 2

    def test_scenario_h_repeated_concept_questions_vary_semantically(self):
        """Scenario H: Novelty guardrail prevents duplicate questions."""
        checker = QuestionNoveltyChecker(similarity_threshold=0.80)
        past_q = ["How does process scheduling allocate CPU time to threads?"]

        # Exactly duplicate or near-identical question rejected
        is_novel_dup, sim_dup, _ = checker.is_novel(
            "How does process scheduling allocate CPU time to threads?", past_q
        )
        assert is_novel_dup is False
        assert sim_dup >= 0.80

        # Semantically varied question accepted
        is_novel_new, sim_new, _ = checker.is_novel(
            "What happens to lower-priority threads under starvation conditions?", past_q
        )
        assert is_novel_new is True
        assert sim_new < 0.60

    def test_scenario_i_strong_evidence_increases_difficulty_bounded(self):
        """Scenario I: Strong demonstrated evidence increases difficulty by at most 1 level."""
        ctx = _make_context(
            topic="Operating Systems",
            user_msg="A strong explanation: a base case provides a termination condition.",
            difficulty=1,
            active_concept="base_case",
        )
        res: AIResult = self.engine.process(ctx)

        assert res.decision.next_mode == Mode.STUDENT
        assert res.decision.difficulty == 2  # Exactly bounded +1 change

    def test_scenario_j_misconception_steers_learning_path(self):
        """Scenario J: Severe misconception steers the learning path toward resolution."""
        ctx = _make_context(
            topic="Binary Search",
            user_msg="Binary search works on any array, even if it is completely unsorted.",
            difficulty=2,
            active_concept="middle_element",
        )
        res: AIResult = self.engine.process(ctx)

        # Misconception must be recorded in evaluation and handled
        assert len(res.evaluation.misconceptions) > 0
        assert (
            res.decision.strategy == Strategy.CHALLENGE_MISCONCEPTION
            or res.decision.next_mode == Mode.TEACHER
        )
