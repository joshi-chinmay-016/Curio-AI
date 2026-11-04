"""
Unit and integration tests for conversational transaction atomicity in ChatService.

Verifies:
1. All turn persistence writes (user message, AI message, evaluation, assessment,
   session state, teacher intervention, concept progress) participate in a single
   atomic Unit of Work.
2. Groq external LLM calls occur strictly outside the database transaction boundary.
3. Failures at any persistence stage trigger a complete transaction rollback.
4. No partial turn (orphaned user messages or desynchronized state) remains after a failure.
5. Retries after failure execute cleanly without duplicate conversational turns.
"""

import uuid
from unittest.mock import MagicMock, call, patch
import pytest

from backend.app.services.chat_service import ChatService
from backend.app.schemas.message import MessageCreate
from backend.app.schemas.common import InputType, LearningMode, LearningStrategy
from backend.app.ai.schemas import (
    AIResult,
    AIResponse,
    LearningDecision,
    Mode,
    StateUpdates,
    Strategy,
    TurnEvaluation as AITurnEvaluation,
)


def _build_mock_ai_result(
    content="This is the AI response.",
    next_mode=Mode.STUDENT,
    strategy=Strategy.PROBE_WHY,
    difficulty=2,
    confidence=0.75,
):
    """Helper to build a valid AIResult for testing."""
    evaluation = AITurnEvaluation(
        correctness=0.8,
        clarity=0.9,
        completeness=0.7,
        depth=0.6,
        relevance=1.0,
        stuck_probability=0.1,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["loops"],
        knowledge_gap=None,
        recommended_strategy=strategy,
        recommended_difficulty=difficulty,
    )
    decision = LearningDecision(
        next_mode=next_mode,
        strategy=strategy,
        difficulty=difficulty,
        confidence=confidence,
        reason="Demonstrates good understanding",
        active_concept="loops",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )
    response = AIResponse(
        content=content,
        mode=next_mode,
        strategy=strategy,
        difficulty=difficulty,
        confidence=confidence,
    )
    state_updates = StateUpdates(
        current_mode=next_mode,
        difficulty=difficulty,
        confidence=confidence,
        active_concept="loops",
        consecutive_successes=1,
        consecutive_failures=0,
        mastered_concepts=["loops"],
        concept_mastery={"loops": 0.85},
        misconception_counts={},
        recent_strategy_history=[strategy],
    )
    return AIResult(
        evaluation=evaluation,
        decision=decision,
        response=response,
        state_updates=state_updates,
    )


def _build_mock_session(session_id, user_id):
    """Helper to build a valid mock Session with SessionState."""
    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.user_id = user_id
    mock_session.topic = "Python Programming"
    mock_session.source_type = "GENERAL"
    mock_session.document_id = None

    mock_state = MagicMock()
    mock_state.current_mode = LearningMode.STUDENT
    mock_state.difficulty = 1
    mock_state.confidence = 0.5
    mock_state.active_concept = "loops"
    mock_state.current_question_id = None
    mock_state.interrupted_question_id = None
    mock_state.consecutive_strong_answers = 0
    mock_state.consecutive_weak_answers = 0
    mock_state.unresolved_misconceptions = []
    mock_state.mastered_concepts = []
    mock_state.concept_mastery = {}
    mock_state.misconception_counts = {}
    mock_state.recent_strategy_history = []
    mock_state.mode_switch_history = []
    mock_state.concept_model = None
    mock_state.teacher_attempt_count = 0
    mock_state.teacher_intervention = None
    mock_state.teacher_intervention_data = None

    mock_session.state = mock_state
    return mock_session


class TestTransactionAtomicity:
    def setup_method(self):
        self.session_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

        # Mock dependencies
        self.mock_ai_engine = MagicMock()
        self.mock_retrieval_service = MagicMock()
        self.mock_retrieval_service.retrieve.return_value = MagicMock(chunks=[])

        self.chat_service = ChatService(
            ai_engine=self.mock_ai_engine,
            retrieval_service=self.mock_retrieval_service,
        )

        # Mock repositories on chat_service
        self.chat_service.session_repo = MagicMock()
        self.chat_service.message_repo = MagicMock()
        self.chat_service.turn_assessment_repo = MagicMock()
        self.chat_service.teacher_intervention_repo = MagicMock()
        self.chat_service.concept_progress_repo = MagicMock()

        # Setup standard session return
        self.mock_db_session = _build_mock_session(self.session_id, self.user_id)
        self.chat_service.session_repo.get_by_id_and_user.return_value = self.mock_db_session
        self.chat_service.session_repo.get.return_value = self.mock_db_session
        self.chat_service.message_repo.list_by_session.return_value = []

    def test_external_groq_called_before_db_writes(self):
        """
        Verify Requirement 2: Keep Groq and other external network calls
        strictly outside the database transaction.
        The AI engine must be invoked before any message is persisted.
        """
        db = MagicMock()
        ai_result = _build_mock_ai_result()
        self.mock_ai_engine.process.return_value = ai_result

        call_order = []
        self.mock_ai_engine.process.side_effect = lambda ctx: call_order.append("ai_engine") or ai_result
        self.chat_service.message_repo.create_message.side_effect = lambda *a, **kw: call_order.append("create_message") or MagicMock(id=uuid.uuid4())

        msg_in = MessageCreate(content="What is a loop?", input_type=InputType.TEXT)
        self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        assert "ai_engine" in call_order
        assert "create_message" in call_order
        # AI Engine MUST be invoked before any message write occurs
        assert call_order.index("ai_engine") < call_order.index("create_message")

    def test_successful_turn_commits_exactly_once(self):
        """
        Verify Requirement 1 & 4:
        - Repository methods called with commit=False.
        - Single cohesive db.commit() executed after all writes succeed.
        """
        db = MagicMock()
        ai_result = _build_mock_ai_result()
        self.mock_ai_engine.process.return_value = ai_result

        user_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="USER", content="Hello", input_type="TEXT")
        ai_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="AI", content="AI Hello", input_type="TEXT")
        self.chat_service.message_repo.create_message.side_effect = [user_msg_mock, ai_msg_mock]

        msg_in = MessageCreate(content="Hello", input_type=InputType.TEXT)
        response = self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        # Exactly ONE commit across the entire conversational turn
        assert db.commit.call_count == 1
        assert db.rollback.call_count == 0

        # Repository methods called with commit=False
        for call_args in self.chat_service.message_repo.create_message.call_args_list:
            assert call_args.kwargs.get("commit") is False
        assert self.chat_service.message_repo.create_evaluation.call_args.kwargs.get("commit") is False
        assert self.chat_service.session_repo.update_state.call_args.kwargs.get("commit") is False

        # Refreshed messages
        db.refresh.assert_has_calls([call(user_msg_mock), call(ai_msg_mock)], any_order=True)

    def test_groq_failure_initiates_no_writes(self):
        """
        If Groq / CurioEngine fails (e.g. timeout, rate limit, network abort):
        Zero database writes or commits occur. No orphaned user message in DB.
        """
        db = MagicMock()
        self.mock_ai_engine.process.side_effect = RuntimeError("Groq LLM 503 Service Unavailable")

        msg_in = MessageCreate(content="Explain recursion", input_type=InputType.TEXT)

        with pytest.raises(RuntimeError, match="Groq LLM 503"):
            self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        # No database write methods called
        self.chat_service.message_repo.create_message.assert_not_called()
        self.chat_service.message_repo.create_evaluation.assert_not_called()
        self.chat_service.session_repo.update_state.assert_not_called()
        assert db.commit.call_count == 0

    def test_evaluation_failure_rolls_back_entire_turn(self):
        """
        Simulate database failure at TurnEvaluation persistence stage:
        Must rollback the user message and AI message already staged in the transaction.
        """
        db = MagicMock()
        ai_result = _build_mock_ai_result()
        self.mock_ai_engine.process.return_value = ai_result

        user_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="USER")
        ai_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="AI")
        self.chat_service.message_repo.create_message.side_effect = [user_msg_mock, ai_msg_mock]

        # Fail at evaluation write
        self.chat_service.message_repo.create_evaluation.side_effect = Exception("DB Disk I/O Error on TurnEvaluation")

        msg_in = MessageCreate(content="Test eval failure", input_type=InputType.TEXT)

        with pytest.raises(Exception, match="DB Disk I/O Error"):
            self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        # Verify full rollback and zero commits
        assert db.commit.call_count == 0
        assert db.rollback.call_count == 1

    def test_session_state_update_failure_rolls_back_all_messages(self):
        """
        Simulate database failure at SessionState update stage:
        Must rollback the user message, AI message, and turn evaluation.
        """
        db = MagicMock()
        ai_result = _build_mock_ai_result()
        self.mock_ai_engine.process.return_value = ai_result

        user_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="USER")
        ai_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="AI")
        self.chat_service.message_repo.create_message.side_effect = [user_msg_mock, ai_msg_mock]

        # Fail at session state update
        self.chat_service.session_repo.update_state.side_effect = Exception("Foreign key violation on session_state")

        msg_in = MessageCreate(content="Test state failure", input_type=InputType.TEXT)

        with pytest.raises(Exception, match="Foreign key violation"):
            self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        assert db.commit.call_count == 0
        assert db.rollback.call_count == 1

    def test_concept_progress_sync_failure_rolls_back_entire_turn(self):
        """
        Simulate database failure at UserConceptProgress synchronization stage:
        Must rollback all messages, evaluations, and state updates.
        """
        db = MagicMock()
        ai_result = _build_mock_ai_result()
        self.mock_ai_engine.process.return_value = ai_result

        user_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="USER")
        ai_msg_mock = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="AI")
        self.chat_service.message_repo.create_message.side_effect = [user_msg_mock, ai_msg_mock]

        # Fail at concept progress upsert
        self.chat_service.concept_progress_repo.upsert_batch.side_effect = Exception("Lock timeout on user_concept_progress")

        msg_in = MessageCreate(content="Test concept progress failure", input_type=InputType.TEXT)

        with pytest.raises(Exception, match="Lock timeout"):
            self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        assert db.commit.call_count == 0
        assert db.rollback.call_count == 1

    def test_retry_after_failure_does_not_duplicate_turn(self):
        """
        Verify Requirement 7:
        Ensure retries do not create duplicate conversational turns.
        Attempt 1 fails and rolls back. Attempt 2 succeeds cleanly.
        """
        db = MagicMock()
        ai_result = _build_mock_ai_result()
        self.mock_ai_engine.process.return_value = ai_result

        # Attempt 1: Session state update fails
        user_msg_mock1 = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="USER", content="Retry me")
        ai_msg_mock1 = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="AI", content="Response 1")
        self.chat_service.message_repo.create_message.side_effect = [user_msg_mock1, ai_msg_mock1]
        self.chat_service.session_repo.update_state.side_effect = Exception("Transient DB connection glitch")

        msg_in = MessageCreate(content="Retry me", input_type=InputType.TEXT)

        with pytest.raises(Exception, match="Transient DB connection glitch"):
            self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        assert db.commit.call_count == 0
        assert db.rollback.call_count == 1

        # Reset mocks for retry attempt 2
        db.reset_mock()
        user_msg_mock2 = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="USER", content="Retry me")
        ai_msg_mock2 = MagicMock(id=uuid.uuid4(), session_id=self.session_id, sender="AI", content="Response 2")
        self.chat_service.message_repo.create_message.side_effect = [user_msg_mock2, ai_msg_mock2]
        self.chat_service.session_repo.update_state.side_effect = None

        response = self.chat_service.send_message(db, self.session_id, msg_in, user_id=self.user_id)

        # Retry successfully commits exactly once
        assert db.commit.call_count == 1
        assert db.rollback.call_count == 0
        assert response.user_message.content == "Retry me"
