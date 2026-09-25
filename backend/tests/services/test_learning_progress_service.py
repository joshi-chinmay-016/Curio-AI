"""
Tests for LearningProgressService (Phase 3 Task 3.4).
"""
import uuid
import pytest
from backend.app.models.concept_progress import UserConceptProgress
from backend.app.models.user import User
from backend.app.repositories.concept_progress_repository import ConceptProgressRepository
from backend.app.services.learning_progress_service import LearningProgressService


pytestmark = pytest.mark.db_integration


class TestLearningProgressService:
    """Test LearningProgressService aggregation and retrieval."""

    def test_get_user_progress_returns_all_progress(self, test_db_session):
        """
        A. get_user_progress returns all progress for the authenticated user.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"progress_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        # Add multiple concept progress records
        repo.upsert(test_db_session, user.id, "recursion", mastery_score=0.8, total_attempts=10, successful_attempts=8, last_difficulty=2, misconception_count=1)
        repo.upsert(test_db_session, user.id, "binary_search", mastery_score=0.6, total_attempts=5, successful_attempts=3, last_difficulty=1, misconception_count=0)
        repo.upsert(test_db_session, user.id, "dynamic_programming", mastery_score=0.0, total_attempts=0, successful_attempts=0, last_difficulty=1, misconception_count=0)

        result = service.get_user_progress(test_db_session, user.id)

        assert result.user_id == user.id
        assert len(result.concepts) == 3
        concept_names = {c.concept for c in result.concepts}
        assert concept_names == {"recursion", "binary_search", "dynamic_programming"}

        # Verify summary
        assert result.summary.total_concepts_tracked == 3
        assert result.summary.concepts_with_progress == 2  # recursion and binary_search > 0
        assert result.summary.total_attempts == 15
        assert result.summary.total_successful_attempts == 11
        assert result.summary.total_misconceptions == 1

    def test_get_concept_progress_returns_requested_concept(self, test_db_session):
        """
        B. get_concept_progress returns the requested user's concept.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"concept_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "recursion", mastery_score=0.75, total_attempts=20, successful_attempts=18, last_difficulty=3, misconception_count=2)

        result = service.get_concept_progress(test_db_session, user.id, "recursion")

        assert result is not None
        assert result.concept == "recursion"
        assert result.mastery_score == 0.75
        assert result.total_attempts == 20
        assert result.successful_attempts == 18
        assert result.last_difficulty == 3
        assert result.misconception_count == 2

    def test_get_concept_progress_nonexistent_returns_none(self, test_db_session):
        """
        D. Missing concept behavior follows project conventions.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"nonexistent_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        result = service.get_concept_progress(test_db_session, user.id, "nonexistent_concept")

        assert result is None

    def test_user_isolation_user_a_cannot_retrieve_user_b_progress(self, test_db_session):
        """
        C. User A cannot retrieve User B's progress.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user_a = User(email=f"iso_a_{uuid.uuid4().hex[:8]}@curio.ai")
        user_b = User(email=f"iso_b_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add_all([user_a, user_b])
        test_db_session.commit()
        test_db_session.refresh(user_a)
        test_db_session.refresh(user_b)

        repo.upsert(test_db_session, user_a.id, "recursion", mastery_score=0.9)
        repo.upsert(test_db_session, user_b.id, "recursion", mastery_score=0.3)

        # User A's request
        result_a = service.get_user_progress(test_db_session, user_a.id)
        assert len(result_a.concepts) == 1
        assert result_a.concepts[0].mastery_score == 0.9

        # User B's request
        result_b = service.get_user_progress(test_db_session, user_b.id)
        assert len(result_b.concepts) == 1
        assert result_b.concepts[0].mastery_score == 0.3

        # Cross-user concept lookup
        result_cross = service.get_concept_progress(test_db_session, user_a.id, "recursion")
        assert result_cross.mastery_score == 0.9

        result_cross_b = service.get_concept_progress(test_db_session, user_b.id, "recursion")
        assert result_cross_b.mastery_score == 0.3

    def test_get_progress_for_multiple_concepts(self, test_db_session):
        """
        F. Multiple concepts are handled correctly.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"multi_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "concept_a", mastery_score=0.5)
        repo.upsert(test_db_session, user.id, "concept_b", mastery_score=0.7)
        repo.upsert(test_db_session, user.id, "concept_c", mastery_score=0.9)

        results = service.get_progress_for_concepts(test_db_session, user.id, ["concept_a", "concept_c", "nonexistent"])

        assert len(results) == 2
        assert results[0].concept == "concept_a"
        assert results[1].concept == "concept_c"

    def test_summary_aggregates_factual_counters(self, test_db_session):
        """
        E. Summary correctly reflects persisted factual counters.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"summary_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        repo.upsert(test_db_session, user.id, "concept_1", mastery_score=0.8, total_attempts=10, successful_attempts=8, misconception_count=1)
        repo.upsert(test_db_session, user.id, "concept_2", mastery_score=0.6, total_attempts=5, successful_attempts=3, misconception_count=2)
        repo.upsert(test_db_session, user.id, "concept_3", mastery_score=0.0, total_attempts=0, successful_attempts=0, misconception_count=0)

        result = service.get_user_progress(test_db_session, user.id)

        assert result.summary.total_concepts_tracked == 3
        assert result.summary.concepts_with_progress == 2
        assert result.summary.total_attempts == 15
        assert result.summary.total_successful_attempts == 11
        assert result.summary.total_misconceptions == 3

    def test_most_recently_practiced_concept(self, test_db_session):
        """
        Summary includes most recently practiced concept from timestamp.
        """
        from datetime import datetime, timezone, timedelta
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"recent_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        repo.upsert(test_db_session, user.id, "older_concept", mastery_score=0.5, last_practiced_at=earlier)
        repo.upsert(test_db_session, user.id, "newer_concept", mastery_score=0.7, last_practiced_at=now)
        repo.upsert(test_db_session, user.id, "never_practiced", mastery_score=0.6)

        result = service.get_user_progress(test_db_session, user.id)

        assert result.summary.most_recently_practiced_concept == "newer_concept"
        assert result.summary.last_practiced_at is not None

    def test_no_mock_user_id_used(self, test_db_session):
        """
        I. No MOCK_USER_ID is introduced.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        # Verify no reference to MOCK_USER_ID in service code
        import inspect
        source = inspect.getsource(LearningProgressService)
        assert "MOCK_USER_ID" not in source
        assert "00000000-0000-0000-0000-000000000000" not in source

    def test_no_ai_logic_in_service(self, test_db_session):
        """
        H. No AI logic is executed by LearningProgressService.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        import inspect
        source = inspect.getsource(LearningProgressService)

        # Verify no AI imports or calls
        assert "CurioEngine" not in source
        assert "CurioEngine" not in source
        assert "ai_engine" not in source
        assert "process(" not in source
        assert "DecisionEngine" not in source
        assert "ScoringEngine" not in source
        assert "GapAnalyzer" not in source
        assert "Groq" not in source
        assert "mock_provider" not in source
        assert "groq" not in source.lower()

    def test_cross_session_aggregation(self, test_db_session):
        """
        G. Multiple sessions/concept records are represented through the user-scoped
        UserConceptProgress model.
        """
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"cross_session_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        # Simulate progress from Session A
        repo.upsert(test_db_session, user.id, "recursion", mastery_score=0.5, total_attempts=5, successful_attempts=3)

        # Simulate progress from Session B (update same concept)
        repo.upsert(test_db_session, user.id, "recursion", mastery_score=0.8, total_attempts=15, successful_attempts=12, misconception_count=1)

        # Verify single user-scoped record aggregates both sessions
        result = service.get_user_progress(test_db_session, user.id)
        assert len(result.concepts) == 1
        assert result.concepts[0].concept == "recursion"
        assert result.concepts[0].mastery_score == 0.8  # Latest AI-provided value
        assert result.concepts[0].total_attempts == 15  # Latest AI-provided value
        assert result.concepts[0].successful_attempts == 12
        assert result.concepts[0].misconception_count == 1

    def test_empty_progress_returns_empty_response(self, test_db_session):
        """Test that user with no progress returns empty but valid response."""
        repo = ConceptProgressRepository()
        service = LearningProgressService(repo=repo)

        user = User(email=f"empty_user_{uuid.uuid4().hex[:8]}@curio.ai")
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        result = service.get_user_progress(test_db_session, user.id)

        assert result.user_id == user.id
        assert len(result.concepts) == 0
        assert result.summary.total_concepts_tracked == 0
        assert result.summary.concepts_with_progress == 0
        assert result.summary.total_attempts == 0
        assert result.summary.total_successful_attempts == 0
        assert result.summary.total_misconceptions == 0
        assert result.summary.most_recently_practiced_concept is None
        assert result.summary.last_practiced_at is None