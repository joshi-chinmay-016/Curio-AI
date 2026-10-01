from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TurnEvaluationResponse(BaseModel):
    correctness: float
    clarity: float
    completeness: float
    depth: float
    relevance: float
    stuck_probability: float
    misconceptions: List[str]
    missing_concepts: List[str]
    undefined_terms: List[str]
    mastered_concepts: List[str]
    knowledge_gap: Optional[str] = None
    recommended_strategy: str
    recommended_difficulty: int

    class Config:
        from_attributes = True


class TurnAssessmentResponse(BaseModel):
    id: UUID
    message_id: UUID
    session_id: UUID
    user_id: UUID
    learning_assessment: Optional[Dict[str, Any]] = None
    turn_interpretation: Optional[Dict[str, Any]] = None
    learning_objective: Optional[Dict[str, Any]] = None
    question_specification: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageMetadataResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    sender: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationHistoryItem(BaseModel):
    message: MessageMetadataResponse
    evaluation: TurnEvaluationResponse
    assessment: Optional[TurnAssessmentResponse] = None


class EvaluationHistoryListResponse(BaseModel):
    items: List[EvaluationHistoryItem]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int