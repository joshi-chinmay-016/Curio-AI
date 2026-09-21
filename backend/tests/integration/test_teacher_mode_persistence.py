"""
Focused Teacher Mode Persistence & Restoration Integration Tests.

These tests execute against the dedicated, isolated 'curio_test_db'
to verify the persistence and restoration lifecycle of Teacher Mode,
question tracking (current and interrupted), learning states, and
defensive fallback handling.

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Never touches or writes to curio_db.
- Uses nested transaction savepoints so all writes roll back on teardown.
- No Base.metadata.create_all() or Alembic downgrades.
"""

from unittest.mock import MagicMock
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.session import Session, SessionState
from backend.app.models.message import Message
from backend.app.schemas.message import MessageCreate
from backend.app.schemas.common import InputType as CommonInputType, LearningMode
from backend.app.services.chat_service import ChatService
from backend.app.ai.schemas import (
    AIResult,
    AIResponse,
    CurrentQuestion,
    LearningDecision,
    Mode,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
)


pytestmark = pytest.mark.db_integration


def _create_mock_ai_result(
    next_mode: Mode = Mode.STUDENT,
    strategy: Strategy = Strategy.PROBE_WHY,
    difficulty: int = 1,
    confidence: float = 0.5,
    should_restore_interrupted_question: bool = False,
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
        should_restore_interrupted_question=should_restore_interrupted_question,
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


def _setup_test_session_in_db(db, topic="Calculus"):
    """Helper to persist a fresh User and Session with initial State in PostgreSQL."""
    user = User(email=f"teacher_audit_{uuid4().hex[:8]}@curio.ai")
    db.add(user)
    db.flush()

    session = Session(
        user_id=user.id,
        topic=topic,
        source_type="GENERAL",
        status="ACTIVE",
    )
    db.add(session)
    db.flush()

    state = SessionState(
        session_id=session.id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.1,
        active_concept="Limits",
        current_question_id=None,
        interrupted_question_id=None,
        consecutive_strong_answers=0,
        consecutive_weak_answers=0,
        unresolved_misconceptions=[],
        mastered_concepts=[],
        teacher_attempt_count=0,
        teacher_intervention=None,
    )
    db.add(state)
    db.commit()
    return session, state


# =====================================================================
# 1. ENTERING TEACHER MODE & PERSISTENCE
# =====================================================================

def test_enter_teacher_mode_persists_interrupted_question(test_db_session):
    """
    Verify that when transitioning from STUDENT to TEACHER mode:
    1. current_mode is updated to 'TEACHER' in PostgreSQL.
    2. The interrupted_question_id is saved as the previous current_question_id.
    3. The new AI teaching explanation becomes current_question_id.
    """
    session, state = _setup_test_session_in_db(test_db_session)

    # Add an active question from the student mode
    student_q = Message(
        session_id=session.id,
        sender="AI",
        content="What is the geometric interpretation of a derivative?",
        input_type="TEXT",
    )
    test_db_session.add(student_q)
    test_db_session.flush()

    state.current_question_id = student_q.id
    test_db_session.commit()

    # Mock engine deciding to transition from STUDENT to TEACHER
    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.TEACH_GAP,
        difficulty=1,
        confidence=0.2,
        state_updates=StateUpdates(
            current_mode=Mode.TEACHER,
            difficulty=1,
            confidence=0.2,
            active_concept="Tangent Slope",
        ),
        content="Let me explain: the derivative represents the slope of the tangent line at any point.",
    )

    service = ChatService(ai_engine=mock_engine)

    # Learner responds with stuck indicator
    user_msg = MessageCreate(content="I'm totally stuck, I don't know.", input_type=CommonInputType.TEXT)
    turn_response = service.send_message(test_db_session, session.id, user_msg)

    # Verify return payload
    assert turn_response.decision.next_mode == LearningMode.TEACHER
    assert turn_response.decision.strategy.value == "TEACH_GAP"

    # Reload fresh state from PostgreSQL
    test_db_session.expire_all()
    reloaded_state = test_db_session.query(SessionState).filter_by(session_id=session.id).one()

    assert reloaded_state.current_mode == "TEACHER"
    # Interrupted question must match the original student question ID
    assert reloaded_state.interrupted_question_id == student_q.id
    # Current question ID must now point to the AI teaching message
    assert reloaded_state.current_question_id == turn_response.ai_message.message_id
    assert reloaded_state.active_concept == "Tangent Slope"
    assert reloaded_state.confidence == 0.2


# =====================================================================
# 2. MULTI-TURN TEACHER MODE STATE RETENTION
# =====================================================================

def test_multi_turn_teacher_mode_preserves_interrupted_question(test_db_session):
    """
    Verify that subsequent messages while remaining in TEACHER mode
    preserve the existing interrupted_question_id without overwriting or clearing it.
    """
    session, state = _setup_test_session_in_db(test_db_session)
    original_interrupted_qid = uuid4()

    state.current_mode = "TEACHER"
    state.interrupted_question_id = original_interrupted_qid
    test_db_session.commit()

    # Engine continues in TEACHER mode
    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.VERIFY_UNDERSTANDING,
        difficulty=1,
        confidence=0.3,
        state_updates=StateUpdates(
            current_mode=Mode.TEACHER,
            difficulty=1,
            confidence=0.3,
            active_concept="Secant to Tangent",
        ),
        content="Think of what happens as the distance between two secant points approaches zero.",
    )

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="Does the secant line become the tangent?", input_type=CommonInputType.TEXT)
    service.send_message(test_db_session, session.id, user_msg)

    # Reload from PostgreSQL
    test_db_session.expire_all()
    reloaded_state = test_db_session.query(SessionState).filter_by(session_id=session.id).one()

    assert reloaded_state.current_mode == "TEACHER"
    # The interrupted question must remain intact
    assert reloaded_state.interrupted_question_id == original_interrupted_qid
    assert reloaded_state.active_concept == "Secant to Tangent"


# =====================================================================
# 3. EXITING TEACHER MODE & RESTORATION
# =====================================================================

def test_exit_teacher_mode_restores_student_mode_and_clears_interrupted(test_db_session):
    """
    Verify that when learner verifies understanding:
    1. decision.should_restore_interrupted_question clears interrupted_question_id to None.
    2. current_mode returns to 'STUDENT'.
    3. Mastered concepts and confidence updates persist in PostgreSQL.
    """
    session, state = _setup_test_session_in_db(test_db_session)
    saved_interrupted_qid = uuid4()

    state.current_mode = "TEACHER"
    state.interrupted_question_id = saved_interrupted_qid
    state.confidence = 0.3
    state.mastered_concepts = ["Limits"]
    test_db_session.commit()

    # Engine returns to STUDENT mode with should_restore_interrupted_question=True
    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.STUDENT,
        strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
        difficulty=2,
        confidence=0.75,
        should_restore_interrupted_question=True,
        state_updates=StateUpdates(
            current_mode=Mode.STUDENT,
            difficulty=2,
            confidence=0.75,
            active_concept="Tangent Slope",
            mastered_concepts=["Tangent Slope Verified"],
        ),
        content="Great job! Now let's return to our original problem: find the slope of y = x^2 at x = 3.",
    )

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(
        content="As delta x approaches 0, the secant slope converges to the instantaneous rate of change.",
        input_type=CommonInputType.TEXT,
    )
    turn_response = service.send_message(test_db_session, session.id, user_msg)

    assert turn_response.decision.next_mode == LearningMode.STUDENT
    assert turn_response.decision.should_restore_interrupted_question is True

    # Reload from PostgreSQL
    test_db_session.expire_all()
    reloaded_state = test_db_session.query(SessionState).filter_by(session_id=session.id).one()

    assert reloaded_state.current_mode == "STUDENT"
    # Interrupted question must be cleared back to None
    assert reloaded_state.interrupted_question_id is None
    # Concepts and confidence must be updated
    assert "Tangent Slope Verified" in reloaded_state.mastered_concepts
    assert reloaded_state.confidence == 0.75


# =====================================================================
# 4. DATABASE HYDRATION OF QUESTION OBJECTS
# =====================================================================

def test_database_hydration_of_question_objects(test_db_session):
    """
    Verify that ChatService safely hydrates CurrentQuestion domain objects
    from real database messages when current_question_id and interrupted_question_id are set.
    """
    session, state = _setup_test_session_in_db(test_db_session)

    # Insert messages that represent the current and interrupted questions
    int_msg = Message(
        session_id=session.id,
        sender="AI",
        content="Original question: What is the chain rule?",
        input_type="TEXT",
    )
    curr_msg = Message(
        session_id=session.id,
        sender="AI",
        content="Teaching question: Can you differentiate f(g(x)) by parts?",
        input_type="TEXT",
    )
    test_db_session.add_all([int_msg, curr_msg])
    test_db_session.flush()

    state.current_mode = "TEACHER"
    state.current_question_id = curr_msg.id
    state.interrupted_question_id = int_msg.id
    test_db_session.commit()

    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(next_mode=Mode.TEACHER)

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="I think we multiply f'(g(x)) by g'(x).", input_type=CommonInputType.TEXT)
    service.send_message(test_db_session, session.id, user_msg)

    # Inspect AIContext passed into CurioEngine
    assert mock_engine.process.call_count == 1
    passed_context = mock_engine.process.call_args[0][0]

    # Verify CurrentQuestion hydration
    assert passed_context.current_state.current_question is not None
    assert passed_context.current_state.current_question.id == str(curr_msg.id)
    assert passed_context.current_state.current_question.content == curr_msg.content

    # Verify InterruptedQuestion hydration
    assert passed_context.current_state.interrupted_question is not None
    assert passed_context.current_state.interrupted_question.id == str(int_msg.id)
    assert passed_context.current_state.interrupted_question.content == int_msg.content


# =====================================================================
# 5. DEFENSIVE HANDLING OF MISSING / MALFORMED QUESTION IDS
# =====================================================================

def test_safe_handling_of_missing_or_orphaned_question_ids(test_db_session):
    """
    Verify that if current_question_id or interrupted_question_id point to non-existent
    UUIDs (e.g. deleted or synthetic messages), hydration gracefully yields None without crashing.
    """
    session, state = _setup_test_session_in_db(test_db_session)

    # Point to nonexistent UUIDs
    orphan_curr_id = uuid4()
    orphan_int_id = uuid4()

    state.current_question_id = orphan_curr_id
    state.interrupted_question_id = orphan_int_id
    test_db_session.commit()

    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(next_mode=Mode.STUDENT)

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="Testing orphaned IDs.", input_type=CommonInputType.TEXT)

    # Must execute cleanly without exception
    turn_response = service.send_message(test_db_session, session.id, user_msg)
    assert turn_response is not None

    passed_context = mock_engine.process.call_args[0][0]
    # Questions should safely be None when not found in history
    assert passed_context.current_state.current_question is None
    assert passed_context.current_state.interrupted_question is None


def test_safe_handling_of_malformed_question_ids_in_engine_updates(test_db_session):
    """
    Verify that when AI engine returns non-UUID string IDs in state_updates,
    ChatService catches the error and safely falls back without raising an unhandled exception.
    """
    session, state = _setup_test_session_in_db(test_db_session)

    # Engine returns placeholder string IDs that are NOT valid UUIDs
    malformed_updates = StateUpdates(
        current_mode=Mode.STUDENT,
        current_question=CurrentQuestion(
            id="q_gen_placeholder_not_a_uuid",
            content="Placeholder Question",
            concept="Limits",
            difficulty=1,
        ),
        interrupted_question=CurrentQuestion(
            id="int_gen_not_a_uuid",
            content="Placeholder Interrupted",
            concept="Limits",
            difficulty=1,
        ),
    )

    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.STUDENT,
        state_updates=malformed_updates,
    )

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="Checking malformed UUID fallback.", input_type=CommonInputType.TEXT)

    turn_response = service.send_message(test_db_session, session.id, user_msg)
    assert turn_response is not None

    # Reload from PostgreSQL
    test_db_session.expire_all()
    reloaded_state = test_db_session.query(SessionState).filter_by(session_id=session.id).one()

    # current_question_id falls back to the generated AI message UUID
    assert reloaded_state.current_question_id == turn_response.ai_message.message_id
    assert isinstance(reloaded_state.current_question_id, UUID)


# =====================================================================
# 6. REST API ENDPOINT TEACHER MODE PERSISTENCE
# =====================================================================

def test_api_endpoint_teacher_mode_flow(override_get_db):
    """
    Verify end-to-end via FastAPI TestClient that Teacher Mode state is
    serialized correctly by GET /api/v1/sessions/{id}.
    """
    with TestClient(app) as client:
        # Create session via API
        create_res = client.post("/api/v1/sessions", json={"topic": "Linear Algebra", "source_type": "GENERAL"})
        assert create_res.status_code == 201
        session_id = create_res.json()["id"]

        # Manually set state to TEACHER with interrupted_question_id in the active test session
        db = override_get_db
        db_state = db.query(SessionState).filter_by(session_id=UUID(session_id)).first()
        interrupted_id = uuid4()
        db_state.current_mode = "TEACHER"
        db_state.interrupted_question_id = interrupted_id
        db_state.teacher_attempt_count = 2
        db_state.teacher_intervention = {
            "active": True,
            "gap": "Matrix inverse",
            "attempt_count": 2,
            "verification_required": True,
        }
        db.commit()

        # Query GET /api/v1/sessions/{session_id}
        get_res = client.get(f"/api/v1/sessions/{session_id}")
        assert get_res.status_code == 200
        data = get_res.json()

        assert data["state"]["current_mode"] == "TEACHER"
        assert data["state"]["interrupted_question_id"] == str(interrupted_id)
        assert data["state"]["teacher_attempt_count"] == 2
        assert data["state"]["teacher_intervention"]["gap"] == "Matrix inverse"

        # Query GET /api/v1/sessions (summary list)
        list_res = client.get("/api/v1/sessions")
        assert list_res.status_code == 200
        matching = next((s for s in list_res.json() if s["session_id"] == session_id), None)
        assert matching is not None
        assert matching["current_mode"] == "TEACHER"


# =====================================================================
# 7. TEACHER MODE ATTEMPT COUNT & INTERVENTION DATABASE PERSISTENCE
# =====================================================================

def test_teacher_mode_persists_attempt_count_and_intervention(test_db_session):
    """
    Verify that when transitioning to TEACHER mode:
    1. teacher_attempt_count is persisted in PostgreSQL.
    2. teacher_intervention is persisted as JSON in PostgreSQL.
    """
    session, state = _setup_test_session_in_db(test_db_session)

    intervention = TeacherIntervention(
        active=True,
        gap="Chain rule nested functions",
        attempt_count=1,
        verification_required=True,
    )
    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.TEACH_GAP,
        state_updates=StateUpdates(
            current_mode=Mode.TEACHER,
            teacher_attempt_count=1,
            teacher_intervention=intervention,
        ),
        content="Let's identify the outer and inner functions first.",
    )

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="I'm stuck on composite functions.", input_type=CommonInputType.TEXT)
    service.send_message(test_db_session, session.id, user_msg)

    test_db_session.expire_all()
    reloaded = test_db_session.query(SessionState).filter_by(session_id=session.id).one()

    assert reloaded.current_mode == "TEACHER"
    assert reloaded.teacher_attempt_count == 1
    assert isinstance(reloaded.teacher_intervention, dict)
    assert reloaded.teacher_intervention["active"] is True
    assert reloaded.teacher_intervention["gap"] == "Chain rule nested functions"
    assert reloaded.teacher_intervention["attempt_count"] == 1


def test_multi_turn_teacher_mode_attempt_progression_in_db(test_db_session):
    """
    Verify multi-turn progression and exit in PostgreSQL:
    Turn 1: attempt 1 persisted.
    Turn 2: attempt 2 persisted.
    Turn 3: exit restores question, resets attempt count to 0 and intervention to None in DB.
    """
    session, state = _setup_test_session_in_db(test_db_session)
    mock_engine = MagicMock()
    service = ChatService(ai_engine=mock_engine)

    # Turn 1: Enter TEACHER mode
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.TEACH_GAP,
        state_updates=StateUpdates(
            current_mode=Mode.TEACHER,
            teacher_attempt_count=1,
            teacher_intervention=TeacherIntervention(active=True, gap="Limits", attempt_count=1),
        ),
    )
    service.send_message(test_db_session, session.id, MessageCreate(content="I don't know.", input_type=CommonInputType.TEXT))

    test_db_session.expire_all()
    s1 = test_db_session.query(SessionState).filter_by(session_id=session.id).one()
    assert s1.teacher_attempt_count == 1
    assert s1.teacher_intervention["attempt_count"] == 1

    # Turn 2: Second attempt in TEACHER mode
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.TEACH_GAP,
        state_updates=StateUpdates(
            current_mode=Mode.TEACHER,
            teacher_attempt_count=2,
            teacher_intervention=TeacherIntervention(active=True, gap="Limits", attempt_count=2),
        ),
    )
    service.send_message(test_db_session, session.id, MessageCreate(content="Still confused.", input_type=CommonInputType.TEXT))

    test_db_session.expire_all()
    s2 = test_db_session.query(SessionState).filter_by(session_id=session.id).one()
    assert s2.teacher_attempt_count == 2
    assert s2.teacher_intervention["attempt_count"] == 2

    # Turn 3: Exit TEACHER mode back to STUDENT
    mock_engine.process.return_value = _create_mock_ai_result(
        next_mode=Mode.STUDENT,
        strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
        should_restore_interrupted_question=True,
        state_updates=StateUpdates(current_mode=Mode.STUDENT),
    )
    service.send_message(test_db_session, session.id, MessageCreate(content="Got it now!", input_type=CommonInputType.TEXT))

    test_db_session.expire_all()
    s3 = test_db_session.query(SessionState).filter_by(session_id=session.id).one()
    assert s3.current_mode == "STUDENT"
    assert s3.teacher_attempt_count == 0
    assert s3.teacher_intervention is None


def test_database_hydration_of_teacher_mode_state(test_db_session):
    """
    Verify ChatService hydrates teacher_attempt_count and teacher_intervention from PostgreSQL
    into AIContext before invoking CurioEngine.
    """
    session, state = _setup_test_session_in_db(test_db_session)
    state.current_mode = "TEACHER"
    state.teacher_attempt_count = 2
    state.teacher_intervention = {
        "active": True,
        "gap": "Product rule factor differentiation",
        "attempt_count": 2,
        "verification_required": True,
    }
    test_db_session.commit()

    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(next_mode=Mode.TEACHER)

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="Testing DB hydration.", input_type=CommonInputType.TEXT)
    service.send_message(test_db_session, session.id, user_msg)

    assert mock_engine.process.call_count == 1
    passed_context = mock_engine.process.call_args[0][0]

    assert passed_context.current_state.teacher_attempt_count == 2
    assert isinstance(passed_context.current_state.teacher_intervention, TeacherIntervention)
    assert passed_context.current_state.teacher_intervention.gap == "Product rule factor differentiation"
    assert passed_context.current_state.teacher_intervention.attempt_count == 2

    assert isinstance(passed_context.learning_context.teacher_intervention, TeacherIntervention)
    assert passed_context.learning_context.teacher_intervention.gap == "Product rule factor differentiation"


def test_safe_handling_of_malformed_intervention_in_database(test_db_session):
    """
    Verify ChatService safely handles corrupted or non-conforming intervention JSON
    in PostgreSQL by setting teacher_intervention to None without crashing.
    """
    session, state = _setup_test_session_in_db(test_db_session)
    state.current_mode = "TEACHER"
    state.teacher_attempt_count = 1
    state.teacher_intervention = {"invalid_negative_count": -50, "attempt_count": -10}
    test_db_session.commit()

    mock_engine = MagicMock()
    mock_engine.process.return_value = _create_mock_ai_result(next_mode=Mode.TEACHER)

    service = ChatService(ai_engine=mock_engine)
    user_msg = MessageCreate(content="Testing corrupted JSON in DB.", input_type=CommonInputType.TEXT)
    service.send_message(test_db_session, session.id, user_msg)

    passed_context = mock_engine.process.call_args[0][0]
    assert passed_context.current_state.teacher_attempt_count == 1
    assert passed_context.current_state.teacher_intervention is None
    assert passed_context.learning_context.teacher_intervention is None


# =====================================================================
# 7. TRANSACTION ISOLATION
# =====================================================================

def test_teacher_mode_isolation_step_1_write_marker(test_db_session):
    """Write a specific teacher marker session to verify isolation."""
    session, _ = _setup_test_session_in_db(test_db_session, topic="TEACHER_ISOLATION_MARKER")
    test_db_session.commit()
    assert session.id is not None


def test_teacher_mode_isolation_step_2_verify_rollback(test_db_session):
    """Verify previous test's teacher marker session was rolled back."""
    found = test_db_session.query(Session).filter_by(topic="TEACHER_ISOLATION_MARKER").first()
    assert found is None, "Teacher Mode isolation failure: marker session leaked across tests!"
