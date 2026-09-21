"""
Real PostgreSQL Integration Tests for Curio AI Backend.

These tests execute against the dedicated, isolated 'curio_test_db'
provisioned via Alembic migrations.

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Never writes to the development database (curio_db).
- Does not call Base.metadata.create_all() or Alembic downgrade.
- Uses nested transaction savepoints so all writes roll back on teardown.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from sqlalchemy import text
from backend.app.models.user import User
from backend.app.models.session import Session, SessionState
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.models.document import Document
from backend.app.models.report import SessionReport
from backend.app.repositories.message_repository import MessageRepository
from backend.app.services.chat_service import ChatService
from backend.app.ai.engine import CurioEngine
from backend.app.schemas.message import MessageCreate
from backend.app.schemas.common import InputType as CommonInputType
from backend.tests.services.test_chat_service import create_mock_ai_result


pytestmark = pytest.mark.db_integration


def test_test_database_url_target(test_db_url):
    """Verify that test fixtures strictly target curio_test_db and not curio_db."""
    assert "curio_test_db" in test_db_url
    assert "curio_db" not in test_db_url.split("/")[-1]


def test_create_and_retrieve_user(test_db_session):
    """Verify creating, persisting, and retrieving a User in PostgreSQL."""
    user = User(email=f"learner_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    assert user.id is not None
    retrieved = test_db_session.query(User).filter_by(id=user.id).first()
    assert retrieved is not None
    assert retrieved.email == user.email
    assert retrieved.created_at is not None


def test_create_session_linked_to_user(test_db_session):
    """Verify creating a Session linked to a User via foreign key."""
    user = User(email=f"session_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Photosynthesis",
        source_type="prompt",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    assert session.id is not None
    retrieved = test_db_session.query(Session).filter_by(id=session.id).first()
    assert retrieved is not None
    assert retrieved.user_id == user.id
    assert retrieved.user.email == user.email
    assert session in user.sessions


def test_create_and_retrieve_messages(test_db_session):
    """Verify creating and retrieving multiple ordered Messages in a Session."""
    user = User(email=f"msg_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Cellular Respiration",
        source_type="prompt",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    msg1 = Message(
        session_id=session.id,
        sender="user",
        content="What is ATP?",
        input_type="text"
    )
    msg2 = Message(
        session_id=session.id,
        sender="ai",
        content="ATP is the energy currency of the cell.",
        input_type="text"
    )
    test_db_session.add_all([msg1, msg2])
    test_db_session.commit()

    messages = (
        test_db_session.query(Message)
        .filter_by(session_id=session.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    assert len(messages) == 2
    assert messages[0].content == "What is ATP?"
    assert messages[1].sender == "ai"
    assert messages[0].session.id == session.id


def test_create_session_state(test_db_session):
    """Verify persisting and retrieving SessionState with JSON fields in PostgreSQL."""
    user = User(email=f"state_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Quantum Mechanics",
        source_type="prompt",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    state = SessionState(
        session_id=session.id,
        current_mode="evaluator",
        difficulty=3,
        confidence=0.75,
        active_concept="Wave-Particle Duality",
        consecutive_strong_answers=2,
        consecutive_weak_answers=0,
        unresolved_misconceptions=["Photon mass confusion"],
        mastered_concepts=["Superposition"]
    )
    test_db_session.add(state)
    test_db_session.commit()

    retrieved = test_db_session.query(SessionState).filter_by(session_id=session.id).first()
    assert retrieved is not None
    assert retrieved.confidence == 0.75
    assert retrieved.unresolved_misconceptions == ["Photon mass confusion"]
    assert retrieved.mastered_concepts == ["Superposition"]
    assert retrieved.teacher_attempt_count == 0
    assert retrieved.teacher_intervention is None
    assert session.state.confidence == 0.75


def test_create_session_state_with_teacher_mode_fields(test_db_session):
    """Verify persisting and retrieving teacher_attempt_count and teacher_intervention in PostgreSQL."""
    user = User(email=f"teacher_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Linear Algebra",
        source_type="prompt",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    state = SessionState(
        session_id=session.id,
        current_mode="TEACHER",
        difficulty=2,
        confidence=0.5,
        active_concept="Eigenvalues",
        consecutive_strong_answers=1,
        consecutive_weak_answers=1,
        unresolved_misconceptions=[],
        mastered_concepts=[],
        teacher_attempt_count=2,
        teacher_intervention={"active": True, "gap": "Characteristic equation", "attempt_count": 2, "verification_required": True}
    )
    test_db_session.add(state)
    test_db_session.commit()

    retrieved = test_db_session.query(SessionState).filter_by(session_id=session.id).first()
    assert retrieved is not None
    assert retrieved.teacher_attempt_count == 2
    assert isinstance(retrieved.teacher_intervention, dict)
    assert retrieved.teacher_intervention["gap"] == "Characteristic equation"
    assert retrieved.teacher_intervention["attempt_count"] == 2


def test_create_turn_evaluation_linked_to_message(test_db_session):
    """Verify creating a TurnEvaluation linked to a Message."""
    user = User(email=f"eval_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Gravity",
        source_type="prompt",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    msg = Message(
        session_id=session.id,
        sender="user",
        content="Gravity pulls objects with mass together.",
        input_type="text"
    )
    test_db_session.add(msg)
    test_db_session.commit()

    eval_record = TurnEvaluation(
        message_id=msg.id,
        correctness=0.9,
        clarity=0.85,
        completeness=0.8,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.05,
        misconceptions=[],
        missing_concepts=["Curvature of spacetime"],
        undefined_terms=[],
        mastered_concepts=["Gravitational Attraction"],
        knowledge_gap="General Relativity perspective missing",
        recommended_strategy="socratic",
        recommended_difficulty=3
    )
    test_db_session.add(eval_record)
    test_db_session.commit()

    retrieved = test_db_session.query(TurnEvaluation).filter_by(message_id=msg.id).first()
    assert retrieved is not None
    assert retrieved.message_id == msg.id
    assert retrieved.correctness == 0.9
    assert retrieved.mastered_concepts == ["Gravitational Attraction"]
    assert msg.evaluation == retrieved


def test_foreign_key_cascades(test_db_session):
    """Verify PostgreSQL foreign key cascade rules when deleting records."""
    user = User(email=f"cascade_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Cascade Testing",
        source_type="prompt",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    msg = Message(
        session_id=session.id,
        sender="user",
        content="Testing cascade delete",
        input_type="text"
    )
    test_db_session.add(msg)
    test_db_session.commit()

    eval_record = TurnEvaluation(
        message_id=msg.id,
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
        recommended_strategy="advance",
        recommended_difficulty=2
    )
    test_db_session.add(eval_record)
    test_db_session.commit()

    # Deleting the Message must cascade delete the TurnEvaluation
    test_db_session.delete(msg)
    test_db_session.commit()
    assert test_db_session.query(TurnEvaluation).filter_by(message_id=msg.id).first() is None

    # Deleting the User must cascade delete the Session
    test_db_session.delete(user)
    test_db_session.commit()
    assert test_db_session.query(Session).filter_by(id=session.id).first() is None


def test_document_and_session_set_null_cascade(test_db_session):
    """Verify that deleting a Document sets session.document_id to NULL rather than deleting session."""
    user = User(email=f"doc_user_{uuid.uuid4().hex[:8]}@curio.ai")
    doc = Document(
        filename="lecture_notes.pdf",
        file_size=10240,
        mime_type="application/pdf"
    )
    test_db_session.add_all([user, doc])
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        document_id=doc.id,
        topic="Lecture Review",
        source_type="document",
        status="active"
    )
    test_db_session.add(session)
    test_db_session.commit()

    assert session.document_id == doc.id

    # Delete document
    test_db_session.delete(doc)
    test_db_session.commit()

    # Session still exists, but document_id is NULL
    refreshed_session = test_db_session.query(Session).filter_by(id=session.id).first()
    assert refreshed_session is not None
    assert refreshed_session.document_id is None


def test_create_session_report(test_db_session):
    """Verify persisting and retrieving a SessionReport with complex JSON fields."""
    user = User(email=f"report_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Full Report Test",
        source_type="prompt",
        status="completed"
    )
    test_db_session.add(session)
    test_db_session.commit()

    report = SessionReport(
        session_id=session.id,
        understanding_score=0.88,
        mastery_level="proficient",
        strengths=["Core concepts", "Analytical problem solving"],
        high_priority_learning_gaps=[],
        medium_priority_learning_gaps=["Advanced derivations"],
        low_priority_learning_gaps=[],
        misconceptions_detected=[],
        concepts_mastered=["Linear algebra fundamentals"],
        teacher_interventions_required=1,
        difficulty_achieved=4,
        personalized_roadmap=["Module 1 complete", "Proceed to Module 2"],
        recommended_exercises=[{"id": 1, "topic": "Eigenvalues"}]
    )
    test_db_session.add(report)
    test_db_session.commit()

    retrieved = test_db_session.query(SessionReport).filter_by(session_id=session.id).first()
    assert retrieved is not None
    assert retrieved.understanding_score == 0.88
    assert retrieved.mastery_level == "proficient"
    assert "Linear algebra fundamentals" in retrieved.concepts_mastered
    assert retrieved.recommended_exercises == [{"id": 1, "topic": "Eigenvalues"}]


def test_get_recent_evaluations_by_session_isolation_and_filtering(test_db_session):
    """Verify that get_recent_evaluations_by_session strictly isolates sessions and filters by USER sender."""
    repo = MessageRepository()
    user = User(email=f"eval_iso_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session_1 = Session(user_id=user.id, topic="Session 1", source_type="prompt", status="active")
    session_2 = Session(user_id=user.id, topic="Session 2", source_type="prompt", status="active")
    test_db_session.add_all([session_1, session_2])
    test_db_session.commit()

    msg1_s1 = Message(session_id=session_1.id, sender="USER", content="User in S1", input_type="text")
    msg2_s1_ai = Message(session_id=session_1.id, sender="AI", content="AI in S1", input_type="text")
    test_db_session.add_all([msg1_s1, msg2_s1_ai])
    test_db_session.commit()

    eval1_s1 = TurnEvaluation(
        message_id=msg1_s1.id,
        correctness=0.9,
        clarity=0.9,
        completeness=0.9,
        depth=0.9,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["s1_concept"],
        recommended_strategy="PROBE_WHY",
        recommended_difficulty=2
    )
    eval2_s1_ai = TurnEvaluation(
        message_id=msg2_s1_ai.id,
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
        recommended_strategy="PROBE_WHY",
        recommended_difficulty=1
    )
    test_db_session.add_all([eval1_s1, eval2_s1_ai])

    msg1_s2 = Message(session_id=session_2.id, sender="USER", content="User in S2", input_type="text")
    test_db_session.add(msg1_s2)
    test_db_session.commit()

    eval1_s2 = TurnEvaluation(
        message_id=msg1_s2.id,
        correctness=0.6,
        clarity=0.6,
        completeness=0.6,
        depth=0.6,
        relevance=1.0,
        stuck_probability=0.2,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["s2_concept"],
        recommended_strategy="TEACH_GAP",
        recommended_difficulty=1
    )
    test_db_session.add(eval1_s2)
    test_db_session.commit()

    s1_evals = repo.get_recent_evaluations_by_session(test_db_session, session_1.id)
    assert len(s1_evals) == 1
    assert s1_evals[0].message_id == msg1_s1.id
    assert s1_evals[0].mastered_concepts == ["s1_concept"]

    s2_evals = repo.get_recent_evaluations_by_session(test_db_session, session_2.id)
    assert len(s2_evals) == 1
    assert s2_evals[0].message_id == msg1_s2.id
    assert s2_evals[0].mastered_concepts == ["s2_concept"]


def test_get_recent_evaluations_limit_and_chronological_ordering(test_db_session):
    """Verify that get_recent_evaluations_by_session fetches the latest 10 evaluations and returns them chronologically."""
    repo = MessageRepository()
    user = User(email=f"eval_order_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(user_id=user.id, topic="Chronological Ordering", source_type="prompt", status="active")
    test_db_session.add(session)
    test_db_session.commit()

    base_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    messages = []
    evaluations = []

    for i in range(12):
        msg = Message(
            session_id=session.id,
            sender="USER",
            content=f"User Turn {i + 1}",
            input_type="text",
            created_at=base_time + timedelta(minutes=i)
        )
        test_db_session.add(msg)
        test_db_session.flush()

        ev = TurnEvaluation(
            message_id=msg.id,
            correctness=0.5,
            clarity=0.5,
            completeness=0.5,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=[f"concept_{i + 1}"],
            knowledge_gap=f"gap_turn_{i + 1}",
            recommended_strategy="PROBE_WHY",
            recommended_difficulty=2
        )
        test_db_session.add(ev)
        messages.append(msg)
        evaluations.append(ev)

    test_db_session.commit()

    recent_evals = repo.get_recent_evaluations_by_session(test_db_session, session.id, limit=10)

    assert len(recent_evals) == 10

    for idx, expected_turn_num in enumerate(range(3, 13)):
        assert recent_evals[idx].knowledge_gap == f"gap_turn_{expected_turn_num}"
        assert recent_evals[idx].mastered_concepts == [f"concept_{expected_turn_num}"]
        assert recent_evals[idx].message_id == messages[expected_turn_num - 1].id


def test_chat_service_hydrates_real_database_evaluations(test_db_session):
    """Verify that ChatService against real PostgreSQL hydrates previous evaluations into AIContext."""
    user = User(email=f"chat_hydrate_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(user_id=user.id, topic="Photosynthesis Real DB", source_type="prompt", status="active")
    test_db_session.add(session)
    test_db_session.commit()

    state = SessionState(
        session_id=session.id,
        current_mode="STUDENT",
        difficulty=2,
        confidence=0.5,
        active_concept="Light Reactions",
        consecutive_strong_answers=1,
        consecutive_weak_answers=0,
    )
    test_db_session.add(state)
    test_db_session.commit()

    prev_msg = Message(
        session_id=session.id,
        sender="USER",
        content="Chlorophyll absorbs light energy.",
        input_type="text"
    )
    test_db_session.add(prev_msg)
    test_db_session.commit()

    prev_eval = TurnEvaluation(
        message_id=prev_msg.id,
        correctness=0.9,
        clarity=0.85,
        completeness=0.8,
        depth=0.75,
        relevance=1.0,
        stuck_probability=0.05,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["chlorophyll_pigments"],
        knowledge_gap="Thylakoid membrane role",
        recommended_strategy="PROBE_WHY",
        recommended_difficulty=2
    )
    test_db_session.add(prev_eval)
    test_db_session.commit()

    mock_engine = MagicMock(spec=CurioEngine)
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)
    new_msg_in = MessageCreate(content="Where does the Calvin cycle take place?", input_type=CommonInputType.TEXT)

    service.send_message(test_db_session, session.id, new_msg_in)

    assert mock_engine.process.called
    context = mock_engine.process.call_args[0][0]
    assert len(context.learning_context.recent_evaluations) == 1
    eval_hydrated = context.learning_context.recent_evaluations[0]
    assert eval_hydrated.correctness == 0.9
    assert eval_hydrated.mastered_concepts == ["chlorophyll_pigments"]
    assert eval_hydrated.knowledge_gap == "Thylakoid membrane role"


def test_isolation_step_1_write_marker(test_db_session):
    """Write a specific marker user in test 1 to test isolation."""
    user = User(email="isolation_marker_check@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    # Marker is visible within this test session
    found = test_db_session.query(User).filter_by(email="isolation_marker_check@curio.ai").first()
    assert found is not None


def test_isolation_step_2_verify_rollback(test_db_session):
    """Verify that previous test's write was completely rolled back and not persisted."""
    found = test_db_session.query(User).filter_by(email="isolation_marker_check@curio.ai").first()
    assert found is None, "Test isolation failed: marker user from previous test leaked into this test!"
