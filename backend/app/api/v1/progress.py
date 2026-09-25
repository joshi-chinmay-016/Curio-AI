"""
Learning Progress API endpoints (Phase 3, Task 5):
- GET /api/v1/users/me/progress: Retrieve authenticated user's complete learning progress.
- GET /api/v1/users/me/progress/batch?concepts=...: Retrieve progress for multiple specific concepts.
- GET /api/v1/users/me/progress/{concept}: Retrieve progress for a specific concept.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.learning_progress import (
    ConceptProgressResponse,
    LearningProgressResponse,
)
from backend.app.services.learning_progress_service import LearningProgressService

router = APIRouter(prefix="/users/me", tags=["Learning Progress"])
progress_service = LearningProgressService()


@router.get(
    "/progress",
    response_model=LearningProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated user's complete learning progress",
)
def get_user_progress(
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LearningProgressResponse:
    """
    Retrieve the authenticated user's complete learning progress.
    Includes all concepts and a factual summary aggregation.
    """
    return progress_service.get_user_progress(db, user_id=current_user.id)


@router.get(
    "/progress/batch",
    response_model=List[ConceptProgressResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve progress for multiple specific concepts",
)
def get_concepts_progress(
    concepts: str = Query(..., description="Comma-separated list of concepts"),
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[ConceptProgressResponse]:
    """
    Retrieve progress for multiple specific concepts belonging to the authenticated user.
    Example: /api/v1/users/me/progress/batch?concepts=recursion,graphs,dp
    """
    concept_list = [c.strip() for c in concepts.split(",") if c.strip()]
    if not concept_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one concept must be specified",
        )
    return progress_service.get_progress_for_concepts(db, user_id=current_user.id, concepts=concept_list)


@router.get(
    "/progress/{concept}",
    response_model=ConceptProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve progress for a specific concept",
)
def get_concept_progress(
    concept: str,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConceptProgressResponse:
    """
    Retrieve progress for a specific concept belonging to the authenticated user.
    Returns 404 if the concept does not exist for the authenticated user.
    """
    result = progress_service.get_concept_progress(db, user_id=current_user.id, concept=concept)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concept progress not found",
        )
    return result