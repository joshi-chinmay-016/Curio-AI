"""
Unit tests validating the expanded semantic benchmark dataset (Milestone B).
Verifies:
- Minimum 100 cases requirement (105 cases present).
- Representation across all 11 required CS domains.
- Representation across required assessment categories.
- Valid machine-evaluable ground truth schema.
"""
import pytest
from backend.app.ai.answer_intelligence.evaluation.benchmark_dataset import (
    ALL_BENCHMARK_CASES,
    BENCHMARK_CASES_DATA,
    BenchmarkCase,
)


def test_benchmark_dataset_size_and_schema():
    """Verify that the benchmark dataset contains at least 250 structured cases for Milestone C."""
    assert len(BENCHMARK_CASES_DATA) >= 250
    assert len(ALL_BENCHMARK_CASES) == len(BENCHMARK_CASES_DATA)

    # Check uniqueness of IDs
    ids = [c.id for c in BENCHMARK_CASES_DATA]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found in benchmark dataset: {len(ids)} vs {len(set(ids))}"


def test_benchmark_dataset_domain_coverage():
    """Verify coverage across all 12 computer science domains specified in Milestone C."""
    required_domains = {
        "DBMS",
        "Operating Systems",
        "Computer Networks",
        "Data Structures",
        "Algorithms",
        "OOP",
        "Python",
        "JavaScript",
        "Backend",
        "Distributed Systems",
        "Machine Learning",
        "System Design",
        "Software Engineering",
    }
    present_domains = {c.domain for c in BENCHMARK_CASES_DATA}
    missing = required_domains - present_domains
    assert not missing, f"Missing required domains in benchmark dataset: {missing}"


def test_benchmark_dataset_category_coverage():
    """Verify representation across intent, relevance, correctness, and language categories."""
    categories = {c.category for c in BENCHMARK_CASES_DATA}
    assert "correct_standard" in categories
    assert "misconception" in categories
    assert "language_analogy" in categories
    assert "language_noise" in categories
    assert "partial_answer" in categories
    assert "related_wrong_concept" in categories
    assert "technically_true_irrelevant" in categories
    assert "mixed_claims" in categories
    assert "intent_help" in categories
    assert "intent_clarification" in categories
    assert "intent_acknowledgment" in categories
    assert "intent_off_topic" in categories
    assert "intent_nonsense" in categories


def test_benchmark_dataset_ground_truth_integrity():
    """Verify every sample contains valid, consistent ground truth labels."""
    for case in BENCHMARK_CASES_DATA:
        assert case.id and len(case.id) > 0
        assert case.question and len(case.question) > 0
        assert case.learner_answer and len(case.learner_answer) > 0
        assert case.target_concept and len(case.target_concept) > 0
        assert case.concept_definition and len(case.concept_definition) > 0

        # Ground truth mutual exclusivity
        if case.should_grant_mastery:
            assert not case.should_deny_mastery, f"Case {case.id} has contradictory mastery ground truth"
            assert case.expected_correctness == "CORRECT"
            assert not case.has_misconception

        if case.has_misconception:
            assert case.should_deny_mastery, f"Case {case.id} has misconception but does not deny mastery"

        # Conversion to dictionary format
        d = case.to_eval_dict()
        assert "expected" in d
        assert "intent" in d["expected"]
        assert "relevance" in d["expected"]
        assert "correctness" in d["expected"]
