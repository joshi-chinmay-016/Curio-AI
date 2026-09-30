"""
Concept-Conditioned Correctness and Completeness Model for Answer Intelligence.
Evaluates correctness conditioned on the target concept and expected evidence,
never merely on general factual truth in the abstract.
"""
from typing import List, Tuple
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    ExpectedEvidence,
    LearnerClaim,
    RelevanceLevel,
)


class CorrectnessModel:
    """Evaluates target-concept correctness and completeness."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def evaluate_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
        relevance_level: RelevanceLevel,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        """
        Evaluates correctness.
        If relevance is IRRELEVANT, short-circuits to UNASSESSABLE / IRRELEVANT with 0.0 score.
        """
        if relevance_level == RelevanceLevel.IRRELEVANT:
            return CorrectnessLevel.UNASSESSABLE, 0.0, []

        return self.provider.assess_correctness(
            claims=claims,
            evidence_items=evidence_items,
            expected=expected,
        )

    def evaluate_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
        relevance_level: RelevanceLevel,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        """
        Evaluates completeness against expected core components.
        """
        if relevance_level == RelevanceLevel.IRRELEVANT:
            return CompletenessLevel.NOT_APPLICABLE, 0.0, []

        return self.provider.assess_completeness(
            evidence_items=evidence_items,
            expected=expected,
        )
