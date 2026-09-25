"""
FastAPI Teacher Intervention API Integration Tests (Phase 3, Task 3.8).
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.session import Session
from backend.app.models.teacher_intervention import TeacherInterventionLog
from backend.app.repositories.teacher_intervention_repository import TeacherInterventionRepository
from backend.app.core.security import create_access_token


pytestmark = pytest.mark.db_integration


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


def _auth_headers_for_user(db, email_prefix: str):
    """Helper: create a user and return auth headers."""
    user, token = _create_user_and_token(db, email_prefix)
    return {"Authorization": f"Bearer {token}"}, user, token


class TestTeacherInterventionAPI:
    """Integration tests for the Teacher Intervention API endpoints."""

    def test_get_user_interventions_unauthenticated(self, raw_client):
        """
        1. Unauthenticated GET /users/me/teacher-interventions → 401.
        """
        res = raw_client.get("/api/v1/users/me/teacher-interventions")
        assert res.status_code == 401

    def test_get_user_interventions_empty(self, authenticated_client, test_db_session):
        """
        4. Empty intervention history returns an empty list.
        """
        res = authenticated_client.get("/api/v1/users/me/teacher-interventions")
        assert res.status_code == 200
        data = res.json()
        assert data["interventions"] == []

    def test_get_user_interventions_own_interventions(self, authenticated_client, test_db_session):
        """
        2. Authenticated user receives their own interventions.
        """
        repo = TeacherInterventionRepository()
        session1 = Session(user_id=authenticated_client.user.id, topic="Topic 1", source_type="GENERAL", status="ACTIVE")
        session2 = Session(user_id=authenticated_client.user.id, topic="Topic 2", source_type="GENERAL", status="ACTIVE")
        test_db_session.add_all([session1, session2])
        test_db_session.commit()
        test_db_session.refresh(session1)
        test_db_session.refresh(session2)

        repo.create(
            test_db_session,
            session_id=session1.id,
            user_id=authenticated_client.user.id,
            gap="Understanding base cases",
            attempt_count=1,
            teacher_explanation="A base case stops infinite recursion...",
            verification_question="What happens without a base case?",
            verification_answer=None,
            verification_passed=None,
            intervention_type="enter",
        )
        repo.create(
            test_db_session,
            session_id=session2.id,
            user_id=authenticated_client.user.id,
            gap="Binary search on unsorted arrays",
            attempt_count=2,
            teacher_explanation="Binary search requires sorted data...",
            verification_question="Why does order matter?",
            verification_answer="Because we need to know which half to discard",
            verification_passed=True,
            intervention_type="continue",
        )

        res = authenticated_client.get("/api/v1/users/me/teacher-interventions")
        assert res.status_code == 200
        data = res.json()
        assert len(data["interventions"]) == 2
        # Check chronological ordering
        assert data["interventions"][0]["gap"] == "Understanding base cases"
        assert data["interventions"][1]["gap"] == "Binary search on unsorted arrays"

    def test_get_user_interventions_isolation(self, raw_client, test_db_session):
        """
        3. User A does not receive User B's interventions.
        """
        from backend.app.core.security import create_access_token

        repo = TeacherInterventionRepository()

        user_a = User(email=f"user_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"user_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        session_a = Session(user_id=user_a.id, topic="A's Session", source_type="GENERAL", status="ACTIVE")
        session_b = Session(user_id=user_b.id, topic="B's Session", source_type="GENERAL", status="ACTIVE")
        test_db_session.add_all([session_a, session_b])
        test_db_session.commit()
        test_db_session.refresh(session_a)
        test_db_session.refresh(session_b)

        repo.create(test_db_session, session_id=session_a.id, user_id=user_a.id, gap="A's Gap", attempt_count=1)
        repo.create(test_db_session, session_id=session_b.id, user_id=user_b.id, gap="B's Gap", attempt_count=1)

        token_a = create_access_token(subject=str(user_a.id))
        token_b = create_access_token(subject=str(user_b.id))

        with raw_client as client_a:
            client_a.headers.update({"Authorization": f"Bearer {token_a}"})
            res_a = client_a.get("/api/v1/users/me/teacher-interventions")
            assert res_a.status_code == 200
            data_a = res_a.json()
            assert len(data_a["interventions"]) == 1
            assert data_a["interventions"][0]["gap"] == "A's Gap"

        with raw_client as client_b:
            client_b.headers.update({"Authorization": f"Bearer {token_b}"})
            res_b = client_b.get("/api/v1/users/me/teacher-interventions")
            assert res_b.status_code == 200
            data_b = res_b.json()
            assert len(data_b["interventions"]) == 1
            assert data_b["interventions"][0]["gap"] == "B's Gap"

    def test_get_session_interventions_own_session(self, authenticated_client, test_db_session):
        """
        5. Session-specific endpoint returns interventions for the authenticated user's session.
        """
        repo = TeacherInterventionRepository()
        session = Session(
            user_id=authenticated_client.user.id,
            topic="Recursion",
            source_type="GENERAL",
            status="ACTIVE",
        )
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        repo.create(
            test_db_session,
            session_id=session.id,
            user_id=authenticated_client.user.id,
            gap="Understanding base cases",
            attempt_count=1,
        )
        repo.create(
            test_db_session,
            session_id=session.id,
            user_id=authenticated_client.user.id,
            gap="Call stack memory",
            attempt_count=2,
        )

        res = authenticated_client.get(f"/api/v1/users/me/sessions/{session.id}/teacher-interventions")
        assert res.status_code == 200
        data = res.json()
        assert len(data["interventions"]) == 2
        assert data["interventions"][0]["gap"] == "Understanding base cases"
        assert data["interventions"][1]["gap"] == "Call stack memory"

    def test_get_session_interventions_cross_user_returns_404(self, raw_client, test_db_session):
        """
        6. Cross-user session access follows existing anti-enumeration behavior.
        """
        from backend.app.core.security import create_access_token

        repo = TeacherInterventionRepository()

        user_a = User(email=f"session_user_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"session_user_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        session = Session(user_id=user_a.id, topic="A's Session", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        repo.create(test_db_session, session.id, user_a.id, "A's Gap", attempt_count=1)

        token_b = create_access_token(subject=str(user_b.id))

        with raw_client as client:
            client.headers.update({"Authorization": f"Bearer {token_b}"})
            res = client.get(f"/api/v1/users/me/sessions/{session.id}/teacher-interventions")
            # Anti-enumeration: returns 404 (not 403) to avoid leaking session existence
            assert res.status_code == 404

    def test_get_session_interventions_nonexistent_session(self, authenticated_client):
        """
        Session that doesn't exist returns 404.
        """
        fake_session_id = uuid.uuid4()
        res = authenticated_client.get(f"/api/v1/users/me/sessions/{fake_session_id}/teacher-interventions")
        assert res.status_code == 404

    def test_chronological_ordering(self, authenticated_client, test_db_session):
        """
        9. Chronological ordering is preserved.
        """
        from datetime import datetime, timezone, timedelta

        repo = TeacherInterventionRepository()
        session = Session(
            user_id=authenticated_client.user.id,
            topic="Ordering Test",
            source_type="GENERAL",
            status="ACTIVE",
        )
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        # Create with explicit timestamps
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(minutes=10)
        later = now + timedelta(minutes=10)

        i1 = TeacherInterventionLog(
            session_id=session.id, user_id=authenticated_client.user.id, gap="First", attempt_count=1,
            created_at=earlier
        )
        i2 = TeacherInterventionLog(
            session_id=session.id, user_id=authenticated_client.user.id, gap="Second", attempt_count=2,
            created_at=now
        )
        i3 = TeacherInterventionLog(
            session_id=session.id, user_id=authenticated_client.user.id, gap="Third", attempt_count=3,
            created_at=later
        )
        test_db_session.add_all([i1, i2, i3])
        test_db_session.commit()

        res = authenticated_client.get(f"/api/v1/users/me/sessions/{session.id}/teacher-interventions")
        assert res.status_code == 200
        data = res.json()
        assert len(data["interventions"]) == 3
        assert data["interventions"][0]["gap"] == "First"
        assert data["interventions"][1]["gap"] == "Second"
        assert data["interventions"][2]["gap"] == "Third"

    def test_inactive_user_cannot_access(self, test_db_session, override_get_db):
        """
        10. Inactive user cannot access endpoint.
        """
        from backend.app.core.security import create_access_token
        from fastapi.testclient import TestClient
        from backend.app.main import app

        repo = TeacherInterventionRepository()
        user = User(email=f"inactive_user_{uuid.uuid4().hex[:8]}@curio.ai", is_active=False)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        token = create_access_token(subject=str(user.id))

        with TestClient(app) as client:
            client.headers.update({"Authorization": f"Bearer {token}"})
            res = client.get("/api/v1/users/me/teacher-interventions")
            # Inactive user gets 400 based on Phase 2 get_current_active_user
            assert res.status_code == 400
            assert "inactive" in res.json()["detail"].lower()

    def test_session_auth_unaffected(self, raw_client, test_db_session):
        """
        11. Existing session/report authentication and IDOR behavior remains intact.
        """
        from backend.app.core.security import create_access_token

        repo = TeacherInterventionRepository()
        user_a = User(email=f"sess_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"sess_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        token_a = create_access_token(subject=str(user_a.id))
        session_a = Session(user_id=user_a.id, topic="Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session_a)
        test_db_session.commit()
        test_db_session.refresh(session_a)
        repo.create(test_db_session, session_id=session_a.id, user_id=user_a.id, gap="A's Gap", attempt_count=1)

        with raw_client as client:
            client.headers.update({"Authorization": f"Bearer {token_a}"})
            res = client.post("/api/v1/sessions", json={"topic": "Test", "source_type": "GENERAL"})
            assert res.status_code == 201
            session_id = res.json()["id"]

            # User B cannot access User A's session
            user_b_obj = test_db_session.query(User).filter_by(email=user_b.email).first()
            token_b = create_access_token(subject=str(user_b_obj.id))
            with raw_client as client2:
                client2.headers.update({"Authorization": f"Bearer {token_b}"})
                res2 = client2.get(f"/api/v1/sessions/{session_id}")
                assert res2.status_code == 404

    def test_no_ai_logic_called(self, authenticated_client, test_db_session):
        """
        12. No AI engine/provider is called by the API.
        """
        import inspect

        repo = TeacherInterventionRepository()
        session = Session(user_id=authenticated_client.user.id, topic="Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        repo.create(
            test_db_session,
            session_id=session.id,
            user_id=authenticated_client.user.id,
            gap="Test Gap",
            attempt_count=1,
        )

        # Verify no AI imports or calls in the router
        import backend.app.api.v1.teacher_interventions as ti_module
        source = inspect.getsource(ti_module)

        assert "CurioEngine" not in source
        assert "DecisionEngine" not in source
        assert "Groq" not in source
        assert "process(" not in source
        assert "evaluate_session" not in source
        assert "generate_report" not in source

    def test_user_id_from_auth_not_request(self, raw_client, test_db_session):
        """
        13. User ID is always derived from authentication, not request input.
        """
        from backend.app.core.security import create_access_token

        repo = TeacherInterventionRepository()
        user_a = User(email=f"user_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"user_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        session_a = Session(user_id=user_a.id, topic="A's Session", source_type="GENERAL", status="ACTIVE")
        session_b = Session(user_id=user_b.id, topic="B's Session", source_type="GENERAL", status="ACTIVE")
        test_db_session.add_all([session_a, session_b])
        test_db_session.commit()
        test_db_session.refresh(session_a)
        test_db_session.refresh(session_b)

        token_a = create_access_token(subject=str(user_a.id))
        repo.create(test_db_session, session_id=session_a.id, user_id=user_a.id, gap="A's Gap", attempt_count=1)
        repo.create(test_db_session, session_id=session_b.id, user_id=user_b.id, gap="B's Gap", attempt_count=1)

        with raw_client as client:
            client.headers.update({"Authorization": f"Bearer {token_a}"})
            res = client.get("/api/v1/users/me/teacher-interventions")
            assert res.status_code == 200
            data = res.json()
            assert data["interventions"][0]["gap"] == "A's Gap"