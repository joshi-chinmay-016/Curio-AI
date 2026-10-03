from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class TurnAssessmentBase(BaseModel):
    learning_assessment: Optional[Dict[str, Any]] = None
    turn_interpretation: Optional[Dict[str, Any]] = None
    learning_objective: Optional[Dict[str, Any]] = None
    question_specification: Optional[Dict[str, Any]] = None


class TurnAssessmentCreate(TurnAssessmentBase):
    message_id: UUID
    session_id: UUID
    user_id: UUID


class TurnAssessmentResponse(TurnAssessmentBase):
    id: UUID
    message_id: UUID
    session_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TurnAssessmentListResponse(BaseModel):
    items: List[TurnAssessmentResponse]
    total: int
    page: int
    page_size: int
    pages: int