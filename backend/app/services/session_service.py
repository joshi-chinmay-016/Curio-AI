from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionSummaryResponse
from backend.app.schemas.common import LearningMode, SessionStatus

# Fake hardcoded User ID for MVP authentication isolation
MOCK_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

class SessionService:
    def __init__(self):
        self.repo = SessionRepository()

    def create_session(self, db: SQLAlchemySession, session_in: SessionCreate) -> SessionResponse:
        # Create a mock user in database if none exists to satisfy foreign key constraints
        from backend.app.models.user import User
        user_exists = db.query(User).filter(User.id == MOCK_USER_ID).first()
        if not user_exists:
            user = User(id=MOCK_USER_ID, email="chinmay.vishal@curio.ai")
            db.add(user)
            db.commit()

        db_session = self.repo.create(db, user_id=MOCK_USER_ID, obj_in=session_in)
        return SessionResponse.model_validate(db_session)

    def get_session(self, db: SQLAlchemySession, session_id: UUID) -> Optional[SessionResponse]:
        db_session = self.repo.get(db, session_id)
        if not db_session:
            return None
        return SessionResponse.model_validate(db_session)

    def list_sessions(self, db: SQLAlchemySession) -> List[SessionSummaryResponse]:
        db_sessions = self.repo.list_by_user(db, MOCK_USER_ID)
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

    def update_session(self, db: SQLAlchemySession, session_id: UUID, session_in: SessionUpdate) -> Optional[SessionResponse]:
        db_session = self.repo.get(db, session_id)
        if not db_session:
            return None
        updated = self.repo.update(db, db_session, session_in)
        return SessionResponse.model_validate(updated)

    def delete_session(self, db: SQLAlchemySession, session_id: UUID) -> bool:
        return self.repo.delete(db, session_id)
