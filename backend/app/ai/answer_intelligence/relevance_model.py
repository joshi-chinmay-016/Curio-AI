"""
Semantic Relevance Model module for Answer Intelligence.
Evaluates whether a learner's answer addresses the current question and target concept
BEFORE correctness is evaluated.
Prevents false mastery on technically true but irrelevant statements or complete non-sequiturs.
"""
from typing import Optional, Tuple
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    ExpectedEvidence,
    RelevanceLevel,
)


class SemanticRelevanceModel:
    """Evaluates semantic relevance of learner's response to the active question and concept."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def evaluate_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        """
        Assesses relevance level and score (0.0 to 1.0).
        """
        return self.provider.assess_relevance(
            user_message=user_message,
            question=question,
            target_concept=target_concept,
            topic=topic,
            expected=expected,
        )
