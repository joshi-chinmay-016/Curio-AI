from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.repositories.session_repository import SessionRepository
from backend.app.models.report import SessionReport
from backend.app.schemas.report import SessionReportResponse
from backend.app.schemas.common import SessionStatus, MasteryLevel
from backend.app.ai.evaluator_mode import EvaluatorModeHandler
from backend.app.ai.providers.groq_provider import GroqLLMProvider
from backend.app.ai.schemas import AIContext, ChatMessage
from backend.app.schemas.common import InputType

class ReportService:
    def __init__(self):
        self.session_repo = SessionRepository()
        self.ai_provider = GroqLLMProvider()
        self.evaluator_handler = EvaluatorModeHandler(self.ai_provider)

    def get_report(self, db: SQLAlchemySession, session_id: UUID) -> Optional[SessionReportResponse]:
        db_report = db.query(SessionReport).filter(SessionReport.session_id == session_id).first()
        if db_report:
            return SessionReportResponse.model_validate(db_report)
        return None

    def compile_report(self, db: SQLAlchemySession, session_id: UUID) -> Optional[SessionReportResponse]:
        # Fetch session
        db_session = self.session_repo.get(db, session_id)
        if not db_session:
            return None

        # Build context
        history_msgs = db_session.messages
        ai_history = [
            ChatMessage(
                sender=m.sender,
                content=m.content,
                input_type=InputType(str(m.input_type).upper()) if m.input_type and str(m.input_type).upper() in InputType.__members__ else InputType.TEXT
            ) for m in history_msgs
        ]

        context = AIContext(
            session_id=session_id,
            topic=db_session.topic,
            current_mode=db_session.state.current_mode,
            difficulty=db_session.state.difficulty,
            active_concept=db_session.state.active_concept,
            history=ai_history
        )

        # Generate report
        report_schema = self.evaluator_handler.generate_report(context)

        # Persist report
        db_report = SessionReport(
            session_id=session_id,
            understanding_score=report_schema.understanding_score,
            mastery_level=report_schema.mastery_level.value if hasattr(report_schema.mastery_level, 'value') else str(report_schema.mastery_level),
            strengths=report_schema.strengths,
            high_priority_learning_gaps=report_schema.high_priority_learning_gaps,
            medium_priority_learning_gaps=report_schema.medium_priority_learning_gaps,
            low_priority_learning_gaps=report_schema.low_priority_learning_gaps,
            misconceptions_detected=report_schema.misconceptions_detected,
            concepts_mastered=report_schema.concepts_mastered,
            teacher_interventions_required=db_session.state.consecutive_weak_answers, # approximate or use history
            difficulty_achieved=db_session.state.difficulty,
            personalized_roadmap=report_schema.personalized_roadmap,
            recommended_exercises=report_schema.recommended_exercises
        )
        db_report = db.merge(db_report)

        # Mark session as completed
        db_session.status = "COMPLETED"
        db_session.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_report)

        return SessionReportResponse.model_validate(db_report)
