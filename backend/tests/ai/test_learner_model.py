"""
Unit tests for LearnerModel and LearnerModelManager (Phase D).
Verifies:
- Acknowledgements NEVER falsely award mastery or evidence count.
- Correct explanations yield bounded mastery increase.
- Misconceptions block fake mastery and set unresolved gap status.
- Teacher verification pass clears gap and establishes proficiency.
- Failed verification preserves gap status.
"""
import pytest
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.schemas import (
    LearnerModel,
    Strategy,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)


def _eval(correctness=0.9, misconceptions=None):
    return TurnEvaluation(
        correctness=correctness,
        clarity=0.9,
        completeness=0.8,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=misconceptions or [],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=2,
    )


def test_acknowledgement_alone_does_not_increase_mastery():
    mgr = LearnerModelManager()
    concept = "binary_search_elimination"

    # User says "I understand now"
    interp = TurnInterpretation(
        intent=TurnIntent.ACKNOWLEDGEMENT,
        is_answer_attempt=False,
    )
    # Even if an evaluation object was synthetically passed, interpretation blocks fake mastery
    state = mgr.update_from_evaluation(concept, _eval(correctness=0.9), interpretation=interp)

    assert state.mastery == 0.0
    assert state.evidence_count == 0
    assert state.attempt_count == 1

    # Using direct record_acknowledgement
    state2 = mgr.record_acknowledgement(concept)
    assert state2.mastery == 0.0
    assert state2.evidence_count == 0
    assert state2.attempt_count == 2


def test_correct_explanation_increases_mastery_and_evidence():
    mgr = LearnerModelManager()
    concept = "virtual_memory_paging"

    state = mgr.update_from_evaluation(
        concept,
        _eval(correctness=0.95),
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT, is_answer_attempt=True),
    )

    assert state.mastery > 0.0
    assert state.evidence_count == 1
    assert state.unresolved_gap is False

    # Second correct turn increases further, bounded by 1.0
    initial_m = state.mastery
    state_turn2 = mgr.update_from_evaluation(
        concept,
        _eval(correctness=0.90),
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT, is_answer_attempt=True),
    )
    assert state_turn2.mastery > initial_m
    assert state_turn2.mastery <= 1.0
    assert state_turn2.evidence_count == 2


def test_misconception_blocks_fake_mastery():
    mgr = LearnerModelManager()
    concept = "mutex_locking"

    # First turn was partially good
    mgr.update_from_evaluation(concept, _eval(correctness=0.7), interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT))
    # Second turn contains a severe misconception
    state = mgr.update_from_evaluation(
        concept,
        _eval(correctness=0.5, misconceptions=["Spinlocks are always faster than mutexes on single-core"]),
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT),
    )

    assert state.unresolved_gap is True
    assert "mutex_locking" in mgr.model.unresolved_gaps
    assert state.misconception_count == 1
    assert state.mastery <= 0.35  # Cap applied on misconception


def test_teacher_verification_pass_resolves_gap():
    mgr = LearnerModelManager()
    concept = "asgi_uvicorn_bridge"

    # Mark as gap
    mgr.model.unresolved_gaps.append(concept)
    state = mgr.get_or_create_concept_state(concept)
    state.unresolved_gap = True
    state.mastery = 0.2

    # Teacher verification pass
    state_after = mgr.record_teacher_verification(concept, passed=True, attempt_count=1)

    assert state_after.unresolved_gap is False
    assert concept not in mgr.model.unresolved_gaps
    assert state_after.mastery >= 0.75
    assert state_after.evidence_count == 1


def test_teacher_verification_fail_preserves_gap():
    mgr = LearnerModelManager()
    concept = "asgi_uvicorn_bridge"

    state = mgr.record_teacher_verification(concept, passed=False, attempt_count=1)
    assert state.unresolved_gap is True
    assert concept in mgr.model.unresolved_gaps
    assert state.mastery <= 0.30
