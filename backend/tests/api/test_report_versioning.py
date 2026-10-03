"""
API and unit tests for Phase 4 Task 4.4 — Report Versioning & Regeneration.
"""
from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from backend.app.main import app
from backend.app.models.message import Message
from backend.app.models.report import SessionReport
from backend.app.models.report_version import SessionReportVersion
from backend.app.models.session import Session, SessionState
from backend.app.models.user import User
from backend.app.core.security import create_access_token
from backend.app.services.report_service import ReportService
from backend.app.repositories.report_version_repository import ReportVersionRepository

pytestmark = pytest.mark.db_integration


# ===================================================================
# Fixtures & Helpers
# ===================================================================

@pytest.fixture
def auth_user_and_session(test_db_session):
    """Creates a user and active session in test DB."""
    user = User(email=f"version_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Dynamic Programming",
        source_type="GENERAL",
        status="ACTIVE",
    )
    test_db_session.add(session)
    test_db_session.commit()

    state = SessionState(
        session_id=session.id,
        current_mode="STUDENT",
        difficulty=3,
        confidence=0.75,
        active_concept="Memoization",
    )
    test_db_session.add(state)
    test_db_session.commit()

    return user, session, state


@pytest.fixture
def other_user_and_session(test_db_session):
    """Creates a second user and session for IDOR testing."""
    user = User(email=f"other_user_{uuid.uuid4().hex[:8]}@curio.ai")
    test_db_session.add(user)
    test_db_session.commit()

    session = Session(
        user_id=user.id,
        topic="Graph Algorithms",
        source_type="GENERAL",
        status="ACTIVE",
    )
    test_db_session.add(session)
    test_db_session.commit()

    return user, session


@pytest.fixture
def client_for_user(override_get_db):
    """Factory to create TestClient authenticated for a given user."""
    def _create(user):
        token = create_access_token(subject=str(user.id))
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c
    return _create


def _seed_messages(test_db_session, session_id):
    """Helper to seed initial messages with at least one USER message."""
    m1 = Message(session_id=session_id, sender="AI", content="Can you explain memoization?")
    m2 = Message(session_id=session_id, sender="USER", content="Memoization caches return values of expensive function calls based on input arguments.")
    test_db_session.add_all([m1, m2])
    test_db_session.commit()


# ===================================================================
# Core Versioning & Regeneration Tests
# ===================================================================

def test_first_report_creates_version_1(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    # 1. First evaluation/compilation
    resp = client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_number"] == 1

    # 2. Check session_reports cache row
    db_report = test_db_session.query(SessionReport).filter(SessionReport.session_id == session.id).first()
    assert db_report is not None
    assert db_report.version_number == 1

    # 3. Check session_report_versions row
    versions = (
        test_db_session.query(SessionReportVersion)
        .filter(SessionReportVersion.session_id == session.id)
        .all()
    )
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].understanding_score == db_report.understanding_score


def test_subsequent_regeneration_creates_version_2(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    # Create Version 1
    resp1 = client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp1.status_code == 200
    assert resp1.json()["version_number"] == 1

    # Explicitly regenerate report
    resp2 = client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["version_number"] == 2

    # Verify both versions exist in database
    v_repo = ReportVersionRepository()
    items, total = v_repo.list_versions_paginated(test_db_session, session.id)
    assert total == 2
    assert [v.version_number for v in items] == [2, 1]

    # Verify latest cache points to version 2
    db_report = test_db_session.query(SessionReport).filter(SessionReport.session_id == session.id).first()
    assert db_report.version_number == 2


def test_historical_version_1_remains_unchanged_after_regeneration(
    test_db_session, auth_user_and_session, client_for_user
):
    """
    Explicit immutability test:
    Record all fields of Version 1, regenerate to Version 2, fetch Version 1 again,
    and assert every single field is strictly unchanged.
    """
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    # 1. Compile Version 1
    client.post(f"/api/v1/sessions/{session.id}/evaluate")

    # 2. Capture Version 1 state
    resp_v1_initial = client.get(f"/api/v1/sessions/{session.id}/reports/1")
    assert resp_v1_initial.status_code == 200
    v1_data_before = resp_v1_initial.json()

    # 3. Add another message and regenerate
    m3 = Message(session_id=session.id, sender="USER", content="I also understand tabulating bottom-up.")
    test_db_session.add(m3)
    test_db_session.commit()

    resp_regen = client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
    assert resp_regen.status_code == 200
    assert resp_regen.json()["version_number"] == 2

    # 4. Fetch Version 1 again
    resp_v1_after = client.get(f"/api/v1/sessions/{session.id}/reports/1")
    assert resp_v1_after.status_code == 200
    v1_data_after = resp_v1_after.json()

    # 5. Assert strict immutability
    assert v1_data_before["id"] == v1_data_after["id"]
    assert v1_data_before["version_number"] == v1_data_after["version_number"] == 1
    assert v1_data_before["understanding_score"] == v1_data_after["understanding_score"]
    assert v1_data_before["mastery_level"] == v1_data_after["mastery_level"]
    assert v1_data_before["strengths"] == v1_data_after["strengths"]
    assert v1_data_before["high_priority_learning_gaps"] == v1_data_after["high_priority_learning_gaps"]
    assert v1_data_before["misconceptions_detected"] == v1_data_after["misconceptions_detected"]
    assert v1_data_before["concepts_mastered"] == v1_data_after["concepts_mastered"]
    assert v1_data_before["personalized_roadmap"] == v1_data_after["personalized_roadmap"]
    assert v1_data_before["created_at"] == v1_data_after["created_at"]


def test_get_report_returns_latest_version(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    client.post(f"/api/v1/sessions/{session.id}/evaluate")
    client.post(f"/api/v1/sessions/{session.id}/report/regenerate")

    # GET /report must return Version 2 (the latest)
    resp = client.get(f"/api/v1/sessions/{session.id}/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == str(session.id)
    assert data["version_number"] == 2


def test_get_reports_returns_all_versions_newest_first(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    # Create v1, v2, v3
    client.post(f"/api/v1/sessions/{session.id}/evaluate")
    client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
    client.post(f"/api/v1/sessions/{session.id}/report/regenerate")

    resp = client.get(f"/api/v1/sessions/{session.id}/reports")
    assert resp.status_code == 200
    history = resp.json()

    assert history["total"] == 3
    assert len(history["items"]) == 3
    # Newest first ordering
    assert [item["version_number"] for item in history["items"]] == [3, 2, 1]


def test_reports_pagination(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    # Create v1, v2, v3
    client.post(f"/api/v1/sessions/{session.id}/evaluate")
    client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
    client.post(f"/api/v1/sessions/{session.id}/report/regenerate")

    # Page 1, page_size 2 -> should return v3, v2
    resp_p1 = client.get(f"/api/v1/sessions/{session.id}/reports?page=1&page_size=2")
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()
    assert data_p1["page"] == 1
    assert data_p1["page_size"] == 2
    assert data_p1["total"] == 3
    assert data_p1["pages"] == 2
    assert [item["version_number"] for item in data_p1["items"]] == [3, 2]

    # Page 2, page_size 2 -> should return v1
    resp_p2 = client.get(f"/api/v1/sessions/{session.id}/reports?page=2&page_size=2")
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert data_p2["page"] == 2
    assert [item["version_number"] for item in data_p2["items"]] == [1]


def test_get_specific_version(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    client.post(f"/api/v1/sessions/{session.id}/evaluate")
    client.post(f"/api/v1/sessions/{session.id}/report/regenerate")

    resp_v1 = client.get(f"/api/v1/sessions/{session.id}/reports/1")
    assert resp_v1.status_code == 200
    assert resp_v1.json()["version_number"] == 1

    resp_v2 = client.get(f"/api/v1/sessions/{session.id}/reports/2")
    assert resp_v2.status_code == 200
    assert resp_v2.json()["version_number"] == 2


def test_get_nonexistent_version_returns_404(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    client.post(f"/api/v1/sessions/{session.id}/evaluate")

    resp = client.get(f"/api/v1/sessions/{session.id}/reports/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Report version not found"


# ===================================================================
# IDOR & Ownership Anti-Enumeration Tests
# ===================================================================

def test_foreign_session_history_returns_404(test_db_session, auth_user_and_session, other_user_and_session, client_for_user):
    user1, session1, _ = auth_user_and_session
    user2, _ = other_user_and_session
    _seed_messages(test_db_session, session1.id)

    # user1 generates report
    client1 = client_for_user(user1)
    client1.post(f"/api/v1/sessions/{session1.id}/evaluate")

    # user2 attempts to read user1's reports history
    client2 = client_for_user(user2)
    resp = client2.get(f"/api/v1/sessions/{session1.id}/reports")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"


def test_foreign_session_version_lookup_returns_404(test_db_session, auth_user_and_session, other_user_and_session, client_for_user):
    user1, session1, _ = auth_user_and_session
    user2, _ = other_user_and_session
    _seed_messages(test_db_session, session1.id)

    client1 = client_for_user(user1)
    client1.post(f"/api/v1/sessions/{session1.id}/evaluate")

    # user2 attempts to read user1's version 1
    client2 = client_for_user(user2)
    resp = client2.get(f"/api/v1/sessions/{session1.id}/reports/1")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Report version not found"


def test_foreign_session_regeneration_returns_404(test_db_session, auth_user_and_session, other_user_and_session, client_for_user):
    user1, session1, _ = auth_user_and_session
    user2, _ = other_user_and_session
    _seed_messages(test_db_session, session1.id)

    client1 = client_for_user(user1)
    client1.post(f"/api/v1/sessions/{session1.id}/evaluate")

    # user2 attempts to regenerate user1's report
    client2 = client_for_user(user2)
    resp = client2.post(f"/api/v1/sessions/{session1.id}/report/regenerate")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"


def test_unauthenticated_regeneration_returns_401(override_get_db, auth_user_and_session):
    _, session, _ = auth_user_and_session
    with TestClient(app) as raw_client:
        resp = raw_client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
        assert resp.status_code == 401


# ===================================================================
# Empty Session & Validation Tests
# ===================================================================

def test_empty_session_regeneration_returns_400(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    # Do NOT seed any messages
    client = client_for_user(user)

    resp = client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
    assert resp.status_code == 400
    assert "Cannot generate report for session with no interaction history" in resp.json()["detail"]


# ===================================================================
# Failure & Transaction Rollback Tests
# ===================================================================

def test_ai_failure_preserves_previous_latest_report(test_db_session, auth_user_and_session, client_for_user):
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    # 1. Compile Version 1 successfully
    resp1 = client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp1.status_code == 200
    score1 = resp1.json()["understanding_score"]

    # 2. Simulate AI failure during regeneration
    with patch("backend.app.services.report_service.CurioEngine.generate_report", side_effect=RuntimeError("AI Provider Timeout")):
        resp2 = client.post(f"/api/v1/sessions/{session.id}/report/regenerate")
        assert resp2.status_code == 500

    # 3. Verify Version 1 is still the latest report and untouched
    resp_latest = client.get(f"/api/v1/sessions/{session.id}/report")
    assert resp_latest.status_code == 200
    assert resp_latest.json()["version_number"] == 1
    assert resp_latest.json()["understanding_score"] == score1

    # 4. Verify no version 2 was inserted
    versions = (
        test_db_session.query(SessionReportVersion)
        .filter(SessionReportVersion.session_id == session.id)
        .all()
    )
    assert len(versions) == 1
    assert versions[0].version_number == 1


def test_unique_constraint_concurrency_protection(test_db_session, auth_user_and_session):
    """
    Verify database UNIQUE(session_id, version_number) prevents duplicate version insertion.
    """
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)

    service = ReportService()
    service.compile_report(test_db_session, session.id)

    # Attempting to directly insert another row with version_number = 1 should raise IntegrityError
    duplicate_v1 = SessionReportVersion(
        session_id=session.id,
        version_number=1,
        understanding_score=50.0,
    )
    test_db_session.add(duplicate_v1)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_existing_report_idempotency_intact(test_db_session, auth_user_and_session, client_for_user):
    """
    Verify calling evaluate repeatedly without regeneration returns existing report without creating new versions.
    """
    user, session, _ = auth_user_and_session
    _seed_messages(test_db_session, session.id)
    client = client_for_user(user)

    resp1 = client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp1.status_code == 200
    assert resp1.json()["version_number"] == 1

    # Repeated evaluate call should return identical report (idempotent)
    resp2 = client.post(f"/api/v1/sessions/{session.id}/evaluate")
    assert resp2.status_code == 200
    assert resp2.json()["version_number"] == 1
    assert resp2.json()["created_at"] == resp1.json()["created_at"]

    # Exactly 1 version row in database
    v_count = (
        test_db_session.query(SessionReportVersion)
        .filter(SessionReportVersion.session_id == session.id)
        .count()
    )
    assert v_count == 1
