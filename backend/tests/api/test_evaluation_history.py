"""
Evaluation History API Tests — Phase 4, Task 4.2.

Tests for the paginated evaluation history endpoint:
GET /api/v1/sessions/{session_id}/evaluations

Safety & Isolation Guarantees:
- Strictly operates against TEST_DATABASE_URL (curio_test_db).
- Uses nested transaction savepoints so all writes roll back on teardown.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.session import Session, SessionState
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.models.turn_assessment import TurnAssessment
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


def _create_user_message_with_evaluation(db, session_id, content="Test answer", evaluation_data=None):
    """Helper: create a USER message with a turn evaluation."""
    msg = Message(
        session_id=session_id,
        sender="USER",
        content=content,
        input_type="TEXT",
    )
    db.add(msg)
    db.flush()

    if evaluation_data is None:
        evaluation_data = {
            "correctness": 0.8,
            "clarity": 0.7,
            "completeness": 0.75,
            "depth": 0.6,
            "relevance": 1.0,
            "stuck_probability": 0.1,
            "misconceptions": [],
            "missing_concepts": [],
            "undefined_terms": [],
            "mastered_concepts": ["test_concept"],
            "knowledge_gap": None,
            "recommended_strategy": "PROBE_WHY",
            "recommended_difficulty": 2,
        }

    eval_obj = TurnEvaluation(
        message_id=msg.id,
        **evaluation_data
    )
    db.add(eval_obj)
    db.commit()
    db.refresh(msg)
    return msg, eval_obj


def _create_turn_assessment(db, message_id, session_id, user_id, assessment_data=None):
    """Helper: create a turn assessment for a message."""
    if assessment_data is None:
        assessment_data = {
            "learning_assessment": {"intent": "ANSWER_ATTEMPT", "classification": "CORRECT"},
            "turn_interpretation": {"intent": "ANSWER_ATTEMPT", "is_answer_attempt": True},
            "learning_objective": {"objective_type": "UNDERSTAND_MECHANISM", "target_concept": "test"},
            "question_specification": {"target_concept": "test", "difficulty": 2},
        }

    assessment = TurnAssessment(
        message_id=message_id,
        session_id=session_id,
        user_id=user_id,
        **assessment_data
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===================================================================
# 1. UNAUTHENTICATED ACCESS — HTTP 401
# ===================================================================

class TestUnauthenticatedAccess:
    """Unauthenticated requests must return HTTP 401."""

    def test_get_evaluations_unauthenticated(self, raw_client, test_db_session):
        user, _ = _create_user_and_token(test_db_session, "unauth_user")
        session = _create_session_for_user(test_db_session, user.id)

        res = raw_client.get(f"/api/v1/sessions/{session.id}/evaluations")
        assert res.status_code == 401

    def test_get_evaluations_with_params_unauthenticated(self, raw_client, test_db_session):
        user, _ = _create_user_and_token(test_db_session, "unauth_user2")
        session = _create_session_for_user(test_db_session, user.id)

        res = raw_client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=10")
        assert res.status_code == 401


# ===================================================================
# 2. OWNER ACCESS — 200 OK
# ===================================================================

class TestOwnerAccess:
    """Authenticated owner can access their evaluation history."""

    def test_owner_gets_empty_history_for_new_session(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "owner_user1")
        session = _create_session_for_user(test_db_session, user.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["items"] == []
            assert data["total"] == 0
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert data["pages"] == 0

    def test_owner_gets_evaluations_without_assessments(self, test_db_session, override_get_db):
        """Old turns have TurnEvaluation but no TurnAssessment."""
        user, token = _create_user_and_token(test_db_session, "owner_user2")
        session = _create_session_for_user(test_db_session, user.id)

        base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Create messages with explicit timestamps
        msg1 = Message(
            session_id=session.id,
            sender="USER",
            content="Answer 1",
            input_type="TEXT",
            created_at=base_time,
        )
        test_db_session.add(msg1)
        test_db_session.flush()
        eval1 = TurnEvaluation(
            message_id=msg1.id,
            correctness=0.8, clarity=0.7, completeness=0.75, depth=0.6,
            relevance=1.0, stuck_probability=0.1,
            misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["test_concept"], knowledge_gap=None,
            recommended_strategy="PROBE_WHY", recommended_difficulty=2,
        )
        test_db_session.add(eval1)

        msg2 = Message(
            session_id=session.id,
            sender="USER",
            content="Answer 2",
            input_type="TEXT",
            created_at=base_time.replace(minute=1),
        )
        test_db_session.add(msg2)
        test_db_session.flush()
        eval2 = TurnEvaluation(
            message_id=msg2.id,
            correctness=0.8, clarity=0.7, completeness=0.75, depth=0.6,
            relevance=1.0, stuck_probability=0.1,
            misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=["test_concept"], knowledge_gap=None,
            recommended_strategy="PROBE_WHY", recommended_difficulty=2,
        )
        test_db_session.add(eval2)
        test_db_session.commit()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2

            # Check structure - first item should be "Answer 1" (earlier timestamp)
            item = data["items"][0]
            assert item["message"]["message_id"] == str(msg1.id)
            assert item["message"]["sender"] == "USER"
            assert item["message"]["content"] == "Answer 1"

            # Check evaluation fields
            assert item["evaluation"]["correctness"] == 0.8
            assert item["evaluation"]["recommended_strategy"] == "PROBE_WHY"

            # Second item should be "Answer 2"
            item2 = data["items"][1]
            assert item2["message"]["message_id"] == str(msg2.id)
            assert item2["message"]["content"] == "Answer 2"

    def test_owner_gets_evaluations_with_assessments(self, test_db_session, override_get_db):
        """New turns have both TurnEvaluation and TurnAssessment."""
        user, token = _create_user_and_token(test_db_session, "owner_user3")
        session = _create_session_for_user(test_db_session, user.id)

        msg1, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Answer with assessment")
        _create_turn_assessment(db=test_db_session, message_id=msg1.id, session_id=session.id, user_id=user.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1

            item = data["items"][0]
            assert item["assessment"] is not None
            assert item["assessment"]["message_id"] == str(msg1.id)
            assert item["assessment"]["learning_assessment"]["intent"] == "ANSWER_ATTEMPT"
            assert item["assessment"]["turn_interpretation"]["intent"] == "ANSWER_ATTEMPT"
            assert item["assessment"]["learning_objective"]["objective_type"] == "UNDERSTAND_MECHANISM"
            assert item["assessment"]["question_specification"]["target_concept"] == "test"

    def test_owner_gets_mixed_old_and_new_turns(self, test_db_session, override_get_db):
        """Session with both old (no assessment) and new (with assessment) turns."""
        user, token = _create_user_and_token(test_db_session, "owner_user4")
        session = _create_session_for_user(test_db_session, user.id)

        base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Old turn: evaluation only (earlier timestamp)
        msg1 = Message(
            session_id=session.id,
            sender="USER",
            content="Old answer",
            input_type="TEXT",
            created_at=base_time,
        )
        test_db_session.add(msg1)
        test_db_session.flush()
        eval1 = TurnEvaluation(
            message_id=msg1.id,
            correctness=0.8, clarity=0.7, completeness=0.75, depth=0.6,
            relevance=1.0, stuck_probability=0.1,
            misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=[], knowledge_gap=None,
            recommended_strategy="PROBE_WHY", recommended_difficulty=2,
        )
        test_db_session.add(eval1)

        # New turn: evaluation + assessment (later timestamp)
        msg2 = Message(
            session_id=session.id,
            sender="USER",
            content="New answer",
            input_type="TEXT",
            created_at=base_time.replace(minute=5),
        )
        test_db_session.add(msg2)
        test_db_session.flush()
        eval2 = TurnEvaluation(
            message_id=msg2.id,
            correctness=0.8, clarity=0.7, completeness=0.75, depth=0.6,
            relevance=1.0, stuck_probability=0.1,
            misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=[], knowledge_gap=None,
            recommended_strategy="PROBE_WHY", recommended_difficulty=2,
        )
        test_db_session.add(eval2)
        test_db_session.commit()

        _create_turn_assessment(test_db_session, msg2.id, session.id, user.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2

            # Items should be ordered chronologically (oldest first)
            assert data["items"][0]["message"]["content"] == "Old answer"
            assert data["items"][0]["assessment"] is None

            assert data["items"][1]["message"]["content"] == "New answer"
            assert data["items"][1]["assessment"] is not None


# ===================================================================
# 3. PAGINATION TESTS
# ===================================================================

class TestPagination:
    """Tests for pagination parameters and behavior."""

    def test_default_pagination(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user1")
        session = _create_session_for_user(test_db_session, user.id)

        for i in range(25):
            _create_user_message_with_evaluation(test_db_session, session.id, f"Answer {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert data["total"] == 25
            assert data["pages"] == 2
            assert len(data["items"]) == 20

    def test_page_2(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user2")
        session = _create_session_for_user(test_db_session, user.id)

        for i in range(25):
            _create_user_message_with_evaluation(test_db_session, session.id, f"Answer {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=2&page_size=20")
            assert res.status_code == 200

            data = res.json()
            assert data["page"] == 2
            assert data["page_size"] == 20
            assert data["total"] == 25
            assert data["pages"] == 2
            assert len(data["items"]) == 5

    def test_custom_page_size(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user3")
        session = _create_session_for_user(test_db_session, user.id)

        for i in range(15):
            _create_user_message_with_evaluation(test_db_session, session.id, f"Answer {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=5")
            assert res.status_code == 200

            data = res.json()
            assert data["page"] == 1
            assert data["page_size"] == 5
            assert data["total"] == 15
            assert data["pages"] == 3
            assert len(data["items"]) == 5

    def test_page_size_max_capped_at_100(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user4")
        session = _create_session_for_user(test_db_session, user.id)

        for i in range(150):
            _create_user_message_with_evaluation(test_db_session, session.id, f"Answer {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=200")
            assert res.status_code == 200

            data = res.json()
            assert data["page_size"] == 100  # capped
            assert len(data["items"]) == 100

    def test_page_size_min_enforced(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user5")
        session = _create_session_for_user(test_db_session, user.id)

        _create_user_message_with_evaluation(test_db_session, session.id, "Answer 1")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=0")
            assert res.status_code == 422

    def test_page_min_enforced(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user6")
        session = _create_session_for_user(test_db_session, user.id)

        _create_user_message_with_evaluation(test_db_session, session.id, "Answer 1")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=0&page_size=20")
            assert res.status_code == 422

    def test_page_beyond_last_returns_empty(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "page_user7")
        session = _create_session_for_user(test_db_session, user.id)

        for i in range(5):
            _create_user_message_with_evaluation(test_db_session, session.id, f"Answer {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=5&page_size=2")
            assert res.status_code == 200

            data = res.json()
            assert data["page"] == 5
            assert data["page_size"] == 2
            assert data["total"] == 5
            assert data["pages"] == 3
            assert data["items"] == []


# ===================================================================
# 4. ORDERING TESTS
# ===================================================================

class TestOrdering:
    """Tests for deterministic chronological ordering."""

    def test_chronological_ordering(self, test_db_session, override_get_db):
        """Evaluation history must be ordered chronologically (oldest first)."""
        user, token = _create_user_and_token(test_db_session, "order_user1")
        session = _create_session_for_user(test_db_session, user.id)

        base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Create messages with specific timestamps
        for i in range(5):
            msg = Message(
                session_id=session.id,
                sender="USER",
                content=f"Answer {i}",
                input_type="TEXT",
                created_at=base_time.replace(second=i * 10),
            )
            test_db_session.add(msg)
            test_db_session.flush()

            eval_obj = TurnEvaluation(
                message_id=msg.id,
                correctness=0.8,
                clarity=0.7,
                completeness=0.75,
                depth=0.6,
                relevance=1.0,
                stuck_probability=0.1,
                misconceptions=[],
                missing_concepts=[],
                undefined_terms=[],
                mastered_concepts=[],
                knowledge_gap=None,
                recommended_strategy="PROBE_WHY",
                recommended_difficulty=2,
            )
            test_db_session.add(eval_obj)

        test_db_session.commit()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=10")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 5
            contents = [item["message"]["content"] for item in data["items"]]
            assert contents == ["Answer 0", "Answer 1", "Answer 2", "Answer 3", "Answer 4"]

    def test_deterministic_ordering_with_same_timestamp(self, test_db_session, override_get_db):
        """When timestamps are identical, ordering by message.id ensures determinism."""
        user, token = _create_user_and_token(test_db_session, "order_user2")
        session = _create_session_for_user(test_db_session, user.id)

        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Create multiple messages with the same timestamp
        for i in range(3):
            msg = Message(
                session_id=session.id,
                sender="USER",
                content=f"Answer {i}",
                input_type="TEXT",
                created_at=fixed_time,
            )
            test_db_session.add(msg)
            test_db_session.flush()

            eval_obj = TurnEvaluation(
                message_id=msg.id,
                correctness=0.8,
                clarity=0.7,
                completeness=0.75,
                depth=0.6,
                relevance=1.0,
                stuck_probability=0.1,
                misconceptions=[],
                missing_concepts=[],
                undefined_terms=[],
                mastered_concepts=[],
                knowledge_gap=None,
                recommended_strategy="PROBE_WHY",
                recommended_difficulty=2,
            )
            test_db_session.add(eval_obj)

        test_db_session.commit()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            # Request multiple times to verify determinism
            all_results = []
            for _ in range(3):
                res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=10")
                assert res.status_code == 200
                data = res.json()
                ids = [item["message"]["message_id"] for item in data["items"]]
                all_results.append(ids)

            # All requests should return the same order (deterministic)
            assert all_results[0] == all_results[1] == all_results[2]
            # Should have all 3 items
            assert len(all_results[0]) == 3


# ===================================================================
# 5. CROSS-USER ISOLATION / IDOR TESTS
# ===================================================================

class TestCrossUserIsolation:
    """User A must never access User B's evaluation history."""

    def test_user_a_cannot_access_user_b_evaluations(self, test_db_session, override_get_db):
        user_a, token_a = _create_user_and_token(test_db_session, "cross_a")
        user_b, _ = _create_user_and_token(test_db_session, "cross_b")

        session_b = _create_session_for_user(test_db_session, user_b.id, "User B Session")
        _create_user_message_with_evaluation(test_db_session, session_b.id, "B's answer")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            res = client.get(f"/api/v1/sessions/{session_b.id}/evaluations")
            assert res.status_code == 404  # Anti-enumeration: 404 not 403

    def test_user_b_cannot_access_user_a_evaluations(self, test_db_session, override_get_db):
        user_a, _ = _create_user_and_token(test_db_session, "cross_c")
        user_b, token_b = _create_user_and_token(test_db_session, "cross_d")

        session_a = _create_session_for_user(test_db_session, user_a.id, "User A Session")
        _create_user_message_with_evaluation(test_db_session, session_a.id, "A's answer")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_b}"
            res = client.get(f"/api/v1/sessions/{session_a.id}/evaluations")
            assert res.status_code == 404

    def test_cross_user_with_assessments(self, test_db_session, override_get_db):
        """Cross-user access blocked even when assessments exist."""
        user_a, token_a = _create_user_and_token(test_db_session, "cross_e")
        user_b, _ = _create_user_and_token(test_db_session, "cross_f")

        session_b = _create_session_for_user(test_db_session, user_b.id, "User B Session")
        msg, _ = _create_user_message_with_evaluation(test_db_session, session_b.id, "B's answer")
        _create_turn_assessment(test_db_session, msg.id, session_b.id, user_b.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_a}"
            res = client.get(f"/api/v1/sessions/{session_b.id}/evaluations")
            assert res.status_code == 404

    def test_nonexistent_session_returns_404(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "nonexist_user")
        fake_session_id = uuid.uuid4()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{fake_session_id}/evaluations")
            assert res.status_code == 404


# ===================================================================
# 6. RESPONSE SCHEMA VALIDATION
# ===================================================================

class TestResponseSchema:
    """Tests for response schema structure."""

    def test_response_contains_required_fields(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "schema_user1")
        session = _create_session_for_user(test_db_session, user.id)
        _create_user_message_with_evaluation(test_db_session, session.id, "Test")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "pages" in data

    def test_item_structure_without_assessment(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "schema_user2")
        session = _create_session_for_user(test_db_session, user.id)
        msg, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Test")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            item = data["items"][0]

            # Message metadata
            assert item["message"]["message_id"] == str(msg.id)
            assert item["message"]["session_id"] == str(session.id)
            assert item["message"]["sender"] == "USER"
            assert item["message"]["content"] == "Test"
            assert "created_at" in item["message"]

            # Evaluation
            assert "correctness" in item["evaluation"]
            assert "clarity" in item["evaluation"]
            assert "completeness" in item["evaluation"]
            assert "depth" in item["evaluation"]
            assert "relevance" in item["evaluation"]
            assert "stuck_probability" in item["evaluation"]
            assert "misconceptions" in item["evaluation"]
            assert "missing_concepts" in item["evaluation"]
            assert "undefined_terms" in item["evaluation"]
            assert "mastered_concepts" in item["evaluation"]
            assert "knowledge_gap" in item["evaluation"]
            assert "recommended_strategy" in item["evaluation"]
            assert "recommended_difficulty" in item["evaluation"]

            # Assessment (should be None for old turns)
            assert item["assessment"] is None

    def test_item_structure_with_assessment(self, test_db_session, override_get_db):
        user, token = _create_user_and_token(test_db_session, "schema_user3")
        session = _create_session_for_user(test_db_session, user.id)
        msg, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Test")
        assessment = _create_turn_assessment(test_db_session, msg.id, session.id, user.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            item = data["items"][0]

            assert item["assessment"] is not None
            assert item["assessment"]["id"] == str(assessment.id)
            assert item["assessment"]["message_id"] == str(msg.id)
            assert item["assessment"]["session_id"] == str(session.id)
            assert item["assessment"]["user_id"] == str(user.id)
            assert "learning_assessment" in item["assessment"]
            assert "turn_interpretation" in item["assessment"]
            assert "learning_objective" in item["assessment"]
            assert "question_specification" in item["assessment"]
            assert "created_at" in item["assessment"]

    def test_assessment_nested_json_preserved(self, test_db_session, override_get_db):
        """Complex nested assessment JSON must be preserved as-is."""
        user, token = _create_user_and_token(test_db_session, "schema_user4")
        session = _create_session_for_user(test_db_session, user.id)
        msg, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Test")

        complex_assessment = {
            "learning_assessment": {
                "intent": "ANSWER_ATTEMPT",
                "claims": [
                    {"text": "Claim 1", "concept_id": "c1", "claim_type": "DEFINITION", "alignment_score": 0.8},
                    {"text": "Claim 2", "concept_id": "c2", "claim_type": "MECHANISM", "alignment_score": 0.7},
                ],
                "evidence": [
                    {"concept_id": "c1", "status": "SUPPORTED", "confidence": 0.9},
                    {"concept_id": "c2", "status": "PARTIALLY_SUPPORTED", "confidence": 0.6},
                ],
                "misconceptions": [{"concept_id": "c2", "severity": "MEDIUM"}],
                "metadata": {"custom_field": "custom_value", "nested": {"key": "value"}},
            },
            "turn_interpretation": {"intent": "ANSWER_ATTEMPT", "is_answer_attempt": True},
            "learning_objective": {"objective_type": "UNDERSTAND_MECHANISM"},
            "question_specification": {"target_concept": "test"},
        }

        _create_turn_assessment(test_db_session, msg.id, session.id, user.id, complex_assessment)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            item = data["items"][0]

            saved = item["assessment"]["learning_assessment"]
            assert len(saved["claims"]) == 2
            assert saved["claims"][0]["claim_type"] == "DEFINITION"
            assert saved["claims"][1]["claim_type"] == "MECHANISM"
            assert saved["evidence"][0]["status"] == "SUPPORTED"
            assert saved["evidence"][1]["status"] == "PARTIALLY_SUPPORTED"
            assert saved["misconceptions"][0]["severity"] == "MEDIUM"
            assert saved["metadata"]["custom_field"] == "custom_value"
            assert saved["metadata"]["nested"]["key"] == "value"


# ===================================================================
# 7. EDGE CASES
# ===================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_ai_messages_excluded_from_history(self, test_db_session, override_get_db):
        """Only USER messages with evaluations should appear in history."""
        user, token = _create_user_and_token(test_db_session, "edge_user1")
        session = _create_session_for_user(test_db_session, user.id)

        # USER message with evaluation (should appear)
        _create_user_message_with_evaluation(test_db_session, session.id, "User answer")

        # AI message (should NOT appear even if it somehow has evaluation)
        ai_msg = Message(
            session_id=session.id,
            sender="AI",
            content="AI response",
            input_type="TEXT",
        )
        test_db_session.add(ai_msg)
        test_db_session.flush()
        eval_obj = TurnEvaluation(
            message_id=ai_msg.id,
            correctness=0.8, clarity=0.7, completeness=0.75, depth=0.6,
            relevance=1.0, stuck_probability=0.1,
            misconceptions=[], missing_concepts=[], undefined_terms=[],
            mastered_concepts=[], knowledge_gap=None,
            recommended_strategy="PROBE_WHY", recommended_difficulty=2,
        )
        test_db_session.add(eval_obj)
        test_db_session.commit()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["message"]["sender"] == "USER"
            assert data["items"][0]["message"]["content"] == "User answer"

    def test_user_without_evaluation_excluded(self, test_db_session, override_get_db):
        """USER messages without evaluations should not appear."""
        user, token = _create_user_and_token(test_db_session, "edge_user2")
        session = _create_session_for_user(test_db_session, user.id)

        # USER message WITHOUT evaluation
        msg = Message(
            session_id=session.id,
            sender="USER",
            content="No evaluation",
            input_type="TEXT",
        )
        test_db_session.add(msg)

        # USER message WITH evaluation
        _create_user_message_with_evaluation(test_db_session, session.id, "Has evaluation")

        test_db_session.commit()

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 1
            assert data["items"][0]["message"]["content"] == "Has evaluation"

    def test_total_count_correct_despite_assessment_joins(self, test_db_session, override_get_db):
        """Total count must not be multiplied by assessment joins."""
        user, token = _create_user_and_token(test_db_session, "edge_user3")
        session = _create_session_for_user(test_db_session, user.id)

        # Create 3 messages with evaluations
        msg1, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Answer 1")
        msg2, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Answer 2")
        msg3, _ = _create_user_message_with_evaluation(test_db_session, session.id, "Answer 3")

        # Add assessment to only one
        _create_turn_assessment(test_db_session, msg1.id, session.id, user.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 200

            data = res.json()
            # Should be 3 evaluations, not 4 (no duplicate from assessment join)
            assert data["total"] == 3
            assert len(data["items"]) == 3

    def test_invalid_session_uuid_format(self, test_db_session, override_get_db):
        """Invalid UUID format should return 422."""
        user, token = _create_user_and_token(test_db_session, "edge_user4")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get("/api/v1/sessions/not-a-uuid/evaluations")
            assert res.status_code == 422

    def test_inactive_user_returns_400(self, test_db_session, override_get_db):
        """Inactive user should return 400 per existing project behavior."""
        user = User(email=f"inactive_{uuid.uuid4().hex[:8]}@curio.ai", is_active=False)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        token = create_access_token(subject=str(user.id))
        session = _create_session_for_user(test_db_session, user.id)

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
            assert res.status_code == 400
            assert "inactive" in res.json()["detail"].lower()


# ===================================================================
# 8. AI BOUNDARY TESTS
# ===================================================================

class TestAIBoundary:
    """Ensure no AI/provider calls are made during history retrieval."""

    def test_no_ai_calls_on_history_retrieval(self, test_db_session, override_get_db):
        """Evaluation history endpoint must not invoke AI engine."""
        user, token = _create_user_and_token(test_db_session, "ai_user1")
        session = _create_session_for_user(test_db_session, user.id)
        _create_user_message_with_evaluation(test_db_session, session.id, "Test answer")

        with patch("backend.app.ai.engine.CurioEngine.process") as mock_ai:
            with TestClient(app) as client:
                client.headers["Authorization"] = f"Bearer {token}"
                res = client.get(f"/api/v1/sessions/{session.id}/evaluations")
                assert res.status_code == 200
                mock_ai.assert_not_called()


# ===================================================================
# 9. DATABASE-LEVEL PAGINATION CONFIRMATION
# ===================================================================

class TestDatabaseLevelPagination:
    """Confirm database-level LIMIT/OFFSET is used."""

    def test_large_dataset_performance(self, test_db_session, override_get_db):
        """Large dataset should not load all records into memory."""
        user, token = _create_user_and_token(test_db_session, "perf_user1")
        session = _create_session_for_user(test_db_session, user.id)

        # Create 1000 evaluations
        for i in range(1000):
            _create_user_message_with_evaluation(test_db_session, session.id, f"Answer {i}")

        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token}"
            # Request first page only
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=1&page_size=10")
            assert res.status_code == 200

            data = res.json()
            assert data["total"] == 1000
            assert data["page"] == 1
            assert data["page_size"] == 10
            assert len(data["items"]) == 10

            # Request middle page
            res = client.get(f"/api/v1/sessions/{session.id}/evaluations?page=50&page_size=10")
            assert res.status_code == 200

            data = res.json()
            assert data["page"] == 50
            assert len(data["items"]) == 10