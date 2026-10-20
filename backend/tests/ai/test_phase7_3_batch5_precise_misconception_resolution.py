"""
Phase 7.3 Batch 5: Precise Misconception Resolution Regression Tests.

Verifies:
1. Two distinct active misconceptions on a concept:
   - Supplying evidence resolving only M1 clears M1 while M2 remains active.
   - Supplying an ambiguous high-scoring answer without specific resolution evidence
     preserves unresolved misconceptions (they are NOT silently cleared in bulk).
2. Single-misconception concept:
   - High-scoring answer with adequate evidence still resolves the single misconception (backward compatibility).
3. State preservation:
   - If active misconceptions remain, unresolved_gap remains True and concept_id stays in unresolved_gaps.
   - None and empty-list semantics remain correct.
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
# Test 1 & 2: Two Active Misconceptions - Specific Evidence Resolves Only One
# ============================================================================

def test_two_misconceptions_evidence_resolves_only_targeted_misconception():
    """
    Test 1: Concept has two active misconceptions:
    - M1: 'Quicksort worst case is O(n log n)'
    - M2: 'Quicksort is a stable sorting algorithm'

    Learner provides a high-scoring answer supplying specific evidence resolving M1.
    Expected:
    - M1 is resolved and removed from active_misconceptions.
    - M2 remains active in active_misconceptions.
    - unresolved_gap remains True on ConceptState.
    - concept_id remains in learner_model.unresolved_gaps.
    """
    learner_m = LearnerModel(session_id="session-batch5-t1")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    # Supply assessment with evidence resolving only M1
    assessment = _make_assessment(
        concept_id=cid,
        score=0.90,
        evidence_descriptions=[m1],
        resolved_misconceptions=[m1],
    )

    mgr.update_from_assessment(cid, assessment)

    # M1 must be resolved; M2 must remain active
    assert m1 not in state.active_misconceptions, f"M1 '{m1}' was expected to be resolved."
    assert m2 in state.active_misconceptions, f"M2 '{m2}' must remain active."
    assert len(state.active_misconceptions) == 1
    # Because M2 is still active, gap status must persist
    assert state.unresolved_gap is True, "unresolved_gap must remain True while M2 is active."
    assert cid in learner_m.unresolved_gaps, f"{cid} must remain in unresolved_gaps while M2 is active."


# ============================================================================
# Test 3 & 4: Ambiguous High-Score Answer Does NOT Silently Clear Misconceptions
# ============================================================================

def test_ambiguous_high_scoring_answer_does_not_clear_multiple_misconceptions():
    """
    Test 2: Concept has two active misconceptions: M1 and M2.
    Learner gives an ambiguous or generic high-scoring answer (0.90) that does NOT
    identify or provide evidence resolving either specific misconception.

    Defect under current production code:
    - Current code unconditionally executes `state.active_misconceptions = []` when score >= 0.80.

    Required behavior:
    - When multiple misconceptions are active and the answer does not identify which one was resolved,
      unresolved misconceptions must be PRESERVED, not silently cleared.
    """
    learner_m = LearnerModel(session_id="session-batch5-t2")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    # Generic high-scoring answer on quicksort with general evidence, NOT addressing M1 or M2
    assessment = _make_assessment(
        concept_id=cid,
        score=0.90,
        evidence_descriptions=["quicksort partitions around a pivot"],
        resolved_misconceptions=None,  # No specific misconception identified
    )

    mgr.update_from_assessment(cid, assessment)

    # Both misconceptions must be preserved because no specific resolution evidence was provided
    assert m1 in state.active_misconceptions, f"M1 '{m1}' was silently cleared without evidence."
    assert m2 in state.active_misconceptions, f"M2 '{m2}' was silently cleared without evidence."
    assert len(state.active_misconceptions) == 2
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# Test 5: Existing Single-Misconception Resolution Preserved
# ============================================================================

def test_single_misconception_resolved_when_evidence_present():
    """
    Test 3: Backward compatibility verification:
    When a concept has exactly ONE active misconception, a high-scoring answer (score >= 0.80)
    with no misconception detected clears that misconception.
    """
    learner_m = LearnerModel(session_id="session-batch5-t3")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1]
    learner_m.unresolved_gaps.append(cid)

    # High-scoring turn without misconception
    assessment = _make_assessment(
        concept_id=cid,
        score=0.88,
        evidence_descriptions=["worst case partition degrades to quadratic"],
    )

    mgr.update_from_assessment(cid, assessment)

    # The single targeted misconception is resolved
    assert state.active_misconceptions == []
    assert state.unresolved_gap is False
    assert cid not in learner_m.unresolved_gaps


# ============================================================================
# Test 6: update_from_evaluation Preserves Multiple Misconceptions
# ============================================================================

def test_update_from_evaluation_preserves_multiple_misconceptions_without_evidence():
    """
    Test 4: Verify TurnEvaluation path also protects against bulk clearing when multiple
    misconceptions are active.
    """
    learner_m = LearnerModel(session_id="session-batch5-t4")
    mgr = LearnerModelManager(learner_m)
    cid = "recursion"

    m1 = "Recursion causes memory leak"
    m2 = "Base case is optional"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    eval_turn = TurnEvaluation(
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

    mgr.update_from_evaluation(
        cid,
        eval_turn,
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT, is_answer_attempt=True),
    )

    # Ambiguous evaluation turn without resolution specification must NOT clear both
    assert m1 in state.active_misconceptions
    assert m2 in state.active_misconceptions
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# Test 5 & 6: None & Empty-List Semantics and EvidenceItem Matching
# ============================================================================

def test_none_and_empty_list_semantics_for_misconception_resolution():
    """
    Test 5: Explicit None and empty list semantics:
    - Empty list [] in resolved_misconceptions: explicit signal that NO misconception was resolved.
      Both active misconceptions must remain.
    - None in resolved_misconceptions with multiple active misconceptions:
      ambiguous turn, neither is cleared.
    - Concept with empty active_misconceptions:
      High score cleanly clears unresolved_gap without raising exceptions.
    """
    cid = "quicksort"
    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"

    # Case A: Explicit empty list [] in resolved_misconceptions
    learner_a = LearnerModel(session_id="session-batch5-empty")
    mgr_a = LearnerModelManager(learner_a)
    st_a = mgr_a.get_or_create_concept_state(cid)
    st_a.unresolved_gap = True
    st_a.active_misconceptions = [m1, m2]
    learner_a.unresolved_gaps.append(cid)

    asmt_empty = _make_assessment(
        concept_id=cid,
        score=0.95,
        resolved_misconceptions=[],  # explicitly empty
    )
    mgr_a.update_from_assessment(cid, asmt_empty)
    assert st_a.active_misconceptions == [m1, m2]
    assert st_a.unresolved_gap is True

    # Case B: Concept with empty active_misconceptions and unresolved_gap=True (e.g. general gap)
    learner_b = LearnerModel(session_id="session-batch5-empty-active")
    mgr_b = LearnerModelManager(learner_b)
    st_b = mgr_b.get_or_create_concept_state(cid)
    st_b.unresolved_gap = True
    st_b.active_misconceptions = []
    learner_b.unresolved_gaps.append(cid)

    asmt_b = _make_assessment(concept_id=cid, score=0.85)
    mgr_b.update_from_assessment(cid, asmt_b)
    assert st_b.unresolved_gap is False
    assert st_b.active_misconceptions == []
    assert cid not in learner_b.unresolved_gaps


def test_evidence_item_matching_resolves_targeted_misconception_without_metadata():
    """
    Test 6: When metadata['resolved_misconceptions'] is absent (None), but assessment.evidence
    contains an EvidenceItem with status=SUPPORTED that matches M1's description,
    M1 is resolved and M2 remains active.
    """
    learner_m = LearnerModel(session_id="session-batch5-evidence-item")
    mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"

    state = mgr.get_or_create_concept_state(cid)
    state.unresolved_gap = True
    state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    # No metadata['resolved_misconceptions'], but evidence has supported item matching M1
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=1.0,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.90,
        claims=[],
        evidence=[
            EvidenceItem(
                concept_id=cid,
                expected_description="Quicksort worst case is O(n log n)",
                status=EvidenceStatus.SUPPORTED,
                confidence=0.95,
            )
        ],
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.90,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.90,
        misconception_status=False,
        misconceptions=[],
        missing_concepts=[],
        contradictory_claims=[],
        classification=AssessmentClassification.CORRECT,
        confidence=0.90,
        supports_mastery=True,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        metadata={},  # No explicit resolved_misconceptions key
    )

    mgr.update_from_assessment(cid, assessment)

    assert m1 not in state.active_misconceptions
    assert m2 in state.active_misconceptions
    assert state.unresolved_gap is True
    assert cid in learner_m.unresolved_gaps

