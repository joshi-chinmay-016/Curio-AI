from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel
from backend.app.schemas.common import MasteryLevel

class SessionReportResponse(BaseModel):
    session_id: UUID
    understanding_score: float
    mastery_level: MasteryLevel
    strengths: List[str]
    high_priority_learning_gaps: List[str]
    medium_priority_learning_gaps: List[str]
    low_priority_learning_gaps: List[str]
    misconceptions_detected: List[str]
    concepts_mastered: List[str]
    teacher_interventions_required: int
    difficulty_achieved: int
    personalized_roadmap: List[str]
    recommended_exercises: List[str]
    created_at: datetime

    class Config:
        from_attributes = True
