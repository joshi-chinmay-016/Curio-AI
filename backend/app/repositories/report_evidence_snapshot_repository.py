from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.report_evidence_snapshot import ReportEvidenceSnapshot


class ReportEvidenceSnapshotRepository:
    def create(
        self,
        db: SQLAlchemySession,
        snapshot: ReportEvidenceSnapshot,
        commit: bool = True,
    ) -> ReportEvidenceSnapshot:
        """
        Create a new evidence snapshot.
        """
        db.add(snapshot)
        if commit:
            db.commit()
            db.refresh(snapshot)
        return snapshot

    def get_by_version_id(
        self, db: SQLAlchemySession, report_version_id: UUID
    ) -> Optional[ReportEvidenceSnapshot]:
        """
        Retrieve the evidence snapshot for a specific report version.
        """
        return (
            db.query(ReportEvidenceSnapshot)
            .filter(ReportEvidenceSnapshot.report_version_id == report_version_id)
            .first()
        )