"""
Unit tests for SemanticEmbeddingProvider (Milestone B).
Verifies:
- Dense sentence embedding inference via all-MiniLM-L6-v2.
- Relevance assessment via cosine similarity.
- Negation detection and contradiction handling.
- Analogy and paraphrase evidence matching.
- Misconception projection against known anti-patterns.
- Principled confidence abstention.
"""
import pytest
from backend.app.ai.answer_intelligence.providers.semantic_embedding_provider import (
    SemanticEmbeddingProvider,
    cosine_similarity,
    has_negation,
)
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


@pytest.fixture(scope="module")
def semantic_provider():
    return SemanticEmbeddingProvider()


def test_cosine_similarity_basic():
    """Verify cosine similarity calculation for known vectors."""
    import numpy as np
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 0.0, 0.0])
    v3 = np.array([0.0, 1.0, 0.0])
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0


def test_negation_detection():
    """Verify detection of explicit negative polarity."""
    assert has_negation("Binary search does not work on unsorted lists.")
    assert has_negation("Transactions never commit partially.")
    assert has_negation("Threads cannot share process registers.")
    assert not has_negation("Atomicity guarantees all operations commit together.")
    assert not has_negation("BFS uses a FIFO queue to traverse neighbors.")


def test_semantic_relevance_assessment(semantic_provider):
    """Verify dense relevance scoring distinguishes relevant from irrelevant answers."""
    # Relevant answer
    rel, score = semantic_provider.assess_relevance(
        user_message="Atomicity ensures either every query in the transaction succeeds or everything rolls back.",
        question="What does atomicity guarantee?",
        target_concept="atomicity",
        topic="DBMS",
        expected=ExpectedEvidence(
            concept_id="atomicity",
            objective_type="definition",
            core_components=["all operations commit together", "rolls back on failure"],
        ),
    )
    assert rel == RelevanceLevel.RELEVANT
    assert score >= 0.50

    # Completely irrelevant answer
    rel_irrel, score_irrel = semantic_provider.assess_relevance(
        user_message="The Eiffel Tower is located in Paris, France.",
        question="What does atomicity guarantee?",
        target_concept="atomicity",
        topic="DBMS",
    )
    assert rel_irrel == RelevanceLevel.IRRELEVANT
    assert score_irrel < 0.25


def test_semantic_claim_extraction(semantic_provider):
    """Verify atomic clause extraction and claim typing."""
    claims = semantic_provider.extract_claims(
        user_message="Atomicity is like a light switch: all operations commit, but failure triggers rollback.",
        target_concept="atomicity",
    )
    assert len(claims) >= 2
    types = [c.claim_type for c in claims]
    assert ClaimType.ANALOGY in types or ClaimType.FACTUAL_ASSERTION in types


def test_semantic_misconception_detection(semantic_provider):
    """Verify dense similarity detection against known misconception embeddings."""
    expected = ExpectedEvidence(
        concept_id="atomicity",
        objective_type="mechanism",
        core_components=["all-or-nothing execution", "rollback on failure"],
        common_misconceptions=["transactions can partially commit successful operations"],
    )

    detected = semantic_provider.detect_misconceptions(
        user_message="When an error happens, the database commits the operations that worked and drops the rest.",
        claims=[],
        expected=expected,
    )
    assert len(detected) > 0
    assert any("partially commit" in m.description for m in detected)


def test_semantic_confidence_abstention(semantic_provider):
    """Verify abstention is triggered for borderline relevance."""
    status, conf = semantic_provider.assess_confidence(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        relevance=RelevanceLevel.PARTIALLY_RELEVANT,
        relevance_score=0.35,  # Borderline zone [0.28, 0.42]
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        claims=[LearnerClaim(text="maybe something about databases", confidence=0.5)],
        evidence_items=[],
    )
    assert status == AssessmentStatus.ABSTAIN
    assert conf <= 0.50
