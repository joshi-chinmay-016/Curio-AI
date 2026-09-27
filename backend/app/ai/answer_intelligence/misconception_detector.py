"""
Misconception Detector module for Answer Intelligence.
Distinguishes lack of knowledge from specific, erroneous mental models.
"""
from typing import List
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    ExpectedEvidence,
    LearnerClaim,
    MisconceptionEvidence,
    RelevanceLevel,
)


class MisconceptionDetector:
    """Detects and diagnoses specific conceptual misconceptions."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def detect(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
        relevance_level: RelevanceLevel,
    ) -> List[MisconceptionEvidence]:
        """
        Detects misconceptions. If the statement is entirely irrelevant,
        it does not count as a target concept misconception.
        """
        if relevance_level == RelevanceLevel.IRRELEVANT:
            return []

        return self.provider.detect_misconceptions(
            user_message=user_message,
            claims=claims,
            expected=expected,
        )
