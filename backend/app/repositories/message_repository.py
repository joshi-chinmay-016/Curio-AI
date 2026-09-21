from typing import List
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.schemas.message import MessageCreate, TurnEvaluationResponse

class MessageRepository:
    def create_message(self, db: SQLAlchemySession, session_id: UUID, sender: str, obj_in: MessageCreate) -> Message:
        db_message = Message(
            session_id=session_id,
            sender=sender,
            content=obj_in.content,
            input_type=obj_in.input_type.value
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message

    def create_evaluation(self, db: SQLAlchemySession, message_id: UUID, eval_in: TurnEvaluationResponse) -> TurnEvaluation:
        db_eval = TurnEvaluation(
            message_id=message_id,
            correctness=eval_in.correctness,
            clarity=eval_in.clarity,
            completeness=eval_in.completeness,
            depth=eval_in.depth,
            relevance=eval_in.relevance,
            stuck_probability=eval_in.stuck_probability,
            misconceptions=eval_in.misconceptions,
            missing_concepts=eval_in.missing_concepts,
            undefined_terms=eval_in.undefined_terms,
            mastered_concepts=eval_in.mastered_concepts,
            knowledge_gap=eval_in.knowledge_gap,
            recommended_strategy=eval_in.recommended_strategy.value if hasattr(eval_in.recommended_strategy, 'value') else str(eval_in.recommended_strategy),
            recommended_difficulty=eval_in.recommended_difficulty
        )
        db.add(db_eval)
        db.commit()
        db.refresh(db_eval)
        return db_eval

    def list_by_session(self, db: SQLAlchemySession, session_id: UUID) -> List[Message]:
        return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()

    def get_recent_evaluations_by_session(
        self, db: SQLAlchemySession, session_id: UUID, limit: int = 10
    ) -> List[TurnEvaluation]:
        """
        Retrieve recent turn evaluations for a given session.
        Joins messages to turn_evaluations, filters by session_id and USER sender,
        fetches up to `limit` latest records, and returns them in chronological order (oldest to newest).
        """
        subquery = (
            db.query(TurnEvaluation)
            .join(Message, TurnEvaluation.message_id == Message.id)
            .filter(Message.session_id == session_id, func.upper(Message.sender) == "USER")
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(subquery))


