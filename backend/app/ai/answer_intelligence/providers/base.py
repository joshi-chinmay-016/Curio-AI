"""
Base Provider Interface for Answer Intelligence.
Enables pluggable assessment backends:
1. Local lightweight models (n-gram, embeddings, NLI)
2. Fine-tuned models
3. LLM structured generation fallback
4. Mock provider for deterministic regression testing
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode


class BaseAssessmentProvider(ABC):
    """Abstract provider for Answer Intelligence pipeline stages."""

    @abstractmethod
    def classify_intent(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float]:
        """Classify user intent with confidence."""
        pass

    @abstractmethod
    def assess_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        """
        Assess whether the response directly addresses the question and target concept.
        Returns (RelevanceLevel, relevance_score between 0.0 and 1.0).
        """
        pass

    @abstractmethod
    def extract_claims(
        self,
        user_message: str,
        target_concept: str,
    ) -> List[LearnerClaim]:
        """Extract atomic claims made by the learner."""
        pass

    @abstractmethod
    def align_concepts(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        """Calculate concept alignment score between 0.0 and 1.0."""
        pass

    @abstractmethod
    def match_evidence(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        """Compare learner claims against expected evidence items."""
        pass

    @abstractmethod
    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        """
        Assess correctness conditioned on the target concept and expected evidence.
        Returns (CorrectnessLevel, score between 0.0 and 1.0, list of contradictory claims).
        """
        pass

    @abstractmethod
    def assess_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        """
        Assess completeness against expected evidence components.
        Returns (CompletenessLevel, score between 0.0 and 1.0, list of missing concept strings).
        """
        pass

    @abstractmethod
    def detect_misconceptions(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[MisconceptionEvidence]:
        """Detect specific incorrect mental models."""
        pass

    @abstractmethod
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
        Determine confidence level and whether the assessment engine should ABSTAIN.
        Returns (AssessmentStatus, confidence between 0.0 and 1.0).
        """
        pass
