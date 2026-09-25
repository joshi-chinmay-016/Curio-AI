from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.teacher_intervention import TeacherInterventionLog


class TeacherInterventionRepository:
    def create(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
        gap: str,
        attempt_count: int = 1,
        teacher_explanation: Optional[str] = None,
        verification_question: Optional[str] = None,
        verification_answer: Optional[str] = None,
        verification_passed: Optional[bool] = None,
        intervention_type: Optional[str] = None,
    ) -> TeacherInterventionLog:
        """
        Create a new teacher intervention log record.
        """
        intervention = TeacherInterventionLog(
            session_id=session_id,
            user_id=user_id,
            gap=gap,
            attempt_count=attempt_count,
            teacher_explanation=teacher_explanation,
            verification_question=verification_question,
            verification_answer=verification_answer,
            verification_passed=1 if verification_passed else 0 if verification_passed is not None else None,
            intervention_type=intervention_type,
        )
        db.add(intervention)
        db.commit()
        db.refresh(intervention)
        return intervention

    def get_by_session(
        self, db: SQLAlchemySession, session_id: UUID, user_id: UUID
    ) -> List[TeacherInterventionLog]:
        """
        Retrieve all intervention logs for a session owned by the user.
        Ordered chronologically by created_at.
        """
        return (
            db.query(TeacherInterventionLog)
            .filter(
                TeacherInterventionLog.session_id == session_id,
                TeacherInterventionLog.user_id == user_id,
            )
            .order_by(TeacherInterventionLog.created_at.asc())
            .all()
        )

    def get_by_user(
        self, db: SQLAlchemySession, user_id: UUID
    ) -> List[TeacherInterventionLog]:
        """
        Retrieve all intervention logs for a user.
        Ordered chronologically by created_at.
        """
        return (
            db.query(TeacherInterventionLog)
            .filter(TeacherInterventionLog.user_id == user_id)
            .order_by(TeacherInterventionLog.created_at.asc())
            .all()
        )

    def get_by_id(
        self, db: SQLAlchemySession, intervention_id: UUID, user_id: UUID
    ) -> Optional[TeacherInterventionLog]:
        """
        Retrieve a specific intervention log by ID, ensuring it belongs to the user.
        """
        return (
            db.query(TeacherInterventionLog)
            .filter(
                TeacherInterventionLog.id == intervention_id,
                TeacherInterventionLog.user_id == user_id,
            )
            .first()
        )

    def delete_by_session(self, db: SQLAlchemySession, session_id: UUID, user_id: UUID) -> int:
        """
        Delete all intervention logs for a session owned by the user.
        Returns count of deleted records.
        """
        count = (
            db.query(TeacherInterventionLog)
            .filter(
                TeacherInterventionLog.session_id == session_id,
                TeacherInterventionLog.user_id == user_id,
            )
            .delete()
        )
        db.commit()
        return count

    def delete_by_user(self, db: SQLAlchemySession, user_id: UUID) -> int:
        """
        Delete all intervention logs for a user.
        Returns count of deleted records.
        """
        count = (
            db.query(TeacherInterventionLog)
            .filter(TeacherInterventionLog.user_id == user_id)
            .delete()
        )
        db.commit()
        return count