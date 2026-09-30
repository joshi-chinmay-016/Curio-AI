"""
Claim Extraction module for Answer Intelligence.
Deconstructs learner responses into discrete semantic assertions and claims.
"""
from typing import List
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import LearnerClaim


class ClaimExtractor:
    """Extracts structured learner claims from an answer attempt."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def extract(self, user_message: str, target_concept: str) -> List[LearnerClaim]:
        """Extract atomic claims made by the learner."""
        return self.provider.extract_claims(user_message, target_concept)
