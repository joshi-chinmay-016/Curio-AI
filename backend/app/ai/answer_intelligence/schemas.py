"""
Answer Intelligence and Learning Assessment Schemas for Curio AI.
Defines strongly typed, provenance-preserving contracts for learner response understanding.
Separates linguistic evaluation from pedagogical state updates and decision making.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssessmentIntent(str, Enum):
    ANSWER_ATTEMPT = "ANSWER_ATTEMPT"
    HELP_REQUEST = "HELP_REQUEST"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    QUESTION_ABOUT_CONCEPT = "QUESTION_ABOUT_CONCEPT"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    READY_TO_CONTINUE = "READY_TO_CONTINUE"
    OFF_TOPIC = "OFF_TOPIC"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    UNCERTAIN = "UNCERTAIN"


class RelevanceLevel(str, Enum):
    RELEVANT = "RELEVANT"
    PARTIALLY_RELEVANT = "PARTIALLY_RELEVANT"
    IRRELEVANT = "IRRELEVANT"
    CONTRADICTORY = "CONTRADICTORY"
    UNCERTAIN = "UNCERTAIN"


class ClaimType(str, Enum):
    DEFINITION = "DEFINITION"
    MECHANISM = "MECHANISM"
    FACTUAL_ASSERTION = "FACTUAL_ASSERTION"
    EXAMPLE = "EXAMPLE"
    ANALOGY = "ANALOGY"
    COUNTER_CLAIM = "COUNTER_CLAIM"
    IRRELEVANT_STATEMENT = "IRRELEVANT_STATEMENT"
    META_COMMENT = "META_COMMENT"


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class LearnerClaim(BaseModel):
    """Structured atomic claim extracted from the learner's response."""
    text: str = Field(description="The exact or paraphrased claim made by the learner.")
    concept_id: Optional[str] = Field(default=None, description="Target concept ID if aligned, else None.")
    claim_type: ClaimType = Field(default=ClaimType.FACTUAL_ASSERTION)
    alignment_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Semantic alignment with target concept.")
    is_factually_sound: Optional[bool] = Field(default=None, description="General factual soundness if assessable.")
    support_status: EvidenceStatus = Field(default=EvidenceStatus.UNKNOWN, description="Claim-level support status against expected evidence.")
    contradiction_status: bool = Field(default=False, description="Whether claim contradicts another claim or expected evidence.")
    contradicts_claim: Optional[str] = Field(default=None, description="Text of the component or claim contradicted.")
    misconception_labels: List[str] = Field(default_factory=list, description="Any detected misconception anti-patterns.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this claim-level evaluation.")
    assessment_rationale: Optional[str] = Field(default=None, description="Short rationale for the claim assessment.")


class EvidenceItem(BaseModel):
    """Comparison of learner claims against expected pedagogical evidence."""
    concept_id: str
    expected_description: str
    status: EvidenceStatus = EvidenceStatus.UNKNOWN
    supported_by_claim: Optional[str] = None
    contradicted_by_claim: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExpectedEvidence(BaseModel):
    """Dynamically generated expected evidence for a target concept and objective."""
    concept_id: str
    objective_type: str
    core_components: List[str] = Field(default_factory=list)
    common_misconceptions: List[str] = Field(default_factory=list)
    contrast_concepts: List[str] = Field(default_factory=list)


class CorrectnessLevel(str, Enum):
    CORRECT = "CORRECT"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    INCORRECT = "INCORRECT"
    INCOMPLETE = "INCOMPLETE"
    MISCONCEPTION = "MISCONCEPTION"
    IRRELEVANT = "IRRELEVANT"
    CONTRADICTORY = "CONTRADICTORY"
    AMBIGUOUS = "AMBIGUOUS"
    UNASSESSABLE = "UNASSESSABLE"


class CompletenessLevel(str, Enum):
    COMPLETE = "COMPLETE"
    SUBSTANTIAL = "SUBSTANTIAL"
    PARTIAL = "PARTIAL"
    MINIMAL = "MINIMAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MisconceptionEvidence(BaseModel):
    """Specific diagnosed misconception with evidence provenance."""
    concept_id: str
    description: str
    learner_statement: str
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    counter_evidence: Optional[str] = None


class AssessmentStatus(str, Enum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ABSTAIN = "ABSTAIN"


class AssessmentClassification(str, Enum):
    CORRECT = "CORRECT"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    INCORRECT = "INCORRECT"
    MISCONCEPTION = "MISCONCEPTION"
    IRRELEVANT = "IRRELEVANT"
    OFF_TOPIC = "OFF_TOPIC"
    CONTRADICTORY = "CONTRADICTORY"
    AMBIGUOUS = "AMBIGUOUS"
    HELP_REQUEST = "HELP_REQUEST"
    CLARIFICATION = "CLARIFICATION"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    UNASSESSABLE = "UNASSESSABLE"


class MasteryDecision(BaseModel):
    """Deterministic output of the MasteryGate for LearnerModel synchronization."""
    supports_mastery: bool
    mastery_delta_allowed: bool
    allowed_delta: float = 0.0
    evidence_count_increment: int = 0
    record_as_gap: bool = False
    record_as_misconception: bool = False
    concept_id: str
    reason: str


class LearningAssessment(BaseModel):
    """
    Primary contract for Answer Intelligence.
    Contains complete structured provenance of what the learner communicated,
    its relevance, alignment, correctness, evidence, and pedagogical implications.
    Does NOT contain private chain-of-thought.
    """
    intent: AssessmentIntent
    is_answer_attempt: bool
    relevance_score: float = Field(ge=0.0, le=1.0)
    relevance_level: RelevanceLevel = RelevanceLevel.RELEVANT
    concept_alignment_score: float = Field(ge=0.0, le=1.0)
    claims: List[LearnerClaim] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    correctness: CorrectnessLevel
    correctness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness: CompletenessLevel
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    misconception_status: bool = False
    misconceptions: List[MisconceptionEvidence] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    contradictory_claims: List[str] = Field(default_factory=list)
    classification: AssessmentClassification
    confidence: float = Field(ge=0.0, le=1.0)
    supports_mastery: bool = False
    assessment_status: AssessmentStatus = AssessmentStatus.HIGH_CONFIDENCE
    recommended_learning_action: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
