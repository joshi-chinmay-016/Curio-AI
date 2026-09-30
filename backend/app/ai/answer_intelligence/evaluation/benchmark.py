"""
Benchmark Runner for Curio AI Answer Intelligence.
Executes the adversarial benchmark suite against an AssessmentAggregator instance
and reports comprehensive safety and accuracy metrics, especially FalseMasteryRate.
"""
import logging
from typing import Any, Dict, List, Optional

from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.evaluation.adversarial_dataset import ADVERSARIAL_BENCHMARK_CASES
from backend.app.ai.answer_intelligence.evaluation.metrics import EvaluationMetrics, compute_metrics
from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode, CurrentQuestion

logger = logging.getLogger("curio.ai.answer_intelligence.benchmark")


class BenchmarkRunner:
    """Runs adversarial evaluations and outputs structured safety metrics."""

    def __init__(self, aggregator: Optional[AssessmentAggregator] = None):
        self.aggregator = aggregator or AssessmentAggregator()

    def run_benchmark(
        self,
        cases: Optional[List[Dict[str, Any]]] = None,
        verbose: bool = False,
    ) -> EvaluationMetrics:
        test_cases = cases or ADVERSARIAL_BENCHMARK_CASES
        eval_records: List[Dict[str, Any]] = []

        for case in test_cases:
            topic = case["topic"]
            concept = case["target_concept"]
            q_text = case["question"]
            ans_text = case["learner_answer"]

            # Build minimal context
            curr_q = CurrentQuestion(
                id="benchmark_q",
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

            # Execute assessment pipeline
            actual_assessment = self.aggregator.assess(
                user_message=ans_text,
                context=context,
                current_question=curr_q,
                concept_model=concept_model,
                target_concept_override=concept,
            )

            if verbose:
                logger.info(
                    "Case %s [%s] -> Intent: %s, Rel: %s (%.2f), Corr: %s (%.2f), SupportsMastery: %s",
                    case["id"],
                    case["category"],
                    actual_assessment.intent.value,
                    actual_assessment.relevance_level.value,
                    actual_assessment.relevance_score,
                    actual_assessment.correctness.value,
                    actual_assessment.correctness_score,
                    actual_assessment.supports_mastery,
                )

            eval_records.append({
                "case_id": case["id"],
                "category": case["category"],
                "expected": case["expected"],
                "actual": actual_assessment,
            })

        self.last_records = eval_records
        metrics = compute_metrics(eval_records)
        return metrics


if __name__ == "__main__":
    runner = BenchmarkRunner()
    metrics = runner.run_benchmark(verbose=True)
    print("=" * 60)
    print("ANSWER INTELLIGENCE BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Samples Evaluated:      {metrics.total_samples}")
    print(f"Intent Accuracy:              {metrics.intent_accuracy * 100:.1f}%")
    print(f"Relevance Accuracy:           {metrics.relevance_accuracy * 100:.1f}%")
    print(f"Correctness Accuracy:         {metrics.correctness_accuracy * 100:.1f}%")
    print(f"Misconception Detection Rate: {metrics.misconception_detection_rate * 100:.1f}%")
    print(f"FALSE MASTERY RATE (Safety):  {metrics.false_mastery_rate * 100:.2f}%")
    print(f"False Rejection Rate:         {metrics.false_rejection_rate * 100:.2f}%")
    print(f"Irrelevant Acceptance Rate:   {metrics.irrelevant_acceptance_rate * 100:.2f}%")
    print(f"Abstention Rate:              {metrics.abstention_rate * 100:.1f}%")
    print("=" * 60)
