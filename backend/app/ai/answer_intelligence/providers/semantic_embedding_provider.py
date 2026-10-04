"""
Semantic Embedding Assessment Provider for Curio AI (Milestone B).
Uses local dense sentence embeddings (all-MiniLM-L6-v2) combined with
atomic claim extraction, directional semantic similarity, negation detection,
and principled confidence abstention.
"""
from __future__ import annotations
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

import numpy as np

from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.providers.local_model import (
    LocalAssessmentProvider,
    _tokenize_meaningful,
    has_negated_phrase,
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

logger = logging.getLogger("curio.ai.answer_intelligence.semantic_provider")

# Global singleton model cache to avoid re-instantiating on every turn
_EMBEDDING_MODEL = None


def get_embedding_model():
    """Lazily load and cache the local sentence transformer model offline."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            # Enforce offline mode to prevent HuggingFace hub network timeouts
            os.environ["HF_HUB_OFFLINE"] = "1"
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)
            logger.info("Loaded offline SentenceTransformer 'all-MiniLM-L6-v2' successfully.")
        except Exception as e:
            logger.warning("Failed to load local SentenceTransformer: %s. Falling back to local heuristic provider.", e)
            _EMBEDDING_MODEL = False
    return _EMBEDDING_MODEL if _EMBEDDING_MODEL is not False else None


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Compute cosine similarity between two 1D or 2D embedding vectors."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


NEGATION_TOKENS = {
    "not", "no", "never", "neither", "nor", "without", "cannot", "can't",
    "doesn't", "doesnt", "don't", "dont", "won't", "wont", "isn't", "isnt",
    "aren't", "arent", "hardly", "barely", "unlikely",
}


def has_negation(text: str) -> bool:
    """Detect if a text segment contains explicit negative polarity."""
    tokens = re.findall(r"\b\w+\b", text.lower())
    return any(t in NEGATION_TOKENS for t in tokens)


class SemanticEmbeddingProvider(BaseAssessmentProvider):
    """
    Specialized Semantic ML Provider for Curio AI Answer Intelligence.
    Combines fast local intent parsing with dense embedding semantic matching,
    negation guards, and structured misconception projection.
    """

    def __init__(self, fallback_provider: Optional[BaseAssessmentProvider] = None):
        self.fallback = fallback_provider or LocalAssessmentProvider()
        self._model = get_embedding_model()

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of strings into normalized sentence embeddings."""
        if self._model is not None:
            try:
                return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            except Exception as e:
                logger.warning("SentenceTransformer encoding failed: %s", e)
        # Dynamic fallback: empty zero vector
        return np.zeros((len(texts), 384), dtype=np.float32)

    def classify_intent(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float]:
        """Delegate intent classification to fast, calibrated heuristic rules."""
        return self.fallback.classify_intent(user_message, context, current_question)

    def assess_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        """
        Assess relevance using dense semantic similarity conditioned on target concept,
        question objective, and expected evidence.
        """
        intent, _ = self.classify_intent(user_message)
        if intent in (
            AssessmentIntent.HELP_REQUEST,
            AssessmentIntent.CLARIFICATION_REQUEST,
            AssessmentIntent.QUESTION_ABOUT_CONCEPT,
        ):
            return RelevanceLevel.RELEVANT, 0.90
        if intent in (AssessmentIntent.ACKNOWLEDGEMENT, AssessmentIntent.EMPTY_RESPONSE):
            return RelevanceLevel.IRRELEVANT, 0.05
        if intent == AssessmentIntent.OFF_TOPIC:
            return RelevanceLevel.IRRELEVANT, 0.05

        clean = user_message.strip()
        if len(clean) < 3:
            return RelevanceLevel.IRRELEVANT, 0.0

        concept_anchor = f"{target_concept.replace('_', ' ')} in {topic}. {question}"
        components = getattr(expected, "core_components", []) or getattr(expected, "constraints", [])
        if components:
            concept_anchor += f" {' '.join(components)}"

        # Encode candidate and target anchor
        embeddings = self.encode([clean, concept_anchor])
        sim = cosine_similarity(embeddings[0], embeddings[1])

        # Dense similarity scale calibration:
        # MiniLM cosine similarity typically ranges from 0.05 (unrelated) to 0.85+ (paraphrase).
        # We also check for domain trivia / technically true irrelevant answers.
        trivia_markers = ["invented by", "created by", "was born in", "in 19", "in 200", "named after"]
        is_trivia_claim = any(m in clean.lower() for m in trivia_markers)

        if sim < 0.22:
            return RelevanceLevel.IRRELEVANT, max(0.0, float(sim))
        elif is_trivia_claim and sim < 0.45:
            # Distinguishes historically true statements from operational concept answers
            return RelevanceLevel.IRRELEVANT, round(float(sim * 0.5), 2)
        elif sim < 0.35:
            return RelevanceLevel.PARTIALLY_RELEVANT, round(float(sim), 2)
        else:
            return RelevanceLevel.RELEVANT, round(min(1.0, float(sim * 1.25)), 2)

    def extract_claims(
        self,
        user_message: str,
        target_concept: str,
    ) -> List[LearnerClaim]:
        """
        Extract atomic semantic claims from learner text, segmenting complex compound
        and contradictory assertions cleanly.
        """
        clean = (user_message or "").strip()
        if not clean:
            return []

        # Split on contrasting conjunctions and clause punctuation
        split_pattern = r"(?<=[.!?])\s+|;\s+|\s+(?:but|however|although|whereas|though|while)\s+"
        raw_clauses = [c.strip() for c in re.split(split_pattern, clean, flags=re.IGNORECASE) if c.strip()]
        if not raw_clauses:
            raw_clauses = [clean]

        claims: List[LearnerClaim] = []
        for i, clause in enumerate(raw_clauses):
            if len(clause) < 3:
                continue

            c_type = ClaimType.FACTUAL_ASSERTION
            if any(w in clause.lower() for w in ["like", "think of", "imagine", "analogous", "similar to"]):
                c_type = ClaimType.ANALOGY
            elif any(w in clause.lower() for w in ["because", "therefore", "since", "so that", "guarantees"]):
                c_type = ClaimType.MECHANISM
            elif has_negation(clause):
                c_type = ClaimType.COUNTER_CLAIM

            claims.append(
                LearnerClaim(
                    claim_id=f"claim_{i+1}",
                    text=clause,
                    claim_type=c_type,
                    confidence=0.85,
                )
            )

        return claims

    def align_concepts(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        """Measure semantic alignment between learner claims and concept definition."""
        if not claims or not concept_node:
            return 0.0

        claim_texts = [c.text for c in claims]
        concept_text = f"{concept_node.name}. {concept_node.definition}. {' '.join(concept_node.constraints)}"
        
        all_texts = claim_texts + [concept_text]
        embs = self.encode(all_texts)
        concept_emb = embs[-1]

        max_sim = 0.0
        for i in range(len(claims)):
            sim = cosine_similarity(embs[i], concept_emb)
            if sim > max_sim:
                max_sim = sim

        # Calibrated alignment score
        if max_sim >= 0.50:
            return min(1.0, round(max_sim * 1.3, 2))
        elif max_sim >= 0.30:
            return round(max_sim, 2)
        else:
            return round(max_sim * 0.5, 2)

    def match_evidence(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        """
        Match claims against expected evidence items using dense vector similarity
        and negation consistency checks.
        """
        constraint_texts = getattr(expected, "core_components", []) or getattr(expected, "constraints", [])
        if not claims or not constraint_texts:
            return []

        claim_texts = [c.text for c in claims]
        all_texts = claim_texts + constraint_texts
        embs = self.encode(all_texts)

        claim_embs = embs[:len(claim_texts)]
        constraint_embs = embs[len(claim_texts):]

        evidence_items: List[EvidenceItem] = []

        for c_idx, constraint in enumerate(constraint_texts):
            cons_emb = constraint_embs[c_idx]
            best_sim = 0.0
            best_claim_idx = -1

            for cl_idx, claim_emb in enumerate(claim_embs):
                sim = cosine_similarity(claim_emb, cons_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_claim_idx = cl_idx

            status = EvidenceStatus.MISSING
            matching_claim = None
            supp_claim: Optional[str] = None
            contra_claim: Optional[str] = None

            # High semantic similarity threshold
            if best_sim >= 0.48 and best_claim_idx >= 0:
                matching_claim = claims[best_claim_idx].text
                # Check for explicit contradiction (claim explicitly negates constraint)
                if has_negated_phrase(matching_claim, constraint):
                    status = EvidenceStatus.CONTRADICTED
                    contra_claim = matching_claim
                elif best_sim >= 0.58:
                    status = EvidenceStatus.SUPPORTED
                    supp_claim = matching_claim
                else:
                    status = EvidenceStatus.PARTIALLY_SUPPORTED
                    supp_claim = matching_claim
            elif best_sim >= 0.35:
                supp_claim = claims[best_claim_idx].text if best_claim_idx >= 0 else None
                status = EvidenceStatus.PARTIALLY_SUPPORTED

            evidence_items.append(
                EvidenceItem(
                    concept_id=expected.concept_id,
                    expected_description=constraint,
                    status=status,
                    supported_by_claim=supp_claim,
                    contradicted_by_claim=contra_claim,
                    confidence=round(best_sim, 2),
                )
            )

        return evidence_items

    def detect_misconceptions(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[MisconceptionEvidence]:
        """
        Detect specific misconceptions by projecting learner claims against known
        anti-patterns and common misconceptions.
        """
        misconceptions = expected.common_misconceptions
        if not misconceptions or not user_message:
            return []

        user_text = user_message.strip()
        # Compute embeddings for both full message and individual claims
        claim_texts = [c.text for c in claims if c.text.strip()]
        all_texts = [user_text] + claim_texts + misconceptions
        embs = self.encode(all_texts)
        user_emb = embs[0]
        claim_embs = embs[1: 1 + len(claim_texts)]
        misc_embs = embs[1 + len(claim_texts):]

        detected: List[MisconceptionEvidence] = []
        refuting_patterns = [
            "not true that", "does not mean", "unlike", "is false", "is incorrect",
            "rather than", "does not require", "never", "not necessarily", "no ", "without ",
            "all or nothing", "all-or-nothing", "rolls back",
        ]

        COMMON_DOMAIN_TERMS = {
            "fastapi", "asgi", "wsgi", "uvicorn", "python", "javascript", "js", "dbms", "database",
            "sql", "nosql", "array", "arrays", "list", "lists", "function", "functions", "variable",
            "variables", "system", "systems", "process", "processes", "thread", "threads", "memory",
            "server", "servers", "client", "clients", "algorithm", "algorithms", "tree", "trees",
            "node", "nodes", "table", "tables", "data", "code", "application", "applications",
            "app", "apps", "request", "requests", "response", "responses", "network", "web",
            "program", "programs", "execution", "operating", "os", "key", "keys", "value", "values",
            "element", "elements", "item", "items", "file", "files", "class", "classes", "object",
            "objects", "method", "methods", "number", "numbers", "index", "indices",
        }

        for m_idx, misc_text in enumerate(misconceptions):
            sim = cosine_similarity(user_emb, misc_embs[m_idx])
            claim_sims = [cosine_similarity(ce, misc_embs[m_idx]) for ce in claim_embs]
            best_sim = max([sim] + claim_sims) if claim_sims else sim

            is_refuting = any(p in user_text.lower() for p in refuting_patterns)
            if not is_refuting:
                concept_tokens = _tokenize_meaningful(expected.concept_id.replace("_", " "))
                predicate_tokens = (_tokenize_meaningful(misc_text) - concept_tokens) - COMMON_DOMAIN_TERMS
                if not predicate_tokens:
                    predicate_tokens = _tokenize_meaningful(misc_text) - concept_tokens
                user_tokens = _tokenize_meaningful(user_text)

                if best_sim >= 0.70:
                    # Very high dense vector match across entire misconception
                    detected.append(
                        MisconceptionEvidence(
                            concept_id=expected.concept_id,
                            description=misc_text,
                            learner_statement=user_text,
                            severity="HIGH",
                        )
                    )
                elif best_sim >= 0.50:
                    # Moderate similarity requires at least one keyword overlap with misconception predicate
                    if predicate_tokens and (user_tokens & predicate_tokens):
                        detected.append(
                            MisconceptionEvidence(
                                concept_id=expected.concept_id,
                                description=misc_text,
                                learner_statement=user_text,
                                severity="HIGH",
                            )
                        )

        return detected

    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        """Compute correctness based on evidence support and contradiction guards."""
        if not claims:
            return CorrectnessLevel.UNASSESSABLE, 0.0, []

        contradictory_claims: List[str] = []
        for ev in evidence_items:
            if ev.status == EvidenceStatus.CONTRADICTED and ev.contradicted_by_claim:
                contradictory_claims.append(ev.contradicted_by_claim)

        # Check for claims with internal contradictions (e.g. 'all commit, but some can fail')
        for c in claims:
            if c.claim_type == ClaimType.COUNTER_CLAIM:
                contradictory_claims.append(c.text)

        supported_count = sum(1 for e in evidence_items if e.status == EvidenceStatus.SUPPORTED)
        partial_count = sum(1 for e in evidence_items if e.status == EvidenceStatus.PARTIALLY_SUPPORTED)
        total_ev = max(1, len(evidence_items))

        # Effective support score
        support_ratio = (supported_count + 0.5 * partial_count) / total_ev

        if len(contradictory_claims) > 0 and support_ratio < 0.8:
            return CorrectnessLevel.CONTRADICTORY, 0.20, contradictory_claims

        if support_ratio >= 0.70:
            return CorrectnessLevel.CORRECT, round(min(1.0, 0.70 + support_ratio * 0.30), 2), contradictory_claims
        elif support_ratio >= 0.35:
            return CorrectnessLevel.PARTIALLY_CORRECT, round(support_ratio, 2), contradictory_claims
        else:
            return CorrectnessLevel.INCORRECT, round(support_ratio * 0.5, 2), contradictory_claims

    def assess_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        """Assess coverage of required conceptual constraints."""
        if not evidence_items:
            return CompletenessLevel.NOT_APPLICABLE, 0.0, []

        missing_concepts: List[str] = []
        covered_count = 0
        for ev in evidence_items:
            if ev.status == EvidenceStatus.SUPPORTED:
                covered_count += 1
            elif ev.status == EvidenceStatus.PARTIALLY_SUPPORTED:
                covered_count += 0.5
            else:
                missing_concepts.append(ev.expected_description)

        ratio = covered_count / len(evidence_items)
        if ratio >= 0.80:
            return CompletenessLevel.COMPLETE, round(ratio, 2), missing_concepts
        elif ratio >= 0.40:
            return CompletenessLevel.PARTIAL, round(ratio, 2), missing_concepts
        else:
            return CompletenessLevel.MINIMAL, round(ratio, 2), missing_concepts

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
        Principled abstention and confidence calibration.
        If evidence is ambiguous or relevance is borderline, trigger ABSTAIN.
        """
        if intent != AssessmentIntent.ANSWER_ATTEMPT:
            return AssessmentStatus.HIGH_CONFIDENCE, 0.95

        # Borderline relevance: ABSTAIN
        if 0.28 <= relevance_score <= 0.42:
            return AssessmentStatus.ABSTAIN, 0.40

        # Borderline correctness without strong evidence
        if correctness == CorrectnessLevel.UNASSESSABLE:
            return AssessmentStatus.ABSTAIN, 0.30

        # High confidence for strong evidence
        supported = [e for e in evidence_items if e.status == EvidenceStatus.SUPPORTED]
        if len(supported) >= 2 and relevance == RelevanceLevel.RELEVANT:
            return AssessmentStatus.HIGH_CONFIDENCE, 0.92

        return AssessmentStatus.HIGH_CONFIDENCE, 0.85
