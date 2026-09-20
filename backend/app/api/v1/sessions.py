from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.db.session import get_db
from backend.app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionSummaryResponse
from backend.app.schemas.common import SessionStatus
from backend.app.schemas.report import SessionReportResponse
from backend.app.services.session_service import SessionService
from backend.app.services.report_service import ReportService

router = APIRouter()
session_service = SessionService()
report_service = ReportService()

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session_in: SessionCreate, db: SQLAlchemySession = Depends(get_db)):
    return session_service.create_session(db, session_in)

@router.get("/sessions", response_model=List[SessionSummaryResponse])
def list_sessions(db: SQLAlchemySession = Depends(get_db)):
    return session_service.list_sessions(db)

@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    session = session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.patch("/sessions/{session_id}", response_model=SessionResponse)
def update_session(session_id: UUID, session_in: SessionUpdate, db: SQLAlchemySession = Depends(get_db)):
    session = session_service.update_session(db, session_id, session_in)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    success = session_service.delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return

@router.post("/sessions/{session_id}/pause", response_model=SessionResponse)
def pause_session(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    session = session_service.update_session(db, session_id, SessionUpdate(status=SessionStatus.PAUSED))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/sessions/{session_id}/resume", response_model=SessionResponse)
def resume_session(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    session = session_service.update_session(db, session_id, SessionUpdate(status=SessionStatus.ACTIVE))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/sessions/{session_id}/end", response_model=SessionReportResponse)
def end_session(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    # Triggers compilation of the report and locks the session
    report = report_service.compile_report(db, session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found or failed to compile report")
    return report


@router.post("/sessions/{session_id}/evaluate", response_model=SessionReportResponse)
def evaluate_session(session_id: UUID, db: SQLAlchemySession = Depends(get_db)):
    """Explicitly triggers session evaluation and generates a structured learning report."""
    report = report_service.compile_report(db, session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found or failed to compile report")
    return report
