"""
Confidence and Abstention Engine for Answer Intelligence.
Calibrates assessment confidence and enforces principled abstention
when answers are ambiguous, incoherent, or provide insufficient signal.
"""
from typing import List, Tuple
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentIntent,
    AssessmentStatus,
    CorrectnessLevel,
    EvidenceItem,
    LearnerClaim,
    RelevanceLevel,
)


class ConfidenceEngine:
    """Computes assessment confidence and determines when to abstain."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def assess_confidence(
        self,
        intent: AssessmentIntent,
        relevance: RelevanceLevel,
        relevance_score: float,
        correctness: CorrectnessLevel,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
    ) -> Tuple[AssessmentStatus, float]:
        """
        Returns (AssessmentStatus, confidence score between 0.0 and 1.0).
        """
        return self.provider.assess_confidence(
            intent=intent,
            relevance=relevance,
            relevance_score=relevance_score,
            correctness=correctness,
            claims=claims,
            evidence_items=evidence_items,
        )
