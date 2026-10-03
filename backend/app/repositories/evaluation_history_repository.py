from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.models.turn_assessment import TurnAssessment


class EvaluationHistoryRepository:
    def get_evaluation_history_by_session(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[tuple], int]:
        """
        Retrieve paginated evaluation history for a session owned by user_id.

        Returns tuples of (Message, TurnEvaluation, TurnAssessment | None).
        TurnAssessment is LEFT JOINed since not all turns have assessments.
        Only USER messages with evaluations are included.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Build base query with ownership enforcement
        query = (
            db.query(Message, TurnEvaluation, TurnAssessment)
            .join(TurnEvaluation, TurnEvaluation.message_id == Message.id)
            .outerjoin(TurnAssessment, TurnAssessment.message_id == Message.id)
            .join(Message.session)  # Join to Session for ownership check
            .filter(Message.session_id == session_id)
            .filter(Message.sender == "USER")
            .filter(Message.session.has(user_id=user_id))
        )

        # Order by message chronology (deterministic)
        query = query.order_by(Message.created_at.asc(), Message.id.asc())

        # Count total before pagination
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return items, total

    def get_evaluation_history_count(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
    ) -> int:
        """Get total count of evaluation history items for a session."""
        return (
            db.query(func.count(Message.id))
            .join(TurnEvaluation, TurnEvaluation.message_id == Message.id)
            .join(Message.session)
            .filter(Message.session_id == session_id)
            .filter(Message.sender == "USER")
            .filter(Message.session.has(user_id=user_id))
            .scalar()
        )