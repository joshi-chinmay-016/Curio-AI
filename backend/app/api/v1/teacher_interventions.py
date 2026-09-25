"""
Teacher Intervention API endpoints (Phase 3, Task 8):
- GET /api/v1/users/me/teacher-interventions: Retrieve all teacher intervention logs for the authenticated user.
- GET /api/v1/users/me/sessions/{session_id}/teacher-interventions: Retrieve teacher interventions for a specific session.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.session import Session
from backend.app.repositories.teacher_intervention_repository import TeacherInterventionRepository
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.teacher_intervention import (
    TeacherInterventionResponse,
    TeacherInterventionListResponse,
)

router = APIRouter(prefix="/users/me", tags=["Teacher Interventions"])
intervention_repo = TeacherInterventionRepository()
session_repo = SessionRepository()


@router.get(
    "/teacher-interventions",
    response_model=TeacherInterventionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve all teacher intervention logs for the authenticated user",
)
def get_user_interventions(
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TeacherInterventionListResponse:
    """
    Retrieve all teacher intervention logs belonging to the authenticated user.
    Results are ordered chronologically by created_at.
    """
    interventions = intervention_repo.get_by_user(db, current_user.id)
    return TeacherInterventionListResponse(
        interventions=[
            TeacherInterventionResponse.model_validate(i) for i in interventions
        ]
    )


@router.get(
    "/sessions/{session_id}/teacher-interventions",
    response_model=TeacherInterventionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve teacher interventions for a specific session owned by the authenticated user",
)
def get_session_interventions(
    session_id: UUID,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TeacherInterventionListResponse:
    """
    Retrieve teacher intervention logs for a specific session owned by the authenticated user.
    Returns 404 if the session does not belong to the authenticated user (anti-enumeration).
    """
    # Verify session ownership first
    session = session_repo.get_by_id_and_user(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    interventions = intervention_repo.get_by_session(db, session_id, current_user.id)
    return TeacherInterventionListResponse(
        interventions=[
            TeacherInterventionResponse.model_validate(i) for i in interventions
        ]
    )