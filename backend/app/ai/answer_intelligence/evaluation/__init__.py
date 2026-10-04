"""Evaluation package for Answer Intelligence."""
from backend.app.ai.answer_intelligence.evaluation.benchmark_dataset import (
    BenchmarkCase,
    BENCHMARK_CASES_DATA,
    ALL_BENCHMARK_CASES,
)
from backend.app.ai.answer_intelligence.evaluation.adversarial_dataset import (
    ADVERSARIAL_BENCHMARK_CASES,
)
from backend.app.ai.answer_intelligence.evaluation.benchmark import BenchmarkRunner
from backend.app.ai.answer_intelligence.evaluation.metrics import (
    EvaluationMetrics,
    compute_metrics,
)

__all__ = [
    "BenchmarkCase",
    "BENCHMARK_CASES_DATA",
    "ALL_BENCHMARK_CASES",
    "ADVERSARIAL_BENCHMARK_CASES",
    "BenchmarkRunner",
    "EvaluationMetrics",
    "compute_metrics",
]
