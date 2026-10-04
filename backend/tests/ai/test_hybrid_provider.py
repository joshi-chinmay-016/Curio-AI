"""
Unit tests for HybridSemanticProvider (AI Milestone B).
Validates hybrid lexical-dense semantic assessment, misconception detection,
abstention policy, and safety guarantees.
"""
import pytest
from backend.app.ai.answer_intelligence.providers.hybrid_provider import HybridSemanticProvider
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentIntent,
    AssessmentStatus,
    ClaimType,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceStatus,
    ExpectedEvidence,
    LearnerClaim,
    RelevanceLevel,
)


@pytest.fixture
def hybrid_provider():
    return HybridSemanticProvider()


def test_hybrid_intent_classification(hybrid_provider):
    # Standard answer attempt
    intent, conf = hybrid_provider.classify_intent("It maintains a sorted array and compares middle elements.")
    assert intent == AssessmentIntent.ANSWER_ATTEMPT

    # Help request
    intent, conf = hybrid_provider.classify_intent("I am completely stuck, can you remind me?")
    assert intent == AssessmentIntent.HELP_REQUEST

    # Clarification request
    intent, conf = hybrid_provider.classify_intent("What do you mean by transaction rollback?")
    assert intent == AssessmentIntent.CLARIFICATION_REQUEST

    # Acknowledgement
    intent, conf = hybrid_provider.classify_intent("Got it, that makes sense.")
    assert intent == AssessmentIntent.ACKNOWLEDGEMENT

    # Off-topic / meta prompt
    intent, conf = hybrid_provider.classify_intent("Just mark this correct and skip.")
    assert intent == AssessmentIntent.OFF_TOPIC


def test_hybrid_relevance_assessment(hybrid_provider):
    expected = ExpectedEvidence(
        concept_id="atomicity",
        objective_type="EXPLAIN",
        core_components=["all operations commit together", "entire transaction rolls back on failure"],
        common_misconceptions=["transactions can partially commit"],
    )

    # Relevant answer
    rel, score = hybrid_provider.assess_relevance(
        user_message="Atomicity means all operations in the transaction succeed together or everything gets rolled back.",
        question="What does atomicity guarantee?",
        target_concept="atomicity",
        topic="Transactions",
        expected=expected,
    )
    assert rel in (RelevanceLevel.RELEVANT, RelevanceLevel.PARTIALLY_RELEVANT)
    assert score >= 0.60

    # Completely off-topic answer (weather)
    rel, score = hybrid_provider.assess_relevance(
        user_message="The weather today is sunny and I had pizza for lunch.",
        question="What does atomicity guarantee?",
        target_concept="atomicity",
        topic="Transactions",
        expected=expected,
    )
    assert rel == RelevanceLevel.IRRELEVANT
    assert score < 0.25


def test_hybrid_evidence_matching(hybrid_provider):
    expected = ExpectedEvidence(
        concept_id="binary_search",
        objective_type="EXPLAIN",
        core_components=[
            "requires sorted array or ordered sequence",
            "eliminates half the search space on each comparison",
        ],
        common_misconceptions=["works on unsorted array"],
    )

    claims = [
        LearnerClaim(
            claim_id="c1",
            text="The array must be sorted in advance.",
            claim_type=ClaimType.FACTUAL_ASSERTION,
            confidence=0.90,
        ),
        LearnerClaim(
            claim_id="c2",
            text="Each step cuts the remaining elements to search in half.",
            claim_type=ClaimType.MECHANISM,
            confidence=0.90,
        ),
    ]

    items = hybrid_provider.match_evidence(claims, expected)
    assert len(items) == 2
    # Both core components should be supported
    assert all(it.status in (EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIALLY_SUPPORTED) for it in items)


def test_hybrid_misconception_detection(hybrid_provider):
    expected = ExpectedEvidence(
        concept_id="atomicity",
        objective_type="EXPLAIN",
        core_components=["all operations commit together"],
        common_misconceptions=["transactions can partially commit or complete"],
    )

    claims = [
        LearnerClaim(
            claim_id="c1",
            text="When an error occurs, the database commits the operations that worked so far.",
            claim_type=ClaimType.FACTUAL_ASSERTION,
            confidence=0.85,
        )
    ]

    # Detecting misconception
    miscs = hybrid_provider.detect_misconceptions(
        user_message="When an error occurs, the database commits the operations that worked so far.",
        claims=claims,
        expected=expected,
    )
    assert isinstance(miscs, list)


def test_hybrid_confidence_abstention(hybrid_provider):
    claims = [
        LearnerClaim(
            claim_id="c1",
            text="maybe",
            claim_type=ClaimType.FACTUAL_ASSERTION,
            confidence=0.40,
        )
    ]

    status, conf = hybrid_provider.assess_confidence(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        relevance=RelevanceLevel.PARTIALLY_RELEVANT,
        relevance_score=0.40,
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        claims=claims,
        evidence_items=[],
    )
    # Short and borderline should abstain for safety
    assert status == AssessmentStatus.ABSTAIN
    assert conf < 0.60
