from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.report import SessionReportResponse
from backend.app.services.report_service import ReportService

router = APIRouter()
report_service = ReportService()


@router.get("/sessions/{session_id}/report", response_model=SessionReportResponse)
def get_report(
    session_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = report_service.get_report(db, session_id, user_id=current_user.id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found. The session must be completed first."
        )
    return report
