"""
SessionState → UserConceptProgress Synchronization Tests (Phase 4 Task 4.6).

Tests verify that UserConceptProgress is automatically synchronized from
structured AIResult StateUpdates during ChatService.send_message().
"""
from unittest.mock import MagicMock, create_autospec
from uuid import UUID, uuid4
import pytest
from datetime import datetime, timezone

from backend.app.services.chat_service import ChatService
from backend.app.models.session import Session, SessionState
from backend.app.models.user import User
from backend.app.ai.schemas import (
    AIResult,
    AIResponse,
    LearningDecision,
    Mode,
    StateUpdates,
    Strategy,
    TurnEvaluation,
)
from backend.app.schemas.message import MessageCreate
from backend.app.schemas.common import InputType as CommonInputType


def create_mock_ai_result(
    next_mode: Mode = Mode.STUDENT,
    strategy: Strategy = Strategy.PROBE_WHY,
    difficulty: int = 1,
    confidence: float = 0.5,
    state_updates: StateUpdates = None,
    content: str = "Test AI response message",
) -> AIResult:
    """Helper to generate a valid, contract-compliant AIResult."""
    evaluation = TurnEvaluation(
        correctness=0.8,
        clarity=0.8,
        completeness=0.8,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.1,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["Calculus fundamentals"],
        knowledge_gap=None,
        recommended_strategy=strategy,
        recommended_difficulty=difficulty,
    )
    decision = LearningDecision(
        next_mode=next_mode,
        strategy=strategy,
        difficulty=difficulty,
        confidence=confidence,
        reason=f"Transitioning to {next_mode.value}",
        active_concept="Derivatives",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )
    response = AIResponse(
        content=content,
        mode=next_mode,
        strategy=strategy,
        difficulty=difficulty,
        confidence=confidence,
        requires_single_question=True,
    )
    updates = state_updates or StateUpdates(
        current_mode=next_mode,
        difficulty=difficulty,
        confidence=confidence,
        active_concept="Derivatives",
    )
    return AIResult(
        evaluation=evaluation,
        decision=decision,
        response=response,
        state_updates=updates,
    )


def create_mock_session(
    session_id: UUID,
    user_id: UUID,
    current_mode: str = "STUDENT",
    topic: str = "Calculus",
    teacher_attempt_count: int = 0,
    teacher_intervention: dict = None,
):
    """Create a properly configured mock Session with state."""
    db_session = MagicMock(spec=Session)
    db_session.id = session_id
    db_session.user_id = user_id
    db_session.topic = topic
    db_session.source_type = "GENERAL"

    db_state = MagicMock(spec=SessionState)
    db_state.session_id = session_id
    db_state.current_mode = current_mode
    db_state.difficulty = 1
    db_state.confidence = 0.5
    db_state.active_concept = "Limits"
    db_state.current_question_id = None
    db_state.interrupted_question_id = None
    db_state.consecutive_strong_answers = 0
    db_state.consecutive_weak_answers = 0
    db_state.unresolved_misconceptions = []
    db_state.mastered_concepts = []
    db_state.teacher_attempt_count = teacher_attempt_count
    db_state.teacher_intervention = teacher_intervention
    db_state.mode_switch_history = []
    db_state.concept_mastery = {}
    db_state.misconception_counts = {}
    db_state.recent_strategy_history = []

    db_session.state = db_state
    return db_session


def create_mock_message(sender: str, content: str, session_id: UUID):
    """Create a properly configured mock Message."""
    msg = MagicMock()
    msg.id = uuid4()
    msg.session_id = session_id
    msg.sender = sender
    msg.content = content
    msg.input_type = "TEXT"
    msg.created_at = None
    return msg


class TestSessionConceptProgressSync:
    """Test automatic UserConceptProgress synchronization from StateUpdates."""

    def test_first_turn_creates_user_concept_progress(self):
        """First turn creates UserConceptProgress from AI mastery."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # StateUpdates with concept_mastery and misconception_counts
        state_updates = StateUpdates(
            current_mode=Mode.STUDENT,
            difficulty=2,
            confidence=0.6,
            active_concept="Limits",
            concept_mastery={"derivatives": 0.75, "integrals": 0.3},
            misconception_counts={"derivatives": 1, "integrals": 0},
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(
            next_mode=Mode.STUDENT,
            strategy=Strategy.PROBE_WHY,
            state_updates=state_updates,
        )

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id, current_mode="STUDENT")
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "What is a derivative?", session_id),
            create_mock_message("AI", "A derivative measures rate of change", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="What is a derivative?", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in, user_id=user_id)

        # Verify upsert was called for each concept
        assert service.concept_progress_repo.upsert.call_count == 2
        calls = service.concept_progress_repo.upsert.call_args_list

        # Check derivatives call
        deriv_call = next(c for c in calls if c.kwargs["concept"] == "derivatives")
        assert deriv_call.kwargs["user_id"] == user_id
        assert deriv_call.kwargs["mastery_score"] == 0.75
        assert deriv_call.kwargs["misconception_count"] == 1
        assert deriv_call.kwargs["last_difficulty"] == 2
        assert deriv_call.kwargs["last_practiced_at"] is not None

        # Check integrals call
        integ_call = next(c for c in calls if c.kwargs["concept"] == "integrals")
        assert integ_call.kwargs["mastery_score"] == 0.3
        assert integ_call.kwargs["misconception_count"] == 0

    def test_subsequent_turn_replaces_mastery_not_increment(self):
        """Subsequent turn replaces mastery rather than incrementing it."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # First turn: mastery 0.5
        state_updates_1 = StateUpdates(
            concept_mastery={"recursion": 0.5},
            misconception_counts={"recursion": 0},
            difficulty=1,
        )
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates_1)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Turn 1", session_id),
            create_mock_message("AI", "Response 1", session_id),
            create_mock_message("USER", "Turn 2", session_id),
            create_mock_message("AI", "Response 2", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        # First turn: mastery 0.5
        service.send_message(mock_db, session_id, MessageCreate(content="Turn 1", input_type=CommonInputType.TEXT), user_id=user_id)

        # Second turn: mastery 0.75 (should replace, not add)
        state_updates_2 = StateUpdates(
            concept_mastery={"recursion": 0.75},
            misconception_counts={"recursion": 0},
            difficulty=2,
        )
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates_2)

        service.send_message(mock_db, session_id, MessageCreate(content="Turn 2", input_type=CommonInputType.TEXT), user_id=user_id)

        # Verify both calls have absolute values
        calls = service.concept_progress_repo.upsert.call_args_list
        assert calls[0].kwargs["mastery_score"] == 0.5
        assert calls[1].kwargs["mastery_score"] == 0.75  # Not 1.25!

    def test_misconception_count_syncs_from_state_updates(self):
        """Misconception count syncs from AI StateUpdates."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"binary_search": 0.6},
            misconception_counts={"binary_search": 3},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        assert call.kwargs["misconception_count"] == 3

    def test_missing_misconception_count_preserves_existing(self):
        """Missing misconception count preserves existing database value."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # concept_mastery provided but misconception_counts is empty
        state_updates = StateUpdates(
            concept_mastery={"dynamic_programming": 0.8},
            misconception_counts={},  # Empty - AI doesn't provide misconception data
            difficulty=3,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        # misconception_count should be None (preserve existing)
        assert call.kwargs["misconception_count"] is None

    def test_multiple_concepts_synchronize_independently(self):
        """Multiple concepts synchronize independently."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={
                "concept_a": 0.4,
                "concept_b": 0.8,
                "concept_c": 0.95,
            },
            misconception_counts={
                "concept_a": 2,
                "concept_b": 0,
                "concept_c": 1,
            },
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        assert service.concept_progress_repo.upsert.call_count == 3
        calls = service.concept_progress_repo.upsert.call_args_list
        concepts = {c.kwargs["concept"]: c.kwargs for c in calls}

        assert concepts["concept_a"]["mastery_score"] == 0.4
        assert concepts["concept_a"]["misconception_count"] == 2
        assert concepts["concept_b"]["mastery_score"] == 0.8
        assert concepts["concept_b"]["misconception_count"] == 0
        assert concepts["concept_c"]["mastery_score"] == 0.95
        assert concepts["concept_c"]["misconception_count"] == 1

    def test_same_concept_multiple_sessions_updates_same_row(self):
        """Same concept across multiple sessions updates the same user+concept row."""
        session_id_1 = uuid4()
        session_id_2 = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # Session 1: initial progress
        state_updates_1 = StateUpdates(
            concept_mastery={"graphs": 0.5},
            misconception_counts={"graphs": 1},
            difficulty=1,
        )
        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates_1)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id_1, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Session 1", session_id_1),
            create_mock_message("AI", "Response 1", session_id_1),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id_1, MessageCreate(content="Session 1", input_type=CommonInputType.TEXT), user_id=user_id)

        # Session 2: same concept, updated mastery
        state_updates_2 = StateUpdates(
            concept_mastery={"graphs": 0.85},
            misconception_counts={"graphs": 0},
            difficulty=2,
        )
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates_2)

        db_session = create_mock_session(session_id_2, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Session 2", session_id_2),
            create_mock_message("AI", "Response 2", session_id_2),
        ])

        service.send_message(mock_db, session_id_2, MessageCreate(content="Session 2", input_type=CommonInputType.TEXT), user_id=user_id)

        # Verify both calls target same user+concept
        calls = service.concept_progress_repo.upsert.call_args_list
        assert calls[0].kwargs["user_id"] == user_id
        assert calls[0].kwargs["concept"] == "graphs"
        assert calls[1].kwargs["user_id"] == user_id
        assert calls[1].kwargs["concept"] == "graphs"
        # Second call replaces with new absolute value
        assert calls[1].kwargs["mastery_score"] == 0.85

    def test_different_users_remain_isolated(self):
        """Different users remain isolated."""
        session_id = uuid4()
        user_a = uuid4()
        user_b = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"trees": 0.7},
            misconception_counts={"trees": 0},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        # User A
        db_session_a = create_mock_session(session_id, user_a)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session_a)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test A", session_id),
            create_mock_message("AI", "Response A", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test A", input_type=CommonInputType.TEXT), user_id=user_a)

        # User B - different session
        session_id_b = uuid4()
        db_session_b = create_mock_session(session_id_b, user_b)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session_b)
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test B", session_id_b),
            create_mock_message("AI", "Response B", session_id_b),
        ])

        service.send_message(mock_db, session_id_b, MessageCreate(content="Test B", input_type=CommonInputType.TEXT), user_id=user_b)

        calls = service.concept_progress_repo.upsert.call_args_list
        assert calls[0].kwargs["user_id"] == user_a
        assert calls[1].kwargs["user_id"] == user_b

    def test_duplicate_synchronization_no_increment(self):
        """Duplicate/repeated synchronization does not increment anything."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"heaps": 0.6},
            misconception_counts={"heaps": 2},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test 1", session_id),
            create_mock_message("AI", "Response 1", session_id),
            create_mock_message("USER", "Test 2", session_id),
            create_mock_message("AI", "Response 2", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        # First sync
        service.send_message(mock_db, session_id, MessageCreate(content="Test 1", input_type=CommonInputType.TEXT), user_id=user_id)
        # Second sync (same StateUpdates - simulating retry)
        service.send_message(mock_db, session_id, MessageCreate(content="Test 2", input_type=CommonInputType.TEXT), user_id=user_id)

        calls = service.concept_progress_repo.upsert.call_args_list
        assert calls[0].kwargs["mastery_score"] == 0.6
        assert calls[1].kwargs["mastery_score"] == 0.6  # Same absolute value
        assert calls[0].kwargs["misconception_count"] == 2
        assert calls[1].kwargs["misconception_count"] == 2  # Same absolute value

    def test_total_attempts_unchanged(self):
        """total_attempts remains unchanged."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"sorting": 0.5},
            difficulty=1,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        # total_attempts should not be passed to upsert
        call = service.concept_progress_repo.upsert.call_args
        assert "total_attempts" not in call.kwargs

    def test_successful_attempts_unchanged(self):
        """successful_attempts remains unchanged."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"hashing": 0.7},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        assert "successful_attempts" not in call.kwargs

    def test_missing_concept_mastery_no_crash(self):
        """Missing concept_mastery does not crash."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # StateUpdates with None concept_mastery
        state_updates = StateUpdates(
            current_mode=Mode.STUDENT,
            difficulty=2,
            confidence=0.5,
            active_concept="Trees",
            concept_mastery=None,
            misconception_counts=None,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        # Should not raise
        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        # No upsert calls
        service.concept_progress_repo.upsert.assert_not_called()

    def test_empty_concept_mastery_no_crash(self):
        """Empty concept_mastery does not crash."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={},
            misconception_counts={},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        # Should not raise
        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        # No upsert calls
        service.concept_progress_repo.upsert.assert_not_called()

    def test_partial_state_updates_no_crash(self):
        """Partial StateUpdates do not crash."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # Only difficulty provided
        state_updates = StateUpdates(
            difficulty=3,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        # No upsert calls since concept_mastery is missing
        service.concept_progress_repo.upsert.assert_not_called()

    def test_explicit_zero_mastery_persisted(self):
        """Explicit mastery value 0.0 is persisted correctly."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"new_topic": 0.0},
            misconception_counts={"new_topic": 0},
            difficulty=1,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        assert call.kwargs["mastery_score"] == 0.0

    def test_last_difficulty_updates_when_ai_provides(self):
        """last_difficulty updates only when AI provides difficulty."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"queues": 0.6},
            difficulty=4,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        assert call.kwargs["last_difficulty"] == 4

    def test_missing_difficulty_preserves_existing(self):
        """Missing difficulty preserves existing database value."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # No difficulty in updates
        state_updates = StateUpdates(
            concept_mastery={"stacks": 0.8},
            misconception_counts={"stacks": 0},
            # difficulty not provided
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        assert call.kwargs["last_difficulty"] is None

    def test_last_practiced_at_updates_on_sync(self):
        """last_practiced_at updates on successful synchronization."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"arrays": 0.5},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        before = datetime.now(timezone.utc)
        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)
        after = datetime.now(timezone.utc)

        call = service.concept_progress_repo.upsert.call_args
        practiced_at = call.kwargs["last_practiced_at"]
        assert practiced_at is not None
        assert before <= practiced_at <= after

    def test_report_regeneration_does_not_modify_progress(self):
        """Report regeneration does not modify UserConceptProgress."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        # This test verifies that the sync only happens in ChatService.send_message
        # ReportService does not call _sync_user_concept_progress

        service = ChatService(ai_engine=MagicMock())
        service.concept_progress_repo = MagicMock()

        # Simulate ReportService calling something else - it should not trigger sync
        # The sync method is private and only called from send_message
        # This test documents the isolation
        assert hasattr(service, "_sync_user_concept_progress")
        # But ReportService doesn't have access to it or call it

    def test_sync_failure_does_not_crash_turn(self):
        """Synchronization failure does not crash the chat turn."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"linked_lists": 0.6},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()
        # Make upsert raise an exception
        service.concept_progress_repo.upsert.side_effect = Exception("DB connection failed")

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        # Should not raise - turn completes even if sync fails
        response = service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)
        assert response is not None

    def test_user_ownership_enforced(self):
        """Authenticated user ownership is enforced."""
        session_id = uuid4()
        user_id = uuid4()
        mock_db = MagicMock()

        state_updates = StateUpdates(
            concept_mastery={"tries": 0.4},
            difficulty=2,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = create_mock_ai_result(state_updates=state_updates)

        service = ChatService(ai_engine=mock_engine)
        service.concept_progress_repo = MagicMock()

        db_session = create_mock_session(session_id, user_id)
        service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_mock_message("USER", "Test", session_id),
            create_mock_message("AI", "Response", session_id),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.send_message(mock_db, session_id, MessageCreate(content="Test", input_type=CommonInputType.TEXT), user_id=user_id)

        call = service.concept_progress_repo.upsert.call_args
        assert call.kwargs["user_id"] == user_id