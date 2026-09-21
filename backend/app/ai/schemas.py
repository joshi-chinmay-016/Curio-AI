from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator


# =====================================================================
# ENUMS
# =====================================================================

class Mode(str, Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    EVALUATOR = "EVALUATOR"

# Backward compatibility alias
LearningMode = Mode


class Difficulty(IntEnum):
    FOUNDATION = 1
    MECHANISM = 2
    APPLICATION = 3
    EDGE_CASE = 4
    SYNTHESIS = 5


class Strategy(str, Enum):
    ASK_FOUNDATION = "ASK_FOUNDATION"
    PROBE_WHY = "PROBE_WHY"
    PROBE_HOW = "PROBE_HOW"
    CLARIFY_TERM = "CLARIFY_TERM"
    PROBE_MISSING_CONCEPT = "PROBE_MISSING_CONCEPT"
    CHALLENGE_MISCONCEPTION = "CHALLENGE_MISCONCEPTION"
    INCREASE_DIFFICULTY = "INCREASE_DIFFICULTY"
    TEACH_GAP = "TEACH_GAP"
    VERIFY_UNDERSTANDING = "VERIFY_UNDERSTANDING"
    RESTORE_INTERRUPTED_QUESTION = "RESTORE_INTERRUPTED_QUESTION"
    OFFER_TERMINATION = "OFFER_TERMINATION"
    GENERATE_REPORT = "GENERATE_REPORT"

# Backward compatibility alias
LearningStrategy = Strategy


class InputType(str, Enum):
    TEXT = "TEXT"
    VOICE = "VOICE"


class SourceMode(str, Enum):
    GENERAL = "GENERAL"
    DOCUMENT = "DOCUMENT"
    MIXED = "MIXED"


class Role(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


# =====================================================================
# CURRENT QUESTION & TEACHER INTERVENTION
# =====================================================================

class CurrentQuestion(BaseModel):
    id: str
    content: str
    concept: str
    difficulty: int = Field(ge=1, le=5)

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        return str(v)


class TeacherIntervention(BaseModel):
    active: bool = False
    gap: str = ""
    attempt_count: int = Field(default=0, ge=0)
    verification_required: bool = True


class ModeTransition(BaseModel):
    from_mode: Mode
    to_mode: Mode
    reason: str
    timestamp: str
    active_concept: Optional[str] = None


# =====================================================================
# SESSION STATE
# =====================================================================

class SessionState(BaseModel):
    session_id: str
    current_mode: Mode = Mode.STUDENT
    current_difficulty: int = Field(default=1, ge=1, le=5)
    understanding_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    active_concept: str = ""
    current_question: Optional[CurrentQuestion] = None
    interrupted_question: Optional[CurrentQuestion] = None
    consecutive_failures: int = Field(default=0, ge=0)
    consecutive_successes: int = Field(default=0, ge=0)
    teacher_attempt_count: int = Field(default=0, ge=0)
    recent_strategy_history: List[Strategy] = Field(default_factory=list)
    misconception_counts: Dict[str, int] = Field(default_factory=dict)
    concept_mastery: Dict[str, float] = Field(default_factory=dict)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    teacher_intervention: Optional[TeacherIntervention] = None
    mode_switch_history: List[ModeTransition] = Field(default_factory=list)

    @field_validator("session_id", mode="before")
    @classmethod
    def serialize_session_id(cls, v: Any) -> str:
        return str(v)

    @field_validator("concept_mastery")
    @classmethod
    def validate_concept_mastery(cls, v: Dict[str, float]) -> Dict[str, float]:
        for concept, score in v.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"Mastery score for '{concept}' must be between 0.0 and 1.0, got {score}")
        return v


# =====================================================================
# TURN EVALUATION
# =====================================================================

class TurnEvaluation(BaseModel):
    correctness: float = Field(ge=0.0, le=1.0)
    clarity: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    depth: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    stuck_probability: float = Field(ge=0.0, le=1.0)
    misconceptions: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    undefined_terms: List[str] = Field(default_factory=list)
    mastered_concepts: List[str] = Field(default_factory=list)
    knowledge_gap: Optional[str] = None
    recommended_strategy: Strategy
    recommended_difficulty: int = Field(ge=1, le=5)


# =====================================================================
# LEARNING DECISION
# =====================================================================

class LearningDecision(BaseModel):
    next_mode: Mode
    strategy: Strategy
    difficulty: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    active_concept: str
    should_offer_termination: bool = False
    should_restore_interrupted_question: bool = False


# =====================================================================
# AI RESPONSE
# =====================================================================

class AIResponse(BaseModel):
    content: str = Field(min_length=1)
    mode: Mode
    strategy: Strategy
    difficulty: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_single_question: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =====================================================================
# STATE UPDATES
# =====================================================================

class StateUpdates(BaseModel):
    active_concept: Optional[str] = None
    interrupted_question: Optional[CurrentQuestion] = None
    mastered_concepts: Optional[List[str]] = None
    unresolved_misconceptions: Optional[List[str]] = None
    teacher_intervention: Optional[TeacherIntervention] = None
    current_question: Optional[CurrentQuestion] = None
    current_mode: Optional[Mode] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    concept_mastery: Optional[Dict[str, float]] = None
    consecutive_failures: Optional[int] = Field(default=None, ge=0)
    consecutive_successes: Optional[int] = Field(default=None, ge=0)
    teacher_attempt_count: Optional[int] = Field(default=None, ge=0)
    recent_strategy_history: Optional[List[Strategy]] = None
    misconception_counts: Optional[Dict[str, int]] = None
    mode_switch_history: Optional[List[ModeTransition]] = None

    @field_validator("concept_mastery")
    @classmethod
    def validate_update_concept_mastery(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is not None:
            for concept, score in v.items():
                if not (0.0 <= score <= 1.0):
                    raise ValueError(f"Mastery score for '{concept}' must be between 0.0 and 1.0, got {score}")
        return v


# =====================================================================
# PHASE 3: EVALUATION & REPORT ENUMS
# =====================================================================

class MasteryLevel(str, Enum):
    BEGINNER = "BEGINNER"
    DEVELOPING = "DEVELOPING"
    PROFICIENT = "PROFICIENT"
    MASTERY = "MASTERY"


class GapStatus(str, Enum):
    DETECTED = "DETECTED"
    CHALLENGED = "CHALLENGED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class GapSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MisconceptionStatus(str, Enum):
    DETECTED = "DETECTED"
    CHALLENGED = "CHALLENGED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


# =====================================================================
# PHASE 3: SESSION EVIDENCE CONTRACTS
# =====================================================================

class TurnEvidence(BaseModel):
    turn_index: int = Field(ge=0)
    question: str
    learner_answer: str
    concept: str
    difficulty: int = Field(ge=1, le=5)
    evaluation: TurnEvaluation


class TeacherInterventionEvidence(BaseModel):
    intervention_index: int = Field(ge=0)
    gap: str
    attempt_count: int = Field(ge=1)
    teacher_explanation: str
    verification_question: str
    verification_answer: Optional[str] = None
    verification_passed: bool = False
    related_concept: str = ""


class ConceptEvidenceItem(BaseModel):
    concept: str
    turns_evaluated: List[int] = Field(default_factory=list)
    correctness_scores: List[float] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    teacher_assisted: bool = False
    highest_difficulty_passed: int = 0


class SessionEvidence(BaseModel):
    session_id: str
    topic: str
    turns: List[TurnEvidence] = Field(default_factory=list)
    teacher_interventions: List[TeacherInterventionEvidence] = Field(default_factory=list)
    concepts_encountered: List[str] = Field(default_factory=list)
    concept_evidence_map: Dict[str, ConceptEvidenceItem] = Field(default_factory=dict)
    difficulty_progression: List[int] = Field(default_factory=list)
    confidence_progression: List[float] = Field(default_factory=list)
    total_learner_turns: int = 0
    successful_turns: int = 0
    failed_turns: int = 0

    @field_validator("session_id", mode="before")
    @classmethod
    def serialize_session_id(cls, v: Any) -> str:
        return str(v)


# =====================================================================
# PHASE 3: CONCEPT ASSESSMENT & EVALUATION CONTRACTS
# =====================================================================

class ConceptAssessment(BaseModel):
    concept: str
    understanding_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    mastery_level: MasteryLevel
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    evidence_references: List[str] = Field(default_factory=list)


class GapAnalysisItem(BaseModel):
    gap: str
    concept: str = ""
    severity: GapSeverity = GapSeverity.MEDIUM
    status: GapStatus = GapStatus.UNRESOLVED
    evidence_references: List[str] = Field(default_factory=list)


class MisconceptionAnalysisItem(BaseModel):
    misconception: str
    concept: str = ""
    status: MisconceptionStatus = MisconceptionStatus.UNRESOLVED
    evidence_references: List[str] = Field(default_factory=list)


class RoadmapItem(BaseModel):
    priority: int = Field(ge=1)
    title: str
    description: str
    target_concept: str
    action_type: str = "PRACTICE"


class SessionEvaluation(BaseModel):
    session_id: str
    topic: str
    understanding_score: float = Field(ge=0.0, le=100.0)
    mastery_level: MasteryLevel
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    strengths: List[str] = Field(default_factory=list)
    knowledge_gaps: List[GapAnalysisItem] = Field(default_factory=list)
    misconceptions: List[MisconceptionAnalysisItem] = Field(default_factory=list)
    resolved_gaps: List[str] = Field(default_factory=list)
    unresolved_gaps: List[str] = Field(default_factory=list)
    resolved_misconceptions: List[str] = Field(default_factory=list)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    concept_assessments: List[ConceptAssessment] = Field(default_factory=list)
    difficulty_progression: List[int] = Field(default_factory=list)
    teacher_intervention_summary: Dict[str, Any] = Field(default_factory=dict)
    recommended_next_steps: List[RoadmapItem] = Field(default_factory=list)

    @field_validator("session_id", mode="before")
    @classmethod
    def serialize_session_id(cls, v: Any) -> str:
        return str(v)


class LearningReport(BaseModel):
    session_id: str
    topic: str
    understanding_score: float = Field(ge=0.0, le=100.0)
    mastery_level: MasteryLevel
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    strengths: List[str] = Field(default_factory=list)
    knowledge_gaps: List[str] = Field(default_factory=list)
    resolved_gaps: List[str] = Field(default_factory=list)
    unresolved_gaps: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    resolved_misconceptions: List[str] = Field(default_factory=list)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    concept_assessments: List[ConceptAssessment] = Field(default_factory=list)
    difficulty_achieved: int = Field(default=1, ge=1, le=5)
    teacher_interventions_required: int = Field(default=0, ge=0)
    recommended_next_steps: List[RoadmapItem] = Field(default_factory=list)
    created_at: Optional[str] = None

    @field_validator("session_id", mode="before")
    @classmethod
    def serialize_session_id(cls, v: Any) -> str:
        return str(v)


# =====================================================================
# AI RESULT
# =====================================================================

class AIResult(BaseModel):
    evaluation: TurnEvaluation
    decision: LearningDecision
    response: AIResponse
    state_updates: StateUpdates
    session_evaluation: Optional[SessionEvaluation] = None
    learning_report: Optional[LearningReport] = None


# =====================================================================
# CONVERSATION MESSAGE
# =====================================================================

class ChatMessage(BaseModel):
    role: Role = Role.USER
    content: str
    input_type: InputType = InputType.TEXT

    def __init__(self, **data: Any):
        # Support legacy 'sender' argument: sender="USER" | "AI"
        if "sender" in data and "role" not in data:
            sender = str(data.pop("sender")).upper()
            if sender == "AI":
                data["role"] = Role.ASSISTANT
            elif sender == "SYSTEM":
                data["role"] = Role.SYSTEM
            else:
                data["role"] = Role.USER
        super().__init__(**data)

    @property
    def sender(self) -> str:
        """Backward compatibility for legacy code expecting `message.sender`."""
        if self.role == Role.ASSISTANT:
            return "AI"
        return self.role.value


# =====================================================================
# AI CONTEXT
# =====================================================================

class SessionInfo(BaseModel):
    session_id: str
    topic: str
    source_mode: SourceMode = SourceMode.GENERAL

    @field_validator("session_id", mode="before")
    @classmethod
    def serialize_session_id(cls, v: Any) -> str:
        return str(v)


class ConversationContext(BaseModel):
    recent_messages: List[ChatMessage] = Field(default_factory=list)
    message_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def sync_message_count(cls, data: Any) -> Any:
        if isinstance(data, dict):
            messages = data.get("recent_messages", [])
            if "message_count" not in data or data["message_count"] == 0:
                data["message_count"] = len(messages)
        return data


class LearningContext(BaseModel):
    mastered_concepts: List[str] = Field(default_factory=list)
    unresolved_misconceptions: List[str] = Field(default_factory=list)
    recent_evaluations: List[TurnEvaluation] = Field(default_factory=list)
    teacher_intervention: Optional[TeacherIntervention] = None


class AIContext(BaseModel):
    session: SessionInfo
    current_state: SessionState
    conversation: ConversationContext
    learning_context: LearningContext = Field(default_factory=LearningContext)
    source_context: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def adapt_legacy_or_flat_inputs(cls, data: Any) -> Any:
        """
        Allows AIContext to be constructed either via nested sub-models:
            AIContext(session=..., current_state=..., conversation=..., learning_context=...)
        or via flat legacy parameters:
            AIContext(session_id=..., topic=..., current_mode=..., difficulty=..., active_concept=..., history=...)
        """
        if not isinstance(data, dict):
            return data

        # If already provided with nested structures, return as-is
        if "session" in data and "current_state" in data and "conversation" in data:
            return data

        # Adapt flat parameters
        session_id = str(data.get("session_id", "default_session"))
        topic = data.get("topic", "General Topic")
        source_mode = data.get("source_mode", SourceMode.GENERAL)

        session_info = SessionInfo(
            session_id=session_id,
            topic=topic,
            source_mode=source_mode
        )

        current_mode = data.get("current_mode", Mode.STUDENT)
        difficulty = data.get("difficulty", 1)
        active_concept = data.get("active_concept", "")

        curr_q = data.get("current_question")
        if isinstance(curr_q, str):
            curr_q = CurrentQuestion(id="curr_q", content=curr_q, concept=active_concept, difficulty=difficulty)

        interrupted_q = data.get("interrupted_question")
        if isinstance(interrupted_q, str):
            interrupted_q = CurrentQuestion(id="int_q", content=interrupted_q, concept=active_concept, difficulty=difficulty)

        current_state = SessionState(
            session_id=session_id,
            current_mode=current_mode,
            current_difficulty=difficulty,
            active_concept=active_concept,
            current_question=curr_q,
            interrupted_question=interrupted_q
        )

        raw_history = data.get("history", data.get("recent_messages", []))
        messages: List[ChatMessage] = []
        for item in raw_history:
            if isinstance(item, ChatMessage):
                messages.append(item)
            elif isinstance(item, dict):
                messages.append(ChatMessage(**item))
            elif hasattr(item, "sender") and hasattr(item, "content"):
                messages.append(ChatMessage(sender=item.sender, content=item.content))

        conversation = ConversationContext(
            recent_messages=messages,
            message_count=len(messages)
        )

        learning_context = data.get("learning_context", LearningContext())
        source_context = data.get("source_context", None)

        return {
            "session": session_info,
            "current_state": current_state,
            "conversation": conversation,
            "learning_context": learning_context,
            "source_context": source_context
        }

    # Backward compatibility accessors
    @property
    def session_id(self) -> str:
        return self.session.session_id

    @property
    def topic(self) -> str:
        return self.session.topic

    @property
    def current_mode(self) -> Mode:
        return self.current_state.current_mode

    @property
    def difficulty(self) -> int:
        return self.current_state.current_difficulty

    @property
    def active_concept(self) -> str:
        return self.current_state.active_concept

    @property
    def history(self) -> List[ChatMessage]:
        return self.conversation.recent_messages

    @property
    def current_question(self) -> Optional[CurrentQuestion]:
        return self.current_state.current_question

    @property
    def interrupted_question(self) -> Optional[CurrentQuestion]:
        return self.current_state.interrupted_question
