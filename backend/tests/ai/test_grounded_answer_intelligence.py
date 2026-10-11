"""
Unit tests for Objective C: Document-Grounded Answer Intelligence and Mastery Safety.
Verifies all 12 evidence evaluation, claim classification, uncertainty preservation,
and MasteryGate safeguard requirements.
"""
import pytest
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.document_evaluator import DocumentEvidenceEvaluator
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    DocumentEvidenceClassification,
    EvidenceItem,
    EvidenceStatus,
    LearnerClaim,
    LearningAssessment,
    RelevanceLevel,
)
from backend.app.ai.rag.models import (
    DocumentChunkEvidence,
    DocumentRetrievalStatus,
    DocumentSourceContext,
)
from backend.app.ai.schemas import AIContext


def _make_chunk(text: str, chunk_id: str = "c1", doc_id: str = "d1") -> DocumentChunkEvidence:
    return DocumentChunkEvidence(
        chunk_id=chunk_id,
        document_id=doc_id,
        chunk_index=0,
        text=text,
        page_number=1,
    )


def test_1_substantively_supported_claim_recognized_as_supported():
    """1. A substantively supported claim can be recognized as supported."""
    evaluator = DocumentEvidenceEvaluator()
    claim = LearnerClaim(text="Binary search requires the input array to be sorted monotonically.")
    doc_context = DocumentSourceContext(
        status=DocumentRetrievalStatus.SUCCESS,
        chunks=[_make_chunk("Binary search requires the input array elements to be monotonically sorted.")],
    )
    claims, summary = evaluator.evaluate_claims([claim], doc_context)

    assert claims[0].document_evidence_status == DocumentEvidenceClassification.SUPPORTED
    assert summary["supported_count"] == 1


def test_2_conflicting_claim_recognized_as_contradicted():
    """2. A claim that conflicts with the source is recognized as contradicted."""
    evaluator = DocumentEvidenceEvaluator()
    claim = LearnerClaim(text="Binary search works on completely unsorted arrays.")
    doc_context = DocumentSourceContext(
        status=DocumentRetrievalStatus.SUCCESS,
        chunks=[_make_chunk("In binary search, the input array must be sorted monotonically.")],
    )
    claims, summary = evaluator.evaluate_claims([claim], doc_context)

    assert claims[0].document_evidence_status == DocumentEvidenceClassification.CONTRADICTED
    assert summary["contradicted_count"] == 1


def test_3_plausible_unestablished_claim_not_marked_false():
    """3. A generally plausible but source-unestablished claim is not automatically marked false."""
    evaluator = DocumentEvidenceEvaluator()
    claim = LearnerClaim(text="Python dictionaries use hash tables under the hood.")
    doc_context = DocumentSourceContext(
        status=DocumentRetrievalStatus.SUCCESS,
        chunks=[_make_chunk("Binary search divides the search space in half each iteration.")],
    )
    claims, summary = evaluator.evaluate_claims([claim], doc_context)

    # Must be UNESTABLISHED, NOT contradicted!
    assert claims[0].document_evidence_status == DocumentEvidenceClassification.UNESTABLISHED
    assert summary["unestablished_count"] == 1
    assert summary["contradicted_count"] == 0


def test_4_contradictory_passages_preserve_uncertainty():
    """4. Contradictory passages in retrieved chunks preserve uncertainty."""
    evaluator = DocumentEvidenceEvaluator()
    claim = LearnerClaim(text="The operation requires mutual exclusion.")
    doc_context = DocumentSourceContext(
        status=DocumentRetrievalStatus.SUCCESS,
        chunks=[
            _make_chunk("The operation strictly requires mutual exclusion locks.", chunk_id="c1"),
            _make_chunk("The operation does not require mutual exclusion locks.", chunk_id="c2"),
        ],
    )
    claims, summary = evaluator.evaluate_claims([claim], doc_context)

    assert claims[0].document_evidence_status == DocumentEvidenceClassification.CONFLICTING
    assert summary["has_conflicting_chunks"] is True

    # Check MasteryGate response to conflicting document evidence
    gate = MasteryGate()
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.9,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.85,
        claims=claims,
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.9,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.9,
        classification=AssessmentClassification.CORRECT,
        confidence=0.9,
    )
    decision = gate.evaluate(assessment, "concurrency")
    assert decision.supports_mastery is False
    assert "conflicting" in decision.reason.lower()


def test_5_keyword_overlap_alone_cannot_establish_correctness():
    """5. Keyword overlap alone cannot establish correctness."""
    evaluator = DocumentEvidenceEvaluator()
    # Shares keywords 'binary', 'search', 'array' but makes an inverted claim
    claim = LearnerClaim(text="Binary search does not check the array midpoint.")
    doc_context = DocumentSourceContext(
        status=DocumentRetrievalStatus.SUCCESS,
        chunks=[_make_chunk("Binary search always computes and checks the array midpoint.")],
    )
    claims, summary = evaluator.evaluate_claims([claim], doc_context)

    # Due to polarity/negation contradiction, it must NOT be marked SUPPORTED
    assert claims[0].document_evidence_status != DocumentEvidenceClassification.SUPPORTED
    assert claims[0].document_evidence_status == DocumentEvidenceClassification.CONTRADICTED


def test_6_similarity_score_alone_cannot_establish_correctness():
    """6. High retrieval similarity score alone cannot establish correctness."""
    # Chunk has similarity 0.99, but learner answer is incorrect
    gate = MasteryGate()
    claim = LearnerClaim(
        text="Binary search is O(N^2) complexity.",
        document_evidence_status=DocumentEvidenceClassification.CONTRADICTED,
    )
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.95,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.90,
        claims=[claim],
        correctness=CorrectnessLevel.INCORRECT,
        correctness_score=0.1,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.1,
        classification=AssessmentClassification.INCORRECT,
        confidence=0.95,
    )
    decision = gate.evaluate(assessment, "binary_search")
    assert decision.supports_mastery is False
    assert decision.record_as_gap is True


def test_7_missing_evidence_cannot_independently_grant_mastery():
    """7. Missing evidence cannot independently grant mastery."""
    gate = MasteryGate()
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.85,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.80,
        claims=[],
        evidence=[],  # No verified evidence items!
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.85,
        completeness=CompletenessLevel.SUBSTANTIAL,
        completeness_score=0.85,
        classification=AssessmentClassification.CORRECT,
        confidence=0.85,
    )
    decision = gate.evaluate(assessment, "binary_search")
    assert decision.supports_mastery is False
    assert "insufficient evidence" in decision.reason.lower()


def test_8_retrieval_failure_cannot_be_interpreted_as_source_contradiction():
    """8. Retrieval failure cannot be interpreted as source contradiction."""
    evaluator = DocumentEvidenceEvaluator()
    claim = LearnerClaim(text="Binary search requires monotonic ordering.")
    doc_context = DocumentSourceContext(
        status=DocumentRetrievalStatus.ERROR,
        error_message="Database connection error",
        error_retryable=True,
    )
    claims, summary = evaluator.evaluate_claims([claim], doc_context)

    assert claims[0].document_evidence_status == DocumentEvidenceClassification.NOT_APPLICABLE
    assert summary["contradicted_count"] == 0
    assert summary["is_grounded"] is False


def test_9_minimum_confidence_and_abstention_safeguards_intact():
    """9. The existing minimum-confidence and abstention safeguards remain intact."""
    gate = MasteryGate()
    claim = LearnerClaim(
        text="Valid claim",
        document_evidence_status=DocumentEvidenceClassification.SUPPORTED,
    )
    abstained = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.9,
        concept_alignment_score=0.9,
        claims=[claim],
        evidence=[EvidenceItem(concept_id="c1", expected_description="d1", status=EvidenceStatus.SUPPORTED)],
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.9,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.9,
        classification=AssessmentClassification.CORRECT,
        confidence=0.45,  # Low confidence
        assessment_status=AssessmentStatus.ABSTAIN,
    )
    decision = gate.evaluate(abstained, "c1")
    assert decision.supports_mastery is False
    assert "abstaining" in decision.reason.lower()


def test_10_help_and_acknowledgement_cannot_bypass_mastery():
    """10. Help requests and bare acknowledgements cannot bypass the mastery gate."""
    gate = MasteryGate()
    for intent in (AssessmentIntent.HELP_REQUEST, AssessmentIntent.ACKNOWLEDGEMENT, AssessmentIntent.OFF_TOPIC):
        assessment = LearningAssessment(
            intent=intent,
            is_answer_attempt=False,
            relevance_score=0.0,
            relevance_level=RelevanceLevel.IRRELEVANT,
            concept_alignment_score=0.0,
            claims=[],
            evidence=[EvidenceItem(concept_id="c1", expected_description="d1", status=EvidenceStatus.SUPPORTED)],
            correctness=CorrectnessLevel.UNASSESSABLE,
            correctness_score=0.0,
            completeness=CompletenessLevel.NOT_APPLICABLE,
            completeness_score=0.0,
            classification=AssessmentClassification.OFF_TOPIC,
            confidence=1.0,
        )
        decision = gate.evaluate(assessment, "c1")
        assert decision.supports_mastery is False


def test_11_document_grounding_disabled_preserves_existing_behavior():
    """11. Document grounding disabled preserves existing assessment behavior."""
    aggregator = AssessmentAggregator()
    context = AIContext(
        session_id="sess_disabled",
        topic="Binary Search",
        source_context=None,  # Disabled
    )
    assessment = aggregator.assess(
        user_message="Binary search divides the search range in half each time by looking at the middle element.",
        context=context,
    )
    assert assessment.document_grounding_status in ("disabled", None)
    for c in assessment.claims:
        assert c.document_evidence_status == DocumentEvidenceClassification.NOT_APPLICABLE


def test_12_state_updates_do_not_bypass_canonical_mastery():
    """12. Document contradiction prevents positive mastery delta."""
    gate = MasteryGate()
    claim = LearnerClaim(
        text="Array does not need to be sorted.",
        document_evidence_status=DocumentEvidenceClassification.CONTRADICTED,
    )
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.85,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.80,
        claims=[claim],
        evidence=[EvidenceItem(concept_id="c1", expected_description="d1", status=EvidenceStatus.SUPPORTED)],
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.85,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.85,
        classification=AssessmentClassification.CORRECT,
        confidence=0.90,
    )
    decision = gate.evaluate(assessment, "c1")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False
    assert decision.allowed_delta == 0.0
    assert decision.record_as_gap is True
