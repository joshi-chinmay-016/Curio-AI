"""
Phase 7 Master Completion Test Suite:
Validates production misconception resolution pipeline, objective-level curriculum coverage,
multi-turn learning reliability, session isolation, and regression stability.
"""
import copy
import pytest
from backend.app.ai.schemas import (
    ConceptNode,
    ConceptModel,
    ConceptState,
    LearnerModel,
    LearningObjective,
    ObjectiveType,
    QuestionSpecification,
    CoverageStatus,
    TurnEvaluation,
    Strategy,
)
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.topic_plan import TopicPlanner
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.schemas import (
    LearningAssessment,
    AssessmentIntent,
    CorrectnessLevel,
    CompletenessLevel,
    AssessmentClassification,
    AssessmentStatus,
    RelevanceLevel,
    EvidenceItem,
    EvidenceStatus,
    MisconceptionEvidence,
)
from backend.app.ai.answer_intelligence.providers.mock_provider import MockAssessmentProvider
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate


def _make_assessment(
    concept_id: str,
    score: float = 0.85,
    evidence_descriptions: list = None,
    resolved_misconceptions: list = None,
    objective_id: str = None,
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
    if objective_id is not None:
        meta["objective_id"] = objective_id

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


# ==============================================================================
# 1. WORKSTREAM A: END-TO-END PRODUCTION MISCONCEPTION RESOLUTION PIPELINE
# ==============================================================================

def test_production_pipeline_misconception_resolution_end_to_end():
    """
    Test that the real production components (QuestionSelector, AssessmentAggregator, LearnerModelManager)
    coordinate to target a specific misconception, produce resolution metadata, and clear ONLY that misconception.
    """
    concept_id = "binary_search"
    misc1 = "Binary search works on unsorted lists."
    misc2 = "Binary search examines every element linearly."

    # Setup learner model with 2 active misconceptions
    learner = LearnerModel(session_id="sess_prod_1")
    state = learner.get_or_create_concept(concept_id)
    state.active_misconceptions = [misc1, misc2]
    state.unresolved_gap = True
    learner.unresolved_gaps = [concept_id]

    node = ConceptNode(
        id=concept_id,
        name="Binary Search",
        difficulty_level=2,
        common_misconceptions=[misc1, misc2],
    )
    c_model = ConceptModel(topic="Algorithms", concepts=[node])

    # 1. QuestionSelector targets the active misconception
    selector = QuestionSelector()
    spec = selector.select_question_specification(
        concept_model=c_model,
        learner_model=learner,
        current_difficulty=2,
    )

    assert spec.target_concept == concept_id
    assert spec.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION
    assert spec.learning_objective.success_criteria == misc1
    assert "resolves: " in spec.evidence_expected

    # 2. AssessmentAggregator processes a strong answer targeting this specification
    mock_prov = MockAssessmentProvider({
        "correctness": CorrectnessLevel.CORRECT,
        "correctness_score": 0.90,
        "completeness": CompletenessLevel.COMPLETE,
        "completeness_score": 1.0,
        "misconceptions": [],
        "evidence": [
            EvidenceItem(
                concept_id=concept_id,
                expected_description=f"resolves: {misc1}",
                status=EvidenceStatus.SUPPORTED,
                confidence=1.0,
            )
        ],
    })
    aggregator = AssessmentAggregator(provider=mock_prov)
    user_answer = "Binary search strictly requires the array to be sorted first because it relies on ordering."
    assessment = aggregator.assess(
        user_message=user_answer,
        target_concept_override=concept_id,
        concept_model=c_model,
        question_specification=spec,
    )

    # In production, aggregator attaches objective_id and resolved_misconceptions when target met
    assert "objective_id" in assessment.metadata
    assert assessment.correctness_score >= 0.80
    assert assessment.metadata.get("resolved_misconceptions") == [misc1]

    # 3. LearnerModelManager updates from this production assessment
    mgr = LearnerModelManager(learner)
    updated = mgr.update_from_assessment(concept_id, assessment)

    # misc1 resolved, but misc2 PRESERVED
    assert misc1 not in updated.active_misconceptions
    assert misc2 in updated.active_misconceptions
    assert updated.unresolved_gap is True
    assert concept_id in learner.unresolved_gaps


def test_production_pipeline_high_score_without_resolution_evidence():
    """
    If the active question does NOT target the misconception (or no specific resolution is evidenced),
    a high score must NOT resolve any misconception.
    """
    concept_id = "recursion"
    misc = "Recursion can run indefinitely without a stack overflow."

    learner = LearnerModel(session_id="sess_prod_2")
    state = learner.get_or_create_concept(concept_id)
    state.active_misconceptions = [misc]
    state.unresolved_gap = True
    learner.unresolved_gaps = [concept_id]

    node = ConceptNode(id=concept_id, name="Recursion", difficulty_level=2)
    c_model = ConceptModel(topic="Recursion", concepts=[node])

    # Question targeting general definition, not resolving misconception
    spec = QuestionSpecification(
        target_concept=concept_id,
        learning_objective=LearningObjective(
            objective_id="rec_def",
            objective_type=ObjectiveType.UNDERSTAND_DEFINITION,
            target_concept=concept_id,
            reason="Check definition",
            evidence_expected="Explains base case and recursive step",
        ),
        difficulty=2,
        reason="Check definition",
        evidence_expected="Explains base case and recursive step",
    )

    mock_prov = MockAssessmentProvider({
        "correctness": CorrectnessLevel.CORRECT,
        "correctness_score": 0.90,
        "completeness": CompletenessLevel.COMPLETE,
        "completeness_score": 1.0,
        "misconceptions": [],
        "evidence": [
            EvidenceItem(
                concept_id=concept_id,
                expected_description="Explains base case and recursive step",
                status=EvidenceStatus.SUPPORTED,
                confidence=1.0,
            )
        ],
    })
    aggregator = AssessmentAggregator(provider=mock_prov)
    assessment = aggregator.assess(
        user_message="Recursion is a method where the solution depends on solutions to smaller instances.",
        target_concept_override=concept_id,
        concept_model=c_model,
        question_specification=spec,
    )

    mgr = LearnerModelManager(learner)
    updated = mgr.update_from_assessment(concept_id, assessment)

    # Misconception remains unresolved
    assert misc in updated.active_misconceptions
    assert updated.unresolved_gap is True


# ==============================================================================
# 2. WORKSTREAM B: MASTERY VERSUS OBJECTIVE-LEVEL CURRICULUM COVERAGE
# ==============================================================================

def test_high_scalar_mastery_does_not_complete_unassessed_objectives():
    """
    Demonstrating a high scalar score (e.g. 0.85) on one objective does not mark
    unassessed essential learning objectives as mastered, and keeps concept coverage IN_PROGRESS.
    """
    c_id = "linked_lists"
    obj1 = LearningObjective(
        objective_id="ll_nodes",
        description="Explain node structure and pointer references",
        essential=True,
    )
    obj2 = LearningObjective(
        objective_id="ll_traversal",
        description="Explain linear pointer traversal and stopping condition",
        essential=True,
    )
    obj3 = LearningObjective(
        objective_id="ll_deletion",
        description="Explain node deletion and edge pointer updates",
        essential=True,
    )

    node = ConceptNode(
        id=c_id,
        name="Linked Lists",
        difficulty_level=2,
        learning_objectives=[obj1, obj2, obj3],
    )
    c_model = ConceptModel(topic="Data Structures", concepts=[node])
    learner = LearnerModel(session_id="sess_obj_1")

    mgr = LearnerModelManager(learner)
    # Learner scores 0.95 on obj1
    asmt = _make_assessment(
        concept_id=c_id,
        score=0.95,
        objective_id="ll_nodes",
    )
    state = mgr.update_from_assessment(c_id, asmt)

    # Mastery scalar is positive
    assert state.mastery > 0.35
    assert "ll_nodes" in state.assessed_objectives
    assert "ll_nodes" in state.mastered_objectives
    assert "ll_traversal" not in state.mastered_objectives
    assert "ll_deletion" not in state.mastered_objectives

    # Topic plan coverage must be IN_PROGRESS, NOT MASTERED
    plan = TopicPlanner.build_topic_plan(c_model, learner, topic="Data Structures")
    item = plan.get_concept(c_id)
    assert item is not None
    assert item.status == CoverageStatus.IN_PROGRESS
    assert item.coverage_status != CoverageStatus.MASTERED


def test_unresolved_misconception_blocks_objective_and_concept_mastery():
    """
    An unresolved misconception prevents an objective from being mastered and forces
    concept status to NEEDS_REVIEW regardless of scalar mastery.
    """
    c_id = "stack_memory"
    obj = LearningObjective(
        objective_id="stack_lifo",
        description="Explain Last-In First-Out operation",
        essential=True,
    )
    node = ConceptNode(
        id=c_id,
        name="Stack Memory",
        difficulty_level=1,
        learning_objectives=[obj],
    )
    c_model = ConceptModel(topic="Memory", concepts=[node])
    learner = LearnerModel(session_id="sess_obj_2")
    state = learner.get_or_create_concept(c_id)
    state.active_misconceptions = ["Stack items are accessed randomly."]
    state.unresolved_gap = True

    mgr = LearnerModelManager(learner)
    asmt = _make_assessment(
        concept_id=c_id,
        score=0.85,
        objective_id="stack_lifo",
    )
    # Update without resolving the active misconception
    updated = mgr.update_from_assessment(c_id, asmt)

    # Active misconception is still present
    assert len(updated.active_misconceptions) == 1
    # Objective must NOT be marked mastered because an unresolved gap/misconception blocks it
    assert "stack_lifo" not in updated.mastered_objectives

    plan = TopicPlanner.build_topic_plan(c_model, learner, topic="Memory")
    item = plan.get_concept(c_id)
    assert item.status == CoverageStatus.NEEDS_REVIEW


def test_all_objectives_mastered_transitions_concept_to_mastered():
    """
    When all essential learning objectives are mastered and no misconceptions remain,
    concept transitions to MASTERED.
    """
    c_id = "queue_ds"
    obj1 = LearningObjective(objective_id="q_fifo", description="FIFO order", essential=True)
    obj2 = LearningObjective(objective_id="q_enqueue", description="Enqueue at rear", essential=True)
    node = ConceptNode(
        id=c_id,
        name="Queue DS",
        difficulty_level=1,
        learning_objectives=[obj1, obj2],
    )
    c_model = ConceptModel(topic="Queue", concepts=[node])
    learner = LearnerModel(session_id="sess_obj_3")
    mgr = LearnerModelManager(learner)

    # Turn 1: Master obj1
    mgr.update_from_assessment(c_id, _make_assessment(c_id, score=0.90, objective_id="q_fifo"))
    plan1 = TopicPlanner.build_topic_plan(c_model, learner, topic="Queue")
    assert plan1.get_concept(c_id).status == CoverageStatus.IN_PROGRESS

    # Turn 2: Master obj2
    state2 = mgr.update_from_assessment(c_id, _make_assessment(c_id, score=0.90, objective_id="q_enqueue"))
    assert "q_fifo" in state2.mastered_objectives
    assert "q_enqueue" in state2.mastered_objectives

    plan2 = TopicPlanner.build_topic_plan(c_model, learner, topic="Queue")
    assert plan2.get_concept(c_id).status == CoverageStatus.MASTERED


def test_question_selector_advances_through_curriculum_objectives():
    """
    QuestionSelector chooses the next unmastered objective on a concept,
    preventing repetitive loop on the same objective.
    """
    c_id = "sorting"
    obj1 = LearningObjective(objective_id="sort_def", description="Definition", essential=True)
    obj2 = LearningObjective(objective_id="sort_compare", description="Comparison", essential=True)
    node = ConceptNode(
        id=c_id,
        name="Sorting",
        difficulty_level=2,
        learning_objectives=[obj1, obj2],
    )
    c_model = ConceptModel(topic="Sorting", concepts=[node])
    learner = LearnerModel(session_id="sess_obj_4")
    state = learner.get_or_create_concept(c_id)

    selector = QuestionSelector()

    # Step 1: Nothing mastered, selector targets obj1
    spec1 = selector.select_question_specification(c_model, learner, current_difficulty=2)
    assert spec1.learning_objective.objective_id == "sort_def"

    # Step 2: obj1 is now mastered
    state.assessed_objectives.append("sort_def")
    state.mastered_objectives.append("sort_def")

    # Step 3: Selector now targets obj2
    spec2 = selector.select_question_specification(c_model, learner, current_difficulty=2)
    assert spec2.learning_objective.objective_id == "sort_compare"


# ==============================================================================
# 3. WORKSTREAM C: MULTI-TURN LEARNING RELIABILITY & REMEDIATION
# ==============================================================================

def test_foundation_recovery_resumes_curriculum_coverage():
    """
    A learner experiencing a foundation gap is boundedly remediated, and once resolved,
    broader curriculum coverage resumes.
    """
    c_base = "hash_function"
    c_adv = "hash_table"

    node_base = ConceptNode(id=c_base, name="Hash Function", difficulty_level=1)
    node_adv = ConceptNode(id=c_adv, name="Hash Table", difficulty_level=3, prerequisites=[c_base])
    c_model = ConceptModel(topic="Hashing", concepts=[node_base, node_adv])

    learner = LearnerModel(session_id="sess_multiturn_1")
    mgr = LearnerModelManager(learner)

    # Learner has an unresolved gap on base concept
    base_state = learner.get_or_create_concept(c_base)
    base_state.unresolved_gap = True
    learner.unresolved_gaps = [c_base]

    selector = QuestionSelector()

    # Selector prioritizes the foundational gap
    spec1 = selector.select_question_specification(c_model, learner, current_difficulty=2)
    assert spec1.target_concept == c_base

    # Remediate base concept with correct answer and clear gap
    asmt = _make_assessment(
        concept_id=c_base,
        score=0.90,
    )
    mgr.update_from_assessment(c_base, asmt)
    assert base_state.unresolved_gap is False
    assert c_base not in learner.unresolved_gaps

    # Now selector can advance to the broader curriculum
    spec2 = selector.select_question_specification(c_model, learner, current_difficulty=2)
    assert spec2.target_concept in (c_base, c_adv)


def test_bounded_difficulty_transitions_without_oscillation():
    """
    Alternating strong and weak answers does not cause rapid unbounded difficulty oscillation.
    Changes must be bounded to at most +-1.
    """
    selector = QuestionSelector()
    node = ConceptNode(id="graph", name="Graph Theory", difficulty_level=3)
    c_state = ConceptState(concept_id="graph", mastery=0.5)

    eval_strong = TurnEvaluation(
        correctness=0.95,
        clarity=1.0,
        completeness=1.0,
        depth=1.0,
        relevance=1.0,
        stuck_probability=0.0,
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=4,
    )
    eval_weak = TurnEvaluation(
        correctness=0.10,
        clarity=1.0,
        completeness=0.2,
        depth=0.1,
        relevance=1.0,
        stuck_probability=0.8,
        recommended_strategy=Strategy.TEACH_GAP,
        recommended_difficulty=2,
    )

    # From difficulty 3 with strong answer -> at most 4
    d1 = selector._calculate_next_difficulty(3, node, c_state, eval_strong)
    assert d1 <= 4
    assert d1 >= 3

    # From difficulty 4 with weak answer -> at least 3
    d2 = selector._calculate_next_difficulty(d1, node, c_state, eval_weak)
    assert d2 >= d1 - 1
    assert d2 <= d1


# ==============================================================================
# 4. WORKSTREAM E: SESSION ISOLATION & SERIALIZATION INTEGRITY
# ==============================================================================

def test_session_state_isolation():
    """
    Two independent learner sessions must never leak mutable state across instances.
    """
    learner1 = LearnerModel(session_id="sess_iso_1")
    learner2 = LearnerModel(session_id="sess_iso_2")

    mgr1 = LearnerModelManager(learner1)
    mgr2 = LearnerModelManager(learner2)

    # Learner 1 introduces a misconception
    asmt_misc = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=1.0,
        concept_alignment_score=1.0,
        correctness=CorrectnessLevel.INCORRECT,
        correctness_score=0.1,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.2,
        misconception_status=True,
        misconceptions=[MisconceptionEvidence(concept_id="trees", description="All trees are binary.", learner_statement="Trees are binary.")],
        classification=AssessmentClassification.MISCONCEPTION,
        confidence=1.0,
    )
    mgr1.update_from_assessment("trees", asmt_misc)

    # Verify learner 1 state
    assert len(learner1.concepts["trees"].active_misconceptions) == 1
    assert "trees" in learner1.unresolved_gaps

    # Verify learner 2 is completely isolated
    assert "trees" not in learner2.concepts
    assert learner2.unresolved_gaps == []


def test_learner_model_serialization_roundtrip_preserves_objectives():
    """
    JSON serialization and deserialization of ConceptState and LearnerModel preserves
    assessed_objectives, mastered_objectives, and active_misconceptions without data loss.
    """
    learner = LearnerModel(session_id="sess_serial_1")
    state = learner.get_or_create_concept("arrays")
    state.mastery = 0.88
    state.assessed_objectives = ["arr_index", "arr_bounds"]
    state.mastered_objectives = ["arr_index"]
    state.active_misconceptions = ["Arrays are dynamic by default in C."]
    state.unresolved_gap = True
    learner.unresolved_gaps = ["arrays"]

    data = learner.model_dump(mode="json")
    restored = LearnerModel.model_validate(data)

    r_state = restored.concepts["arrays"]
    assert r_state.mastery == 0.88
    assert r_state.assessed_objectives == ["arr_index", "arr_bounds"]
    assert r_state.mastered_objectives == ["arr_index"]
    assert r_state.active_misconceptions == ["Arrays are dynamic by default in C."]
    assert r_state.unresolved_gap is True
    assert restored.unresolved_gaps == ["arrays"]
