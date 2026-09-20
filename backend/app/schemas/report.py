from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import MasteryLevel


class SessionReportResponse(BaseModel):
    session_id: UUID
    understanding_score: float
    mastery_level: MasteryLevel
    strengths: List[str] = Field(default_factory=list)
    high_priority_learning_gaps: List[str] = Field(default_factory=list)
    medium_priority_learning_gaps: List[str] = Field(default_factory=list)
    low_priority_learning_gaps: List[str] = Field(default_factory=list)
    misconceptions_detected: List[str] = Field(default_factory=list)
    concepts_mastered: List[str] = Field(default_factory=list)
    teacher_interventions_required: int = 0
    difficulty_achieved: int = 1
    personalized_roadmap: List[Any] = Field(default_factory=list)
    recommended_exercises: List[Any] = Field(default_factory=list)
    evidence_confidence: float = 0.0
    concept_assessments: List[Any] = Field(default_factory=list)
    resolved_gaps: List[str] = Field(default_factory=list)
    unresolved_gaps: List[str] = Field(default_factory=list)
    resolved_misconceptions: List[str] = Field(default_factory=list)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    session_evaluation: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
