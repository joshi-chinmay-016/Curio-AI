from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel
from backend.app.schemas.common import LearningMode, LearningStrategy, InputType

class ChatMessage(BaseModel):
    sender: str  # USER, AI
    content: str
    input_type: InputType = InputType.TEXT

class AIContext(BaseModel):
    session_id: UUID
    topic: str
    current_mode: LearningMode
    difficulty: int
    active_concept: str
    current_question: Optional[str] = None
    interrupted_question: Optional[str] = None
    document_context: Optional[str] = None
    history: List[ChatMessage]

class TurnEvaluation(BaseModel):
    correctness: float  # 0 to 1
    clarity: float  # 0 to 1
    completeness: float  # 0 to 1
    depth: float  # 0 to 1
    relevance: float  # 0 to 1
    stuck_probability: float  # 0 to 1
    misconceptions: List[str]
    missing_concepts: List[str]
    undefined_terms: List[str]
    mastered_concepts: List[str]
    knowledge_gap: Optional[str] = None
    recommended_strategy: LearningStrategy
    recommended_difficulty: int

class LearningDecision(BaseModel):
    next_mode: LearningMode
    strategy: LearningStrategy
    difficulty: int
    confidence: float
    reason: str
    active_concept: str
    should_offer_termination: bool
    should_restore_interrupted_question: bool

class AIResponse(BaseModel):
    content: str
    mode: LearningMode
    strategy: LearningStrategy
    difficulty: int
    confidence: float
    metadata: Dict[str, Any] = {}
