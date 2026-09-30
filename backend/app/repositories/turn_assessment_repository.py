from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.turn_assessment import TurnAssessment
from backend.app.models.message import Message
from backend.app.schemas.session import SessionStateBase


class TurnAssessmentRepository:
    def create_assessment(
        self,
        db: SQLAlchemySession,
        message_id: UUID,
        session_id: UUID,
        user_id: UUID,
        learning_assessment: Optional[dict] = None,
        turn_interpretation: Optional[dict] = None,
        learning_objective: Optional[dict] = None,
        question_specification: Optional[dict] = None,
    ) -> TurnAssessment:
        db_assessment = TurnAssessment(
            message_id=message_id,
            session_id=session_id,
            user_id=user_id,
            learning_assessment=learning_assessment,
            turn_interpretation=turn_interpretation,
            learning_objective=learning_objective,
            question_specification=question_specification,
        )
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        return db_assessment

    def get_by_message_id(self, db: SQLAlchemySession, message_id: UUID) -> Optional[TurnAssessment]:
        return db.query(TurnAssessment).filter(TurnAssessment.message_id == message_id).first()

    def get_by_session_id(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[TurnAssessment], int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = db.query(TurnAssessment).filter(TurnAssessment.session_id == session_id)

        total = query.count()

        offset = (page - 1) * page_size
        items = (
            query.order_by(TurnAssessment.created_at.asc(), TurnAssessment.id.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return items, total

    def get_by_user_and_session(
        self,
        db: SQLAlchemySession,
        user_id: UUID,
        session_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[TurnAssessment], int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = db.query(TurnAssessment).filter(
            TurnAssessment.user_id == user_id,
            TurnAssessment.session_id == session_id,
        )

        total = query.count()

        offset = (page - 1) * page_size
        items = (
            query.order_by(TurnAssessment.created_at.asc(), TurnAssessment.id.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return items, total

    def delete_by_session_id(self, db: SQLAlchemySession, session_id: UUID) -> int:
        count = db.query(TurnAssessment).filter(TurnAssessment.session_id == session_id).delete()
        db.commit()
        return count

    def delete_by_message_id(self, db: SQLAlchemySession, message_id: UUID) -> bool:
        assessment = db.query(TurnAssessment).filter(TurnAssessment.message_id == message_id).first()
        if assessment:
            db.delete(assessment)
            db.commit()
            return True
        return False