"""
Repository for SessionReportVersion immutable persistence and history retrieval.
"""
import math
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.models.report_version import SessionReportVersion


class ReportVersionRepository:
    def create_version(
        self, db: SQLAlchemySession, version: SessionReportVersion, commit: bool = True
    ) -> SessionReportVersion:
        """
        Append an immutable report version row.
        Does not allow modifying existing versions.
        """
        db.add(version)
        if commit:
            db.commit()
            db.refresh(version)
        return version

    def get_latest_version(
        self, db: SQLAlchemySession, session_id: UUID
    ) -> Optional[SessionReportVersion]:
        """Retrieve the newest version for a session by version_number."""
        return (
            db.query(SessionReportVersion)
            .filter(SessionReportVersion.session_id == session_id)
            .order_by(SessionReportVersion.version_number.desc())
            .first()
        )

    def get_by_version_number(
        self, db: SQLAlchemySession, session_id: UUID, version_number: int
    ) -> Optional[SessionReportVersion]:
        """Retrieve an exact historical report version for a session."""
        return (
            db.query(SessionReportVersion)
            .filter(
                SessionReportVersion.session_id == session_id,
                SessionReportVersion.version_number == version_number,
            )
            .first()
        )

    def get_max_version_number(
        self, db: SQLAlchemySession, session_id: UUID
    ) -> Optional[int]:
        """
        Return the current MAX(version_number) for a session.
        Returns None if no versions exist yet.
        """
        return (
            db.query(func.max(SessionReportVersion.version_number))
            .filter(SessionReportVersion.session_id == session_id)
            .scalar()
        )

    def list_versions_paginated(
        self,
        db: SQLAlchemySession,
        session_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SessionReportVersion], int]:
        """
        Retrieve paginated report versions for a session ordered newest first (version_number DESC).
        Returns (items, total_count).
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = db.query(SessionReportVersion).filter(
            SessionReportVersion.session_id == session_id
        )

        total = query.count()
        items = (
            query.order_by(SessionReportVersion.version_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total
