"""
Phase 7.3 Batch 5: Precise Misconception Resolution Regression Tests.

Comprehensive regression suite verifying:
1. Two active misconceptions with evidence for only one.
2. Similar or overlapping misconception wording that must not trigger false resolution.
3. A high-scoring answer with no resolution evidence.
4. A single active misconception without sufficient resolution evidence.
5. Explicit evidence that resolves a single misconception.
6. Multiple misconceptions explicitly resolved, while an unrelated misconception remains active.
7. Consistent behavior across both assessment and evaluation paths.
8. Correct synchronization of active_misconceptions, unresolved_gap, and model.unresolved_gaps.
"""
import pytest

from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    LearningAssessment,
    RelevanceLevel,
)
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.schemas import (
    LearnerModel,
    Strategy,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)


def _make_assessment(
    concept_id: str,
    score: float = 0.85,
    evidence_descriptions: list = None,
    resolved_misconceptions: list = None,
) -> LearningAssessment:
    ev_items = [
        EvidenceItem(
            concept_id=concept_id,
            expected_description=desc,
            status=EvidenceStatus.SUPPORTED,
            confidence=1.0,
        )
        for desc in (evidence_descriptions or ["standard core component"])
    ]
    meta = {}
    if resolved_misconceptions is not None:
        meta["resolved_misconceptions"] = list(resolved_misconceptions)

    return LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=1.0,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=score,
        claims=[],
        evidence=ev_items,
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=score,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=score,
        misconception_status=False,
        misconceptions=[],
        missing_concepts=[],
        contradictory_claims=[],
        classification=AssessmentClassification.CORRECT,
        confidence=score,
        supports_mastery=True,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        metadata=meta,
    )


# ============================================================================
# 1. Two active misconceptions with evidence for only one
# ============================================================================

def test_1_two_misconceptions_evidence_for_only_one():
    """
    Scenario: Concept has two active misconceptions: M1 and M2.
    Learner provides high-scoring answer refuting only M1.
    Expected:
    - M1 is resolved and removed.
    - M2 remains active.
    - unresolved_gap remains True.
    - concept_id remains in learner_model.unresolved_gaps.
    """
    learner_m = LearnerModel(session_id="session-t1")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    assessment = _make_assessment(
        concept_id=cid,
        score=0.90,
        evidence_descriptions=[m1],
        resolved_misconceptions=[m1],
    )

    mgr.update_from_assessment(cid, assessment)

    assert m1 not in state.active_misconceptions
    assert m2 in state.active_misconceptions
    assert len(state.active_misconceptions) == 1
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# 2. Similar or overlapping misconception wording must not trigger false resolution
# ============================================================================

def test_2_overlapping_wording_must_not_trigger_false_resolution():
    """
    Scenario: Misconceptions have significant lexical overlap:
    - M1: 'Recursion causes memory leak'
    - M2: 'Recursion causes stack overflow'
    - M3: 'Hash collision'
    - M4: 'Hash collision can be avoided by large tables'
    Evidence only resolves M1.
    Expected:
    - M1 is resolved.
    - M2 is NOT resolved despite sharing 'Recursion causes'.
    - M3 and M4 are NOT resolved.
    """
    learner_m = LearnerModel(session_id="session-t2")
    mgr = LearnerModelManager(learner_m)
    cid = "recursion"

    m1 = "Recursion causes memory leak"
    m2 = "Recursion causes stack overflow"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    # Supply evidence specifically for M1
    assessment = _make_assessment(
        concept_id=cid,
        score=0.92,
        evidence_descriptions=["resolves: Recursion causes memory leak"],
        resolved_misconceptions=[m1],
    )

    mgr.update_from_assessment(cid, assessment)

    assert m1 not in state.active_misconceptions
    assert m2 in state.active_misconceptions, "M2 was falsely resolved due to overlapping wording!"
    assert state.unresolved_gap is True

    # Case B: m_sub is a substring of m_long
    # Under naive substring matching, resolving m_sub falsely resolves m_long!
    cid2 = "hashing"
    m_sub = "hash collision"
    m_long = "hash collision can be avoided by large tables"
    state2 = mgr.get_or_create_concept_state(cid2)
    state2.unresolved_gap = True
    state2.active_misconceptions = [m_sub, m_long]
    learner_m.unresolved_gaps.append(cid2)

    asmt2 = _make_assessment(
        concept_id=cid2,
        score=0.92,
        evidence_descriptions=[m_sub],
        resolved_misconceptions=[m_sub],
    )
    mgr.update_from_assessment(cid2, asmt2)

    assert m_sub not in state2.active_misconceptions
    assert m_long in state2.active_misconceptions, (
        f"Defect: '{m_long}' was falsely resolved because '{m_sub}' is a substring of it!"
    )



# ============================================================================
# 3. High-scoring answer with no resolution evidence
# ============================================================================

def test_3_high_scoring_answer_with_no_resolution_evidence():
    """
    Scenario: Concept has multiple active misconceptions.
    Learner provides a high score (0.95) with generic conceptual evidence.
    No resolution evidence for any misconception.
    Expected:
    - All misconceptions remain active.
    - unresolved_gap remains True.
    """
    learner_m = LearnerModel(session_id="session-t3")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    assessment = _make_assessment(
        concept_id=cid,
        score=0.95,
        evidence_descriptions=["quicksort partitions around a chosen pivot"],
        resolved_misconceptions=None,
    )

    mgr.update_from_assessment(cid, assessment)

    assert m1 in state.active_misconceptions
    assert m2 in state.active_misconceptions
    assert len(state.active_misconceptions) == 2
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# 4. Single active misconception without sufficient resolution evidence
# ============================================================================

def test_4_single_active_misconception_without_sufficient_evidence_not_cleared():
    """
    Scenario: Concept has exactly ONE active misconception.
    Learner provides a high-scoring answer (0.90) on the concept, but supplies
    NO resolution evidence targeting the misconception.
    Required Behavior:
    - A high score alone CANNOT clear a specific misconception without adequate resolution evidence.
    - The misconception MUST remain active.
    - unresolved_gap MUST remain True.
    """
    learner_m = LearnerModel(session_id="session-t4")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1]
    learner_m.unresolved_gaps.append(cid)

    # High-scoring turn with generic evidence, NOT refuting M1
    assessment = _make_assessment(
        concept_id=cid,
        score=0.92,
        evidence_descriptions=["quicksort is recursive"],
        resolved_misconceptions=None,
    )

    mgr.update_from_assessment(cid, assessment)

    # Must NOT be cleared without evidence!
    assert m1 in state.active_misconceptions, "Single misconception was cleared on high score without evidence!"
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# 5. Explicit evidence that resolves a single misconception
# ============================================================================

def test_5_explicit_evidence_resolves_single_misconception():
    """
    Scenario: Concept has a single active misconception.
    Learner provides a high score (0.90) with explicit evidence refuting the misconception.
    Expected:
    - Misconception is cleared.
    - unresolved_gap is cleared.
    - concept_id is removed from unresolved_gaps.
    """
    learner_m = LearnerModel(session_id="session-t5")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1]
    learner_m.unresolved_gaps.append(cid)

    # High-scoring turn with explicit resolution evidence
    assessment = _make_assessment(
        concept_id=cid,
        score=0.90,
        evidence_descriptions=[m1],
        resolved_misconceptions=[m1],
    )

    mgr.update_from_assessment(cid, assessment)

    assert state.active_misconceptions == []
    assert state.unresolved_gap is False
    assert cid not in learner_m.unresolved_gaps


# ============================================================================
# 6. Multiple misconceptions explicitly resolved, unrelated remains active
# ============================================================================

def test_6_multiple_misconceptions_resolved_unrelated_remains_active():
    """
    Scenario: Concept has THREE active misconceptions: M1, M2, M3.
    Learner provides evidence resolving M1 and M2.
    Expected:
    - M1 and M2 are cleared.
    - M3 remains active.
    - unresolved_gap remains True.
    """
    learner_m = LearnerModel(session_id="session-t6")
    mgr = LearnerModelManager(learner_m)
    cid = "sorting"

    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is stable"
    m3 = "Mergesort space complexity is O(1)"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2, m3]
    learner_m.unresolved_gaps.append(cid)

    assessment = _make_assessment(
        concept_id=cid,
        score=0.94,
        evidence_descriptions=[m1, m2],
        resolved_misconceptions=[m1, m2],
    )

    mgr.update_from_assessment(cid, assessment)

    assert m1 not in state.active_misconceptions
    assert m2 not in state.active_misconceptions
    assert m3 in state.active_misconceptions
    assert len(state.active_misconceptions) == 1
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# 7. Consistent behavior across both assessment and evaluation paths
# ============================================================================

def test_7_consistent_behavior_across_both_assessment_and_evaluation_paths():
    """
    Scenario: Verify update_from_evaluation behaves identically to update_from_assessment:
    - Without explicit resolution evidence: preserves misconception.
    - With explicit resolution evidence: clears only evidenced misconception.
    """
    cid = "recursion"
    m1 = "Recursion causes memory leak"
    m2 = "Base case is optional"

    # Path A: update_from_evaluation without evidence -> neither cleared
    learner_a = LearnerModel(session_id="session-t7a")
    mgr_a = LearnerModelManager(learner_a)
    st_a = mgr_a.get_or_create_concept_state(cid)
    st_a.unresolved_gap = True
    st_a.active_misconceptions = [m1, m2]
    learner_a.unresolved_gaps.append(cid)

    eval_a = TurnEvaluation(
        correctness=0.92,
        clarity=0.90,
        completeness=0.85,
        depth=0.80,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[cid],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=3,
    )
    mgr_a.update_from_evaluation(
        cid,
        eval_a,
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT, is_answer_attempt=True),
        resolved_misconceptions=None,
    )
    assert m1 in st_a.active_misconceptions
    assert m2 in st_a.active_misconceptions
    assert st_a.unresolved_gap is True

    # Path B: update_from_evaluation with explicit evidence for M1 -> M1 cleared, M2 preserved
    learner_b = LearnerModel(session_id="session-t7b")
    mgr_b = LearnerModelManager(learner_b)
    st_b = mgr_b.get_or_create_concept_state(cid)
    st_b.unresolved_gap = True
    st_b.active_misconceptions = [m1, m2]
    learner_b.unresolved_gaps.append(cid)

    mgr_b.update_from_evaluation(
        cid,
        eval_a,
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT, is_answer_attempt=True),
        resolved_misconceptions=[m1],
    )
    assert m1 not in st_b.active_misconceptions
    assert m2 in st_b.active_misconceptions
    assert st_b.unresolved_gap is True


# ============================================================================
# 8. Correct synchronization of active_misconceptions, unresolved_gap, and gaps
# ============================================================================

def test_8_correct_synchronization_of_state_flags_and_gaps():
    """
    Scenario: Full lifecycle synchronization check:
    - Step 1: Active misconceptions exist -> unresolved_gap=True, cid in unresolved_gaps.
    - Step 2: Partial resolution -> remaining misconceptions -> unresolved_gap=True, cid in unresolved_gaps.
    - Step 3: Complete resolution -> active_misconceptions=[] -> unresolved_gap=False, cid removed from unresolved_gaps.
    - Step 4: General gap with empty active_misconceptions -> high score clears gap cleanly.
    """
    cid = "hashing"
    m1 = "Hash tables have O(1) worst case lookup"
    m2 = "Collisions can be eliminated by larger capacity"

    learner = LearnerModel(session_id="session-t8")
    mgr = LearnerModelManager(learner)
    st = mgr.get_or_create_concept_state(cid)
    st.unresolved_gap = True
    st.active_misconceptions = [m1, m2]
    learner.unresolved_gaps.append(cid)

    # Step 2: Partial resolution of M1
    asmt_partial = _make_assessment(cid, score=0.90, resolved_misconceptions=[m1])
    mgr.update_from_assessment(cid, asmt_partial)
    assert st.active_misconceptions == [m2]
    assert st.unresolved_gap is True
    assert cid in learner.unresolved_gaps

    # Step 3: Complete resolution of M2
    asmt_complete = _make_assessment(cid, score=0.90, resolved_misconceptions=[m2])
    mgr.update_from_assessment(cid, asmt_complete)
    assert st.active_misconceptions == []
    assert st.unresolved_gap is False
    assert cid not in learner.unresolved_gaps

    # Step 4: General gap without misconceptions (e.g. from prior difficulty failure)
    st.unresolved_gap = True
    st.active_misconceptions = []
    learner.unresolved_gaps.append(cid)

    asmt_general = _make_assessment(cid, score=0.88)
    mgr.update_from_assessment(cid, asmt_general)
    assert st.active_misconceptions == []
    assert st.unresolved_gap is False
    assert cid not in learner.unresolved_gaps
