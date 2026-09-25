"""
Service layer for learning session reports and evaluations (Phase 3G).
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.ai.engine import CurioEngine
from backend.app.ai.schemas import (
    ChatMessage,
    InputType,
    LearningReport,
    Role,
    SessionEvaluation,
    TurnEvaluation,
)
from backend.app.ai.session_evidence import SessionEvidenceBuilder
from backend.app.models.report import SessionReport
from backend.app.repositories.report_repository import ReportRepository
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.report import SessionReportResponse


class ReportService:
    def __init__(
        self,
        ai_engine: Optional[CurioEngine] = None,
        session_repo: Optional[SessionRepository] = None,
        report_repo: Optional[ReportRepository] = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.report_repo = report_repo or ReportRepository()
        self.ai_engine = ai_engine or CurioEngine()
        self.evidence_builder = SessionEvidenceBuilder()

    def get_report(
        self, db: SQLAlchemySession, session_id: UUID, user_id: Optional[UUID] = None
    ) -> Optional[SessionReportResponse]:
        """Retrieve existing report for a session with ownership verification."""
        if user_id:
            session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not session:
                return None
        db_report = self.report_repo.get_by_session_id(db, session_id)
        if db_report:
            return SessionReportResponse.model_validate(db_report)
        return None

    def compile_report(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        force_recompute: bool = False,
        user_id: Optional[UUID] = None,
    ) -> Optional[SessionReportResponse]:
        """
        Compiles the final learning report for a session:
        - If already compiled and not force_recompute, returns existing report (idempotent).
        - Otherwise, builds structured SessionEvidence from session messages & turn evaluations,
          evaluates understanding via CurioEngine, persists the report, and marks the session COMPLETED.
        """
        if user_id:
            session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not session:
                return None

        # 1. Idempotent check
        if not force_recompute:
            existing = self.report_repo.get_by_session_id(db, session_id)
            if existing:
                return SessionReportResponse.model_validate(existing)

        # 2. Fetch session
        db_session = session if user_id else self.session_repo.get(db, session_id)
        if not db_session:
            return None

        # 3. Extract messages and turn evaluations
        history_msgs = db_session.messages or []
        evaluations = []
        for m in history_msgs:
            if m.sender.upper() == "USER" and getattr(m, "evaluation", None):
                db_ev = m.evaluation
                evaluations.append(
                    TurnEvaluation(
                        correctness=db_ev.correctness,
                        clarity=db_ev.clarity,
                        completeness=db_ev.completeness,
                        depth=db_ev.depth,
                        relevance=db_ev.relevance,
                        stuck_probability=db_ev.stuck_probability,
                        misconceptions=db_ev.misconceptions or [],
                        missing_concepts=db_ev.missing_concepts or [],
                        undefined_terms=db_ev.undefined_terms or [],
                        mastered_concepts=db_ev.mastered_concepts or [],
                        knowledge_gap=db_ev.knowledge_gap,
                        recommended_strategy=db_ev.recommended_strategy,
                        recommended_difficulty=db_ev.recommended_difficulty,
                    )
                )

        # 4. Build structured SessionEvidence
        active_concept = db_session.state.active_concept if db_session.state else ""
        diff_hist = [db_session.state.difficulty] if db_session.state else [1]
        evidence = self.evidence_builder.build_from_history(
            session_id=str(session_id),
            topic=db_session.topic,
            messages=history_msgs,
            evaluations=evaluations,
            difficulty_history=diff_hist,
            active_concept=active_concept,
            db=db,
            user_id=user_id,
        )

        # 5. Evaluate session & generate report via CurioEngine
        session_evaluation: SessionEvaluation = self.ai_engine.evaluate_session(evidence)
        learning_report: LearningReport = self.ai_engine.generate_report(evidence)

        # 6. Map to database model
        roadmap_dump = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in learning_report.recommended_next_steps
        ]
        concept_assessments_dump = [
            ca.model_dump() if hasattr(ca, "model_dump") else ca
            for ca in learning_report.concept_assessments
        ]

        mastery_val = (
            learning_report.mastery_level.value
            if hasattr(learning_report.mastery_level, "value")
            else str(learning_report.mastery_level)
        )

        gaps = learning_report.knowledge_gaps
        high_gaps = gaps[:3]
        med_gaps = gaps[3:6]
        low_gaps = gaps[6:]

        concepts_mastered = [
            ca.concept
            for ca in learning_report.concept_assessments
            if ca.mastery_level in ["PROFICIENT", "MASTERY"]
        ]
        if not concepts_mastered and learning_report.understanding_score >= 70:
            concepts_mastered = [db_session.topic]

        db_report = SessionReport(
            session_id=session_id,
            understanding_score=learning_report.understanding_score,
            mastery_level=mastery_val,
            strengths=learning_report.strengths,
            high_priority_learning_gaps=high_gaps,
            medium_priority_learning_gaps=med_gaps,
            low_priority_learning_gaps=low_gaps,
            misconceptions_detected=learning_report.misconceptions,
            concepts_mastered=concepts_mastered,
            teacher_interventions_required=learning_report.teacher_interventions_required,
            difficulty_achieved=learning_report.difficulty_achieved,
            personalized_roadmap=roadmap_dump,
            recommended_exercises=[item.get("title", "") for item in roadmap_dump if isinstance(item, dict)],
            evidence_confidence=learning_report.evidence_confidence,
            concept_assessments=concept_assessments_dump,
            resolved_gaps=learning_report.resolved_gaps,
            unresolved_gaps=learning_report.unresolved_gaps,
            resolved_misconceptions=learning_report.resolved_misconceptions,
            unresolved_misconceptions=learning_report.unresolved_misconceptions,
            session_evaluation=session_evaluation.model_dump() if hasattr(session_evaluation, "model_dump") else {},
        )

        # 7. Persist report and mark session COMPLETED
        persisted_report = self.report_repo.create_or_update(db, db_report)
        db_session.status = "COMPLETED"
        db_session.ended_at = datetime.now(timezone.utc)
        db.commit()

        return SessionReportResponse.model_validate(persisted_report)
