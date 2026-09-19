"""
Curio AI Engine Package.
Public boundary for the AI reasoning layer.
"""
from backend.app.ai.engine import CurioEngine
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    Difficulty,
    InputType,
    LearningContext,
    LearningDecision,
    LearningMode,
    LearningStrategy,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    SourceMode,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
)

__all__ = [
    "CurioEngine",
    "AIContext",
    "AIResult",
    "AIResponse",
    "SessionState",
    "TurnEvaluation",
    "LearningDecision",
    "StateUpdates",
    "CurrentQuestion",
    "TeacherIntervention",
    "ChatMessage",
    "SessionInfo",
    "ConversationContext",
    "LearningContext",
    "Mode",
    "LearningMode",
    "Difficulty",
    "Strategy",
    "LearningStrategy",
    "InputType",
    "SourceMode",
    "Role",
]
