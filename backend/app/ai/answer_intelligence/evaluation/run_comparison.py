"""
Comparison runner for Milestone B Answer Intelligence providers:
1. LocalAssessmentProvider (Baseline)
2. SemanticEmbeddingProvider (Specialized Dense NLI / Embedding)
3. HybridSemanticProvider (Selected Hybrid Architecture)
"""
import sys
import json
from backend.app.ai.answer_intelligence.providers.local_model import LocalAssessmentProvider
from backend.app.ai.answer_intelligence.providers.semantic_embedding_provider import SemanticEmbeddingProvider
from backend.app.ai.answer_intelligence.providers.hybrid_provider import HybridSemanticProvider
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.evaluation.benchmark import BenchmarkRunner
from backend.app.ai.answer_intelligence.evaluation.benchmark_dataset import ALL_BENCHMARK_CASES

def main():
    providers = {
        "Baseline Local": LocalAssessmentProvider(),
        "Semantic Embedding": SemanticEmbeddingProvider(),
        "Hybrid Semantic": HybridSemanticProvider(),
    }

    results = {}
    print(f"Running comparison benchmark across {len(ALL_BENCHMARK_CASES)} cases...\n")

    for name, prov in providers.items():
        print(f"Evaluating: {name}...")
        aggregator = AssessmentAggregator(provider=prov)
        runner = BenchmarkRunner(aggregator=aggregator)
        metrics = runner.run_benchmark(cases=ALL_BENCHMARK_CASES)
        results[name] = metrics.model_dump()
        print(f"Done {name}.\n")

    print("=========================================================================================")
    print("AI MILESTONE B — PROVIDER COMPARISON BENCHMARK RESULTS (105 Machine-Labeled Cases)")
    print("=========================================================================================")
    header = f"{'Metric':<30} | {'Baseline Local':<18} | {'Semantic Embedding':<18} | {'Hybrid Semantic':<18}"
    print(header)
    print("-" * len(header))

    keys = [
        ("total_samples", "Total Cases"),
        ("intent_accuracy", "Intent Accuracy"),
        ("relevance_accuracy", "Relevance Accuracy"),
        ("correctness_accuracy", "Correctness Accuracy"),
        ("completeness_accuracy", "Completeness Accuracy"),
        ("misconception_precision", "Misconception Precision"),
        ("misconception_recall", "Misconception Recall"),
        ("mastery_precision", "Mastery Precision"),
        ("mastery_recall", "Mastery Recall"),
        ("false_mastery_rate", "False Mastery Rate"),
        ("false_rejection_rate", "False Rejection Rate"),
        ("irrelevant_acceptance_rate", "Irrel. Acceptance Rate"),
        ("abstention_rate", "Abstention Rate"),
        ("average_latency_ms", "Latency Avg (ms)"),
        ("p95_latency_ms", "Latency P95 (ms)"),
        ("cold_start_latency_ms", "Cold Start (ms)"),
    ]

    for k, label in keys:
        b_val = results["Baseline Local"].get(k, 0)
        s_val = results["Semantic Embedding"].get(k, 0)
        h_val = results["Hybrid Semantic"].get(k, 0)

        def fmt(val):
            if isinstance(val, float):
                return f"{val:.4f}"
            return str(val)

        print(f"{label:<30} | {fmt(b_val):<18} | {fmt(s_val):<18} | {fmt(h_val):<18}")

    print("=========================================================================================")

if __name__ == "__main__":
    main()
