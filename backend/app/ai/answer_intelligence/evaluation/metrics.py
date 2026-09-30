"""
Evaluation Metrics for Answer Intelligence and Mastery Safety.
Focuses heavily on safety metrics, primarily FalseMasteryRate.
"""
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    total_samples: int = 0
    intent_accuracy: float = 0.0
    relevance_accuracy: float = 0.0
    correctness_accuracy: float = 0.0
    misconception_detection_rate: float = 0.0
    false_mastery_rate: float = Field(default=0.0, description="Rate of incorrect/irrelevant answers granted mastery.")
    false_rejection_rate: float = Field(default=0.0, description="Rate of correct answers denied mastery.")
    irrelevant_acceptance_rate: float = Field(default=0.0, description="Rate of irrelevant answers classified as relevant.")
    abstention_rate: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


def compute_metrics(results: List[Dict[str, Any]]) -> EvaluationMetrics:
    """
    Computes rigorous assessment and safety metrics from evaluation runs.
    """
    total = len(results)
    if total == 0:
        return EvaluationMetrics()

    intent_correct = 0
    relevance_correct = 0
    correctness_correct = 0

    misconception_true_positives = 0
    misconception_total_expected = 0

    # Safety metrics
    incorrect_or_irrelevant_total = 0
    false_mastery_count = 0

    correct_substantive_total = 0
    false_rejection_count = 0

    irrelevant_total = 0
    irrelevant_accepted_count = 0

    abstention_count = 0

    for r in results:
        expected = r["expected"]
        actual = r["actual"]

        # Intent
        if actual.intent.value == expected.get("intent"):
            intent_correct += 1

        # Relevance
        exp_rel = expected.get("relevance")
        if exp_rel and actual.relevance_level.value == exp_rel:
            relevance_correct += 1

        # Correctness
        exp_corr = expected.get("correctness")
        if exp_corr and actual.correctness.value == exp_corr:
            correctness_correct += 1

        # Misconceptions
        if expected.get("has_misconception"):
            misconception_total_expected += 1
            if actual.misconception_status or actual.misconceptions:
                misconception_true_positives += 1

        # Abstention
        if actual.assessment_status.value == "ABSTAIN":
            abstention_count += 1

        # Safety: Incorrect or Irrelevant responses
        is_unworthy = expected.get("should_deny_mastery", False)
        if is_unworthy:
            incorrect_or_irrelevant_total += 1
            if actual.supports_mastery:
                false_mastery_count += 1

        # Safety: Substantive correct responses
        is_worthy = expected.get("should_grant_mastery", False)
        if is_worthy:
            correct_substantive_total += 1
            if not actual.supports_mastery:
                false_rejection_count += 1

        # Irrelevant acceptance
        if exp_rel == "IRRELEVANT":
            irrelevant_total += 1
            if actual.relevance_level.value != "IRRELEVANT":
                irrelevant_accepted_count += 1

    intent_acc = intent_correct / total
    rel_acc = relevance_correct / max(1, sum(1 for r in results if "relevance" in r["expected"]))
    corr_acc = correctness_correct / max(1, sum(1 for r in results if "correctness" in r["expected"]))

    misc_rate = (
        misconception_true_positives / misconception_total_expected
        if misconception_total_expected > 0
        else 1.0
    )

    false_mastery = (
        false_mastery_count / incorrect_or_irrelevant_total
        if incorrect_or_irrelevant_total > 0
        else 0.0
    )

    false_rejection = (
        false_rejection_count / correct_substantive_total
        if correct_substantive_total > 0
        else 0.0
    )

    irrel_acceptance = (
        irrelevant_accepted_count / irrelevant_total
        if irrelevant_total > 0
        else 0.0
    )

    return EvaluationMetrics(
        total_samples=total,
        intent_accuracy=round(intent_acc, 3),
        relevance_accuracy=round(rel_acc, 3),
        correctness_accuracy=round(corr_acc, 3),
        misconception_detection_rate=round(misc_rate, 3),
        false_mastery_rate=round(false_mastery, 4),
        false_rejection_rate=round(false_rejection, 4),
        irrelevant_acceptance_rate=round(irrel_acceptance, 4),
        abstention_rate=round(abstention_count / total, 3),
        details={
            "false_mastery_count": false_mastery_count,
            "incorrect_or_irrelevant_total": incorrect_or_irrelevant_total,
            "false_rejection_count": false_rejection_count,
            "correct_substantive_total": correct_substantive_total,
        },
    )
