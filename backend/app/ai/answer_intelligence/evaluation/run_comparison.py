"""
Comparison runner for Milestone C Answer Intelligence providers:
1. LocalAssessmentProvider (Baseline Lexical)
2. SemanticEmbeddingProvider (Dense MiniLM Baseline)
3. HybridSemanticProvider (Milestone C Enhanced Asymmetric & Structured Safeguards)

Outputs structured, reproducible comparison metrics and JSON artifacts across all 255 benchmark cases.
"""
import argparse
import json
import os
import sys
from typing import Any, Dict

from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.evaluation.benchmark import BenchmarkRunner
from backend.app.ai.answer_intelligence.evaluation.benchmark_dataset import ALL_BENCHMARK_CASES
from backend.app.ai.answer_intelligence.providers.hybrid_provider import HybridSemanticProvider
from backend.app.ai.answer_intelligence.providers.local_model import LocalAssessmentProvider
from backend.app.ai.answer_intelligence.providers.semantic_embedding_provider import SemanticEmbeddingProvider


def run_provider_comparison(output_json: str = "docs/ai_milestone_c_provider_comparison.json") -> Dict[str, Any]:
    providers = {
        "Baseline Local": LocalAssessmentProvider(),
        "Semantic Embedding": SemanticEmbeddingProvider(),
        "Hybrid Semantic": HybridSemanticProvider(),
    }

    results: Dict[str, Any] = {}
    total_cases = len(ALL_BENCHMARK_CASES)
    print(f"Running Milestone C comparison benchmark across {total_cases} cases...\n")

    for name, prov in providers.items():
        print(f"Evaluating provider: {name}...")
        aggregator = AssessmentAggregator(provider=prov)
        runner = BenchmarkRunner(aggregator=aggregator)
        metrics = runner.run_benchmark(cases=ALL_BENCHMARK_CASES)
        results[name] = {
            "metrics": metrics.model_dump(),
            "details": metrics.details,
            "provider_class": prov.__class__.__name__,
        }
        print(f"Completed {name}.\n")

    # Save to JSON
    out_dir = os.path.dirname(output_json)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    summary_payload = {
        "benchmark_version": "AI Milestone C",
        "total_cases": total_cases,
        "dataset_domains": 12,
        "results": results,
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)
    print(f"Saved machine-readable comparison results to {output_json}\n")

    # Print Table
    print("=" * 95)
    print(f"AI MILESTONE C — PROVIDER COMPARISON BENCHMARK RESULTS ({total_cases} Labeled Cases)")
    print("=" * 95)
    header = f"{'Metric':<32} | {'Baseline Local':<16} | {'Semantic Embedding':<18} | {'Hybrid Semantic (C)':<18}"
    print(header)
    print("-" * len(header))

    keys = [
        ("total_samples", "Total Cases", "int"),
        ("intent_accuracy", "Intent Accuracy", "pct"),
        ("relevance_accuracy", "Relevance Accuracy", "pct"),
        ("correctness_accuracy", "Correctness Accuracy", "pct"),
        ("completeness_accuracy", "Completeness Accuracy", "pct"),
        ("misconception_precision", "Misconception Precision", "pct"),
        ("misconception_recall", "Misconception Recall", "pct"),
        ("mastery_precision", "Mastery Precision", "pct"),
        ("mastery_recall", "Mastery Recall", "pct"),
        ("false_mastery_rate", "FALSE MASTERY RATE (Safety)", "pct"),
        ("false_rejection_rate", "False Rejection Rate", "pct"),
        ("irrelevant_acceptance_rate", "Irrel. Acceptance Rate", "pct"),
        ("abstention_rate", "Abstention Rate", "pct"),
        ("average_latency_ms", "Latency Avg (ms)", "float"),
        ("p95_latency_ms", "Latency P95 (ms)", "float"),
        ("cold_start_latency_ms", "Cold Start (ms)", "float"),
    ]

    for k, label, typ in keys:
        b_val = results["Baseline Local"]["metrics"].get(k, 0)
        s_val = results["Semantic Embedding"]["metrics"].get(k, 0)
        h_val = results["Hybrid Semantic"]["metrics"].get(k, 0)

        def fmt(val: Any) -> str:
            if typ == "pct":
                return f"{float(val) * 100:.1f}%"
            elif typ == "float":
                return f"{float(val):.2f}"
            return str(val)

        print(f"{label:<32} | {fmt(b_val):<16} | {fmt(s_val):<18} | {fmt(h_val):<18}")

    print("=" * 95)
    return summary_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Milestone C Answer Intelligence provider comparison.")
    parser.add_argument("--output", default="docs/ai_milestone_c_provider_comparison.json", help="Path to output JSON.")
    args = parser.parse_args()
    run_provider_comparison(output_json=args.output)
