"""
Answer Intelligence and Learning Assessment layer for Curio AI.
Provides decoupled, evidence-grounded learner-response understanding.
"""
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.claim_extractor import ClaimExtractor
from backend.app.ai.answer_intelligence.concept_aligner import ConceptAligner
from backend.app.ai.answer_intelligence.confidence import ConfidenceEngine
from backend.app.ai.answer_intelligence.correctness_model import CorrectnessModel
from backend.app.ai.answer_intelligence.evidence_extractor import EvidenceExtractor
from backend.app.ai.answer_intelligence.intent_classifier import IntentClassifier
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.misconception_detector import MisconceptionDetector
from backend.app.ai.answer_intelligence.relevance_model import SemanticRelevanceModel
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    ClaimType,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    ExpectedEvidence,
    LearnerClaim,
    LearningAssessment,
    MasteryDecision,
    MisconceptionEvidence,
    RelevanceLevel,
)

__all__ = [
    "AssessmentAggregator",
    "AssessmentClassification",
    "AssessmentIntent",
    "AssessmentStatus",
    "ClaimExtractor",
    "ClaimType",
    "CompletenessLevel",
    "ConceptAligner",
    "ConfidenceEngine",
    "CorrectnessLevel",
    "CorrectnessModel",
    "EvidenceExtractor",
    "EvidenceItem",
    "EvidenceStatus",
    "ExpectedEvidence",
    "IntentClassifier",
    "LearnerClaim",
    "LearningAssessment",
    "MasteryDecision",
    "MasteryGate",
    "MisconceptionDetector",
    "MisconceptionEvidence",
    "RelevanceLevel",
    "SemanticRelevanceModel",
]
