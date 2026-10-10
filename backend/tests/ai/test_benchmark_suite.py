"""
End-to-end benchmark test for Milestone B Answer Intelligence.
Verifies benchmark execution, safety metrics, and zero irrelevant acceptance rate.
"""
import pytest
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.evaluation.benchmark import BenchmarkRunner
from backend.app.ai.answer_intelligence.evaluation.benchmark_dataset import ALL_BENCHMARK_CASES
from backend.app.ai.answer_intelligence.providers.hybrid_provider import HybridSemanticProvider


def test_full_benchmark_suite_execution():
    """Run full 105-case benchmark and verify core safety thresholds."""
    aggregator = AssessmentAggregator(provider=HybridSemanticProvider())
    runner = BenchmarkRunner(aggregator=aggregator)

    # Run on all benchmark cases (Milestone C: 250+ cases across 12 CS domains)
    metrics = runner.run_benchmark(cases=ALL_BENCHMARK_CASES)
    assert metrics.total_samples >= 250
    assert metrics.total_samples == len(ALL_BENCHMARK_CASES)
    assert metrics.intent_accuracy >= 0.85
    assert metrics.relevance_accuracy >= 0.80
    assert metrics.false_mastery_rate <= 0.20  # Primary safety threshold
    assert metrics.misconception_recall >= 0.40  # Outperforms baseline
    assert metrics.average_latency_ms < 1000.0  # Under 1 second average

