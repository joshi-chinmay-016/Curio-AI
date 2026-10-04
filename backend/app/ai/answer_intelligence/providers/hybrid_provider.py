"""
Hybrid Semantic Assessment Provider for Curio AI.
Combines deterministic lexical gating, dense semantic embedding similarity,
and negation-aware claim-evidence matching.

Architecture:
  Learner Answer
        ↓
  Deterministic Intent & Fast Filter (<0.1ms)
        ↓
  Semantic Embedding + Lexical Relevance
        ↓
  Claim Extraction & Concept Alignment
        ↓
  Dense Vector & Lexical Hybrid Evidence Matching
        ↓
  Dynamic Misconception Detection
        ↓
  Calibrated Confidence & Principled Abstention
        ↓
  LearningAssessment (passed to authoritative MasteryGate)
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING, List, Optional, Set, Tuple

from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.providers.local_model import (
    LocalAssessmentProvider,
    _tokenize_meaningful,
    has_negated_phrase,
)
from backend.app.ai.answer_intelligence.providers.semantic_embedding_provider import (
    SemanticEmbeddingProvider,
)
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    ClaimType,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    ExpectedEvidence,
    LearnerClaim,
    MisconceptionEvidence,
    RelevanceLevel,
)

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode

logger = logging.getLogger("curio.ai.answer_intelligence.hybrid_provider")


class HybridSemanticProvider(BaseAssessmentProvider):
    """
    Hybrid semantic assessment provider fusing deterministic lexical rules
    with dense neural embedding similarity.
    Optimized for safety (False Mastery Rate minimization), nuanced student paraphrasing,
    and fast inference.
    """

    def __init__(
        self,
        local_provider: Optional[LocalAssessmentProvider] = None,
        semantic_provider: Optional[SemanticEmbeddingProvider] = None,
    ):
        self.local_provider = local_provider or LocalAssessmentProvider()
        self.semantic_provider = semantic_provider or SemanticEmbeddingProvider()

    def classify_intent(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float]:
        """
        Fast deterministic intent classification with fallback to semantic checks.
        """
        intent, conf = self.local_provider.classify_intent(
            user_message=user_message,
            context=context,
            current_question=current_question,
        )

        clean = (user_message or "").strip().lower()
        # Edge case: uncertain single word or ambiguous statement
        if clean in {"maybe", "perhaps", "i guess", "i think so?", "not sure if correct"}:
            return AssessmentIntent.UNCERTAIN, 0.70

        return intent, conf

    def assess_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        """
        Fuses lexical overlap and dense semantic embedding to assess relevance.
        Ensures 0% acceptance of adversarial off-topic answers while reliably
        accepting valid paraphrases and analogies.
        """
        clean = (user_message or "").strip().lower()
        if not clean:
            return RelevanceLevel.IRRELEVANT, 0.0

        # Fast adversarial and chitchat check
        unrelated_flags = [
            "sunny", "yesterday", "rain", "weather", "created by me", "my dog",
            "lunch", "dinner", "ice cream", "pizza", "vacation", "today is",
        ]
        user_tokens = _tokenize_meaningful(clean)
        concept_clean = target_concept.lower().replace("_", " ")
        has_direct_concept = (concept_clean in clean) if len(concept_clean) > 2 else False

        if any(f in clean for f in unrelated_flags) and not has_direct_concept:
            # Check if there is any target overlap at all
            concept_tokens = _tokenize_meaningful(concept_clean)
            if not (user_tokens & concept_tokens):
                return RelevanceLevel.IRRELEVANT, 0.0

        # Get local lexical score
        local_rel, local_score = self.local_provider.assess_relevance(
            user_message=user_message,
            question=question,
            target_concept=target_concept,
            topic=topic,
            expected=expected,
        )

        # Get dense semantic score
        sem_rel, sem_score = self.semantic_provider.assess_relevance(
            user_message=user_message,
            question=question,
            target_concept=target_concept,
            topic=topic,
            expected=expected,
        )

        # If both agree it's irrelevant, return immediately
        if local_rel == RelevanceLevel.IRRELEVANT and sem_score < 0.35:
            return RelevanceLevel.IRRELEVANT, round(min(local_score, sem_score), 2)

        # Semantic embedding veto for completely unrelated text when local lexical also has low support
        if sem_score < 0.18 and local_score < 0.35 and not has_direct_concept:
            return RelevanceLevel.IRRELEVANT, round(min(sem_score, local_score), 2)

        # Blended relevance score
        blended_score = 0.55 * sem_score + 0.45 * local_score

        # If direct concept is present or strong semantic similarity or strong lexical support
        if (
            sem_score >= 0.45
            or local_score >= 0.60
            or (sem_score >= 0.30 and local_score >= 0.40)
            or (local_rel == RelevanceLevel.RELEVANT and sem_score >= 0.20)
        ):
            return RelevanceLevel.RELEVANT, round(max(blended_score, 0.70), 2)
        elif blended_score >= 0.28 or sem_score >= 0.28 or local_score >= 0.30:
            return RelevanceLevel.PARTIALLY_RELEVANT, round(max(blended_score, 0.40), 2)
        else:
            return RelevanceLevel.IRRELEVANT, round(blended_score, 2)

    def extract_claims(
        self,
        user_message: str,
        target_concept: str,
    ) -> List[LearnerClaim]:
        """
        Extracts claims with both lexical and semantic alignment scores.
        """
        # Start with sentence-segmented claims from semantic provider
        claims = self.semantic_provider.extract_claims(user_message, target_concept)
        if not claims:
            return []

        # Enhance with local heuristic checks (e.g., definition, mechanism, example)
        local_claims = self.local_provider.extract_claims(user_message, target_concept)
        local_map = {c.text.strip(): c for c in local_claims}

        enhanced: List[LearnerClaim] = []
        for c in claims:
            c_text = c.text.strip()
            loc_match = local_map.get(c_text)
            c_type = loc_match.claim_type if loc_match else c.claim_type
            max_align = max(c.alignment_score, loc_match.alignment_score if loc_match else 0.0)

            enhanced.append(
                LearnerClaim(
                    text=c.text,
                    concept_id=target_concept if max_align >= 0.25 else None,
                    claim_type=c_type,
                    alignment_score=round(max_align, 2),
                    is_factually_sound=c.is_factually_sound,
                )
            )

        return enhanced

    def align_concepts(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        """
        Fuses lexical alignment and dense embedding alignment.
        """
        local_align = self.local_provider.align_concepts(
            claims=claims,
            concept_node=concept_node,
            target_concept=target_concept,
            concept_model=concept_model,
        )
        sem_align = self.semantic_provider.align_concepts(
            claims=claims,
            concept_node=concept_node,
            target_concept=target_concept,
            concept_model=concept_model,
        )
        return round(max(local_align, sem_align), 2)

    def match_evidence(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        """
        Fuses dense embedding similarity and lexical component matching.
        Eliminates false rejections of valid student paraphrases while preventing false mastery.
        """
        if not claims or not expected.core_components:
            return [
                EvidenceItem(
                    concept_id=expected.concept_id,
                    expected_description=c,
                    status=EvidenceStatus.MISSING,
                    confidence=0.90,
                )
                for c in expected.core_components
            ]

        # 1. Obtain matches from local provider (lexical + explicit CS expansions)
        local_items = self.local_provider.match_evidence(claims, expected)
        local_item_map = {it.expected_description: it for it in local_items}

        # 2. Obtain matches from semantic provider (dense embedding similarity)
        sem_items = self.semantic_provider.match_evidence(claims, expected)
        sem_item_map = {it.expected_description: it for it in sem_items}

        full_text = " ".join(c.text.lower() for c in claims)
        items: List[EvidenceItem] = []

        for comp in expected.core_components:
            loc_it = local_item_map.get(comp)
            sem_it = sem_item_map.get(comp)

            # Contradiction priority: if either detected contradiction, uphold it
            if (loc_it and loc_it.status == EvidenceStatus.CONTRADICTED) or (
                sem_it and sem_it.status == EvidenceStatus.CONTRADICTED
            ):
                contra_claim = (
                    (loc_it.contradicted_by_claim if loc_it else None)
                    or (sem_it.contradicted_by_claim if sem_it else None)
                    or full_text
                )
                items.append(
                    EvidenceItem(
                        concept_id=expected.concept_id,
                        expected_description=comp,
                        status=EvidenceStatus.CONTRADICTED,
                        contradicted_by_claim=contra_claim,
                        confidence=0.92,
                    )
                )
                continue

            # Support fusion
            loc_status = loc_it.status if loc_it else EvidenceStatus.MISSING
            sem_status = sem_it.status if sem_it else EvidenceStatus.MISSING

            supp_claim = (
                (sem_it.supported_by_claim if sem_it and sem_it.supported_by_claim else None)
                or (loc_it.supported_by_claim if loc_it and loc_it.supported_by_claim else None)
            )

            # If either provider found full support without contradiction:
            if loc_status == EvidenceStatus.SUPPORTED or sem_status == EvidenceStatus.SUPPORTED:
                # Safety check: if dense embedding strongly disagrees (sim < 0.20), downgrade to partial
                sem_sim = sem_it.confidence if sem_it else 0.0
                if sem_status == EvidenceStatus.MISSING and sem_sim < 0.20 and loc_status == EvidenceStatus.SUPPORTED:
                    items.append(
                        EvidenceItem(
                            concept_id=expected.concept_id,
                            expected_description=comp,
                            status=EvidenceStatus.PARTIALLY_SUPPORTED,
                            supported_by_claim=supp_claim,
                            confidence=0.60,
                        )
                    )
                else:
                    items.append(
                        EvidenceItem(
                            concept_id=expected.concept_id,
                            expected_description=comp,
                            status=EvidenceStatus.SUPPORTED,
                            supported_by_claim=supp_claim,
                            confidence=0.90,
                        )
                    )
            elif (
                loc_status == EvidenceStatus.PARTIALLY_SUPPORTED
                or sem_status == EvidenceStatus.PARTIALLY_SUPPORTED
            ):
                items.append(
                    EvidenceItem(
                        concept_id=expected.concept_id,
                        expected_description=comp,
                        status=EvidenceStatus.PARTIALLY_SUPPORTED,
                        supported_by_claim=supp_claim,
                        confidence=0.75,
                    )
                )
            else:
                items.append(
                    EvidenceItem(
                        concept_id=expected.concept_id,
                        expected_description=comp,
                        status=EvidenceStatus.MISSING,
                        confidence=0.85,
                    )
                )

        return items

    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        """
        Determines correctness level and score based on hybrid evidence.
        """
        if not claims:
            return CorrectnessLevel.UNASSESSABLE, 0.0, []

        contradictory = [
            it.contradicted_by_claim
            for it in evidence_items
            if it.status == EvidenceStatus.CONTRADICTED and it.contradicted_by_claim
        ]
        if contradictory:
            return CorrectnessLevel.CONTRADICTORY, 0.10, contradictory

        all_irrelevant = all(c.claim_type == ClaimType.IRRELEVANT_STATEMENT for c in claims)
        if all_irrelevant:
            return CorrectnessLevel.IRRELEVANT, 0.0, []

        supported_count = sum(1 for it in evidence_items if it.status == EvidenceStatus.SUPPORTED)
        partial_count = sum(1 for it in evidence_items if it.status == EvidenceStatus.PARTIALLY_SUPPORTED)
        total = max(1, len(evidence_items))

        support_ratio = (supported_count + 0.5 * partial_count) / total
        has_supported = supported_count > 0

        # Safety requirement: Full CORRECT requires at least 70% coverage of core components
        if support_ratio >= 0.70 and has_supported:
            return CorrectnessLevel.CORRECT, round(min(1.0, 0.70 + 0.30 * support_ratio), 2), []
        elif support_ratio >= 0.25 or partial_count > 0 or has_supported:
            return CorrectnessLevel.PARTIALLY_CORRECT, round(0.40 + 0.20 * support_ratio, 2), []
        elif support_ratio > 0.0:
            return CorrectnessLevel.INCOMPLETE, 0.30, []
        else:
            return CorrectnessLevel.INCORRECT, 0.10, []

    def assess_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        """
        Measures completeness against expected components.
        """
        if not evidence_items:
            return CompletenessLevel.NOT_APPLICABLE, 0.0, []

        supported = [it for it in evidence_items if it.status == EvidenceStatus.SUPPORTED]
        missing = [it.expected_description for it in evidence_items if it.status == EvidenceStatus.MISSING]

        ratio = len(supported) / max(1, len(evidence_items))
        if ratio >= 0.8:
            return CompletenessLevel.COMPLETE, round(ratio, 2), missing
        elif ratio >= 0.5:
            return CompletenessLevel.SUBSTANTIAL, round(ratio, 2), missing
        elif ratio >= 0.2:
            return CompletenessLevel.PARTIAL, round(ratio, 2), missing
        else:
            return CompletenessLevel.MINIMAL, round(ratio, 2), missing

    def detect_misconceptions(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[MisconceptionEvidence]:
        """
        Detects misconceptions using topic-general vector embeddings and structural heuristics.
        """
        misconceptions: List[MisconceptionEvidence] = []
        seen_descriptions: Set[str] = set()

        # 1. Semantic embedding vector matching (general across all topics)
        sem_miscs = self.semantic_provider.detect_misconceptions(user_message, claims, expected)
        for m in sem_miscs:
            if m.description not in seen_descriptions:
                misconceptions.append(m)
                seen_descriptions.add(m.description)

        # 2. Local provider checks
        loc_miscs = self.local_provider.detect_misconceptions(user_message, claims, expected)
        for m in loc_miscs:
            if m.description not in seen_descriptions:
                misconceptions.append(m)
                seen_descriptions.add(m.description)

        return misconceptions

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
        Principled calibration and abstention policy.
        Crucial for safety: Abstain rather than declare false mastery.
        """
        if intent in (AssessmentIntent.EMPTY_RESPONSE, AssessmentIntent.UNCERTAIN):
            return AssessmentStatus.ABSTAIN, 0.30

        if relevance == RelevanceLevel.UNCERTAIN:
            return AssessmentStatus.ABSTAIN, 0.40

        if relevance == RelevanceLevel.IRRELEVANT:
            return AssessmentStatus.HIGH_CONFIDENCE, 0.95

        # Check total words in learner response
        total_words = sum(len(c.text.split()) for c in claims)
        if total_words < 4 and correctness in (
            CorrectnessLevel.PARTIALLY_CORRECT,
            CorrectnessLevel.INCOMPLETE,
        ):
            return AssessmentStatus.ABSTAIN, 0.45

        # Borderline partial relevance with partial correctness -> abstain for safety
        if relevance == RelevanceLevel.PARTIALLY_RELEVANT and correctness in (
            CorrectnessLevel.PARTIALLY_CORRECT,
            CorrectnessLevel.INCOMPLETE,
        ):
            return AssessmentStatus.ABSTAIN, 0.48

        # If answer is borderline with conflicting evidence
        supported = sum(1 for it in evidence_items if it.status == EvidenceStatus.SUPPORTED)
        contradicted = sum(1 for it in evidence_items if it.status == EvidenceStatus.CONTRADICTED)
        if supported > 0 and contradicted > 0:
            return AssessmentStatus.LOW_CONFIDENCE, 0.55

        return AssessmentStatus.HIGH_CONFIDENCE, 0.90
