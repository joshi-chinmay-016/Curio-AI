"""
Adversarial Benchmark Tests for Curio AI Answer Intelligence.
Verifies safety and pedagogical assessment accuracy across the adversarial dataset.
Asserts that FalseMasteryRate is 0.0% and no incorrect/irrelevant responses grant mastery.
"""
import pytest
from backend.app.ai.answer_intelligence.evaluation.benchmark import BenchmarkRunner
from backend.app.ai.answer_intelligence.evaluation.adversarial_dataset import ADVERSARIAL_BENCHMARK_CASES


def test_adversarial_benchmark_zero_false_mastery():
    """Verify that false mastery rate across all adversarial cases is strictly 0.0%."""
    runner = BenchmarkRunner()
    metrics = runner.run_benchmark(verbose=False)

    assert metrics.total_samples >= 20
    assert metrics.details.get("false_mastery_count") == 0
    assert metrics.false_mastery_rate == 0.0
    assert metrics.irrelevant_acceptance_rate == 0.0
    assert metrics.false_rejection_rate == 0.0
    assert metrics.intent_accuracy >= 0.95
    assert metrics.relevance_accuracy >= 0.95
    assert metrics.correctness_accuracy >= 0.95
    assert metrics.misconception_detection_rate >= 0.95


@pytest.mark.parametrize("case", [c for c in ADVERSARIAL_BENCHMARK_CASES if c["expected"].get("should_deny_mastery")])
def test_individual_adversarial_cases_deny_mastery(case):
    """Parametrized test ensuring every individual negative/adversarial case denies mastery."""
    runner = BenchmarkRunner()
    metrics = runner.run_benchmark(cases=[case], verbose=False)
    record = runner.last_records[0]
    actual = record["actual"]

    assert not actual.supports_mastery, (
        f"Case '{case['id']}' [{case['category']}] incorrectly granted mastery! "
        f"Answer: '{case['learner_answer']}', Correctness: {actual.correctness.value}, "
        f"Relevance: {actual.relevance_level.value} ({actual.relevance_score:.2f})"
    )


@pytest.mark.parametrize("case", [c for c in ADVERSARIAL_BENCHMARK_CASES if c["expected"].get("should_grant_mastery")])
def test_individual_substantive_cases_grant_mastery(case):
    """Parametrized test ensuring genuinely correct substantive cases grant mastery."""
    runner = BenchmarkRunner()
    metrics = runner.run_benchmark(cases=[case], verbose=False)
    record = runner.last_records[0]
    actual = record["actual"]

    assert actual.supports_mastery, (
        f"Case '{case['id']}' [{case['category']}] was falsely rejected! "
        f"Answer: '{case['learner_answer']}', Correctness: {actual.correctness.value}, "
        f"Relevance: {actual.relevance_level.value} ({actual.relevance_score:.2f})"
    )
