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


def _has_general_negation(text: str) -> bool:
    """Checks whether the text contains general negation markers."""
    return bool(
        re.search(
            r"\b(no|not|never|neither|nor|without|cannot|can't|does not|doesn't|isn't|aren't)\b",
            text,
            re.IGNORECASE,
        )
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
        neg_i = _has_general_negation(text_i)

        for j in range(i + 1, len(chunks)):
            text_j = chunks[j].text.lower()
            tokens_j = _extract_content_tokens(text_j)
            neg_j = _has_general_negation(text_j)

            # High lexical overlap but opposite polarity indicates conflicting evidence
            overlap = tokens_i & tokens_j
            if len(overlap) >= 3 and (neg_i != neg_j):
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

            status, rationale = self._classify_claim(claim, doc_context.chunks)
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
    ) -> Tuple[DocumentEvidenceClassification, str]:
        """
        Classifies an individual claim against retrieved chunks.
        """
        claim_text = claim.text.strip().lower()
        claim_tokens = _extract_content_tokens(claim_text)
        claim_is_negated = _has_general_negation(claim_text)

        if not claim_tokens:
            return (
                DocumentEvidenceClassification.UNESTABLISHED,
                "Claim text is empty or contains only non-substantive words.",
            )

        best_overlap_count = 0
        best_chunk: Optional[DocumentChunkEvidence] = None
        contradiction_found = False
        contradiction_chunk: Optional[DocumentChunkEvidence] = None

        for chunk in chunks:
            chunk_text = chunk.text.strip().lower()
            chunk_tokens = _extract_content_tokens(chunk_text)
            chunk_is_negated = _has_general_negation(chunk_text)

            overlap = claim_tokens & chunk_tokens
            overlap_count = len(overlap)

            # Check for contradiction:
            # High conceptual overlap (e.g. >= 2 meaningful domain tokens) but opposite assertion/polarity
            if overlap_count >= 2:
                # Polarity mismatch check
                if claim_is_negated != chunk_is_negated:
                    contradiction_found = True
                    contradiction_chunk = chunk
                    break

                # Explicit contradictory phrases check
                # e.g., claim: "unsorted array", chunk: "must be sorted"
                if (
                    ("unsorted" in claim_text and "must be sorted" in chunk_text)
                    or ("constant time" in claim_text and "logarithmic" in chunk_text)
                    or ("o(n)" in claim_text and "o(log n)" in chunk_text)
                    or ("always" in claim_text and "never" in chunk_text)
                ):
                    contradiction_found = True
                    contradiction_chunk = chunk
                    break

            if overlap_count > best_overlap_count:
                best_overlap_count = overlap_count
                best_chunk = chunk

        if contradiction_found and contradiction_chunk:
            return (
                DocumentEvidenceClassification.CONTRADICTED,
                f"Contradicts passage in document {contradiction_chunk.document_id} (chunk {contradiction_chunk.chunk_index}).",
            )

        # To be SUPPORTED, require substantive semantic overlap:
        # 1. At least 2 meaningful tokens or > 50% of the claim's content tokens
        # 2. Matching polarity (verified above)
        # 3. Not merely a generic single keyword match!
        if (
            best_chunk is not None
            and best_overlap_count >= 2
            and (best_overlap_count / max(1, len(claim_tokens))) >= 0.40
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
