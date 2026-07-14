from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from backend.app.schemas.common import InputType, LearningMode, LearningStrategy

class MessageCreate(BaseModel):
    content: str
    input_type: InputType = InputType.TEXT

class MessageResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    sender: str  # USER, AI
    content: str
    input_type: InputType
    created_at: datetime

    class Config:
        from_attributes = True

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
    recommended_strategy: LearningStrategy
    recommended_difficulty: int

    class Config:
        from_attributes = True

class LearningDecisionResponse(BaseModel):
    next_mode: LearningMode
    strategy: LearningStrategy
    difficulty: int
    confidence: float
    reason: str
    active_concept: str
    should_offer_termination: bool
    should_restore_interrupted_question: bool

class ChatTurnResponse(BaseModel):
    user_message: MessageResponse
    ai_message: MessageResponse
    evaluation: TurnEvaluationResponse
    decision: LearningDecisionResponse
