"""
Service layer for learning session reports, versioning, and evaluations (Phase 3G & Phase 4.4).
"""
from datetime import datetime, timezone
import math
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.ai.engine import CurioEngine
from backend.app.ai.schemas import (
    LearningReport,
    SessionEvaluation,
    SessionEvidence,
    TurnEvaluation,
)
from backend.app.ai.session_evidence import SessionEvidenceBuilder
from backend.app.models.report import SessionReport
from backend.app.models.report_version import SessionReportVersion
from backend.app.models.report_evidence_snapshot import ReportEvidenceSnapshot
from backend.app.models.session import Session
from backend.app.repositories.report_repository import ReportRepository
from backend.app.repositories.report_version_repository import ReportVersionRepository
from backend.app.repositories.report_evidence_snapshot_repository import ReportEvidenceSnapshotRepository
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.report import (
    SessionReportHistoryListResponse,
    SessionReportResponse,
    SessionReportVersionResponse,
)


class ReportService:
    def __init__(
        self,
        ai_engine: Optional[CurioEngine] = None,
        session_repo: Optional[SessionRepository] = None,
        report_repo: Optional[ReportRepository] = None,
        version_repo: Optional[ReportVersionRepository] = None,
        evidence_snapshot_repo: Optional[ReportEvidenceSnapshotRepository] = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.report_repo = report_repo or ReportRepository()
        self.version_repo = version_repo or ReportVersionRepository()
        self.evidence_snapshot_repo = evidence_snapshot_repo or ReportEvidenceSnapshotRepository()
        self.ai_engine = ai_engine or CurioEngine()
        self.evidence_builder = SessionEvidenceBuilder()

    def get_report(
        self, db: SQLAlchemySession, session_id: UUID, user_id: Optional[UUID] = None
    ) -> Optional[SessionReportResponse]:
        """Retrieve latest/current report for a session with ownership verification."""
        if user_id:
            session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not session:
                return None
        db_report = self.report_repo.get_by_session_id(db, session_id)
        if db_report:
            return SessionReportResponse.model_validate(db_report)
        return None

    def get_report_version(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        version_number: int,
        user_id: Optional[UUID] = None,
    ) -> Optional[SessionReportVersionResponse]:
        """Retrieve a specific historical report version for an owned session."""
        if user_id:
            session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not session:
                return None
        db_version = self.version_repo.get_by_version_number(db, session_id, version_number)
        if db_version:
            return SessionReportVersionResponse.model_validate(db_version)
        return None

    def get_report_history(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Optional[SessionReportHistoryListResponse]:
        """Retrieve paginated report history for an owned session ordered newest first."""
        if user_id:
            session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
            if not session:
                return None

        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        items, total = self.version_repo.list_versions_paginated(
            db, session_id, page=page, page_size=page_size
        )
        pages = math.ceil(total / page_size) if total > 0 else 0

        return SessionReportHistoryListResponse(
            items=[SessionReportVersionResponse.model_validate(v) for v in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def _build_report_data(
        self,
        db: SQLAlchemySession,
        db_session: Session,
        user_id: Optional[UUID],
    ) -> tuple[dict, SessionEvidence]:
        """
        Assembles evidence and runs CurioEngine to produce structured report data.
        Returns a tuple of (report_data dict, SessionEvidence object).
        """
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

        active_concept = db_session.state.active_concept if db_session.state else ""
        diff_hist = [db_session.state.difficulty] if db_session.state else [1]
        evidence = self.evidence_builder.build_from_history(
            session_id=str(db_session.id),
            topic=db_session.topic,
            messages=history_msgs,
            evaluations=evaluations,
            difficulty_history=diff_hist,
            active_concept=active_concept,
            db=db,
            user_id=user_id,
        )

        session_evaluation: SessionEvaluation = self.ai_engine.evaluate_session(evidence)
        learning_report: LearningReport = self.ai_engine.generate_report(evidence)

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

        report_data = {
            "understanding_score": learning_report.understanding_score,
            "mastery_level": mastery_val,
            "strengths": learning_report.strengths,
            "high_priority_learning_gaps": high_gaps,
            "medium_priority_learning_gaps": med_gaps,
            "low_priority_learning_gaps": low_gaps,
            "misconceptions_detected": learning_report.misconceptions,
            "concepts_mastered": concepts_mastered,
            "teacher_interventions_required": learning_report.teacher_interventions_required,
            "difficulty_achieved": learning_report.difficulty_achieved,
            "personalized_roadmap": roadmap_dump,
            "recommended_exercises": [
                item.get("title", "") for item in roadmap_dump if isinstance(item, dict)
            ],
            "evidence_confidence": learning_report.evidence_confidence,
            "concept_assessments": concept_assessments_dump,
            "resolved_gaps": learning_report.resolved_gaps,
            "unresolved_gaps": learning_report.unresolved_gaps,
            "resolved_misconceptions": learning_report.resolved_misconceptions,
            "unresolved_misconceptions": learning_report.unresolved_misconceptions,
            "session_evaluation": (
                session_evaluation.model_dump()
                if hasattr(session_evaluation, "model_dump")
                else {}
            ),
        }

        return report_data, evidence

    def compile_report(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        force_recompute: bool = False,
        user_id: Optional[UUID] = None,
    ) -> Optional[SessionReportResponse]:
        """
        Compiles the learning report for a session:
        - If already compiled and not force_recompute, returns existing report (idempotent).
        - Otherwise, builds structured evidence, calls CurioEngine, allocates next version,
          persists immutable SessionReportVersion, updates SessionReport cache, and marks session COMPLETED
          in a single atomic transaction.
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

        # 2. Acquire lock on parent session for atomic version allocation
        locked_session = (
            db.query(Session)
            .filter(Session.id == session_id)
            .with_for_update()
            .first()
        )
        if not locked_session:
            return None

        # Re-check idempotency under lock in case another transaction just committed
        if not force_recompute:
            existing = self.report_repo.get_by_session_id(db, session_id)
            if existing:
                return SessionReportResponse.model_validate(existing)

        # 3. Determine next version number
        max_version = self.version_repo.get_max_version_number(db, session_id)
        next_version = (max_version or 0) + 1

        try:
            # 4. Build evidence (used for both snapshot and AI generation)
            report_data, evidence = self._build_report_data(db, locked_session, user_id)

            # 5. Create version object first (to get ID)
            version_obj = SessionReportVersion(
                session_id=session_id,
                version_number=next_version,
                **report_data,
            )
            self.version_repo.create_version(db, version_obj, commit=False)
            # Flush to get version ID
            db.flush()

            # 5. Create evidence snapshot with version reference
            evidence_json = evidence.model_dump(mode="json")
            snapshot = ReportEvidenceSnapshot(
                report_version_id=version_obj.id,
                schema_version=1,
                evidence_json=evidence_json,
            )
            self.evidence_snapshot_repo.create(db, snapshot, commit=False)

            # 6. Update current/latest SessionReport cache
            db_report = SessionReport(
                session_id=session_id,
                version_number=next_version,
                **report_data,
            )
            persisted_report = self.report_repo.create_or_update(
                db, db_report, commit=False
            )

            # 7. Complete session
            locked_session.status = "COMPLETED"
            if not locked_session.ended_at:
                locked_session.ended_at = datetime.now(timezone.utc)

            # 8. Single atomic commit
            db.commit()
            db.refresh(persisted_report)
            return SessionReportResponse.model_validate(persisted_report)
        except Exception:
            db.rollback()
            raise

    def regenerate_report(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        user_id: UUID,
    ) -> Optional[SessionReportResponse]:
        """
        Explicitly regenerates the report for a session:
        1. Verifies user ownership.
        2. Validates session has meaningful interaction history (raises ValueError if empty).
        3. Locks session row with FOR UPDATE.
        4. Invokes CurioEngine to evaluate and generate new report.
        5. Allocates next sequential version number N+1.
        6. Persists immutable version N+1 to session_report_versions.
        7. Updates session_reports latest cache.
        8. Commits atomically.
        """
        # 1. Ownership check
        session = self.session_repo.get_by_id_and_user(db, session_id, user_id)
        if not session:
            return None

        # 2. Check for meaningful interaction history
        history_msgs = session.messages or []
        user_messages = [m for m in history_msgs if m.sender.upper() == "USER"]
        if not user_messages:
            raise ValueError("Cannot generate report for session with no interaction history")

        # 3. Lock session row
        locked_session = (
            db.query(Session)
            .filter(Session.id == session_id)
            .with_for_update()
            .first()
        )
        if not locked_session:
            return None

        # 4. Determine next version number
        max_version = self.version_repo.get_max_version_number(db, session_id)
        next_version = (max_version or 0) + 1

        try:
            # 5. Build evidence (used for both snapshot and AI generation)
            report_data, evidence = self._build_report_data(db, locked_session, user_id)

            # 6. Create version object first (to get ID)
            version_obj = SessionReportVersion(
                session_id=session_id,
                version_number=next_version,
                **report_data,
            )
            self.version_repo.create_version(db, version_obj, commit=False)
            # Flush to get version ID
            db.flush()

            # 7. Create evidence snapshot with version reference
            evidence_json = evidence.model_dump(mode="json")
            snapshot = ReportEvidenceSnapshot(
                report_version_id=version_obj.id,
                schema_version=1,
                evidence_json=evidence_json,
            )
            self.evidence_snapshot_repo.create(db, snapshot, commit=False)

            # 8. Update SessionReport latest cache
            db_report = SessionReport(
                session_id=session_id,
                version_number=next_version,
                **report_data,
            )
            persisted_report = self.report_repo.create_or_update(
                db, db_report, commit=False
            )

            # 9. Complete session if not already completed
            locked_session.status = "COMPLETED"
            if not locked_session.ended_at:
                locked_session.ended_at = datetime.now(timezone.utc)

            # 10. Single atomic commit
            db.commit()
            db.refresh(persisted_report)
            return SessionReportResponse.model_validate(persisted_report)
        except Exception:
            db.rollback()
            raise
