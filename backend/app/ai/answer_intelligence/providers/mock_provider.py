"""
Mock Assessment Provider for deterministic testing and calibration.
Allows pre-programmed assessment results or falls back to local heuristic behavior.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.providers.local_model import LocalAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    ClaimType,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    ExpectedEvidence,
    LearnerClaim,
    MisconceptionEvidence,
    RelevanceLevel,
)

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode


class MockAssessmentProvider(BaseAssessmentProvider):
    """
    Mock assessment provider for unit and regression testing.
    Can be configured with specific test fixtures or use LocalAssessmentProvider heuristics.
    """

    def __init__(self, override_map: Optional[Dict[str, Any]] = None):
        self._local = LocalAssessmentProvider()
        self.override_map = override_map or {}

    def classify_intent(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float]:
        if "intent" in self.override_map:
            return self.override_map["intent"], 1.0
        return self._local.classify_intent(user_message, context, current_question)

    def assess_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        if "relevance" in self.override_map:
            return self.override_map["relevance"], self.override_map.get("relevance_score", 1.0)
        return self._local.assess_relevance(user_message, question, target_concept, topic, expected)

    def extract_claims(
        self,
        user_message: str,
        target_concept: str,
    ) -> List[LearnerClaim]:
        if "claims" in self.override_map:
            return self.override_map["claims"]
        return self._local.extract_claims(user_message, target_concept)

    def align_concepts(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        if "alignment_score" in self.override_map:
            return self.override_map["alignment_score"]
        return self._local.align_concepts(claims, concept_node, target_concept, concept_model)

    def match_evidence(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        if "evidence" in self.override_map:
            return self.override_map["evidence"]
        return self._local.match_evidence(claims, expected)

    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        if "correctness" in self.override_map:
            return (
                self.override_map["correctness"],
                self.override_map.get("correctness_score", 0.9),
                self.override_map.get("contradictory_claims", []),
            )
        return self._local.assess_correctness(claims, evidence_items, expected)

    def assess_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        if "completeness" in self.override_map:
            return (
                self.override_map["completeness"],
                self.override_map.get("completeness_score", 1.0),
                self.override_map.get("missing_concepts", []),
            )
        return self._local.assess_completeness(evidence_items, expected)

    def detect_misconceptions(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[MisconceptionEvidence]:
        if "misconceptions" in self.override_map:
            return self.override_map["misconceptions"]
        return self._local.detect_misconceptions(user_message, claims, expected)

    def assess_confidence(
        self,
        intent: AssessmentIntent,
        relevance: RelevanceLevel,
        relevance_score: float,
        correctness: CorrectnessLevel,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
    ) -> Tuple[AssessmentStatus, float]:
        if "assessment_status" in self.override_map:
            return self.override_map["assessment_status"], self.override_map.get("confidence", 0.95)
        return self._local.assess_confidence(intent, relevance, relevance_score, correctness, claims, evidence_items)
