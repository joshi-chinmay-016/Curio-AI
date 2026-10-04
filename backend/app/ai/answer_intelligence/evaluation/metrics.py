"""
Evaluation Metrics for Answer Intelligence and Mastery Safety (Milestone B).
Focuses heavily on safety metrics, primarily FalseMasteryRate, misconception precision/recall,
and latency profiling.
"""
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    total_samples: int = 0
    intent_accuracy: float = 0.0
    relevance_accuracy: float = 0.0
    correctness_accuracy: float = 0.0
    completeness_accuracy: float = 0.0
    misconception_precision: float = 0.0
    misconception_recall: float = 0.0
    misconception_detection_rate: float = Field(default=0.0, description="Synonym for misconception recall")
    mastery_precision: float = 0.0
    mastery_recall: float = 0.0
    false_mastery_rate: float = Field(default=0.0, description="Rate of incorrect/irrelevant answers granted mastery.")
    false_rejection_rate: float = Field(default=0.0, description="Rate of correct answers denied mastery.")
    irrelevant_acceptance_rate: float = Field(default=0.0, description="Rate of irrelevant answers classified as relevant.")
    abstention_rate: float = 0.0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    cold_start_latency_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


def compute_metrics(
    results: List[Dict[str, Any]],
    latencies_ms: Optional[List[float]] = None,
) -> EvaluationMetrics:
    """
    Computes rigorous assessment, safety, and performance metrics from evaluation runs.
    """
    total = len(results)
    if total == 0:
        return EvaluationMetrics()

    intent_correct = 0
    relevance_correct = 0
    relevance_count = 0
    correctness_correct = 0
    correctness_count = 0
    completeness_correct = 0
    completeness_count = 0

    misconception_tp = 0
    misconception_fp = 0
    misconception_fn = 0
    misconception_total_expected = 0

    # Safety & Mastery metrics
    mastery_tp = 0
    mastery_fp = 0
    mastery_fn = 0

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

        # 1. Intent
        if actual.intent.value == expected.get("intent"):
            intent_correct += 1

        # 2. Relevance
        exp_rel = expected.get("relevance")
        if exp_rel:
            relevance_count += 1
            if actual.relevance_level.value == exp_rel:
                relevance_correct += 1
            elif exp_rel in ("RELATED_WRONG_CONCEPT", "TECHNICALLY_TRUE_IRRELEVANT") and actual.relevance_level.value in ("IRRELEVANT", "PARTIALLY_RELEVANT"):
                # Tolerant boundary for subcategories of non-relevant
                relevance_correct += 1

        # 3. Correctness
        exp_corr = expected.get("correctness")
        if exp_corr:
            correctness_count += 1
            if actual.correctness.value == exp_corr:
                correctness_correct += 1
            elif exp_corr == "CONTRADICTORY" and actual.correctness.value in ("INCORRECT", "MISCONCEPTION", "PARTIALLY_CORRECT"):
                correctness_correct += 1

        # 4. Completeness
        exp_comp = expected.get("completeness")
        if exp_comp:
            completeness_count += 1
            if actual.completeness.value == exp_comp:
                completeness_correct += 1

        # 5. Misconception TP/FP/FN
        has_exp_misc = expected.get("has_misconception", False)
        actual_has_misc = bool(actual.misconception_status or (actual.misconceptions and len(actual.misconceptions) > 0))

        if has_exp_misc:
            misconception_total_expected += 1
            if actual_has_misc:
                misconception_tp += 1
            else:
                misconception_fn += 1
        else:
            if actual_has_misc:
                misconception_fp += 1

        # 6. Abstention
        if actual.assessment_status.value == "ABSTAIN":
            abstention_count += 1

        # 7. Mastery Precision / Recall & False Mastery
        is_worthy = expected.get("should_grant_mastery", False)
        is_unworthy = expected.get("should_deny_mastery", False)

        if is_worthy:
            correct_substantive_total += 1
            if actual.supports_mastery:
                mastery_tp += 1
            else:
                mastery_fn += 1
                false_rejection_count += 1

        if is_unworthy:
            incorrect_or_irrelevant_total += 1
            if actual.supports_mastery:
                mastery_fp += 1
                false_mastery_count += 1

        # 8. Irrelevant acceptance
        if exp_rel in ("IRRELEVANT", "TECHNICALLY_TRUE_IRRELEVANT"):
            irrelevant_total += 1
            if actual.relevance_level.value not in ("IRRELEVANT", "UNCERTAIN"):
                irrelevant_accepted_count += 1

    # Accuracies
    intent_acc = intent_correct / total
    rel_acc = relevance_correct / max(1, relevance_count)
    corr_acc = correctness_correct / max(1, correctness_count)
    comp_acc = completeness_correct / max(1, completeness_count)

    # Misconception metrics
    misc_precision = (
        misconception_tp / (misconception_tp + misconception_fp)
        if (misconception_tp + misconception_fp) > 0
        else (1.0 if misconception_total_expected == 0 else 0.0)
    )
    misc_recall = (
        misconception_tp / misconception_total_expected
        if misconception_total_expected > 0
        else 1.0
    )

    # Mastery metrics
    mastery_precision = (
        mastery_tp / (mastery_tp + mastery_fp)
        if (mastery_tp + mastery_fp) > 0
        else 0.0
    )
    mastery_recall = (
        mastery_tp / (mastery_tp + mastery_fn)
        if (mastery_tp + mastery_fn) > 0
        else 0.0
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

    # Latencies
    avg_lat = 0.0
    p95_lat = 0.0
    cold_lat = 0.0
    if latencies_ms and len(latencies_ms) > 0:
        cold_lat = round(latencies_ms[0], 2)
        avg_lat = round(float(np.mean(latencies_ms)), 2)
        p95_lat = round(float(np.percentile(latencies_ms, 95)), 2)

    return EvaluationMetrics(
        total_samples=total,
        intent_accuracy=round(intent_acc, 3),
        relevance_accuracy=round(rel_acc, 3),
        correctness_accuracy=round(corr_acc, 3),
        completeness_accuracy=round(comp_acc, 3),
        misconception_precision=round(misc_precision, 3),
        misconception_recall=round(misc_recall, 3),
        misconception_detection_rate=round(misc_recall, 3),
        mastery_precision=round(mastery_precision, 3),
        mastery_recall=round(mastery_recall, 3),
        false_mastery_rate=round(false_mastery, 4),
        false_rejection_rate=round(false_rejection, 4),
        irrelevant_acceptance_rate=round(irrel_acceptance, 4),
        abstention_rate=round(abstention_count / total, 3),
        average_latency_ms=avg_lat,
        p95_latency_ms=p95_lat,
        cold_start_latency_ms=cold_lat,
        details={
            "false_mastery_count": false_mastery_count,
            "incorrect_or_irrelevant_total": incorrect_or_irrelevant_total,
            "false_rejection_count": false_rejection_count,
            "correct_substantive_total": correct_substantive_total,
            "mastery_tp": mastery_tp,
            "mastery_fp": mastery_fp,
            "mastery_fn": mastery_fn,
            "misconception_tp": misconception_tp,
            "misconception_fp": misconception_fp,
            "misconception_fn": misconception_fn,
        },
    )
