import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.report import (
    SessionReportHistoryListResponse,
    SessionReportResponse,
    SessionReportVersionResponse,
)
from backend.app.services.report_service import ReportService

logger = logging.getLogger("curio_reports")
router = APIRouter()
report_service = ReportService()


@router.get("/sessions/{session_id}/report", response_model=SessionReportResponse)
def get_report(
    session_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the current/latest report for an owned session."""
    report = report_service.get_report(db, session_id, user_id=current_user.id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. The session must be completed first."
        )
    return report


@router.post(
    "/sessions/{session_id}/report/regenerate",
    response_model=SessionReportResponse,
    status_code=status.HTTP_200_OK,
)
def regenerate_report(
    session_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Explicitly regenerate a report for an owned session, creating a new immutable version N+1.
    Requires meaningful interaction history in the session.
    """
    try:
        report = report_service.regenerate_report(db, session_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate report for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate report",
        )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return report


@router.get(
    "/sessions/{session_id}/reports",
    response_model=SessionReportHistoryListResponse,
    status_code=status.HTTP_200_OK,
)
def get_report_history(
    session_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve paginated report history for an owned session, ordered newest first.
    Anti-enumeration: Returns 404 for foreign or nonexistent sessions.
    """
    history = report_service.get_report_history(
        db, session_id, user_id=current_user.id, page=page, page_size=page_size
    )
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return history


@router.get(
    "/sessions/{session_id}/reports/{version_number}",
    response_model=SessionReportVersionResponse,
    status_code=status.HTTP_200_OK,
)
def get_report_version(
    session_id: UUID,
    version_number: int,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve an exact historical report version for an owned session.
    Anti-enumeration: Returns 404 for foreign sessions, nonexistent sessions, or nonexistent versions.
    """
    version = report_service.get_report_version(
        db, session_id, version_number=version_number, user_id=current_user.id
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report version not found",
        )
    return version
