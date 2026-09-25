"""
Unit and integration tests for ConceptProgressRepository.
"""
import uuid
import pytest
from backend.app.models.concept_progress import UserConceptProgress
from backend.app.models.user import User
from backend.app.repositories.concept_progress_repository import ConceptProgressRepository


pytestmark = pytest.mark.db_integration


class TestConceptProgressRepository:
    """Test concept progress repository CRUD operations."""

    def test_create_progress(self, test_db_session):
        """Test creating concept progress for a user."""
        repo = ConceptProgressRepository()
        user = User(email=f"create_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        progress = repo.upsert(
            test_db_session,
            user_id=user.id,
            concept="photosynthesis",
            mastery_score=0.75,
            total_attempts=10,
            successful_attempts=8,
            last_difficulty=2,
            misconception_count=1,
        )

        assert progress.user_id == user.id
        assert progress.concept == "photosynthesis"
        assert progress.mastery_score == 0.75
        assert progress.total_attempts == 10
        assert progress.successful_attempts == 8
        assert progress.last_difficulty == 2
        assert progress.misconception_count == 1
        # last_practiced_at is only set when explicitly provided
        assert progress.last_practiced_at is None

    def test_get_by_user_and_concept(self, test_db_session):
        """Test retrieving specific concept progress for a user."""
        repo = ConceptProgressRepository()
        user = User(email=f"get_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "cellular_respiration", mastery_score=0.8)

        progress = repo.get_by_user_and_concept(test_db_session, user.id, "cellular_respiration")
        assert progress is not None
        assert progress.concept == "cellular_respiration"
        assert progress.mastery_score == 0.8

        # Non-existent concept
        progress_none = repo.get_by_user_and_concept(test_db_session, user.id, "nonexistent")
        assert progress_none is None

    def test_get_by_user(self, test_db_session):
        """Test retrieving all concept progress for a user."""
        repo = ConceptProgressRepository()
        user = User(email=f"list_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "concept_a", mastery_score=0.5)
        repo.upsert(test_db_session, user.id, "concept_b", mastery_score=0.7)
        repo.upsert(test_db_session, user.id, "concept_c", mastery_score=0.9)

        progress_list = repo.get_by_user(test_db_session, user.id)
        assert len(progress_list) == 3
        concepts = [p.concept for p in progress_list]
        assert "concept_a" in concepts
        assert "concept_b" in concepts
        assert "concept_c" in concepts
        # Should be ordered by concept name
        assert progress_list[0].concept == "concept_a"
        assert progress_list[1].concept == "concept_b"
        assert progress_list[2].concept == "concept_c"

    def test_update_existing_progress(self, test_db_session):
        """Test updating existing concept progress."""
        repo = ConceptProgressRepository()
        user = User(email=f"update_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        # Initial create
        repo.upsert(test_db_session, user.id, "genetics", mastery_score=0.6, total_attempts=5)

        # Update with new values
        progress = repo.upsert(
            test_db_session,
            user.id,
            "genetics",
            mastery_score=0.85,
            total_attempts=10,
            successful_attempts=9,
            last_difficulty=3,
            misconception_count=0,
        )

        assert progress.mastery_score == 0.85
        assert progress.total_attempts == 10
        assert progress.successful_attempts == 9
        assert progress.last_difficulty == 3
        assert progress.misconception_count == 0

    def test_partial_update_preserves_fields(self, test_db_session):
        """Test that partial update preserves unspecified fields."""
        repo = ConceptProgressRepository()
        user = User(email=f"partial_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(
            test_db_session,
            user.id,
            "quantum_mechanics",
            mastery_score=0.7,
            total_attempts=10,
            successful_attempts=7,
            last_difficulty=2,
            misconception_count=2,
        )

        # Only update mastery_score
        progress = repo.upsert(test_db_session, user.id, "quantum_mechanics", mastery_score=0.9)

        assert progress.mastery_score == 0.9
        # Other fields should be preserved
        assert progress.total_attempts == 10
        assert progress.successful_attempts == 7
        assert progress.last_difficulty == 2
        assert progress.misconception_count == 2

    def test_delete_progress(self, test_db_session):
        """Test deleting concept progress."""
        repo = ConceptProgressRepository()
        user = User(email=f"delete_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "thermodynamics", mastery_score=0.5)
        deleted = repo.delete(test_db_session, user.id, "thermodynamics")
        assert deleted is True

        progress = repo.get_by_user_and_concept(test_db_session, user.id, "thermodynamics")
        assert progress is None

        # Delete non-existent
        deleted_false = repo.delete(test_db_session, user.id, "nonexistent")
        assert deleted_false is False

    def test_delete_by_user(self, test_db_session):
        """Test deleting all progress for a user."""
        repo = ConceptProgressRepository()
        user = User(email=f"delete_all_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "concept_1", mastery_score=0.5)
        repo.upsert(test_db_session, user.id, "concept_2", mastery_score=0.6)
        repo.upsert(test_db_session, user.id, "concept_3", mastery_score=0.7)

        count = repo.delete_by_user(test_db_session, user.id)
        assert count == 3

        progress_list = repo.get_by_user(test_db_session, user.id)
        assert len(progress_list) == 0

    def test_default_values(self, test_db_session):
        """Test default values for new progress records."""
        repo = ConceptProgressRepository()
        user = User(email=f"default_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        progress = repo.upsert(test_db_session, user.id, "new_concept")

        assert progress.mastery_score == 0.0
        assert progress.total_attempts == 0
        assert progress.successful_attempts == 0
        assert progress.last_difficulty == 1
        assert progress.misconception_count == 0
        assert progress.last_practiced_at is None

    def test_user_isolation(self, test_db_session):
        """Test that users cannot access each other's concept progress."""
        repo = ConceptProgressRepository()

        user_a = User(email=f"iso_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"iso_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        repo.upsert(test_db_session, user_a.id, "shared_concept", mastery_score=0.8)
        repo.upsert(test_db_session, user_b.id, "shared_concept", mastery_score=0.5)

        # User A can only see their progress
        progress_a = repo.get_by_user_and_concept(test_db_session, user_a.id, "shared_concept")
        assert progress_a.mastery_score == 0.8

        # User B can only see their progress
        progress_b = repo.get_by_user_and_concept(test_db_session, user_b.id, "shared_concept")
        assert progress_b.mastery_score == 0.5

        # User A's list doesn't contain User B's progress
        list_a = repo.get_by_user(test_db_session, user_a.id)
        assert len(list_a) == 1
        assert list_a[0].concept == "shared_concept"
        assert list_a[0].mastery_score == 0.8

    def test_cascade_delete_user(self, test_db_session):
        """Test that deleting a user cascades to concept progress."""
        repo = ConceptProgressRepository()
        user = User(email=f"cascade_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "concept_x", mastery_score=0.5)
        repo.upsert(test_db_session, user.id, "concept_y", mastery_score=0.7)

        # Delete the user
        test_db_session.delete(user)
        test_db_session.commit()

        # Concept progress should be deleted due to cascade
        progress_list = repo.get_by_user(test_db_session, user.id)
        assert len(progress_list) == 0

    def test_upsert_with_last_practiced_at(self, test_db_session):
        """Test upsert with last_practiced_at timestamp."""
        from datetime import datetime, timezone
        repo = ConceptProgressRepository()
        user = User(email=f"time_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        now = datetime.now(timezone.utc)
        progress = repo.upsert(
            test_db_session,
            user.id,
            "timed_concept",
            last_practiced_at=now,
        )

        assert progress.last_practiced_at is not None
        # Compare within a few seconds
        diff = abs((progress.last_practiced_at - now).total_seconds())
        assert diff < 5

    def test_unique_constraint_user_concept(self, test_db_session):
        """Test that (user_id, concept) pair is unique."""
        repo = ConceptProgressRepository()
        user = User(email=f"unique_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "unique_concept", mastery_score=0.5)

        # Second upsert with same user and concept should update, not create duplicate
        progress = repo.upsert(test_db_session, user.id, "unique_concept", mastery_score=0.9)

        # Should be same record, updated
        assert progress.mastery_score == 0.9

        # Verify only one record exists
        all_progress = repo.get_by_user(test_db_session, user.id)
        assert len(all_progress) == 1

    def test_persistence_round_trip(self, test_db_session):
        """Test that progress persists correctly after commit."""
        repo = ConceptProgressRepository()
        user = User(email=f"persist_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        # Create progress
        progress = repo.upsert(
            test_db_session,
            user.id,
            "persistent_concept",
            mastery_score=0.88,
            total_attempts=20,
            successful_attempts=18,
            last_difficulty=4,
            misconception_count=1,
        )
        concept = progress.concept
        user_id = progress.user_id
        mastery = progress.mastery_score

        # Refresh from DB
        test_db_session.expire_all()
        refreshed = repo.get_by_user_and_concept(test_db_session, user_id, concept)

        assert refreshed is not None
        assert refreshed.user_id == user_id
        assert refreshed.concept == concept
        assert refreshed.mastery_score == mastery
        assert refreshed.total_attempts == 20
        assert refreshed.successful_attempts == 18
        assert refreshed.last_difficulty == 4
        assert refreshed.misconception_count == 1