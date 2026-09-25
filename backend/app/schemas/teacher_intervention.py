from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class TeacherInterventionResponse(BaseModel):
    id: UUID
    session_id: UUID
    gap: str
    attempt_count: int
    teacher_explanation: Optional[str]
    verification_question: Optional[str]
    verification_answer: Optional[str]
    verification_passed: Optional[bool]
    intervention_type: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeacherInterventionListResponse(BaseModel):
    interventions: List[TeacherInterventionResponse]