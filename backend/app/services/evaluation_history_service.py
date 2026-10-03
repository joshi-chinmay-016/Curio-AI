from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.evaluation_history_repository import EvaluationHistoryRepository
from backend.app.repositories.session_repository import SessionRepository
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.models.turn_assessment import TurnAssessment
from backend.app.schemas.evaluation_history import (
    EvaluationHistoryItem,
    EvaluationHistoryListResponse,
    MessageMetadataResponse,
    TurnEvaluationResponse,
    TurnAssessmentResponse,
)


class EvaluationHistoryService:
    def __init__(self, repo: Optional[EvaluationHistoryRepository] = None, session_repo: Optional[SessionRepository] = None):
        self.repo = repo or EvaluationHistoryRepository()
        self.session_repo = session_repo or SessionRepository()

    def get_evaluation_history(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Optional[EvaluationHistoryListResponse]:
        """
        Retrieve paginated evaluation history for a session owned by user_id.
        Returns None if session not found or not owned by user (anti-enumeration: 404).
        """
        # Verify session ownership first (anti-enumeration)
        session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
        if not session:
            return None

        # Apply pagination bounds (matching repository conventions)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Get paginated evaluation history
        items, total = self.repo.get_evaluation_history_by_session(
            db=db,
            session_id=session_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        # Convert to response schema
        history_items = []
        for msg, eval_obj, assessment_obj in items:
            message_metadata = MessageMetadataResponse(
                message_id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                content=msg.content,
                created_at=msg.created_at,
            )

            evaluation = TurnEvaluationResponse(
                correctness=eval_obj.correctness,
                clarity=eval_obj.clarity,
                completeness=eval_obj.completeness,
                depth=eval_obj.depth,
                relevance=eval_obj.relevance,
                stuck_probability=eval_obj.stuck_probability,
                misconceptions=eval_obj.misconceptions or [],
                missing_concepts=eval_obj.missing_concepts or [],
                undefined_terms=eval_obj.undefined_terms or [],
                mastered_concepts=eval_obj.mastered_concepts or [],
                knowledge_gap=eval_obj.knowledge_gap,
                recommended_strategy=eval_obj.recommended_strategy,
                recommended_difficulty=eval_obj.recommended_difficulty,
            )

            assessment = None
            if assessment_obj:
                assessment = TurnAssessmentResponse(
                    id=assessment_obj.id,
                    message_id=assessment_obj.message_id,
                    session_id=assessment_obj.session_id,
                    user_id=assessment_obj.user_id,
                    learning_assessment=assessment_obj.learning_assessment,
                    turn_interpretation=assessment_obj.turn_interpretation,
                    learning_objective=assessment_obj.learning_objective,
                    question_specification=assessment_obj.question_specification,
                    created_at=assessment_obj.created_at,
                )

            history_items.append(EvaluationHistoryItem(
                message=message_metadata,
                evaluation=evaluation,
                assessment=assessment,
            ))

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return EvaluationHistoryListResponse(
            items=history_items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )