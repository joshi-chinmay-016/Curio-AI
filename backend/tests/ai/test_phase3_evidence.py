"""
Unit tests for SessionEvidenceBuilder (Phase 3B).
Tests:
1. Successful turn evidence
2. Failed turn evidence
3. Teacher intervention evidence
4. Resolved gap evidence
5. Unresolved gap evidence
6. Repeated misconception
7. Difficulty progression
8. Confidence progression
9. Multiple concepts
10. Empty session
11. Minimal evidence session
"""
import uuid
from backend.app.ai.schemas import (
    ChatMessage,
    Role,
    Strategy,
    TurnEvaluation,
)
from backend.app.ai.session_evidence import SessionEvidenceBuilder


def test_empty_session_evidence():
    builder = SessionEvidenceBuilder()
    evidence = builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Recursion",
        messages=[],
    )
    assert evidence.total_learner_turns == 0
    assert evidence.successful_turns == 0
    assert evidence.failed_turns == 0
    assert len(evidence.turns) == 0
    assert len(evidence.teacher_interventions) == 0
    assert len(evidence.concepts_encountered) == 0


def test_minimal_evidence_session():
    builder = SessionEvidenceBuilder()
    messages = [
        ChatMessage(role=Role.ASSISTANT, content="What is binary search?"),
        ChatMessage(role=Role.USER, content="It divides search space in half."),
    ]
    evals = [
        TurnEvaluation(
            correctness=0.9,
            clarity=0.8,
            completeness=0.8,
            depth=0.7,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Divide and Conquer"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        )
    ]
    evidence = builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
    )
    assert evidence.total_learner_turns == 1
    assert evidence.successful_turns == 1
    assert evidence.failed_turns == 0
    assert len(evidence.turns) == 1
    assert evidence.turns[0].concept == "Divide and Conquer"
    assert "Divide and Conquer" in evidence.concept_evidence_map
    assert evidence.concept_evidence_map["Divide and Conquer"].highest_difficulty_passed == 2


def test_successful_and_failed_turn_evidence():
    builder = SessionEvidenceBuilder()
    messages = [
        {"sender": "AI", "content": "What is the base case?"},
        {"sender": "USER", "content": "The condition that stops recursion."},
        {"sender": "AI", "content": "How does call stack memory behave?"},
        {"sender": "USER", "content": "I don't know, it's infinite I guess."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Base Case"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        ),
        TurnEvaluation(
            correctness=0.1,
            clarity=0.4,
            completeness=0.1,
            depth=0.0,
            relevance=0.8,
            stuck_probability=0.9,
            misconceptions=["Stack memory is infinite"],
            knowledge_gap="Call stack memory limit",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
    ]
    evidence = builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Recursion",
        messages=messages,
        evaluations=evals,
    )
    assert evidence.total_learner_turns == 2
    assert evidence.successful_turns == 1
    assert evidence.failed_turns == 1
    assert len(evidence.turns) == 2


def test_teacher_intervention_evidence_resolved():
    """Verify teacher intervention where verification passed."""
    builder = SessionEvidenceBuilder()
    messages = [
        {"sender": "AI", "content": "Can binary search be run on unsorted arrays?"},
        {"sender": "USER", "content": "Yes, it works on any list."},
        {
            "sender": "AI",
            "content": "Sorting gives us an ordering we can rely on.\n\nNow suppose the middle value is 10 and target is 7. Why can we ignore everything after 10?",
            "metadata": {"mode": "TEACHER", "gap": "Belief that binary search works without sorted order", "attempt_count": 1},
        },
        {"sender": "USER", "content": "Because 7 is smaller than 10, and since it is sorted, all items after 10 are even larger."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.2,
            clarity=0.8,
            completeness=0.2,
            depth=0.1,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=["Binary search works on unsorted arrays"],
            knowledge_gap="Belief that binary search works without sorted order",
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
            mastered_concepts=["Order-based elimination"],
            recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            recommended_difficulty=2,
        ),
    ]
    evidence = builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
    )
    assert len(evidence.teacher_interventions) == 1
    intervention = evidence.teacher_interventions[0]
    assert intervention.gap == "Belief that binary search works without sorted order"
    assert intervention.verification_passed is True
    assert intervention.verification_answer is not None
    assert "Order-based elimination" in intervention.related_concept


def test_teacher_intervention_evidence_unresolved():
    """Verify teacher intervention where verification failed."""
    builder = SessionEvidenceBuilder()
    messages = [
        {"sender": "AI", "content": "Explain binary search."},
        {"sender": "USER", "content": "I don't know at all."},
        {
            "sender": "AI",
            "content": "Sorting allows us to discard half the space.\n\nWhy can we ignore everything after 10?",
            "metadata": {"mode": "TEACHER", "gap": "Order elimination", "attempt_count": 1},
        },
        {"sender": "USER", "content": "I still don't understand."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.0,
            clarity=0.2,
            completeness=0.0,
            depth=0.0,
            relevance=0.5,
            stuck_probability=0.95,
            knowledge_gap="Order elimination",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.1,
            clarity=0.3,
            completeness=0.1,
            depth=0.0,
            relevance=0.5,
            stuck_probability=0.9,
            knowledge_gap="Still confused on order elimination",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
    ]
    evidence = builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Binary Search",
        messages=messages,
        evaluations=evals,
    )
    assert len(evidence.teacher_interventions) == 1
    intervention = evidence.teacher_interventions[0]
    assert intervention.verification_passed is False


def test_repeated_misconception_and_multi_concept():
    builder = SessionEvidenceBuilder()
    messages = [
        {"sender": "AI", "content": "Q1"},
        {"sender": "USER", "content": "A1"},
        {"sender": "AI", "content": "Q2"},
        {"sender": "USER", "content": "A2"},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.3,
            clarity=0.6,
            completeness=0.4,
            depth=0.2,
            relevance=0.9,
            stuck_probability=0.1,
            misconceptions=["Stack memory is infinite"],
            missing_concepts=["Stack Limit"],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.35,
            clarity=0.5,
            completeness=0.4,
            depth=0.2,
            relevance=0.9,
            stuck_probability=0.1,
            misconceptions=["Stack memory is infinite"],
            missing_concepts=["Stack Overflow"],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        ),
    ]
    diff_hist = [1, 1]
    conf_hist = [0.1, 0.15]
    evidence = builder.build_from_history(
        session_id=str(uuid.uuid4()),
        topic="Call Stack",
        messages=messages,
        evaluations=evals,
        difficulty_history=diff_hist,
        confidence_history=conf_hist,
    )
    assert evidence.difficulty_progression == [1, 1]
    assert evidence.confidence_progression == [0.1, 0.15]
    assert len(evidence.concepts_encountered) >= 1
    # Check that the misconception was tracked in concept evidence
    for c_item in evidence.concept_evidence_map.values():
        if "Stack memory is infinite" in c_item.misconceptions:
            assert True
            break
    else:
        pytest.fail("Misconception not captured in concept evidence map")
