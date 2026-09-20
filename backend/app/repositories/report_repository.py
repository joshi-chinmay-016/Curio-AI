"""
Repository for SessionReport persistence.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.models.report import SessionReport


class ReportRepository:
    def get_by_session_id(self, db: SQLAlchemySession, session_id: UUID) -> Optional[SessionReport]:
        return db.query(SessionReport).filter(SessionReport.session_id == session_id).first()

    def create_or_update(self, db: SQLAlchemySession, report: SessionReport) -> SessionReport:
        merged = db.merge(report)
        db.commit()
        db.refresh(merged)
        return merged

    def delete(self, db: SQLAlchemySession, session_id: UUID) -> bool:
        report = self.get_by_session_id(db, session_id)
        if report:
            db.delete(report)
            db.commit()
            return True
        return False
