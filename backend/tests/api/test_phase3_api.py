"""
Integration and API tests for Phase 3 Evaluator Mode, Reporting, and Persistence (3G).
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.evaluation import TurnEvaluation as DBTurnEvaluation
from backend.app.models.message import Message
from backend.app.models.report import SessionReport
from backend.app.models.session import Session, SessionState
from backend.app.models.user import User
from backend.app.repositories.report_repository import ReportRepository
from backend.app.services.report_service import ReportService
from backend.app.ai.engine import CurioEngine
from backend.app.ai.providers.mock_provider import MockLLMProvider

pytestmark = pytest.mark.db_integration


@pytest.fixture
def api_client(override_get_db):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_user_and_session(test_db_session):
    user = User(email=f"eval_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Binary Search",
        source_type="GENERAL",
        status="ACTIVE",
    )
    test_db_session.add(session)
    test_db_session.commit()

    state = SessionState(
        session_id=session.id,
        current_mode="STUDENT",
        difficulty=2,
        confidence=0.6,
        active_concept="Monotonic Search",
    )
    test_db_session.add(state)
    test_db_session.commit()

    return user, session, state


def test_evaluate_valid_session(api_client, test_db_session, test_user_and_session):
    user, session, state = test_user_and_session

    # Seed messages and evaluations
    m1 = Message(session_id=session.id, sender="AI", content="What is binary search?")
    test_db_session.add(m1)
    test_db_session.commit()

    m2 = Message(session_id=session.id, sender="USER", content="It divides a sorted list in half to find a target.")
    test_db_session.add(m2)
    test_db_session.commit()

    te1 = DBTurnEvaluation(
        message_id=m2.id,
        correctness=0.9,
        clarity=0.85,
        completeness=0.85,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["Divide and conquer"],
        recommended_strategy="INCREASE_DIFFICULTY",
        recommended_difficulty=2,
    )
    test_db_session.add(te1)
    test_db_session.commit()

    # Call evaluate endpoint
    response = api_client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == str(session.id)
    assert 0.0 <= data["understanding_score"] <= 100.0
    assert data["mastery_level"] in ["BEGINNER", "DEVELOPING", "PROFICIENT", "MASTERY"]
    assert "Divide and conquer" in data["strengths"] or len(data["strengths"]) > 0
    assert len(data["personalized_roadmap"]) >= 1

    # Verify session is marked COMPLETED in database
    db_sess = test_db_session.query(Session).filter(Session.id == session.id).first()
    assert db_sess.status == "COMPLETED"
    assert db_sess.ended_at is not None


def test_evaluate_invalid_session(api_client):
    fake_id = uuid.uuid4()
    response = api_client.post(f"/api/v1/sessions/{fake_id}/evaluate")
    assert response.status_code == 404


def test_get_report_endpoint(api_client, test_db_session, test_user_and_session):
    user, session, state = test_user_and_session

    # Before evaluation, getting report returns 404
    resp_pre = api_client.get(f"/api/v1/sessions/{session.id}/report")
    assert resp_pre.status_code == 404

    # Evaluate
    resp_eval = api_client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp_eval.status_code == 200

    # After evaluation, report is retrievable
    resp_post = api_client.get(f"/api/v1/sessions/{session.id}/report")
    assert resp_post.status_code == 200
    assert resp_post.json()["session_id"] == str(session.id)


def test_repeated_evaluation_is_idempotent(api_client, test_db_session, test_user_and_session):
    user, session, state = test_user_and_session

    resp1 = api_client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp1.status_code == 200
    score1 = resp1.json()["understanding_score"]

    # Second evaluate call returns the same persisted report
    resp2 = api_client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp2.status_code == 200
    assert resp2.json()["understanding_score"] == score1
    assert resp2.json()["created_at"] == resp1.json()["created_at"]


def test_end_session_triggers_report(api_client, test_db_session, test_user_and_session):
    user, session, state = test_user_and_session

    response = api_client.post(f"/api/v1/sessions/{session.id}/end")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == str(session.id)
    assert "understanding_score" in data


def test_report_service_direct_persistence(test_db_session, test_user_and_session):
    user, session, state = test_user_and_session
    mock_engine = CurioEngine(MockLLMProvider())
    service = ReportService(ai_engine=mock_engine)

    report = service.compile_report(test_db_session, session.id)
    assert report is not None
    assert report.session_id == session.id

    # Verify retrieval
    retrieved = service.get_report(test_db_session, session.id)
    assert retrieved is not None
    assert retrieved.understanding_score == report.understanding_score
