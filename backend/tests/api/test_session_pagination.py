"""
Session Pagination & Filtering Tests — Phase 4, Task 4.1.

Tests for the new paginated session list endpoint with filtering capabilities.

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Uses nested transaction savepoints so all writes roll back on teardown.
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.session import Session, SessionState
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


def _create_session_for_user(db, user_id, topic="Test Topic", status="ACTIVE", created_at=None):
    """Helper: create a session owned by user_id in the test DB."""
    session = Session(
        user_id=user_id,
        topic=topic,
        source_type="GENERAL",
        status=status,
    )
    if created_at is not None:
        session.created_at = created_at
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


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===================================================================
# 1. PAGINATION TESTS
# ===================================================================

class TestSessionPagination:
    """Tests for pagination parameters and behavior."""

    def test_pagination_defaults(self, test_db_session, override_get_db):
        """Test default pagination values (page=1, page_size=20)."""
        user, token = _create_user_and_token(test_db_session, "paging_user")

        # Create 25 sessions
        for i in range(25):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions")
            assert res.status_code == 200
            page = res.json()

            assert page["page"] == 1
            assert page["page_size"] == 20
            assert page["total"] == 25
            assert page["pages"] == 2
            assert len(page["items"]) == 20

    def test_pagination_page_2(self, test_db_session, override_get_db):
        """Test retrieving page 2."""
        user, token = _create_user_and_token(test_db_session, "paging_user2")

        for i in range(25):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=2&page_size=20")
            assert res.status_code == 200
            page = res.json()

            assert page["page"] == 2
            assert page["page_size"] == 20
            assert page["total"] == 25
            assert page["pages"] == 2
            assert len(page["items"]) == 5

    def test_pagination_custom_page_size(self, test_db_session, override_get_db):
        """Test custom page_size."""
        user, token = _create_user_and_token(test_db_session, "paging_user3")

        for i in range(15):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=1&page_size=5")
            assert res.status_code == 200
            page = res.json()

            assert page["page"] == 1
            assert page["page_size"] == 5
            assert page["total"] == 15
            assert page["pages"] == 3
            assert len(page["items"]) == 5

    def test_page_size_max_enforced(self, test_db_session, override_get_db):
        """Test page_size is capped at 100."""
        user, token = _create_user_and_token(test_db_session, "paging_user4")

        for i in range(150):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=1&page_size=200")
            assert res.status_code == 200
            page = res.json()

            assert page["page_size"] == 100  # capped
            assert len(page["items"]) == 100

    def test_page_size_min_enforced(self, test_db_session, override_get_db):
        """Test page_size minimum is 1."""
        user, token = _create_user_and_token(test_db_session, "paging_user5")

        for i in range(5):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=1&page_size=0")
            # FastAPI validation should reject page_size < 1
            assert res.status_code == 422

    def test_page_min_enforced(self, test_db_session, override_get_db):
        """Test page minimum is 1."""
        user, token = _create_user_and_token(test_db_session, "paging_user6")

        _create_session_for_user(test_db_session, user.id, topic="Session 1")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=0&page_size=20")
            assert res.status_code == 422

    def test_page_beyond_last_returns_empty(self, test_db_session, override_get_db):
        """Test requesting page beyond last returns empty items with valid metadata."""
        user, token = _create_user_and_token(test_db_session, "paging_user7")

        for i in range(5):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=5&page_size=2")
            assert res.status_code == 200
            page = res.json()

            assert page["page"] == 5
            assert page["page_size"] == 2
            assert page["total"] == 5
            assert page["pages"] == 3
            assert page["items"] == []

    def test_pagination_ordering_deterministic(self, test_db_session, override_get_db):
        """Test pagination ordering is deterministic (newest first, then by id)."""
        user, token = _create_user_and_token(test_db_session, "paging_user8")

        # Create sessions with slight time gaps
        base_time = datetime.now(timezone.utc)
        for i in range(10):
            created = base_time + timedelta(seconds=i)
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}", created_at=created)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            # Get all pages
            all_items = []
            for page_num in range(1, 4):
                res = client.get(f"/api/v1/sessions?page={page_num}&page_size=4")
                assert res.status_code == 200
                all_items.extend(res.json()["items"])

            # Should be ordered newest first
            topics = [item["topic"] for item in all_items]
            assert topics == [f"Session {i}" for i in range(9, -1, -1)]


# ===================================================================
# 2. STATUS FILTER TESTS
# ===================================================================

class TestSessionStatusFilter:
    """Tests for status filtering."""

    def test_status_filter_active(self, test_db_session, override_get_db):
        """Test filtering by ACTIVE status."""
        user, token = _create_user_and_token(test_db_session, "filter_user1")

        _create_session_for_user(test_db_session, user.id, topic="Active 1", status="ACTIVE")
        _create_session_for_user(test_db_session, user.id, topic="Active 2", status="ACTIVE")
        _create_session_for_user(test_db_session, user.id, topic="Paused 1", status="PAUSED")
        _create_session_for_user(test_db_session, user.id, topic="Completed 1", status="COMPLETED")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?status=ACTIVE")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 2
            assert len(page["items"]) == 2
            assert all(item["status"] == "ACTIVE" for item in page["items"])

    def test_status_filter_paused(self, test_db_session, override_get_db):
        """Test filtering by PAUSED status."""
        user, token = _create_user_and_token(test_db_session, "filter_user2")

        _create_session_for_user(test_db_session, user.id, topic="Active 1", status="ACTIVE")
        _create_session_for_user(test_db_session, user.id, topic="Paused 1", status="PAUSED")
        _create_session_for_user(test_db_session, user.id, topic="Paused 2", status="PAUSED")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?status=PAUSED")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 2
            assert all(item["status"] == "PAUSED" for item in page["items"])

    def test_status_filter_completed(self, test_db_session, override_get_db):
        """Test filtering by COMPLETED status."""
        user, token = _create_user_and_token(test_db_session, "filter_user3")

        _create_session_for_user(test_db_session, user.id, topic="Active 1", status="ACTIVE")
        _create_session_for_user(test_db_session, user.id, topic="Completed 1", status="COMPLETED")
        _create_session_for_user(test_db_session, user.id, topic="Completed 2", status="COMPLETED")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?status=COMPLETED")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 2
            assert all(item["status"] == "COMPLETED" for item in page["items"])

    def test_status_filter_case_insensitive(self, test_db_session, override_get_db):
        """Test status filter accepts case variations."""
        user, token = _create_user_and_token(test_db_session, "filter_user4")

        _create_session_for_user(test_db_session, user.id, topic="Active 1", status="ACTIVE")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?status=active")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 1

    def test_status_filter_invalid(self, test_db_session, override_get_db):
        """Test invalid status returns 422."""
        user, token = _create_user_and_token(test_db_session, "filter_user5")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?status=INVALID_STATUS")
            assert res.status_code == 422

    def test_status_filter_no_results(self, test_db_session, override_get_db):
        """Test status filter with no matching sessions."""
        user, token = _create_user_and_token(test_db_session, "filter_user6")

        _create_session_for_user(test_db_session, user.id, topic="Active 1", status="ACTIVE")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?status=COMPLETED")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 0
            assert page["items"] == []


# ===================================================================
# 3. DATE RANGE FILTER TESTS
# ===================================================================

class TestSessionDateRangeFilter:
    """Tests for created_after and created_before filters."""

    def test_created_after_filter(self, test_db_session, override_get_db):
        """Test filtering by created_after."""
        user, token = _create_user_and_token(test_db_session, "date_user1")

        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        _create_session_for_user(test_db_session, user.id, topic="Old", status="ACTIVE", created_at=base - timedelta(days=10))
        _create_session_for_user(test_db_session, user.id, topic="New 1", status="ACTIVE", created_at=base)
        _create_session_for_user(test_db_session, user.id, topic="New 2", status="ACTIVE", created_at=base + timedelta(days=5))

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions?created_after={base.isoformat()}")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 2
            topics = [item["topic"] for item in page["items"]]
            assert "New 1" in topics
            assert "New 2" in topics
            assert "Old" not in topics

    def test_created_before_filter(self, test_db_session, override_get_db):
        """Test filtering by created_before."""
        user, token = _create_user_and_token(test_db_session, "date_user2")

        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        _create_session_for_user(test_db_session, user.id, topic="Old 1", status="ACTIVE", created_at=base - timedelta(days=10))
        _create_session_for_user(test_db_session, user.id, topic="Old 2", status="ACTIVE", created_at=base - timedelta(days=5))
        _create_session_for_user(test_db_session, user.id, topic="New", status="ACTIVE", created_at=base + timedelta(days=5))

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions?created_before={base.isoformat()}")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 2
            topics = [item["topic"] for item in page["items"]]
            assert "Old 1" in topics
            assert "Old 2" in topics
            assert "New" not in topics

    def test_created_after_and_before_combined(self, test_db_session, override_get_db):
        """Test both created_after and created_before together."""
        user, token = _create_user_and_token(test_db_session, "date_user3")

        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        _create_session_for_user(test_db_session, user.id, topic="Before", status="ACTIVE", created_at=base - timedelta(days=10))
        _create_session_for_user(test_db_session, user.id, topic="In Range 1", status="ACTIVE", created_at=base - timedelta(days=3))
        _create_session_for_user(test_db_session, user.id, topic="In Range 2", status="ACTIVE", created_at=base)
        _create_session_for_user(test_db_session, user.id, topic="In Range 3", status="ACTIVE", created_at=base + timedelta(days=3))
        _create_session_for_user(test_db_session, user.id, topic="After", status="ACTIVE", created_at=base + timedelta(days=10))

        start = (base - timedelta(days=5)).isoformat()
        end = (base + timedelta(days=5)).isoformat()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions?created_after={start}&created_before={end}")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 3
            topics = [item["topic"] for item in page["items"]]
            assert "In Range 1" in topics
            assert "In Range 2" in topics
            assert "In Range 3" in topics
            assert "Before" not in topics
            assert "After" not in topics

    def test_date_filter_invalid_format(self, test_db_session, override_get_db):
        """Test invalid date format returns 422."""
        user, token = _create_user_and_token(test_db_session, "date_user4")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?created_after=not-a-date")
            assert res.status_code == 422


# ===================================================================
# 4. COMBINED FILTER TESTS
# ===================================================================

class TestSessionCombinedFilters:
    """Tests for combining pagination with filters."""

    def test_pagination_with_status_filter(self, test_db_session, override_get_db):
        """Test pagination works with status filter."""
        user, token = _create_user_and_token(test_db_session, "combined_user1")

        for i in range(8):
            _create_session_for_user(test_db_session, user.id, topic=f"Active {i}", status="ACTIVE")
        for i in range(4):
            _create_session_for_user(test_db_session, user.id, topic=f"Paused {i}", status="PAUSED")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            # Page 1 of ACTIVE sessions with page_size=3
            res = client.get("/api/v1/sessions?status=ACTIVE&page=1&page_size=3")
            assert res.status_code == 200
            page = res.json()

            assert page["page"] == 1
            assert page["page_size"] == 3
            assert page["total"] == 8
            assert page["pages"] == 3
            assert len(page["items"]) == 3
            assert all(item["status"] == "ACTIVE" for item in page["items"])

            # Page 2
            res = client.get("/api/v1/sessions?status=ACTIVE&page=2&page_size=3")
            assert res.status_code == 200
            page = res.json()
            assert page["page"] == 2
            assert len(page["items"]) == 3

            # Page 3
            res = client.get("/api/v1/sessions?status=ACTIVE&page=3&page_size=3")
            assert res.status_code == 200
            page = res.json()
            assert page["page"] == 3
            assert len(page["items"]) == 2

    def test_pagination_with_date_filter(self, test_db_session, override_get_db):
        """Test pagination works with date filter."""
        user, token = _create_user_and_token(test_db_session, "combined_user2")

        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            created = base + timedelta(days=i)
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}", status="ACTIVE", created_at=created)

        start = base.isoformat()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions?created_after={start}&page=1&page_size=4")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 10
            assert page["pages"] == 3
            assert len(page["items"]) == 4

    def test_status_and_date_filter_combined(self, test_db_session, override_get_db):
        """Test status and date filters combined."""
        user, token = _create_user_and_token(test_db_session, "combined_user3")

        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        # Active sessions in range
        _create_session_for_user(test_db_session, user.id, topic="Active In", status="ACTIVE", created_at=base)
        _create_session_for_user(test_db_session, user.id, topic="Active In 2", status="ACTIVE", created_at=base + timedelta(days=5))
        # Paused sessions in range
        _create_session_for_user(test_db_session, user.id, topic="Paused In", status="PAUSED", created_at=base)
        # Active sessions out of range
        _create_session_for_user(test_db_session, user.id, topic="Active Out", status="ACTIVE", created_at=base - timedelta(days=10))
        _create_session_for_user(test_db_session, user.id, topic="Active Out 2", status="ACTIVE", created_at=base + timedelta(days=15))

        start = base.isoformat()
        end = (base + timedelta(days=10)).isoformat()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions?status=ACTIVE&created_after={start}&created_before={end}")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 2
            topics = [item["topic"] for item in page["items"]]
            assert "Active In" in topics
            assert "Active In 2" in topics


# ===================================================================
# 5. USER ISOLATION TESTS
# ===================================================================

class TestSessionUserIsolation:
    """Tests for cross-user isolation with pagination and filters."""

    def test_user_a_cannot_see_user_b_sessions_paginated(self, test_db_session, override_get_db):
        """User A's paginated list must not contain User B's sessions."""
        user_a, token_a = _create_user_and_token(test_db_session, "iso_user_a")
        user_b, token_b = _create_user_and_token(test_db_session, "iso_user_b")

        for i in range(5):
            _create_session_for_user(test_db_session, user_a.id, topic=f"User A Session {i}")
        for i in range(5):
            _create_session_for_user(test_db_session, user_b.id, topic=f"User B Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            res = client.get("/api/v1/sessions?page=1&page_size=10")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 5
            assert len(page["items"]) == 5
            topics = [item["topic"] for item in page["items"]]
            assert all("User A" in t for t in topics)
            assert not any("User B" in t for t in topics)

    def test_user_b_cannot_see_user_a_sessions_paginated(self, test_db_session, override_get_db):
        """User B's paginated list must not contain User A's sessions."""
        user_a, token_a = _create_user_and_token(test_db_session, "iso_user_c")
        user_b, token_b = _create_user_and_token(test_db_session, "iso_user_d")

        for i in range(3):
            _create_session_for_user(test_db_session, user_a.id, topic=f"User A Session {i}")
        for i in range(7):
            _create_session_for_user(test_db_session, user_b.id, topic=f"User B Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_b}"
            res = client.get("/api/v1/sessions?page=1&page_size=10")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 7
            assert len(page["items"]) == 7
            topics = [item["topic"] for item in page["items"]]
            assert all("User B" in t for t in topics)
            assert not any("User A" in t for t in topics)

    def test_user_a_cannot_filter_user_b_sessions(self, test_db_session, override_get_db):
        """User A cannot use filters to access User B's sessions."""
        user_a, token_a = _create_user_and_token(test_db_session, "iso_user_e")
        user_b, token_b = _create_user_and_token(test_db_session, "iso_user_f")

        _create_session_for_user(test_db_session, user_a.id, topic="A Active", status="ACTIVE")
        _create_session_for_user(test_db_session, user_b.id, topic="B Active", status="ACTIVE")
        _create_session_for_user(test_db_session, user_b.id, topic="B Paused", status="PAUSED")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            # User A filters for ACTIVE - should only see their own
            res = client.get("/api/v1/sessions?status=ACTIVE")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 1
            assert page["items"][0]["topic"] == "A Active"

    def test_user_isolation_across_pages(self, test_db_session, override_get_db):
        """User isolation holds across multiple pages."""
        user_a, token_a = _create_user_and_token(test_db_session, "iso_user_g")
        user_b, token_b = _create_user_and_token(test_db_session, "iso_user_h")

        for i in range(15):
            _create_session_for_user(test_db_session, user_a.id, topic=f"User A Session {i}")
        for i in range(15):
            _create_session_for_user(test_db_session, user_b.id, topic=f"User B Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            # Check all pages
            all_topics = []
            for page_num in range(1, 4):
                res = client.get(f"/api/v1/sessions?page={page_num}&page_size=10")
                assert res.status_code == 200
                page = res.json()
                all_topics.extend([item["topic"] for item in page["items"]])

            assert len(all_topics) == 15
            assert all("User A" in t for t in all_topics)
            assert not any("User B" in t for t in all_topics)


# ===================================================================
# 6. UNAUTHENTICATED ACCESS TESTS
# ===================================================================

class TestSessionPaginationUnauthenticated:
    """Tests for unauthenticated access to paginated endpoint."""

    def test_get_sessions_unauthenticated(self, raw_client):
        """GET /api/v1/sessions requires authentication."""
        res = raw_client.get("/api/v1/sessions")
        assert res.status_code == 401

    def test_get_sessions_with_params_unauthenticated(self, raw_client):
        """GET /api/v1/sessions with pagination params requires authentication."""
        res = raw_client.get("/api/v1/sessions?page=1&page_size=10&status=ACTIVE")
        assert res.status_code == 401


# ===================================================================
# 7. RESPONSE SCHEMA VALIDATION
# ===================================================================

class TestSessionPaginationResponseSchema:
    """Tests for response schema structure."""

    def test_response_contains_required_fields(self, test_db_session, override_get_db):
        """Test response has all required pagination fields."""
        user, token = _create_user_and_token(test_db_session, "schema_user1")

        _create_session_for_user(test_db_session, user.id, topic="Test")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions")
            assert res.status_code == 200
            page = res.json()

            assert "items" in page
            assert "total" in page
            assert "page" in page
            assert "page_size" in page
            assert "pages" in page

    def test_items_are_session_summaries(self, test_db_session, override_get_db):
        """Test items contain expected session summary fields."""
        user, token = _create_user_and_token(test_db_session, "schema_user2")

        _create_session_for_user(test_db_session, user.id, topic="Test Topic", status="ACTIVE")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions")
            assert res.status_code == 200
            page = res.json()

            item = page["items"][0]
            assert "session_id" in item
            assert "topic" in item
            assert "status" in item
            assert "current_mode" in item
            assert "difficulty" in item
            assert "confidence" in item
            assert "created_at" in item
            assert "last_active_at" in item

    def test_empty_list_response(self, test_db_session, override_get_db):
        """Test response for user with no sessions."""
        user, token = _create_user_and_token(test_db_session, "schema_user3")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 0
            assert page["page"] == 1
            assert page["page_size"] == 20
            assert page["pages"] == 0
            assert page["items"] == []


# ===================================================================
# 8. EDGE CASES
# ===================================================================

class TestSessionPaginationEdgeCases:
    """Edge case tests."""

    def test_large_page_size_capped(self, test_db_session, override_get_db):
        """Test very large page_size is capped at 100."""
        user, token = _create_user_and_token(test_db_session, "edge_user1")

        for i in range(150):
            _create_session_for_user(test_db_session, user.id, topic=f"Session {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions?page=1&page_size=10000")
            assert res.status_code == 200
            page = res.json()

            assert page["page_size"] == 100
            assert len(page["items"]) == 100

    def test_last_active_at_present(self, test_db_session, override_get_db):
        """Test last_active_at is included in response."""
        user, token = _create_user_and_token(test_db_session, "edge_user2")

        _create_session_for_user(test_db_session, user.id, topic="Test")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions")
            assert res.status_code == 200
            page = res.json()

            assert page["items"][0]["last_active_at"] is not None

    def test_no_sessions_total_zero(self, test_db_session, override_get_db):
        """Test total is 0 for user with no sessions."""
        user, token = _create_user_and_token(test_db_session, "edge_user3")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions")
            assert res.status_code == 200
            page = res.json()

            assert page["total"] == 0
            assert page["pages"] == 0