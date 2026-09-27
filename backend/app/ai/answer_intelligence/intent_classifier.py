"""
Intent Classifier module for Answer Intelligence.
Distinguishes answer attempts, help requests, clarifications, conceptual questions,
acknowledgements, readiness signals, off-topic statements, and empty responses.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import AssessmentIntent

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext


class IntentClassifier:
    """Classifies the communicative intent of a learner's turn."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def classify(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float, bool]:
        """
        Returns (intent, confidence, is_answer_attempt).
        """
        intent, conf = self.provider.classify_intent(
            user_message=user_message,
            context=context,
            current_question=current_question,
        )

        is_answer = (intent == AssessmentIntent.ANSWER_ATTEMPT)
        return intent, conf, is_answer
