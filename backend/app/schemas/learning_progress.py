from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ConceptProgressResponse(BaseModel):
    concept: str
    mastery_score: float
    total_attempts: int
    successful_attempts: int
    last_practiced_at: Optional[datetime]
    last_difficulty: int
    misconception_count: int

    model_config = ConfigDict(from_attributes=True)


class LearningProgressSummary(BaseModel):
    total_concepts_tracked: int
    concepts_with_progress: int
    total_attempts: int
    total_successful_attempts: int
    total_misconceptions: int
    most_recently_practiced_concept: Optional[str]
    last_practiced_at: Optional[datetime]


class LearningProgressResponse(BaseModel):
    user_id: UUID
    concepts: List[ConceptProgressResponse]
    summary: LearningProgressSummary

    model_config = ConfigDict(from_attributes=True)