"""
Benchmark Runner for Curio AI Answer Intelligence (Milestone B).
Executes the expanded semantic benchmark suite against an AssessmentAggregator instance
and reports comprehensive safety, accuracy, and latency metrics, especially FalseMasteryRate.
"""
import logging
import time
from typing import Any, Dict, List, Optional

from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.evaluation.adversarial_dataset import ADVERSARIAL_BENCHMARK_CASES
from backend.app.ai.answer_intelligence.evaluation.benchmark_dataset import ALL_BENCHMARK_CASES
from backend.app.ai.answer_intelligence.evaluation.metrics import EvaluationMetrics, compute_metrics
from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode, CurrentQuestion

logger = logging.getLogger("curio.ai.answer_intelligence.benchmark")


class BenchmarkRunner:
    """Runs adversarial and semantic evaluations and outputs structured safety metrics."""

    def __init__(self, aggregator: Optional[AssessmentAggregator] = None):
        self.aggregator = aggregator or AssessmentAggregator()
        self.last_records: List[Dict[str, Any]] = []
        self.last_latencies_ms: List[float] = []

    def run_benchmark(
        self,
        cases: Optional[List[Dict[str, Any]]] = None,
        use_full_suite: bool = False,
        verbose: bool = False,
    ) -> EvaluationMetrics:
        if cases is not None:
            test_cases = cases
        elif use_full_suite:
            test_cases = ALL_BENCHMARK_CASES
        else:
            test_cases = ADVERSARIAL_BENCHMARK_CASES

        eval_records: List[Dict[str, Any]] = []
        latencies_ms: List[float] = []

        for case in test_cases:
            topic = case.get("topic", "General")
            concept = case.get("target_concept", "general_concept")
            q_text = case.get("question", "")
            ans_text = case.get("learner_answer", "")

            # Build minimal context
            curr_q = CurrentQuestion(
                id=f"benchmark_{case.get('id', 'q')}",
                content=q_text,
                concept=concept,
                difficulty=2,
            )
            c_def = case.get("concept_definition", f"Core definition of {concept}")
            c_ev = case.get("expected_evidence", [])
            c_misc = case.get("common_misconceptions", [])

            concept_model = ConceptModel(
                topic=topic,
                concepts=[
                    ConceptNode(
                        id=concept,
                        name=concept.replace("_", " ").title(),
                        definition=c_def,
                        constraints=c_ev,
                        common_misconceptions=c_misc,
                        difficulty_level=2,
                    )
                ],
            )
            context = AIContext(
                topic=topic,
                active_concept=concept,
                current_question=curr_q,
            )

            # Measure inference latency with perf_counter
            t0 = time.perf_counter()
            actual_assessment = self.aggregator.assess(
                user_message=ans_text,
                context=context,
                current_question=curr_q,
                concept_model=concept_model,
                target_concept_override=concept,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(elapsed_ms)

            if verbose:
                logger.info(
                    "Case %s [%s] (%.2fms) -> Intent: %s, Rel: %s (%.2f), Corr: %s (%.2f), Misc: %s, Mastery: %s",
                    case.get("id"),
                    case.get("category"),
                    elapsed_ms,
                    actual_assessment.intent.value,
                    actual_assessment.relevance_level.value,
                    actual_assessment.relevance_score,
                    actual_assessment.correctness.value,
                    actual_assessment.correctness_score,
                    actual_assessment.misconception_status,
                    actual_assessment.supports_mastery,
                )

            eval_records.append({
                "case_id": case.get("id"),
                "category": case.get("category"),
                "expected": case.get("expected", {}),
                "actual": actual_assessment,
                "latency_ms": elapsed_ms,
            })

        self.last_records = eval_records
        self.last_latencies_ms = latencies_ms
        metrics = compute_metrics(eval_records, latencies_ms=latencies_ms)
        return metrics


def print_benchmark_summary(metrics: EvaluationMetrics, title: str = "ANSWER INTELLIGENCE BENCHMARK RESULTS"):
    print("=" * 65)
    print(title)
    print("=" * 65)
    print(f"Total Samples Evaluated:      {metrics.total_samples}")
    print(f"Intent Accuracy:              {metrics.intent_accuracy * 100:.1f}%")
    print(f"Relevance Accuracy:           {metrics.relevance_accuracy * 100:.1f}%")
    print(f"Correctness Accuracy:         {metrics.correctness_accuracy * 100:.1f}%")
    print(f"Completeness Accuracy:        {metrics.completeness_accuracy * 100:.1f}%")
    print(f"Misconception Precision:      {metrics.misconception_precision * 100:.1f}%")
    print(f"Misconception Recall:         {metrics.misconception_recall * 100:.1f}%")
    print(f"Mastery Precision:            {metrics.mastery_precision * 100:.1f}%")
    print(f"Mastery Recall:               {metrics.mastery_recall * 100:.1f}%")
    print(f"FALSE MASTERY RATE (Safety):  {metrics.false_mastery_rate * 100:.2f}%")
    print(f"False Rejection Rate:         {metrics.false_rejection_rate * 100:.2f}%")
    print(f"Irrelevant Acceptance Rate:   {metrics.irrelevant_acceptance_rate * 100:.2f}%")
    print(f"Abstention Rate:              {metrics.abstention_rate * 100:.1f}%")
    print(f"Cold-Start Latency:           {metrics.cold_start_latency_ms:.2f} ms")
    print(f"Average Latency:              {metrics.average_latency_ms:.2f} ms")
    print(f"p95 Latency:                  {metrics.p95_latency_ms:.2f} ms")
    print("=" * 65)


if __name__ == "__main__":
    runner = BenchmarkRunner()
    metrics = runner.run_benchmark(use_full_suite=True, verbose=True)
    print_benchmark_summary(metrics, "FULL 105-CASE BENCHMARK RESULTS (BASELINE LOCAL PROVIDER)")
