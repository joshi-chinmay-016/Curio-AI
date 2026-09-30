"""
Concept Alignment module for Answer Intelligence.
Maps extracted learner claims against the target Concept Model node and concept graph.
Distinguishes general factual correctness from target-concept relevance.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import LearnerClaim

if TYPE_CHECKING:
    from backend.app.ai.schemas import ConceptModel, ConceptNode


class ConceptAligner:
    """Calculates semantic alignment between learner claims and the target concept."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def align(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        """
        Returns concept alignment score between 0.0 and 1.0.
        """
        return self.provider.align_concepts(
            claims=claims,
            concept_node=concept_node,
            target_concept=target_concept,
            concept_model=concept_model,
        )
