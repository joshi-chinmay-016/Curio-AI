from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.concept_progress_repository import ConceptProgressRepository
from backend.app.schemas.learning_progress import (
    ConceptProgressResponse,
    LearningProgressResponse,
    LearningProgressSummary,
)


class LearningProgressService:
    def __init__(self, repo: Optional[ConceptProgressRepository] = None):
        self.repo = repo or ConceptProgressRepository()

    def get_user_progress(
        self, db: SQLAlchemySession, user_id: UUID
    ) -> LearningProgressResponse:
        """
        Retrieve all concept progress for a user with summary aggregation.
        """
        concepts = self.repo.get_by_user(db, user_id)

        concept_responses = [
            ConceptProgressResponse(
                concept=c.concept,
                mastery_score=c.mastery_score,
                total_attempts=c.total_attempts,
                successful_attempts=c.successful_attempts,
                last_practiced_at=c.last_practiced_at,
                last_difficulty=c.last_difficulty,
                misconception_count=c.misconception_count,
            )
            for c in concepts
        ]

        # Factual summary aggregation (no AI logic)
        total_concepts = len(concepts)
        concepts_with_progress = sum(1 for c in concepts if c.mastery_score > 0.0)
        total_attempts = sum(c.total_attempts for c in concepts)
        total_successful = sum(c.successful_attempts for c in concepts)
        total_misconceptions = sum(c.misconception_count for c in concepts)

        # Most recently practiced
        practiced = [c for c in concepts if c.last_practiced_at is not None]
        most_recent = (
            max(practiced, key=lambda c: c.last_practiced_at) if practiced else None
        )

        summary = LearningProgressSummary(
            total_concepts_tracked=total_concepts,
            concepts_with_progress=concepts_with_progress,
            total_attempts=total_attempts,
            total_successful_attempts=total_successful,
            total_misconceptions=total_misconceptions,
            most_recently_practiced_concept=most_recent.concept if most_recent else None,
            last_practiced_at=most_recent.last_practiced_at if most_recent else None,
        )

        return LearningProgressResponse(
            user_id=user_id,
            concepts=concept_responses,
            summary=summary,
        )

    def get_concept_progress(
        self, db: SQLAlchemySession, user_id: UUID, concept: str
    ) -> Optional[ConceptProgressResponse]:
        """
        Retrieve a single concept's progress for a user.
        """
        progress = self.repo.get_by_user_and_concept(db, user_id, concept)
        if not progress:
            return None

        return ConceptProgressResponse(
            concept=progress.concept,
            mastery_score=progress.mastery_score,
            total_attempts=progress.total_attempts,
            successful_attempts=progress.successful_attempts,
            last_practiced_at=progress.last_practiced_at,
            last_difficulty=progress.last_difficulty,
            misconception_count=progress.misconception_count,
        )

    def get_progress_for_concepts(
        self, db: SQLAlchemySession, user_id: UUID, concepts: List[str]
    ) -> List[ConceptProgressResponse]:
        """
        Retrieve progress for specific concepts for a user.
        Returns only concepts that have progress records.
        """
        results = []
        for concept in concepts:
            progress = self.get_concept_progress(db, user_id, concept)
            if progress:
                results.append(progress)
        return results