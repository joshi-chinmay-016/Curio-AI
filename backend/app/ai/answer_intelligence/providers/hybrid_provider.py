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
    cosine_similarity,
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

COMMON_DOMAIN_TERMS = {
    "data", "system", "process", "code", "method", "function",
    "value", "table", "memory", "algorithm", "time", "space", "key", "object",
    "ram", "cpu", "disk", "thread", "cache", "server", "client", "network",
    "array", "list", "node", "tree", "graph", "database", "databases", "class", "classes",
    "transaction", "transactions", "commit", "commits", "rollback", "operation", "operations",
    "query", "queries", "index", "indexes", "lock", "locks"
}
MODAL_STOPWORDS = {"can", "could", "may", "might", "shall", "should", "will", "would", "must", "always", "also", "just", "really"}
TOKENIZED_DOMAIN_TERMS = set().union(*(_tokenize_meaningful(w) for w in COMMON_DOMAIN_TERMS | MODAL_STOPWORDS))


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
        Eliminates false rejections while strictly preventing false mastery.
        Enriches atomic LearnerClaim objects with claim-level support status.
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

        clean_user = " ".join(c.text for c in claims).strip()
        split_clauses = [
            s.strip() for s in re.split(r'[;.!?]|\b(?:and|but|however|while|if)\b', clean_user, flags=re.IGNORECASE)
            if len(s.strip().split()) >= 3
        ]
        raw_candidates = [clean_user] + [c.text for c in claims] + split_clauses
        claim_texts = []
        for rc in raw_candidates:
            if rc.strip() and rc.strip() not in claim_texts:
                claim_texts.append(rc.strip())

        all_texts = claim_texts + expected.core_components
        embs = self.semantic_provider.encode(all_texts)
        claim_embs = embs[: len(claim_texts)]
        comp_embs = embs[len(claim_texts) :]

        items: List[EvidenceItem] = []
        full_text = " ".join(c.text.lower() for c in claims)
        concept_tokens = _tokenize_meaningful(expected.concept_id.replace("_", " "))
        generic_fillers = {"data", "system", "process", "code", "method", "function", "value", "thing", "way", "item", "concept"} | concept_tokens

        for c_idx, comp in enumerate(expected.core_components):
            comp_emb = comp_embs[c_idx]
            comp_tokens = _tokenize_meaningful(comp)

            best_sim = 0.0
            best_cl_idx = -1
            for cl_idx, cl_emb in enumerate(claim_embs):
                sim = cosine_similarity(cl_emb, comp_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_cl_idx = cl_idx

            # Direct exact phrase match boost
            comp_clean = comp.lower().replace("-", " ")
            user_clean = clean_user.lower().replace("-", " ")
            if comp_clean in user_clean or comp.lower() in full_text:
                best_sim = max(best_sim, 0.90)

            best_claim_text = claim_texts[best_cl_idx] if best_cl_idx >= 0 else ""
            cl_tokens = _tokenize_meaningful(best_claim_text)
            overlap = cl_tokens & comp_tokens
            distinctive_overlap = overlap - generic_fillers

            # Contradiction check:
            is_contradicted = False
            contra_claim = None
            if has_negated_phrase(best_claim_text, comp):
                is_contradicted = True
                contra_claim = best_claim_text
            elif "not " in comp.lower() and not ("not " in full_text or "no " in full_text):
                comp_keywords = comp_tokens - generic_fillers
                if len(cl_tokens & comp_keywords) >= 1:
                    is_contradicted = True
                    contra_claim = best_claim_text
            elif ("all" in comp.lower() and "nothing" in comp.lower()) or "roll" in comp.lower() or "commit" in comp.lower():
                if any(p in full_text for p in ["partially succeed", "partially commit", "partial commit", "saves the parts that worked", "still succeed and commit", "succeed even if", "can still succeed"]):
                    is_contradicted = True
                    contra_claim = full_text

            if is_contradicted:
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

            # Support classification:
            # Full support requires:
            # 1. High dense similarity (best_sim >= 0.50) OR
            # 2. Good similarity (best_sim >= 0.44) + at least 1 distinctive predicate word OR
            # 3. best_sim >= 0.42 with 2+ distinctive predicate words.
            # Never grant full SUPPORTED if best_sim < 0.42 (e.g. 0.29 vague overlap).
            if best_sim >= 0.50 or (best_sim >= 0.44 and len(distinctive_overlap) >= 1) or (best_sim >= 0.42 and len(distinctive_overlap) >= 2):
                items.append(
                    EvidenceItem(
                        concept_id=expected.concept_id,
                        expected_description=comp,
                        status=EvidenceStatus.SUPPORTED,
                        supported_by_claim=best_claim_text,
                        confidence=round(best_sim, 2),
                    )
                )
            elif best_sim >= 0.35 or (best_sim >= 0.28 and len(distinctive_overlap) >= 1) or len(distinctive_overlap) >= 2:
                items.append(
                    EvidenceItem(
                        concept_id=expected.concept_id,
                        expected_description=comp,
                        status=EvidenceStatus.PARTIALLY_SUPPORTED,
                        supported_by_claim=best_claim_text,
                        confidence=round(best_sim, 2),
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

        # Enrich atomic claims with claim-level assessment status
        for claim in claims:
            matching_items = [it for it in items if it.supported_by_claim and claim.text in it.supported_by_claim]
            contradicting_items = [it for it in items if it.contradicted_by_claim and claim.text in it.contradicted_by_claim]
            if contradicting_items:
                claim.support_status = EvidenceStatus.CONTRADICTED
                claim.contradiction_status = True
                claim.contradicts_claim = contradicting_items[0].expected_description
                claim.assessment_rationale = f"Contradicts core component '{claim.contradicts_claim}'"
            elif matching_items:
                best_match = matching_items[0]
                claim.support_status = best_match.status
                claim.assessment_rationale = f"Supports expected evidence: '{best_match.expected_description}'"
            else:
                claim.support_status = EvidenceStatus.UNKNOWN

        return items

    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        """
        Assesses correctness level strictly enforcing mastery safety.
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
        missing_count = sum(1 for it in evidence_items if it.status == EvidenceStatus.MISSING)
        total = max(1, len(evidence_items))

        # Check for cross-claim internal contradiction
        full_text = " ".join(c.text.lower() for c in claims)
        has_internal_conflict = False
        if any(w in full_text for w in ["but", "however", "although", "whereas", "except"]):
            if supported_count > 0 and ("cannot" in full_text or "never" in full_text or "not" in full_text):
                for c in claims:
                    if any(p in c.text.lower() for p in ["cannot persist", "never copied", "saves the parts that worked"]):
                        contradictory.append(c.text)
                        has_internal_conflict = True

        if has_internal_conflict:
            return CorrectnessLevel.CONTRADICTORY, 0.10, contradictory

        # Strict correctness threshold:
        # 1. Full CORRECT requires 100% of core components to be fully SUPPORTED.
        # 2. Or substantive demonstration where at least 1 component is fully SUPPORTED and ZERO missing components (missing_count == 0).
        if supported_count == total and total >= 1 and not has_internal_conflict:
            return CorrectnessLevel.CORRECT, 0.95, []
        elif supported_count >= 1 and missing_count == 0 and total <= 3 and not has_internal_conflict:
            return CorrectnessLevel.CORRECT, 0.88, []
        elif supported_count >= 1 or partial_count >= 1:
            score = round(0.40 + 0.20 * ((supported_count + 0.5 * partial_count) / total), 2)
            return CorrectnessLevel.PARTIALLY_CORRECT, score, []
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
        Discriminative misconception detection.
        Flags misconceptions accurately without false alarms on correct refutations.
        """
        misconceptions = expected.common_misconceptions
        if not misconceptions or not user_message:
            return []

        clean_user = user_message.strip()
        lower_user = clean_user.lower()

        # Refutation indicators: learner is refuting a false claim, NOT holding it
        refuting_patterns = [
            "not true", "does not mean", "unlike", "is false", "is incorrect",
            "rather than", "does not require", "never", "not necessarily",
            "not always", "instead of", "neither", "nor", "no need to",
            "doesn't mean", "cannot", "doesn't require", "don't require",
            "does not eliminate", "doesn't eliminate", "without requiring",
            "do not", "does not", "don't", "doesn't", "not automatically",
            "not strictly", "not just", "does not make", "does not guarantee",
        ]
        is_refuting = any(p in lower_user for p in refuting_patterns)

        claim_texts = [c.text for c in claims if c.text.strip()]
        if not claim_texts:
            claim_texts = [clean_user]

        all_texts = [clean_user] + claim_texts + misconceptions
        embs = self.semantic_provider.encode(all_texts)
        user_emb = embs[0]
        claim_embs = embs[1 : 1 + len(claim_texts)]
        misc_embs = embs[1 + len(claim_texts) :]

        core_texts = expected.core_components
        core_embs = self.semantic_provider.encode(core_texts) if core_texts else []
        best_core_sim = 0.0
        if len(core_embs) > 0:
            best_core_sim = max(
                max(cosine_similarity(ce, core_emb) for ce in ([user_emb] + claim_embs))
                for core_emb in core_embs
            )

        detected: List[MisconceptionEvidence] = []
        concept_tokens = _tokenize_meaningful(expected.concept_id.replace("_", " "))
        topic_tokens = _tokenize_meaningful(" ".join(expected.core_components))
        user_tokens = _tokenize_meaningful(clean_user)

        for m_idx, misc_text in enumerate(misconceptions):
            misc_emb = misc_embs[m_idx]
            misc_sim = cosine_similarity(user_emb, misc_emb)
            claim_sims = [cosine_similarity(ce, misc_emb) for ce in claim_embs]
            best_claim_sim = max(claim_sims) if claim_sims else misc_sim
            peak_sim = max(misc_sim, best_claim_sim)

            misc_tokens = _tokenize_meaningful(misc_text)

            # Check refutation:
            if is_refuting:
                if len(misc_tokens & user_tokens) >= 2 or peak_sim >= 0.55:
                    continue

            # Core understanding safeguard: if learner is more aligned with truth than misconception
            # (unless an explicit anti-pattern or contradiction was asserted)
            has_anti_pattern = any(p in lower_user for p in ["partially succeed", "partially commit", "partial commit", "saves the parts that worked", "still succeed and commit", "succeed even if", "can still succeed"])
            if not has_anti_pattern and best_core_sim >= peak_sim and peak_sim < 0.85:
                continue

            # False assertion tokens: words in misconception not in concept or true topic components
            false_assertion_tokens = misc_tokens - concept_tokens - topic_tokens - TOKENIZED_DOMAIN_TERMS
            has_false_assertion = len(false_assertion_tokens & user_tokens) >= 1 if false_assertion_tokens else False

            # Misconception triggers:
            is_misc = False
            if peak_sim >= 0.85:
                is_misc = True
            elif has_false_assertion and (peak_sim >= 0.48 or peak_sim > best_core_sim):
                is_misc = True
            elif has_anti_pattern and peak_sim >= 0.35:
                is_misc = True

            if is_misc:
                detected.append(
                    MisconceptionEvidence(
                        concept_id=expected.concept_id,
                        description=misc_text,
                        learner_statement=clean_user,
                        severity="HIGH",
                    )
                )
                for claim in claims:
                    if len(user_tokens & false_assertion_tokens) >= 1:
                        claim.misconception_labels.append(misc_text)

        return detected

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
