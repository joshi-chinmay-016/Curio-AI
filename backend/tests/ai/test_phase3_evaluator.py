"""
Unit and Integration Tests for SessionEvaluator and ReportBuilder (Phase 3C & 3F).
Verifies:
1. Strong session evaluation
2. Weak session evaluation
3. Mixed session evaluation
4. Teacher-assisted session (resolved gap)
5. Session with unresolved misconception
6. Session with resolved misconception
7. Insufficient evidence session
8. Structured LearningReport generation
"""
import uuid
import pytest
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.report_builder import ReportBuilder
from backend.app.ai.schemas import (
    LearningReport,
    MasteryLevel,
    SessionEvaluation,
    Strategy,
    TurnEvaluation,
)
from backend.app.ai.session_evidence import SessionEvidenceBuilder
from backend.app.ai.session_evaluator import SessionEvaluator


@pytest.fixture
def evaluator():
    provider = MockLLMProvider()
    return SessionEvaluator(provider)


@pytest.fixture
def evidence_builder():
    return SessionEvidenceBuilder()


def test_strong_session_evaluation(evaluator, evidence_builder):
    """Learner demonstrates consistent high performance across turns."""
    messages = [
        {"sender": "AI", "content": "What is binary search?"},
        {"sender": "USER", "content": "An algorithm that divides a sorted list in half to find a target in O(log n)."},
        {"sender": "AI", "content": "Why is sorting required?"},
        {"sender": "USER", "content": "Because the middle comparison only guarantees which half to discard if elements are monotonically ordered."},
        {"sender": "AI", "content": "What happens if there are duplicate elements?"},
        {"sender": "USER", "content": "Binary search finds an instance, but to find first or last occurrence you must continue searching in that direction."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Binary Search Definition"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        ),
        TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.9,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Monotonic Ordering"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=3,
        ),
        TurnEvaluation(
            correctness=0.9,
            clarity=0.85,
            completeness=0.85,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Duplicate Handling"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=4,
        ),
    ]

    evidence = evidence_builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
        difficulty_history=[1, 2, 3],
    )

    evaluation = evaluator.evaluate_session(evidence)

    assert evaluation.understanding_score >= 80.0
    assert evaluation.mastery_level in [MasteryLevel.PROFICIENT, MasteryLevel.MASTERY]
    assert evaluation.evidence_confidence >= 0.65
    assert len(evaluation.strengths) >= 1
    assert len(evaluation.unresolved_gaps) == 0
    assert len(evaluation.unresolved_misconceptions) == 0

    report = evaluator.generate_report(evidence)
    assert isinstance(report, LearningReport)
    assert report.understanding_score == evaluation.understanding_score
    assert report.mastery_level == evaluation.mastery_level
    assert len(report.recommended_next_steps) >= 1


def test_weak_session_evaluation(evaluator, evidence_builder):
    """Learner struggles and fails across turns with unresolved gaps."""
    messages = [
        {"sender": "AI", "content": "What is binary search?"},
        {"sender": "USER", "content": "It searches by looping through everything one by one."},
        {"sender": "AI", "content": "How does it divide the search space?"},
        {"sender": "USER", "content": "I don't know, I'm stuck."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.2,
            clarity=0.6,
            completeness=0.2,
            depth=0.1,
            relevance=0.8,
            stuck_probability=0.2,
            misconceptions=["Confusing binary search with linear search"],
            knowledge_gap="Divide and conquer principle",
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.0,
            clarity=0.2,
            completeness=0.0,
            depth=0.0,
            relevance=0.5,
            stuck_probability=0.95,
            knowledge_gap="Divide and conquer principle",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
    ]

    evidence = evidence_builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
    )

    evaluation = evaluator.evaluate_session(evidence)

    assert evaluation.understanding_score < 45.0
    assert evaluation.mastery_level == MasteryLevel.BEGINNER
    assert "Divide and conquer principle" in evaluation.unresolved_gaps
    assert "Confusing binary search with linear search" in evaluation.unresolved_misconceptions

    # Roadmap should prioritize the unresolved misconception and gap
    report = evaluator.generate_report(evidence)
    action_types = [item.action_type for item in report.recommended_next_steps]
    assert "RESOLVE_MISCONCEPTION" in action_types or "FILL_GAP" in action_types


def test_mixed_session_evaluation(evaluator, evidence_builder):
    """Learner knows fundamentals well but fails on boundary conditions."""
    messages = [
        {"sender": "AI", "content": "What is binary search?"},
        {"sender": "USER", "content": "It cuts the search space in half each step on sorted data."},
        {"sender": "AI", "content": "What loop condition should you use?"},
        {"sender": "USER", "content": "I'm not sure, maybe while (low != high)? Or low < high? I always get off-by-one errors."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.9,
            clarity=0.85,
            completeness=0.85,
            depth=0.8,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Divide and conquer logic"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        ),
        TurnEvaluation(
            correctness=0.4,
            clarity=0.6,
            completeness=0.4,
            depth=0.3,
            relevance=0.9,
            stuck_probability=0.5,
            knowledge_gap="Loop termination condition (low <= high)",
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=2,
        ),
    ]

    evidence = evidence_builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
        difficulty_history=[1, 2],
    )

    evaluation = evaluator.evaluate_session(evidence)

    assert 40.0 <= evaluation.understanding_score <= 80.0
    assert evaluation.mastery_level in [MasteryLevel.DEVELOPING, MasteryLevel.PROFICIENT]
    assert "Loop termination condition (low <= high)" in evaluation.unresolved_gaps


def test_teacher_assisted_session_resolved(evaluator, evidence_builder):
    """Teacher mode intervened on a gap, verification passed, learner succeeded later."""
    messages = [
        {"sender": "AI", "content": "Does binary search work on unsorted arrays?"},
        {"sender": "USER", "content": "Yes it works on any array."},
        {
            "sender": "AI",
            "content": "Sorting gives an ordering we rely on.\n\nNow suppose the middle is 10 and target is 7. Why can we ignore everything after 10?",
            "metadata": {"mode": "TEACHER", "gap": "Sorted order elimination", "attempt_count": 1},
        },
        {"sender": "USER", "content": "Because 7 is less than 10, and all elements after 10 are greater than 10."},
        {"sender": "AI", "content": "Now how would you handle an array of size 1?"},
        {"sender": "USER", "content": "Check if that single element equals the target; low and high will both be index 0."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.2,
            clarity=0.8,
            completeness=0.2,
            depth=0.1,
            relevance=1.0,
            stuck_probability=0.1,
            misconceptions=["Binary search works on unsorted arrays"],
            knowledge_gap="Sorted order elimination",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Sorted order elimination"],
            recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            recommended_difficulty=2,
        ),
        TurnEvaluation(
            correctness=0.9,
            clarity=0.85,
            completeness=0.9,
            depth=0.8,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Single-element boundary case"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=3,
        ),
    ]

    evidence = evidence_builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
        difficulty_history=[1, 2, 3],
    )

    evaluation = evaluator.evaluate_session(evidence)

    assert "Sorted order elimination" in evaluation.resolved_gaps
    assert "Binary search works on unsorted arrays" in evaluation.resolved_misconceptions
    assert evaluation.teacher_intervention_summary["successful_interventions"] == 1


def test_insufficient_evidence_handling(evaluator, evidence_builder):
    """Empty or 1-turn session is handled gracefully without errors or inflated claims."""
    # 0 turns
    empty_ev = evidence_builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Operating Systems",
        messages=[],
    )
    eval_empty = evaluator.evaluate_session(empty_ev)
    assert eval_empty.understanding_score == 0.0
    assert eval_empty.mastery_level == MasteryLevel.BEGINNER
    assert eval_empty.evidence_confidence == 0.0

    report_empty = evaluator.generate_report(empty_ev)
    assert report_empty.understanding_score == 0.0
    assert len(report_empty.recommended_next_steps) >= 1
