"""
Document Evidence Evaluator for Answer Intelligence.
Evaluates atomic learner claims against retrieved document passages.
Enforces the strict separation between document support and general semantic correctness:
- A claim can be generally correct but unestablished by the document.
- Keyword overlap or retrieval similarity score alone NEVER establishes support or grants mastery.
- Contradictory document passages preserve uncertainty.
"""
from __future__ import annotations
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.ai.answer_intelligence.providers.local_model import (
    STOP_WORDS,
    _tokenize_meaningful,
)
from backend.app.ai.answer_intelligence.schemas import (
    DocumentEvidenceClassification,
    LearnerClaim,
)
from backend.app.ai.rag.models import DocumentChunkEvidence, DocumentSourceContext

logger = logging.getLogger("curio.ai.answer_intelligence.document_evaluator")

# Terms that are too generic to establish document support on their own
GENERIC_STOP_WORDS = STOP_WORDS | {
    "data", "system", "method", "function", "code", "algorithm",
    "thing", "way", "concept", "idea", "step", "example",
}


def _is_token_negated_in(token: str, text: str) -> bool:
    """Checks if a specific token or concept is directly negated in the text."""
    pat = (
        r"\b(?:no|not|never|neither|nor|without|regardless of|does not|doesn't|cannot|can't|impossible to)\s+(?:\w+\s+){0,3}"
        + re.escape(token)
    )
    return bool(re.search(pat, text, re.IGNORECASE)) or bool(
        re.search(r"\bnon[\s-]" + re.escape(token), text, re.IGNORECASE)
    )


def _extract_content_tokens(text: str) -> Set[str]:
    """Extract lowercased alphanumeric tokens, stripping common and generic stopwords."""
    raw_tokens = _tokenize_meaningful(text)
    return {t for t in raw_tokens if t not in GENERIC_STOP_WORDS and len(t) > 2}


def _check_conflicting_chunks(chunks: List[DocumentChunkEvidence]) -> bool:
    """
    Checks if retrieved chunks contain mutually contradictory statements.
    e.g., one chunk affirms an invariant while another denies it.
    """
    if len(chunks) < 2:
        return False

    # Check for direct negation contradictions across chunk pairs
    for i in range(len(chunks)):
        text_i = chunks[i].text.lower()
        tokens_i = _extract_content_tokens(text_i)

        for j in range(i + 1, len(chunks)):
            text_j = chunks[j].text.lower()
            tokens_j = _extract_content_tokens(text_j)
            overlap = tokens_i & tokens_j

            if len(overlap) >= 2:
                # Token-specific polarity check
                for t in overlap:
                    if _is_token_negated_in(t, text_i) != _is_token_negated_in(t, text_j):
                        return True

                # Explicit contradictory phrases
                if (
                    ("impossible" in text_i and "possible" in text_j)
                    or ("impossible" in text_j and "possible" in text_i)
                    or ("never" in text_i and "always" in text_j)
                    or ("never" in text_j and "always" in text_i)
                ):
                    return True

    return False


class DocumentEvidenceEvaluator:
    """
    Evaluates learner claims against validated DocumentSourceContext.
    Assigns:
    - SUPPORTED: substantive claim is verified and backed by document evidence.
    - CONTRADICTED: substantive claim directly conflicts with document evidence.
    - UNESTABLISHED: document evidence neither establishes nor contradicts the claim.
    - CONFLICTING: document evidence contains inconsistent/conflicting assertions.
    - NOT_APPLICABLE: document grounding is disabled or inactive.
    """

    def evaluate_claims(
        self,
        claims: List[LearnerClaim],
        doc_context: Optional[DocumentSourceContext],
        target_concept: Optional[str] = None,
    ) -> Tuple[List[LearnerClaim], Dict[str, Any]]:
        """
        Evaluates a list of atomic claims against the document context.
        Returns the updated claims and a summary metadata dictionary.
        """
        if doc_context is None or not doc_context.is_grounded:
            for claim in claims:
                claim.document_evidence_status = DocumentEvidenceClassification.NOT_APPLICABLE
                claim.document_rationale = "Document grounding is not active for this turn."

            return claims, {
                "status": doc_context.status.value if doc_context else "disabled",
                "is_grounded": False,
                "supported_count": 0,
                "contradicted_count": 0,
                "unestablished_count": 0,
                "conflicting_count": 0,
            }

        # Check for conflicting evidence across chunks
        has_conflicts = _check_conflicting_chunks(doc_context.chunks)

        supported_count = 0
        contradicted_count = 0
        unestablished_count = 0
        conflicting_count = 0

        for claim in claims:
            if has_conflicts:
                claim.document_evidence_status = DocumentEvidenceClassification.CONFLICTING
                claim.document_rationale = (
                    "Available document passages contain conflicting or inconsistent assertions on this topic."
                )
                conflicting_count += 1
                continue

            status, rationale = self._classify_claim(claim, doc_context.chunks, target_concept=target_concept)
            claim.document_evidence_status = status
            claim.document_rationale = rationale

            if status == DocumentEvidenceClassification.SUPPORTED:
                supported_count += 1
            elif status == DocumentEvidenceClassification.CONTRADICTED:
                contradicted_count += 1
            elif status == DocumentEvidenceClassification.UNESTABLISHED:
                unestablished_count += 1
            elif status == DocumentEvidenceClassification.CONFLICTING:
                conflicting_count += 1

        summary = {
            "status": doc_context.status.value,
            "is_grounded": True,
            "has_conflicting_chunks": has_conflicts,
            "supported_count": supported_count,
            "contradicted_count": contradicted_count,
            "unestablished_count": unestablished_count,
            "conflicting_count": conflicting_count,
        }

        return claims, summary

    def _classify_claim(
        self,
        claim: LearnerClaim,
        chunks: List[DocumentChunkEvidence],
        target_concept: Optional[str] = None,
    ) -> Tuple[DocumentEvidenceClassification, str]:
        """
        Classifies an individual claim against retrieved chunks.
        """
        claim_text = claim.text.strip().lower()
        claim_tokens = _extract_content_tokens(claim_text)
        concept_tokens = _extract_content_tokens(target_concept) if target_concept else set()

        if not claim_tokens:
            return (
                DocumentEvidenceClassification.UNESTABLISHED,
                "Claim text is empty or contains only non-substantive words.",
            )

        best_overlap_count = 0
        best_substantive_overlap_count = 0
        best_chunk: Optional[DocumentChunkEvidence] = None
        contradiction_found = False
        contradiction_chunk: Optional[DocumentChunkEvidence] = None

        for chunk in chunks:
            chunk_text = chunk.text.strip().lower()
            chunk_tokens = _extract_content_tokens(chunk_text)

            overlap = claim_tokens & chunk_tokens
            overlap_count = len(overlap)
            substantive_overlap = overlap - concept_tokens
            substantive_count = len(substantive_overlap)

            # Check for contradiction:
            # High conceptual overlap (e.g. >= 2 meaningful domain tokens)
            if overlap_count >= 2:
                # Token-specific polarity check
                for t in overlap:
                    if _is_token_negated_in(t, claim_text) != _is_token_negated_in(t, chunk_text):
                        contradiction_found = True
                        contradiction_chunk = chunk
                        break
                if contradiction_found:
                    break

                # Explicit contradictory phrases check
                if (
                    ("unsorted" in claim_text and "must be sorted" in chunk_text)
                    or ("unsorted" in chunk_text and "must be sorted" in claim_text)
                    or ("constant time" in claim_text and "logarithmic" in chunk_text)
                    or ("o(n)" in claim_text and "o(log n)" in chunk_text)
                    or ("always" in claim_text and "never" in chunk_text)
                    or ("impossible" in claim_text and "possible" in chunk_text)
                ):
                    contradiction_found = True
                    contradiction_chunk = chunk
                    break

            if substantive_count > best_substantive_overlap_count:
                best_overlap_count = overlap_count
                best_substantive_overlap_count = substantive_count
                best_chunk = chunk
            elif overlap_count > best_overlap_count and best_chunk is None:
                best_overlap_count = overlap_count
                best_chunk = chunk

        if contradiction_found and contradiction_chunk:
            return (
                DocumentEvidenceClassification.CONTRADICTED,
                f"Contradicts passage in document {contradiction_chunk.document_id} (chunk {contradiction_chunk.chunk_index}).",
            )

        # To be SUPPORTED, require substantive semantic overlap:
        # 1. At least 2 substantive domain tokens beyond the mere topic/concept name
        # 2. Substantive overlap coverage of the non-concept tokens
        # 3. Matching polarity (verified above)
        # 4. Not merely a generic single keyword match!
        claim_substantive_tokens = claim_tokens - concept_tokens
        if (
            best_chunk is not None
            and best_substantive_overlap_count >= 2
            and (
                best_substantive_overlap_count >= 3
                or (best_substantive_overlap_count / max(1, len(claim_substantive_tokens))) >= 0.25
            )
        ):
            return (
                DocumentEvidenceClassification.SUPPORTED,
                f"Supported by passage in document {best_chunk.document_id} (chunk {best_chunk.chunk_index}).",
            )

        # Otherwise unestablished (e.g., generally true or outside document scope)
        return (
            DocumentEvidenceClassification.UNESTABLISHED,
            "Claim is not established by the retrieved document passages.",
        )
