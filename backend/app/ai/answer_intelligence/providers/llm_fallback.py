"""
LLM Fallback Assessment Provider for Curio AI.
Executes deep prompt-based structured analysis using configured LLM providers,
falling back defensively to LocalAssessmentProvider upon exceptions or invalid responses.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.ai.answer_intelligence.prompts.assessment_prompts import (
    build_claims_and_evidence_prompt,
    build_relevance_assessment_prompt,
)
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.providers.local_model import LocalAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
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
from backend.app.ai.providers.base import BaseAIProvider

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode

logger = logging.getLogger("curio.ai.answer_intelligence.llm_provider")


class LLMRelevanceResponse(BaseModel):
    relevance_level: RelevanceLevel
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class LLMClaimsEvidenceResponse(BaseModel):
    claims: List[LearnerClaim] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    misconceptions: List[MisconceptionEvidence] = Field(default_factory=list)
    contradictory_claims: List[str] = Field(default_factory=list)


class LLMAssessmentProvider(BaseAssessmentProvider):
    """
    LLM-powered assessment provider.
    Combines local heuristic guards for fast intent/safety routing
    with structured LLM analysis for nuance.
    """

    def __init__(self, llm_provider: BaseAIProvider):
        self.llm = llm_provider
        self._local = LocalAssessmentProvider()

    def classify_intent(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float]:
        # Fast deterministic classification for clear signals
        return self._local.classify_intent(user_message, context, current_question)

    def assess_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        # Check local heuristic first: if clear irrelevant / off-topic, don't waste LLM tokens
        local_rel, local_score = self._local.assess_relevance(
            user_message, question, target_concept, topic, expected
        )
        if local_rel == RelevanceLevel.IRRELEVANT and local_score <= 0.10:
            return local_rel, local_score

        prompt = build_relevance_assessment_prompt(
            user_message=user_message,
            question=question,
            target_concept=target_concept,
            topic=topic,
            expected_evidence=expected,
        )

        try:
            res: LLMRelevanceResponse = self.llm.generate_structured(prompt, LLMRelevanceResponse)
            return res.relevance_level, res.relevance_score
        except Exception as e:
            logger.warning("LLM relevance assessment failed (%s); using local heuristic.", e)
            return local_rel, local_score

    def extract_claims(
        self,
        user_message: str,
        target_concept: str,
    ) -> List[LearnerClaim]:
        return self._local.extract_claims(user_message, target_concept)

    def align_concepts(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        return self._local.align_concepts(claims, concept_node, target_concept, concept_model)

    def match_evidence(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        return self._local.match_evidence(claims, expected)

    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        return self._local.assess_correctness(claims, evidence_items, expected)

    def assess_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        return self._local.assess_completeness(evidence_items, expected)

    def detect_misconceptions(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[MisconceptionEvidence]:
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
        return self._local.assess_confidence(intent, relevance, relevance_score, correctness, claims, evidence_items)
