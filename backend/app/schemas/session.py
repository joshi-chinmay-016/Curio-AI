from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel
from backend.app.schemas.common import LearningMode, SessionStatus, SourceType

class SessionStateBase(BaseModel):
    current_mode: LearningMode = LearningMode.STUDENT
    difficulty: int = 1
    confidence: float = 0.0
    active_concept: str = "Core Definition"
    current_question_id: Optional[UUID] = None
    interrupted_question_id: Optional[UUID] = None
    consecutive_strong_answers: int = 0
    consecutive_weak_answers: int = 0
    unresolved_misconceptions: List[str] = []
    mastered_concepts: List[str] = []
    concept_mastery: Dict[str, float] = {}
    misconception_counts: Dict[str, int] = {}
    recent_strategy_history: List[str] = []
    mode_switch_history: List[dict] = []
    teacher_attempt_count: int = 0
    teacher_intervention: Optional[Dict[str, Any]] = None

class SessionStateResponse(SessionStateBase):
    session_id: UUID

    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    topic: str
    source_type: SourceType = SourceType.GENERAL
    document_id: Optional[UUID] = None

class SessionUpdate(BaseModel):
    topic: Optional[str] = None
    status: Optional[SessionStatus] = None

class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    topic: str
    source_type: SourceType
    document_id: Optional[UUID]
    status: SessionStatus
    created_at: datetime
    last_active_at: datetime
    ended_at: Optional[datetime]
    state: Optional[SessionStateResponse] = None

    class Config:
        from_attributes = True

class SessionSummaryResponse(BaseModel):
    session_id: UUID
    topic: str
    status: SessionStatus
    current_mode: LearningMode
    difficulty: int
    confidence: float
    created_at: datetime
    last_active_at: datetime

    class Config:
        from_attributes = True
