from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionSummaryResponse,
    SessionListResponse,
)
from backend.app.schemas.common import LearningMode, SessionStatus


class SessionService:
    def __init__(self, repo: Optional[SessionRepository] = None):
        self.repo = repo or SessionRepository()

    def create_session(
        self,
        db: SQLAlchemySession,
        session_in: SessionCreate,
        user_id: UUID,
    ) -> SessionResponse:
        """Create a new session associated with the authenticated user."""
        db_session = self.repo.create(db, user_id=user_id, obj_in=session_in)
        return SessionResponse.model_validate(db_session)

    def get_session(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
    ) -> Optional[SessionResponse]:
        """Retrieve a session ensuring ownership by the authenticated user."""
        db_session = self.repo.get_by_id_and_user(db, session_id, user_id)
        if not db_session:
            return None
        return SessionResponse.model_validate(db_session)

    def list_sessions(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
    ) -> List[SessionSummaryResponse]:
        """List all sessions belonging strictly to the authenticated user (legacy, no pagination)."""
        db_sessions = self.repo.list_by_user(db, user_id)
        summaries = []
        for s in db_sessions:
            mode = LearningMode.STUDENT
            difficulty = 1
            confidence = 0.0
            if s.state:
                mode = LearningMode(s.state.current_mode)
                difficulty = s.state.difficulty
                confidence = s.state.confidence

            summaries.append(SessionSummaryResponse(
                session_id=s.id,
                topic=s.topic,
                status=SessionStatus(s.status),
                current_mode=mode,
                difficulty=difficulty,
                confidence=confidence,
                created_at=s.created_at,
                last_active_at=s.last_active_at
            ))
        return summaries

    def list_sessions_paginated(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[SessionStatus] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> SessionListResponse:
        """
        List sessions for a user with pagination and optional filters.

        Args:
            db: Database session.
            user_id: Owner user ID (always enforced).
            page: Page number (1-indexed).
            page_size: Items per page (capped at 100).
            status: Optional session status filter.
            created_after: Optional filter for sessions created at or after this timestamp.
            created_before: Optional filter for sessions created at or before this timestamp.

        Returns:
            SessionListResponse with items and pagination metadata.
        """
        # Cap page_size at 100
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        items, total = self.repo.list_by_user_paginated(
            db=db,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
            created_after=created_after,
            created_before=created_before,
        )

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        summaries = []
        for s in items:
            mode = LearningMode.STUDENT
            difficulty = 1
            confidence = 0.0
            if s.state:
                mode = LearningMode(s.state.current_mode)
                difficulty = s.state.difficulty
                confidence = s.state.confidence

            summaries.append(SessionSummaryResponse(
                session_id=s.id,
                topic=s.topic,
                status=SessionStatus(s.status),
                current_mode=mode,
                difficulty=difficulty,
                confidence=confidence,
                created_at=s.created_at,
                last_active_at=s.last_active_at
            ))

        return SessionListResponse(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def update_session(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        session_in: SessionUpdate,
        user_id: UUID,
    ) -> Optional[SessionResponse]:
        """Update a session ensuring ownership by the authenticated user."""
        updated = self.repo.update_by_id_and_user(db, session_id, user_id, session_in)
        if not updated:
            return None
        return SessionResponse.model_validate(updated)

    def delete_session(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a session ensuring ownership by the authenticated user."""
        return self.repo.delete_by_id_and_user(db, session_id, user_id)
