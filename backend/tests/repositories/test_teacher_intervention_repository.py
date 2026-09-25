"""
Integration tests for TeacherInterventionRepository (Phase 3, Task 3.6).
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from backend.app.models.teacher_intervention import TeacherInterventionLog
from backend.app.models.user import User
from backend.app.models.session import Session
from backend.app.repositories.teacher_intervention_repository import TeacherInterventionRepository


pytestmark = pytest.mark.db_integration


class TestTeacherInterventionRepository:
    """Test TeacherInterventionRepository CRUD operations and ownership."""

    def test_create_intervention(self, test_db_session):
        """
        1. Create intervention record.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"create_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Recursion", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        intervention = repo.create(
            test_db_session,
            session_id=session.id,
            user_id=user.id,
            gap="Understanding base cases in recursion",
            attempt_count=1,
            teacher_explanation="A base case stops infinite recursion...",
            verification_question="What happens without a base case?",
            verification_answer=None,
            verification_passed=None,
            intervention_type="enter",
        )

        assert intervention.session_id == session.id
        assert intervention.user_id == user.id
        assert intervention.gap == "Understanding base cases in recursion"
        assert intervention.attempt_count == 1
        assert intervention.teacher_explanation == "A base case stops infinite recursion..."
        assert intervention.verification_question == "What happens without a base case?"
        assert intervention.verification_answer is None
        assert intervention.verification_passed is None
        assert intervention.intervention_type == "enter"
        assert intervention.created_at is not None

    def test_get_by_session(self, test_db_session):
        """
        2. Retrieve interventions by session.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"get_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Binary Search", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        # Create multiple interventions
        repo.create(test_db_session, session.id, user.id, "Gap 1", attempt_count=1, intervention_type="enter")
        repo.create(test_db_session, session.id, user.id, "Gap 2", attempt_count=2, intervention_type="continue")
        repo.create(test_db_session, session.id, user.id, "Gap 3", attempt_count=3, intervention_type="exit")

        interventions = repo.get_by_session(test_db_session, session.id, user.id)

        assert len(interventions) == 3
        # Should be ordered chronologically
        assert interventions[0].gap == "Gap 1"
        assert interventions[1].gap == "Gap 2"
        assert interventions[2].gap == "Gap 3"

    def test_get_by_session_chronological_order(self, test_db_session):
        """
        3. Retrieve interventions in deterministic chronological order.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"chrono_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Chronological Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        # Create with explicit timestamps
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(minutes=10)
        later = now + timedelta(minutes=10)

        i1 = TeacherInterventionLog(
            session_id=session.id, user_id=user.id, gap="First", attempt_count=1,
            created_at=earlier
        )
        i2 = TeacherInterventionLog(
            session_id=session.id, user_id=user.id, gap="Second", attempt_count=2,
            created_at=now
        )
        i3 = TeacherInterventionLog(
            session_id=session.id, user_id=user.id, gap="Third", attempt_count=3,
            created_at=later
        )
        test_db_session.add_all([i1, i2, i3])
        test_db_session.commit()

        interventions = repo.get_by_session(test_db_session, session.id, user.id)

        assert len(interventions) == 3
        assert interventions[0].gap == "First"
        assert interventions[1].gap == "Second"
        assert interventions[2].gap == "Third"

    def test_get_by_user(self, test_db_session):
        """
        4. Retrieve interventions by user.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"list_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session1 = Session(user_id=user.id, topic="Session 1", source_type="GENERAL", status="ACTIVE")
        session2 = Session(user_id=user.id, topic="Session 2", source_type="GENERAL", status="ACTIVE")
        test_db_session.add_all([session1, session2])
        test_db_session.commit()
        test_db_session.refresh(session1)
        test_db_session.refresh(session2)

        repo.create(test_db_session, session1.id, user.id, "Gap A", attempt_count=1)
        repo.create(test_db_session, session1.id, user.id, "Gap B", attempt_count=2)
        repo.create(test_db_session, session2.id, user.id, "Gap C", attempt_count=1)

        interventions = repo.get_by_user(test_db_session, user.id)

        assert len(interventions) == 3
        concepts = {i.gap for i in interventions}
        assert concepts == {"Gap A", "Gap B", "Gap C"}

    def test_get_by_id(self, test_db_session):
        """
        5. Optional get-by-ID is user scoped.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"id_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="ID Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        created = repo.create(test_db_session, session.id, user.id, "Gap X", attempt_count=1)

        # Retrieve by ID with correct user
        found = repo.get_by_id(test_db_session, created.id, user.id)
        assert found is not None
        assert found.id == created.id
        assert found.gap == "Gap X"

        # Retrieve by ID with wrong user
        other_user = User(email=f"other_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(other_user)
        test_db_session.commit()
        test_db_session.refresh(other_user)

        not_found = repo.get_by_id(test_db_session, created.id, other_user.id)
        assert not_found is None

    def test_user_isolation(self, test_db_session):
        """
        5. User isolation: User A cannot retrieve User B's intervention records.
        """
        repo = TeacherInterventionRepository()

        user_a = User(email=f"iso_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"iso_b_{uuid.uuid4().hex[:8]}@curio.ai")
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

        repo.create(test_db_session, session_a.id, user_a.id, "A's Gap", attempt_count=1)
        repo.create(test_db_session, session_b.id, user_b.id, "B's Gap", attempt_count=1)

        # User A's session interventions
        a_interventions = repo.get_by_session(test_db_session, session_a.id, user_a.id)
        assert len(a_interventions) == 1
        assert a_interventions[0].gap == "A's Gap"

        # User B's session interventions
        b_interventions = repo.get_by_session(test_db_session, session_b.id, user_b.id)
        assert len(b_interventions) == 1
        assert b_interventions[0].gap == "B's Gap"

        # Cross-user access: User A tries to access User B's session
        cross = repo.get_by_session(test_db_session, session_b.id, user_a.id)
        assert len(cross) == 0

    def test_same_session_other_user_cannot_access(self, test_db_session):
        """
        6. Same session belonging to another user cannot be accessed.
        """
        repo = TeacherInterventionRepository()

        user_a = User(email=f"access_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"access_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        session = Session(user_id=user_a.id, topic="Shared Session", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        repo.create(test_db_session, session.id, user_a.id, "Owner's Gap", attempt_count=1)

        # User B tries to access User A's session
        b_interventions = repo.get_by_session(test_db_session, session.id, user_b.id)
        assert len(b_interventions) == 0

    def test_foreign_key_session_relationship(self, test_db_session):
        """
        8. Foreign-key/session relationship works.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"fk_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="FK Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        intervention = repo.create(test_db_session, session.id, user.id, "FK Gap", attempt_count=1)

        # Verify relationship loads correctly
        test_db_session.refresh(intervention)
        assert intervention.session is not None
        assert intervention.session.id == session.id
        assert intervention.session.topic == "FK Test"

    def test_cascade_delete_session(self, test_db_session):
        """
        9. Cascade delete behavior works where supported by the existing DB setup.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"cascade_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Cascade Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        repo.create(test_db_session, session.id, user.id, "Gap 1", attempt_count=1)
        repo.create(test_db_session, session.id, user.id, "Gap 2", attempt_count=2)

        # Delete session
        test_db_session.delete(session)
        test_db_session.commit()

        # Interventions should be cascade deleted
        interventions = repo.get_by_session(test_db_session, session.id, user.id)
        assert len(interventions) == 0

    def test_multiple_interventions_same_session(self, test_db_session):
        """
        10. Multiple interventions can exist for the same session.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"multi_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Multi Intervention", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        repo.create(test_db_session, session.id, user.id, "Gap 1", attempt_count=1, intervention_type="enter")
        repo.create(test_db_session, session.id, user.id, "Gap 1", attempt_count=2, intervention_type="continue")
        repo.create(test_db_session, session.id, user.id, "Gap 2", attempt_count=1, intervention_type="enter")

        interventions = repo.get_by_session(test_db_session, session.id, user.id)

        assert len(interventions) == 3
        gap_1_count = sum(1 for i in interventions if i.gap == "Gap 1")
        gap_2_count = sum(1 for i in interventions if i.gap == "Gap 2")
        assert gap_1_count == 2
        assert gap_2_count == 1

    def test_timestamps_persist_correctly(self, test_db_session):
        """
        11. Timestamps persist correctly.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"time_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Time Test", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        before = datetime.now(timezone.utc) - timedelta(seconds=1)
        intervention = repo.create(test_db_session, session.id, user.id, "Timed Gap", attempt_count=1)
        after = datetime.now(timezone.utc) + timedelta(seconds=1)

        assert intervention.created_at is not None
        assert before <= intervention.created_at <= after

    def test_persistence_round_trip(self, test_db_session):
        """
        12. Round-trip persistence through PostgreSQL.
        """
        repo = TeacherInterventionRepository()
        user = User(email=f"roundtrip_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        session = Session(user_id=user.id, topic="Roundtrip", source_type="GENERAL", status="ACTIVE")
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)

        created = repo.create(
            test_db_session,
            session_id=session.id,
            user_id=user.id,
            gap="Roundtrip Gap",
            attempt_count=3,
            teacher_explanation="Explanation text",
            verification_question="Verify?",
            verification_answer="Answer",
            verification_passed=True,
            intervention_type="exit",
        )

        # Refresh from DB
        test_db_session.expire_all()
        refreshed = repo.get_by_id(test_db_session, created.id, user.id)

        assert refreshed is not None
        assert refreshed.id == created.id
        assert refreshed.session_id == session.id
        assert refreshed.user_id == user.id
        assert refreshed.gap == "Roundtrip Gap"
        assert refreshed.attempt_count == 3
        assert refreshed.teacher_explanation == "Explanation text"
        assert refreshed.verification_question == "Verify?"
        assert refreshed.verification_answer == "Answer"
        assert refreshed.verification_passed == 1
        assert refreshed.intervention_type == "exit"