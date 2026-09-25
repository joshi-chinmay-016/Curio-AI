from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.concept_progress import UserConceptProgress


class ConceptProgressRepository:
    def get_by_user(self, db: SQLAlchemySession, user_id: UUID) -> List[UserConceptProgress]:
        """Retrieve all concept progress records for a user."""
        return (
            db.query(UserConceptProgress)
            .filter(UserConceptProgress.user_id == user_id)
            .order_by(UserConceptProgress.concept.asc())
            .all()
        )

    def get_by_user_and_concept(
        self, db: SQLAlchemySession, user_id: UUID, concept: str
    ) -> Optional[UserConceptProgress]:
        """Retrieve a specific concept progress record for a user."""
        return (
            db.query(UserConceptProgress)
            .filter(UserConceptProgress.user_id == user_id, UserConceptProgress.concept == concept)
            .first()
        )

    def upsert(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        concept: str,
        mastery_score: Optional[float] = None,
        total_attempts: Optional[int] = None,
        successful_attempts: Optional[int] = None,
        last_practiced_at: Optional[datetime] = None,
        last_difficulty: Optional[int] = None,
        misconception_count: Optional[int] = None,
    ) -> UserConceptProgress:
        """
        Create or update concept progress for a user.
        Only updates fields that are explicitly provided (not None).
        """
        from datetime import datetime, timezone
        progress = self.get_by_user_and_concept(db, user_id, concept)
        if not progress:
            progress = UserConceptProgress(
                user_id=user_id,
                concept=concept,
                mastery_score=mastery_score if mastery_score is not None else 0.0,
                total_attempts=total_attempts if total_attempts is not None else 0,
                successful_attempts=successful_attempts if successful_attempts is not None else 0,
                last_difficulty=last_difficulty if last_difficulty is not None else 1,
                misconception_count=misconception_count if misconception_count is not None else 0,
            )
            if last_practiced_at is not None:
                progress.last_practiced_at = last_practiced_at
            db.add(progress)
        else:
            if mastery_score is not None:
                progress.mastery_score = mastery_score
            if total_attempts is not None:
                progress.total_attempts = total_attempts
            if successful_attempts is not None:
                progress.successful_attempts = successful_attempts
            if last_practiced_at is not None:
                progress.last_practiced_at = last_practiced_at
            if last_difficulty is not None:
                progress.last_difficulty = last_difficulty
            if misconception_count is not None:
                progress.misconception_count = misconception_count

        db.commit()
        db.refresh(progress)
        return progress

    def delete(self, db: SQLAlchemySession, user_id: UUID, concept: str) -> bool:
        """Delete a concept progress record for a user."""
        progress = self.get_by_user_and_concept(db, user_id, concept)
        if progress:
            db.delete(progress)
            db.commit()
            return True
        return False

    def delete_by_user(self, db: SQLAlchemySession, user_id: UUID) -> int:
        """Delete all concept progress records for a user. Returns count deleted."""
        count = (
            db.query(UserConceptProgress)
            .filter(UserConceptProgress.user_id == user_id)
            .delete()
        )
        db.commit()
        return count