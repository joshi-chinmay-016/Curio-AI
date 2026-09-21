from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.session import Session, SessionState
from backend.app.schemas.session import SessionCreate, SessionUpdate, SessionStateBase

class SessionRepository:
    def create(self, db: SQLAlchemySession, user_id: UUID, obj_in: SessionCreate) -> Session:
        db_session = Session(
            user_id=user_id,
            topic=obj_in.topic,
            source_type=obj_in.source_type.value,
            document_id=obj_in.document_id,
            status="ACTIVE"
        )
        db.add(db_session)
        db.flush()  # get ID

        # Create initial state
        db_state = SessionState(
            session_id=db_session.id,
            current_mode="STUDENT",
            difficulty=1,
            confidence=0.0,
            active_concept="Core Definition",
            unresolved_misconceptions=[],
            mastered_concepts=[]
        )
        db.add(db_state)
        db.commit()
        db.refresh(db_session)
        return db_session

    def get(self, db: SQLAlchemySession, id: UUID) -> Optional[Session]:
        return db.query(Session).filter(Session.id == id).first()

    def list_by_user(self, db: SQLAlchemySession, user_id: UUID) -> List[Session]:
        return db.query(Session).filter(Session.user_id == user_id).order_by(Session.created_at.desc()).all()

    def update(self, db: SQLAlchemySession, db_session: Session, obj_in: SessionUpdate) -> Session:
        if obj_in.topic is not None:
            db_session.topic = obj_in.topic
        if obj_in.status is not None:
            db_session.status = obj_in.status.value
            if obj_in.status.value == "COMPLETED" and db_session.ended_at is None:
                from datetime import datetime, timezone
                db_session.ended_at = datetime.now(timezone.utc)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    def update_state(self, db: SQLAlchemySession, session_id: UUID, state_in: SessionStateBase) -> SessionState:
        db_state = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if not db_state:
            db_state = SessionState(session_id=session_id)
            db.add(db_state)

        db_state.current_mode = state_in.current_mode.value if hasattr(state_in.current_mode, 'value') else str(state_in.current_mode)
        db_state.difficulty = state_in.difficulty
        db_state.confidence = state_in.confidence
        db_state.active_concept = state_in.active_concept
        db_state.current_question_id = state_in.current_question_id
        db_state.interrupted_question_id = state_in.interrupted_question_id
        db_state.consecutive_strong_answers = state_in.consecutive_strong_answers
        db_state.consecutive_weak_answers = state_in.consecutive_weak_answers
        db_state.unresolved_misconceptions = state_in.unresolved_misconceptions
        db_state.mastered_concepts = state_in.mastered_concepts
        if hasattr(state_in, 'teacher_intervention_data') and state_in.teacher_intervention_data is not None:
            db_state.teacher_intervention_data = state_in.teacher_intervention_data
        if hasattr(state_in, 'mode_switch_history') and state_in.mode_switch_history is not None:
            db_state.mode_switch_history = state_in.mode_switch_history

        db.add(db_state)
        db.commit()
        db.refresh(db_state)
        return db_state

    def delete(self, db: SQLAlchemySession, id: UUID) -> bool:
        db_session = db.query(Session).filter(Session.id == id).first()
        if db_session:
            db.delete(db_session)
            db.commit()
            return True
        return False
