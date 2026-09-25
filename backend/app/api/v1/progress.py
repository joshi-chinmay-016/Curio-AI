from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.app.api.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.learning_progress import (
    LearningProgressResponse,
    ConceptProgressResponse,
)
from backend.app.services.learning_progress_service import LearningProgressService

router = APIRouter(prefix="/users/me", tags=["Learning Progress"])
progress_service = LearningProgressService()


@router.get("/progress", response_model=LearningProgressResponse)
def get_user_progress(
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve the authenticated user's complete learning progress.
    """
    return progress_service.get_user_progress(db, user_id=current_user.id)


@router.get("/progress/{concept}", response_model=ConceptProgressResponse)
def get_concept_progress(
    concept: str,
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve progress for a specific concept belonging to the authenticated user.
    """
    result = progress_service.get_concept_progress(db, user_id=current_user.id, concept=concept)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept progress not found")
    return result


@router.get("/progress", response_model=List[ConceptProgressResponse])
def get_concepts_progress(
    concepts: Optional[str] = Query(None, description="Comma-separated list of concepts"),
    db: SQLAlchemySession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve progress for multiple specific concepts belonging to the authenticated user.
    """
    if not concepts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="concepts query parameter is required")
    concept_list = [c.strip() for c in concepts.split(",") if c.strip()]
    return progress_service.get_progress_for_concepts(db, user_id=current_user.id, concepts=concept_list)