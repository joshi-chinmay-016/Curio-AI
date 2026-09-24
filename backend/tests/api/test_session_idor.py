"""
Session IDOR (Insecure Direct Object Reference) Security Tests — Phase 2, Task 5.

Comprehensive authorization and isolation test suite verifying that:
- Unauthenticated requests across all session, message, and report endpoints return HTTP 401.
- Cross-user session access returns HTTP 404 (anti-enumeration), not 403.
- Each user can only see, modify, and delete their own sessions.
- Cross-user access attempts do not leak data, modify session state, insert messages,
  trigger AI processing, or delete resources.
- Message and report access is strictly scoped to session ownership.

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Uses nested transaction savepoints so all writes roll back on teardown.
"""

import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.session import Session, SessionState
from backend.app.models.message import Message
from backend.app.models.report import SessionReport
from backend.app.models.user import User
from backend.app.core.security import create_access_token
from backend.app.db.session import get_db


pytestmark = pytest.mark.db_integration


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def raw_client(override_get_db):
    """Unauthenticated TestClient — no Authorization header."""
    with TestClient(app) as client:
        yield client


def _create_user_and_token(db, email_prefix: str):
    """Helper: create a user in the test DB and return (user, token)."""
    user = User(email=f"{email_prefix}_{uuid.uuid4().hex[:8]}@curio.ai")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id))
    return user, token


def _create_session_for_user(db, user_id, topic="Test Topic", status="ACTIVE"):
    """Helper: create a session owned by user_id in the test DB."""
    session = Session(
        user_id=user_id,
        topic=topic,
        source_type="GENERAL",
        status=status,
    )
    db.add(session)
    db.flush()
    state = SessionState(
        session_id=session.id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.0,
        active_concept="Core Concept",
        unresolved_misconceptions=[],
        mastered_concepts=[],
        teacher_attempt_count=0,
        teacher_intervention=None,
    )
    db.add(state)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def user_a(test_db_session):
    user, token = _create_user_and_token(test_db_session, "idor_user_a")
    return user, token


@pytest.fixture
def user_b(test_db_session):
    user, token = _create_user_and_token(test_db_session, "idor_user_b")
    return user, token


@pytest.fixture
def session_a(test_db_session, user_a):
    user, _ = user_a
    return _create_session_for_user(test_db_session, user.id, topic="User A Session")


@pytest.fixture
def session_b(test_db_session, user_b):
    user, _ = user_b
    return _create_session_for_user(test_db_session, user.id, topic="User B Session")


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===================================================================
# 1. UNAUTHENTICATED ACCESS — HTTP 401
# ===================================================================

class TestUnauthenticatedAccess:
    """All session, message, and report endpoints must reject unauthenticated requests with HTTP 401."""

    def test_post_sessions_unauthenticated(self, raw_client):
        res = raw_client.post("/api/v1/sessions", json={"topic": "X", "source_type": "GENERAL"})
        assert res.status_code == 401

    def test_get_sessions_unauthenticated(self, raw_client):
        res = raw_client.get("/api/v1/sessions")
        assert res.status_code == 401

    def test_get_session_by_id_unauthenticated(self, raw_client, session_a):
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}")
        assert res.status_code == 401

    def test_patch_session_unauthenticated(self, raw_client, session_a):
        res = raw_client.patch(f"/api/v1/sessions/{session_a.id}", json={"topic": "Hacked"})
        assert res.status_code == 401

    def test_delete_session_unauthenticated(self, raw_client, session_a):
        res = raw_client.delete(f"/api/v1/sessions/{session_a.id}")
        assert res.status_code == 401

    def test_pause_session_unauthenticated(self, raw_client, session_a):
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/pause")
        assert res.status_code == 401

    def test_resume_session_unauthenticated(self, raw_client, session_a):
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/resume")
        assert res.status_code == 401

    def test_end_session_unauthenticated(self, raw_client, session_a):
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/end")
        assert res.status_code == 401

    def test_evaluate_session_unauthenticated(self, raw_client, session_a):
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/evaluate")
        assert res.status_code == 401

    def test_post_message_unauthenticated(self, raw_client, session_a):
        res = raw_client.post(
            f"/api/v1/sessions/{session_a.id}/messages",
            json={"content": "hack", "input_type": "TEXT"},
        )
        assert res.status_code == 401

    def test_get_messages_unauthenticated(self, raw_client, session_a):
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}/messages")
        assert res.status_code == 401

    def test_get_report_unauthenticated(self, raw_client, session_a):
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}/report")
        assert res.status_code == 401


# ===================================================================
# 2. CROSS-USER SESSION ISOLATION — HTTP 404 (Anti-Enumeration)
# ===================================================================

class TestCrossUserSessionIsolation:
    """
    User A must not be able to access, modify, or interact with User B's sessions,
    and User B must not be able to access, modify, or interact with User A's sessions.
    All unauthorized cross-user access attempts must return HTTP 404 to avoid
    leaking resource existence (anti-enumeration).
    """

    def test_user_a_cannot_get_user_b_session(self, raw_client, user_a, session_b):
        _, token_a = user_a
        res = raw_client.get(f"/api/v1/sessions/{session_b.id}", headers=_auth_header(token_a))
        assert res.status_code == 404

    def test_user_b_cannot_get_user_a_session(self, raw_client, user_b, session_a):
        _, token_b = user_b
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}", headers=_auth_header(token_b))
        assert res.status_code == 404

    def test_user_a_cannot_patch_user_b_session(self, raw_client, user_a, session_b, test_db_session):
        _, token_a = user_a
        original_topic = session_b.topic
        res = raw_client.patch(
            f"/api/v1/sessions/{session_b.id}",
            json={"topic": "Hijacked Topic"},
            headers=_auth_header(token_a),
        )
        assert res.status_code == 404
        test_db_session.refresh(session_b)
        assert session_b.topic == original_topic

    def test_user_b_cannot_patch_user_a_session(self, raw_client, user_b, session_a, test_db_session):
        _, token_b = user_b
        original_topic = session_a.topic
        res = raw_client.patch(
            f"/api/v1/sessions/{session_a.id}",
            json={"topic": "Hijacked Topic by B"},
            headers=_auth_header(token_b),
        )
        assert res.status_code == 404
        test_db_session.refresh(session_a)
        assert session_a.topic == original_topic

    def test_user_a_cannot_delete_user_b_session(self, raw_client, user_a, session_b, test_db_session):
        _, token_a = user_a
        res = raw_client.delete(f"/api/v1/sessions/{session_b.id}", headers=_auth_header(token_a))
        assert res.status_code == 404
        still_exists = test_db_session.query(Session).filter(Session.id == session_b.id).first()
        assert still_exists is not None

    def test_user_b_cannot_delete_user_a_session(self, raw_client, user_b, session_a, test_db_session):
        _, token_b = user_b
        res = raw_client.delete(f"/api/v1/sessions/{session_a.id}", headers=_auth_header(token_b))
        assert res.status_code == 404
        still_exists = test_db_session.query(Session).filter(Session.id == session_a.id).first()
        assert still_exists is not None

    def test_user_a_cannot_pause_user_b_session(self, raw_client, user_a, session_b, test_db_session):
        _, token_a = user_a
        res = raw_client.post(f"/api/v1/sessions/{session_b.id}/pause", headers=_auth_header(token_a))
        assert res.status_code == 404
        test_db_session.refresh(session_b)
        assert session_b.status == "ACTIVE"

    def test_user_b_cannot_pause_user_a_session(self, raw_client, user_b, session_a, test_db_session):
        _, token_b = user_b
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/pause", headers=_auth_header(token_b))
        assert res.status_code == 404
        test_db_session.refresh(session_a)
        assert session_a.status == "ACTIVE"

    def test_user_a_cannot_resume_user_b_session(self, raw_client, user_a, user_b, test_db_session):
        user_b_obj, _ = user_b
        paused_session = _create_session_for_user(test_db_session, user_b_obj.id, topic="Paused B", status="PAUSED")
        _, token_a = user_a
        res = raw_client.post(f"/api/v1/sessions/{paused_session.id}/resume", headers=_auth_header(token_a))
        assert res.status_code == 404
        test_db_session.refresh(paused_session)
        assert paused_session.status == "PAUSED"

    def test_user_b_cannot_resume_user_a_session(self, raw_client, user_a, user_b, test_db_session):
        user_a_obj, _ = user_a
        paused_session = _create_session_for_user(test_db_session, user_a_obj.id, topic="Paused A", status="PAUSED")
        _, token_b = user_b
        res = raw_client.post(f"/api/v1/sessions/{paused_session.id}/resume", headers=_auth_header(token_b))
        assert res.status_code == 404
        test_db_session.refresh(paused_session)
        assert paused_session.status == "PAUSED"

    def test_user_a_cannot_end_user_b_session(self, raw_client, user_a, session_b, test_db_session):
        _, token_a = user_a
        res = raw_client.post(f"/api/v1/sessions/{session_b.id}/end", headers=_auth_header(token_a))
        assert res.status_code == 404
        test_db_session.refresh(session_b)
        assert session_b.status == "ACTIVE"

    def test_user_b_cannot_end_user_a_session(self, raw_client, user_b, session_a, test_db_session):
        _, token_b = user_b
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/end", headers=_auth_header(token_b))
        assert res.status_code == 404
        test_db_session.refresh(session_a)
        assert session_a.status == "ACTIVE"

    def test_user_a_cannot_evaluate_user_b_session(self, raw_client, user_a, session_b):
        _, token_a = user_a
        res = raw_client.post(f"/api/v1/sessions/{session_b.id}/evaluate", headers=_auth_header(token_a))
        assert res.status_code == 404

    def test_user_b_cannot_evaluate_user_a_session(self, raw_client, user_b, session_a):
        _, token_b = user_b
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/evaluate", headers=_auth_header(token_b))
        assert res.status_code == 404

    def test_user_a_cannot_post_message_to_user_b_session(self, raw_client, user_a, session_b, test_db_session):
        _, token_a = user_a
        initial_count = test_db_session.query(Message).filter(Message.session_id == session_b.id).count()
        with patch("backend.app.services.chat_service.CurioEngine.process") as mock_ai:
            res = raw_client.post(
                f"/api/v1/sessions/{session_b.id}/messages",
                json={"content": "Cross-user injection attempt", "input_type": "TEXT"},
                headers=_auth_header(token_a),
            )
            assert res.status_code == 404
            # Verify AI was not invoked
            mock_ai.assert_not_called()
        # Verify no message persisted
        final_count = test_db_session.query(Message).filter(Message.session_id == session_b.id).count()
        assert final_count == initial_count

    def test_user_b_cannot_post_message_to_user_a_session(self, raw_client, user_b, session_a, test_db_session):
        _, token_b = user_b
        initial_count = test_db_session.query(Message).filter(Message.session_id == session_a.id).count()
        with patch("backend.app.services.chat_service.CurioEngine.process") as mock_ai:
            res = raw_client.post(
                f"/api/v1/sessions/{session_a.id}/messages",
                json={"content": "Cross-user injection by B", "input_type": "TEXT"},
                headers=_auth_header(token_b),
            )
            assert res.status_code == 404
            mock_ai.assert_not_called()
        final_count = test_db_session.query(Message).filter(Message.session_id == session_a.id).count()
        assert final_count == initial_count

    def test_user_a_cannot_get_messages_from_user_b_session(self, raw_client, user_a, session_b):
        _, token_a = user_a
        res = raw_client.get(f"/api/v1/sessions/{session_b.id}/messages", headers=_auth_header(token_a))
        assert res.status_code == 404

    def test_user_b_cannot_get_messages_from_user_a_session(self, raw_client, user_b, session_a):
        _, token_b = user_b
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}/messages", headers=_auth_header(token_b))
        assert res.status_code == 404

    def test_user_a_cannot_get_report_for_user_b_session(self, raw_client, user_a, session_b, test_db_session):
        # Create an existing report for Session B
        report = SessionReport(
            session_id=session_b.id,
            understanding_score=85.0,
            mastery_level="INTERMEDIATE",
            strengths=["A"],
            high_priority_learning_gaps=[],
            medium_priority_learning_gaps=[],
            low_priority_learning_gaps=[],
            misconceptions_detected=[],
            concepts_mastered=[],
            personalized_roadmap=[],
            recommended_exercises=[],
            concept_assessments=[],
            resolved_gaps=[],
            unresolved_gaps=[],
            resolved_misconceptions=[],
            unresolved_misconceptions=[],
            session_evaluation={},
        )
        test_db_session.add(report)
        test_db_session.commit()

        _, token_a = user_a
        res = raw_client.get(f"/api/v1/sessions/{session_b.id}/report", headers=_auth_header(token_a))
        assert res.status_code == 404

    def test_user_b_cannot_get_report_for_user_a_session(self, raw_client, user_b, session_a, test_db_session):
        report = SessionReport(
            session_id=session_a.id,
            understanding_score=90.0,
            mastery_level="ADVANCED",
            strengths=["B"],
            high_priority_learning_gaps=[],
            medium_priority_learning_gaps=[],
            low_priority_learning_gaps=[],
            misconceptions_detected=[],
            concepts_mastered=[],
            personalized_roadmap=[],
            recommended_exercises=[],
            concept_assessments=[],
            resolved_gaps=[],
            unresolved_gaps=[],
            resolved_misconceptions=[],
            unresolved_misconceptions=[],
            session_evaluation={},
        )
        test_db_session.add(report)
        test_db_session.commit()

        _, token_b = user_b
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}/report", headers=_auth_header(token_b))
        assert res.status_code == 404


# ===================================================================
# 3. SESSION CREATION & LIST ISOLATION
# ===================================================================

class TestSessionListIsolation:
    """User A's session list must not contain User B's sessions and vice versa."""

    def test_user_creates_session_assigned_authenticated_user_id(self, raw_client, user_a, test_db_session):
        user_obj, token_a = user_a
        res = raw_client.post(
            "/api/v1/sessions",
            json={"topic": "Quantum Computing", "source_type": "GENERAL"},
            headers=_auth_header(token_a),
        )
        assert res.status_code == 201
        session_data = res.json()
        assert session_data["topic"] == "Quantum Computing"
        session_id = uuid.UUID(session_data["id"])

        db_sess = test_db_session.query(Session).filter(Session.id == session_id).first()
        assert db_sess is not None
        assert db_sess.user_id == user_obj.id

    def test_user_a_list_contains_only_own_sessions(self, raw_client, user_a, user_b, session_a, session_b):
        _, token_a = user_a
        res = raw_client.get("/api/v1/sessions", headers=_auth_header(token_a))
        assert res.status_code == 200
        session_ids = [s["session_id"] for s in res.json()]
        assert str(session_a.id) in session_ids
        assert str(session_b.id) not in session_ids

    def test_user_b_list_contains_only_own_sessions(self, raw_client, user_a, user_b, session_a, session_b):
        _, token_b = user_b
        res = raw_client.get("/api/v1/sessions", headers=_auth_header(token_b))
        assert res.status_code == 200
        session_ids = [s["session_id"] for s in res.json()]
        assert str(session_b.id) in session_ids
        assert str(session_a.id) not in session_ids


# ===================================================================
# 4. OWNER CAN ACCESS OWN SESSION
# ===================================================================

class TestOwnerAccess:
    """Authenticated users can access their own sessions normally."""

    def test_owner_can_get_own_session(self, raw_client, user_a, session_a):
        _, token_a = user_a
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}", headers=_auth_header(token_a))
        assert res.status_code == 200
        assert res.json()["id"] == str(session_a.id)

    def test_owner_can_patch_own_session(self, raw_client, user_a, session_a):
        _, token_a = user_a
        res = raw_client.patch(
            f"/api/v1/sessions/{session_a.id}",
            json={"topic": "Updated Topic"},
            headers=_auth_header(token_a),
        )
        assert res.status_code == 200
        assert res.json()["topic"] == "Updated Topic"

    def test_owner_can_delete_own_session(self, raw_client, user_a, session_a):
        _, token_a = user_a
        res = raw_client.delete(f"/api/v1/sessions/{session_a.id}", headers=_auth_header(token_a))
        assert res.status_code == 204

    def test_owner_can_pause_own_session(self, raw_client, user_a, session_a):
        _, token_a = user_a
        res = raw_client.post(f"/api/v1/sessions/{session_a.id}/pause", headers=_auth_header(token_a))
        assert res.status_code == 200
        assert res.json()["status"] == "PAUSED"

    def test_owner_can_resume_own_session(self, raw_client, user_a, user_b, test_db_session):
        user_a_obj, token_a = user_a
        paused_session = _create_session_for_user(test_db_session, user_a_obj.id, topic="Paused Mine", status="PAUSED")
        res = raw_client.post(f"/api/v1/sessions/{paused_session.id}/resume", headers=_auth_header(token_a))
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"

    def test_owner_can_get_own_messages(self, raw_client, user_a, session_a):
        _, token_a = user_a
        res = raw_client.get(f"/api/v1/sessions/{session_a.id}/messages", headers=_auth_header(token_a))
        assert res.status_code == 200
        assert isinstance(res.json(), list)
