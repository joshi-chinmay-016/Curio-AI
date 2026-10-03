"""
Learning Timeline Aggregation API Tests — Phase 4, Task 4.3.

Tests for the paginated learning timeline aggregation endpoint:
GET /api/v1/users/me/timeline

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Uses nested transaction savepoints so all writes roll back on teardown.
- Does NOT run the full test suite; only targeted timeline tests.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.session import Session, SessionState
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.models.turn_assessment import TurnAssessment
from backend.app.models.teacher_intervention import TeacherInterventionLog
from backend.app.models.report import SessionReport
from backend.app.models.user import User
from backend.app.core.security import create_access_token
from backend.app.schemas.timeline import SUPPORTED_EVENT_TYPES


pytestmark = pytest.mark.db_integration


# ===================================================================
# Fixtures & Test Helpers
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


def _create_session(
    db,
    user_id,
    topic="Test Topic",
    source_type="GENERAL",
    status="ACTIVE",
    created_at=None,
    ended_at=None,
):
    """Helper: create a session owned by user_id."""
    session = Session(
        user_id=user_id,
        topic=topic,
        source_type=source_type,
        status=status,
    )
    if created_at is not None:
        session.created_at = created_at
    if ended_at is not None:
        session.ended_at = ended_at
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


def _create_message(
    db,
    session_id,
    sender="USER",
    content="Test message content",
    input_type="TEXT",
    created_at=None,
):
    """Helper: create a message in session."""
    msg = Message(
        session_id=session_id,
        sender=sender,
        content=content,
        input_type=input_type,
    )
    if created_at is not None:
        msg.created_at = created_at
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _create_evaluation(
    db,
    message_id,
    correctness=0.9,
    recommended_strategy="PROBE_DEEPER",
    recommended_difficulty=3,
):
    """Helper: create a TurnEvaluation for a message."""
    ev = TurnEvaluation(
        message_id=message_id,
        correctness=correctness,
        clarity=0.8,
        completeness=0.85,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.05,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["recursion"],
        knowledge_gap=None,
        recommended_strategy=recommended_strategy,
        recommended_difficulty=recommended_difficulty,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _create_turn_assessment(
    db,
    message_id,
    session_id,
    user_id,
    created_at=None,
    has_learning_assessment=True,
    has_turn_interpretation=True,
    has_learning_objective=True,
    has_question_specification=True,
):
    """Helper: create a TurnAssessment."""
    assessment = TurnAssessment(
        message_id=message_id,
        session_id=session_id,
        user_id=user_id,
        learning_assessment={"intent": "ANSWER_ATTEMPT", "secret_key": "private_data"} if has_learning_assessment else None,
        turn_interpretation={"intent": "ANSWER_ATTEMPT"} if has_turn_interpretation else None,
        learning_objective={"target_concept": "base_case"} if has_learning_objective else None,
        question_specification={"difficulty": 2} if has_question_specification else None,
    )
    if created_at is not None:
        assessment.created_at = created_at
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def _create_teacher_intervention(
    db,
    session_id,
    user_id,
    gap="Struggling with base cases",
    intervention_type="enter",
    attempt_count=1,
    verification_passed=1,
    created_at=None,
):
    """Helper: create a TeacherInterventionLog."""
    log = TeacherInterventionLog(
        session_id=session_id,
        user_id=user_id,
        gap=gap,
        intervention_type=intervention_type,
        attempt_count=attempt_count,
        verification_passed=verification_passed,
        teacher_explanation="A base case is required.",
        verification_question="Why do we need a base case?",
        verification_answer="To prevent infinite recursion.",
    )
    if created_at is not None:
        log.created_at = created_at
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _create_session_report(
    db,
    session_id,
    understanding_score=0.88,
    mastery_level="PROFICIENT",
    concepts_mastered=None,
    created_at=None,
):
    """Helper: create a SessionReport."""
    if concepts_mastered is None:
        concepts_mastered = ["recursion", "memoization"]
    report = SessionReport(
        session_id=session_id,
        understanding_score=understanding_score,
        mastery_level=mastery_level,
        strengths=["Good conceptual grasp"],
        high_priority_learning_gaps=[],
        medium_priority_learning_gaps=[],
        low_priority_learning_gaps=[],
        misconceptions_detected=[],
        concepts_mastered=concepts_mastered,
        teacher_interventions_required=1,
        difficulty_achieved=3,
        personalized_roadmap=["dynamic_programming"],
        recommended_exercises=["fibonacci_dp"],
        evidence_confidence=0.9,
    )
    if created_at is not None:
        report.created_at = created_at
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ===================================================================
# 1. AUTHENTICATION TESTS
# ===================================================================

class TestTimelineAuthentication:
    """Authentication checks for GET /api/v1/users/me/timeline."""

    def test_unauthenticated_returns_401(self, raw_client):
        """Unauthenticated request must return 401."""
        res = raw_client.get("/api/v1/users/me/timeline")
        assert res.status_code == 401

    def test_unauthenticated_with_params_returns_401(self, raw_client):
        """Unauthenticated request with query params must also return 401."""
        res = raw_client.get("/api/v1/users/me/timeline?page=1&page_size=10")
        assert res.status_code == 401


# ===================================================================
# 2. OWNERSHIP & ANTI-ENUMERATION TESTS
# ===================================================================

class TestTimelineOwnership:
    """Ownership and IDOR protection tests."""

    def test_user_sees_only_own_timeline(self, test_db_session, override_get_db):
        """User A must see only User A's events, never User B's events."""
        user_a, token_a = _create_user_and_token(test_db_session, "user_a")
        user_b, token_b = _create_user_and_token(test_db_session, "user_b")

        session_a = _create_session(test_db_session, user_a.id, topic="User A Session")
        session_b = _create_session(test_db_session, user_b.id, topic="User B Session")

        _create_message(test_db_session, session_a.id, sender="USER", content="Message A")
        _create_message(test_db_session, session_b.id, sender="USER", content="Message B")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            res = client.get("/api/v1/users/me/timeline")
            assert res.status_code == 200
            data = res.json()

            # Ensure all items belong to session_a
            for item in data["items"]:
                assert item["session_id"] == str(session_a.id)
                assert item["session_id"] != str(session_b.id)

    def test_foreign_session_id_returns_404(self, test_db_session, override_get_db):
        """Querying with a session_id belonging to another user must return 404."""
        user_a, token_a = _create_user_and_token(test_db_session, "user_a_idor")
        user_b, _ = _create_user_and_token(test_db_session, "user_b_idor")

        session_b = _create_session(test_db_session, user_b.id, topic="Private B Session")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            res = client.get(f"/api/v1/users/me/timeline?session_id={session_b.id}")
            assert res.status_code == 404
            assert res.json()["detail"] == "Session not found"

    def test_nonexistent_session_id_returns_404(self, test_db_session, override_get_db):
        """Querying with a non-existent session_id must return 404."""
        user_a, token_a = _create_user_and_token(test_db_session, "user_a_nonexistent")
        random_id = uuid.uuid4()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            res = client.get(f"/api/v1/users/me/timeline?session_id={random_id}")
            assert res.status_code == 404
            assert res.json()["detail"] == "Session not found"

    def test_owned_session_with_no_events_matching_filter_returns_200_empty(self, test_db_session, override_get_db):
        """Owned session with no events matching a filter must return 200 with empty list, not 404."""
        user, token = _create_user_and_token(test_db_session, "user_owned_empty")
        session = _create_session(test_db_session, user.id, topic="Empty Session")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            # Filter for teacher_intervention when none exist
            res = client.get(f"/api/v1/users/me/timeline?session_id={session.id}&event_types=teacher_intervention")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 0
            assert data["items"] == []
            assert data["pages"] == 0


# ===================================================================
# 3. EVENT TYPES & METADATA TESTS
# ===================================================================

class TestTimelineEventTypes:
    """Verification of all 7 supported event types and their factual metadata."""

    def test_session_created_event(self, test_db_session, override_get_db):
        """session_created contains topic and source_type."""
        user, token = _create_user_and_token(test_db_session, "evt_sc")
        session = _create_session(test_db_session, user.id, topic="Binary Trees", source_type="DOCUMENT")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=session_created")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "session_created"
            assert item["session_id"] == str(session.id)
            assert item["entity_id"] == str(session.id)
            assert item["metadata"]["topic"] == "Binary Trees"
            assert item["metadata"]["source_type"] == "DOCUMENT"

    def test_user_message_event(self, test_db_session, override_get_db):
        """user_message contains bounded content and input_type."""
        user, token = _create_user_and_token(test_db_session, "evt_um")
        session = _create_session(test_db_session, user.id, topic="Recursion")
        long_content = "A" * 600
        msg = _create_message(test_db_session, session.id, sender="USER", content=long_content, input_type="VOICE")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=user_message")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "user_message"
            assert item["message_id"] == str(msg.id)
            assert item["metadata"]["input_type"] == "VOICE"
            assert len(item["metadata"]["content"]) == 500  # bounded to 500 chars

    def test_ai_message_excluded(self, test_db_session, override_get_db):
        """AI messages (sender='AI') must NOT appear in the timeline."""
        user, token = _create_user_and_token(test_db_session, "evt_ai_excl")
        session = _create_session(test_db_session, user.id, topic="AI Exclusion")
        _create_message(test_db_session, session.id, sender="AI", content="I am an AI assistant")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=user_message")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 0

    def test_evaluation_event(self, test_db_session, override_get_db):
        """evaluation contains persisted correctness, strategy, and difficulty."""
        user, token = _create_user_and_token(test_db_session, "evt_eval")
        session = _create_session(test_db_session, user.id, topic="Graph Theory")
        msg = _create_message(test_db_session, session.id, sender="USER", content="A graph has vertices")
        _create_evaluation(
            test_db_session,
            msg.id,
            correctness=0.95,
            recommended_strategy="PROBE_DEEPER",
            recommended_difficulty=4,
        )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=evaluation")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "evaluation"
            assert item["message_id"] == str(msg.id)
            assert item["metadata"]["correctness"] == 0.95
            assert item["metadata"]["recommended_strategy"] == "PROBE_DEEPER"
            assert item["metadata"]["recommended_difficulty"] == 4

    def test_turn_assessment_event(self, test_db_session, override_get_db):
        """turn_assessment contains only presence flags, not raw JSON."""
        user, token = _create_user_and_token(test_db_session, "evt_ta")
        session = _create_session(test_db_session, user.id, topic="Sorting")
        msg = _create_message(test_db_session, session.id, sender="USER", content="QuickSort partitions")
        assessment = _create_turn_assessment(
            test_db_session,
            msg.id,
            session.id,
            user.id,
            has_learning_assessment=True,
            has_turn_interpretation=True,
            has_learning_objective=False,
            has_question_specification=True,
        )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=turn_assessment")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "turn_assessment"
            assert item["message_id"] == str(msg.id)
            assert item["entity_id"] == str(assessment.id)
            meta = item["metadata"]
            assert meta["has_learning_assessment"] is True
            assert meta["has_turn_interpretation"] is True
            assert meta["has_learning_objective"] is False
            assert meta["has_question_specification"] is True
            # Verify no raw private data leaked
            assert "secret_key" not in str(meta)

    def test_teacher_intervention_event(self, test_db_session, override_get_db):
        """teacher_intervention contains intervention_type, bounded gap, attempt_count, verification_passed."""
        user, token = _create_user_and_token(test_db_session, "evt_ti")
        session = _create_session(test_db_session, user.id, topic="Dynamic Programming")
        long_gap = "G" * 600
        ti = _create_teacher_intervention(
            test_db_session,
            session.id,
            user.id,
            gap=long_gap,
            intervention_type="enter",
            attempt_count=2,
            verification_passed=1,
        )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=teacher_intervention")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "teacher_intervention"
            assert item["entity_id"] == str(ti.id)
            meta = item["metadata"]
            assert meta["intervention_type"] == "enter"
            assert meta["attempt_count"] == 2
            assert meta["verification_passed"] == 1
            assert len(meta["gap"]) == 500  # truncated

    def test_report_generated_event(self, test_db_session, override_get_db):
        """report_generated contains understanding_score, mastery_level, concepts_mastered_count."""
        user, token = _create_user_and_token(test_db_session, "evt_rg")
        session = _create_session(test_db_session, user.id, topic="Heaps")
        _create_session_report(
            test_db_session,
            session.id,
            understanding_score=0.92,
            mastery_level="MASTERY",
            concepts_mastered=["min_heap", "max_heap", "heapify"],
        )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=report_generated")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "report_generated"
            assert item["session_id"] == str(session.id)
            meta = item["metadata"]
            assert meta["understanding_score"] == 0.92
            assert meta["mastery_level"] == "MASTERY"
            assert meta["concepts_mastered_count"] == 3

    def test_session_ended_event(self, test_db_session, override_get_db):
        """session_ended event only present when ended_at is not NULL."""
        user, token = _create_user_and_token(test_db_session, "evt_se")
        now = datetime.now(timezone.utc)
        # Active session without ended_at
        active_sess = _create_session(test_db_session, user.id, topic="Active S")
        # Completed session with ended_at
        ended_sess = _create_session(
            test_db_session,
            user.id,
            topic="Completed S",
            status="COMPLETED",
            ended_at=now,
        )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?event_types=session_ended")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            item = data["items"][0]
            assert item["event_type"] == "session_ended"
            assert item["session_id"] == str(ended_sess.id)
            assert item["metadata"]["status"] == "COMPLETED"


# ===================================================================
# 4. MULTIPLE SESSIONS & MERGING TESTS
# ===================================================================

class TestTimelineMultipleSessions:
    """Events across multiple owned sessions must merge seamlessly."""

    def test_events_from_multiple_sessions_merge_correctly(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "multi_sess")
        t0 = datetime(2024, 2, 1, 10, 0, 0, tzinfo=timezone.utc)

        s1 = _create_session(test_db_session, user.id, topic="S1", created_at=t0)
        s2 = _create_session(test_db_session, user.id, topic="S2", created_at=t0 + timedelta(hours=1))

        _create_message(test_db_session, s1.id, sender="USER", content="M1", created_at=t0 + timedelta(minutes=10))
        _create_message(test_db_session, s2.id, sender="USER", content="M2", created_at=t0 + timedelta(hours=1, minutes=10))

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 4
            session_ids = [item["session_id"] for item in data["items"]]
            # s1 created, s1 message, s2 created, s2 message
            assert session_ids == [str(s1.id), str(s1.id), str(s2.id), str(s2.id)]


# ===================================================================
# 5. ORDERING TESTS
# ===================================================================

class TestTimelineOrdering:
    """Chronological primary order and deterministic secondary order."""

    def test_chronological_ordering(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "order_user")
        t0 = datetime(2024, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

        s = _create_session(test_db_session, user.id, topic="Ordering", created_at=t0)
        _create_message(test_db_session, s.id, sender="USER", content="Second", created_at=t0 + timedelta(minutes=5))
        _create_message(test_db_session, s.id, sender="USER", content="Third", created_at=t0 + timedelta(minutes=10))

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?session_id={s.id}")
            assert res.status_code == 200
            data = res.json()
            timestamps = [datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")) for item in data["items"]]
            assert timestamps == sorted(timestamps)

    def test_deterministic_ordering_for_equal_timestamps(self, test_db_session, override_get_db):
        """Repeated identical requests must produce identical stable ordering even for events with equal timestamps."""
        user, token = _create_user_and_token(test_db_session, "stable_user")
        t0 = datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

        s = _create_session(test_db_session, user.id, topic="Stable Order", created_at=t0)
        # Message and Evaluation share created_at t0 + 1 min
        m_time = t0 + timedelta(minutes=1)
        m = _create_message(test_db_session, s.id, sender="USER", content="Ans", created_at=m_time)
        _create_evaluation(test_db_session, m.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res1 = client.get(f"/api/v1/users/me/timeline?session_id={s.id}")
            res2 = client.get(f"/api/v1/users/me/timeline?session_id={s.id}")
            assert res1.status_code == 200
            assert res2.status_code == 200
            assert res1.json()["items"] == res2.json()["items"]


# ===================================================================
# 6. PAGINATION TESTS
# ===================================================================

class TestTimelinePagination:
    """Pagination behaviors: default, pages, custom size, cap at 100, beyond last page, empty."""

    def test_default_pagination(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_default")
        s = _create_session(test_db_session, user.id, topic="Paging")
        for i in range(25):
            _create_message(test_db_session, s.id, sender="USER", content=f"Msg {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline")
            assert res.status_code == 200
            data = res.json()
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert data["total"] == 26  # 1 session_created + 25 messages
            assert data["pages"] == 2
            assert len(data["items"]) == 20

    def test_pagination_page_2(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_page2")
        s = _create_session(test_db_session, user.id, topic="Paging Page 2")
        for i in range(25):
            _create_message(test_db_session, s.id, sender="USER", content=f"Msg {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=2&page_size=20")
            assert res.status_code == 200
            data = res.json()
            assert data["page"] == 2
            assert data["total"] == 26
            assert data["pages"] == 2
            assert len(data["items"]) == 6

    def test_custom_page_size(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_custom")
        s = _create_session(test_db_session, user.id, topic="Custom Page Size")
        for i in range(10):
            _create_message(test_db_session, s.id, sender="USER", content=f"Msg {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=1&page_size=5")
            assert res.status_code == 200
            data = res.json()
            assert data["page_size"] == 5
            assert len(data["items"]) == 5

    def test_page_size_max_enforced(self, test_db_session, override_get_db):
        """page_size > 100 must be capped at 100."""
        user, token = _create_user_and_token(test_db_session, "pg_max")
        _create_session(test_db_session, user.id, topic="Max Page Size")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=1&page_size=200")
            assert res.status_code == 200
            data = res.json()
            assert data["page_size"] == 100

    def test_page_size_min_enforced(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_min")
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=1&page_size=0")
            assert res.status_code == 422

    def test_page_min_enforced(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_pagemin")
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=0&page_size=20")
            assert res.status_code == 422

    def test_beyond_last_page(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_beyond")
        _create_session(test_db_session, user.id, topic="Beyond")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=99&page_size=20")
            assert res.status_code == 200
            data = res.json()
            assert data["items"] == []
            assert data["total"] == 1
            assert data["pages"] == 1
            assert data["page"] == 99

    def test_empty_timeline(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "pg_empty")
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline")
            assert res.status_code == 200
            data = res.json()
            assert data["items"] == []
            assert data["total"] == 0
            assert data["pages"] == 0


# ===================================================================
# 7. FILTERING TESTS
# ===================================================================

class TestTimelineFiltering:
    """Filtering by session_id, event_types, start, end, and combinations."""

    def test_filter_by_session_id(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_sess")
        s1 = _create_session(test_db_session, user.id, topic="S1")
        s2 = _create_session(test_db_session, user.id, topic="S2")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?session_id={s1.id}")
            assert res.status_code == 200
            data = res.json()
            assert all(item["session_id"] == str(s1.id) for item in data["items"])

    def test_filter_by_event_types_single(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_et_single")
        s = _create_session(test_db_session, user.id, topic="ET Single")
        _create_message(test_db_session, s.id, sender="USER", content="Hello")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?event_types=session_created")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            assert data["items"][0]["event_type"] == "session_created"

    def test_filter_by_event_types_multiple(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_et_multi")
        s = _create_session(test_db_session, user.id, topic="ET Multi")
        _create_message(test_db_session, s.id, sender="USER", content="Hello")
        _create_session_report(test_db_session, s.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?event_types=session_created,report_generated")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 2
            types = {item["event_type"] for item in data["items"]}
            assert types == {"session_created", "report_generated"}

    def test_filter_by_event_types_invalid(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_et_inv")
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?event_types=invalid_event_type")
            assert res.status_code == 422

    def test_filter_by_start_and_end(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_dates")
        t0 = datetime(2024, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

        s = _create_session(test_db_session, user.id, topic="Dates", created_at=t0 - timedelta(days=2))
        _create_message(test_db_session, s.id, sender="USER", content="Target", created_at=t0)
        _create_message(test_db_session, s.id, sender="USER", content="Late", created_at=t0 + timedelta(days=2))

        start_str = (t0 - timedelta(hours=1)).isoformat()
        end_str = (t0 + timedelta(hours=1)).isoformat()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?start={start_str}&end={end_str}")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            assert data["items"][0]["metadata"]["content"] == "Target"

    def test_filter_by_invalid_start_returns_422(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_inv_start")
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?start=not-a-datetime")
            assert res.status_code == 422

    def test_combined_filters(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "flt_comb")
        t0 = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)

        s1 = _create_session(test_db_session, user.id, topic="S1", created_at=t0)
        s2 = _create_session(test_db_session, user.id, topic="S2", created_at=t0)

        _create_message(test_db_session, s1.id, sender="USER", content="S1 M1", created_at=t0 + timedelta(minutes=1))
        _create_message(test_db_session, s2.id, sender="USER", content="S2 M1", created_at=t0 + timedelta(minutes=1))

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(
                f"/api/v1/users/me/timeline?session_id={s1.id}&event_types=user_message&start={t0.isoformat()}"
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            assert data["items"][0]["session_id"] == str(s1.id)
            assert data["items"][0]["event_type"] == "user_message"


# ===================================================================
# 8. BACKWARD COMPATIBILITY TESTS
# ===================================================================

class TestTimelineBackwardCompatibility:
    """Old turns without TurnAssessment and turns with TurnAssessment."""

    def test_old_turns_without_turn_assessment_still_appear(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "bw_compat")
        s = _create_session(test_db_session, user.id, topic="Legacy Session")
        m = _create_message(test_db_session, s.id, sender="USER", content="Legacy message")
        _create_evaluation(test_db_session, m.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?session_id={s.id}")
            assert res.status_code == 200
            data = res.json()
            types = [item["event_type"] for item in data["items"]]
            assert "user_message" in types
            assert "evaluation" in types
            assert "turn_assessment" not in types

    def test_turns_with_turn_assessment_expose_only_presence_metadata(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "ta_presence")
        s = _create_session(test_db_session, user.id, topic="Assessed Session")
        m = _create_message(test_db_session, s.id, sender="USER", content="Assessed message")
        _create_turn_assessment(
            test_db_session,
            m.id,
            s.id,
            user.id,
            has_learning_assessment=True,
            has_turn_interpretation=False,
            has_learning_objective=True,
            has_question_specification=False,
        )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/users/me/timeline?session_id={s.id}&event_types=turn_assessment")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            meta = data["items"][0]["metadata"]
            assert meta == {
                "has_learning_assessment": True,
                "has_turn_interpretation": False,
                "has_learning_objective": True,
                "has_question_specification": False,
            }


# ===================================================================
# 9. AI BOUNDARY TESTS
# ===================================================================

class TestTimelineAIBoundary:
    """Verify timeline endpoint never invokes CurioEngine, Groq, or LangGraph."""

    def test_no_ai_provider_or_engine_calls(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "ai_boundary")
        s = _create_session(test_db_session, user.id, topic="AI Boundary Test")
        _create_message(test_db_session, s.id, sender="USER", content="Hello")

        with patch("backend.app.ai.engine.CurioEngine") as mock_engine, \
             patch("backend.app.services.chat_service.ChatService") as mock_chat:
            with TestClient(app) as client:
                client.headers["Authorization"] = f"Bearer {token}"
                res = client.get("/api/v1/users/me/timeline")
                assert res.status_code == 200

            mock_engine.assert_not_called()
            mock_chat.assert_not_called()


# ===================================================================
# 10. PERFORMANCE & BULK DATASET TESTS
# ===================================================================

class TestTimelinePerformance:
    """Query execution with a large dataset."""

    def test_large_event_dataset_paginated(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "bulk_user")
        t0 = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Create 3 sessions with 40 messages each -> 123 events total
        for s_idx in range(3):
            s = _create_session(test_db_session, user.id, topic=f"Bulk S{s_idx}", created_at=t0 + timedelta(days=s_idx))
            for m_idx in range(40):
                _create_message(
                    test_db_session,
                    s.id,
                    sender="USER",
                    content=f"Bulk message {s_idx}-{m_idx}",
                    created_at=t0 + timedelta(days=s_idx, minutes=m_idx + 1),
                )

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/users/me/timeline?page=1&page_size=25")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 123  # 3 sessions + 120 messages
            assert data["pages"] == 5
            assert len(data["items"]) == 25
