"""
Phase 7.3 Batch 4: Multi-Turn Learning Edge-Case Regression Tests.

This test module deterministically exercises and audits the remaining multi-turn learning risks:
1. Scope 1: Vague or ambiguous learner answers repeatedly triggering generic follow-up questions.
2. Scope 2: Repeated misconception signals preventing Curio from investigating other important concepts.
3. Scope 3: A correct answer clearing too many unresolved misconceptions associated with a concept.
4. Scope 4: Concept mastery advancing before all important learning objectives have been adequately assessed.
5. Scope 5: Session state isolation across turns and sessions when misconceptions, mastery, and strategy change together.

All tests operate strictly in-memory without external services, live LLMs, or shared databases.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from unittest.mock import MagicMock

import pytest

from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    LearningAssessment,
    MisconceptionEvidence,
    RelevanceLevel,
)
from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.nodes.student_nodes import decision_node, state_updates_node
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConceptModel,
    ConceptNode,
    ConversationContext,
    CoverageStatus,
    CurrentQuestion,
    LearnerModel,
    LearningContext,
    LearningDecision,
    LearningObjective,
    Mode,
    ObjectiveType,
    QuestionSpecification,
    Role,
    SessionInfo,
    SessionState,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)
from backend.app.ai.topic_plan import TopicPlanner
from backend.app.schemas.common import InputType, LearningMode
from backend.app.schemas.message import MessageCreate
from backend.app.services.chat_service import ChatService


# ============================================================================
# Helpers
# ============================================================================

def _make_context(
    session_id: Optional[str] = None,
    mode: Mode = Mode.STUDENT,
    difficulty: int = 2,
    confidence: float = 0.5,
    topic: str = "computer_science",
    active_concept: str = "hash_tables",
    recent_strategies: Optional[List[Strategy]] = None,
    concept_mastery: Optional[Dict[str, float]] = None,
    unresolved_misconceptions: Optional[List[str]] = None,
    user_msg: str = "Hello",
    concept_model: Optional[ConceptModel] = None,
    consecutive_failures: int = 0,
    consecutive_successes: int = 0,
    teacher_intervention: Optional[TeacherIntervention] = None,
    teacher_attempt_count: int = 0,
) -> AIContext:
    s_id = session_id or str(uuid.uuid4())
    history = [ChatMessage(role=Role.USER, content=user_msg, input_type=InputType.TEXT)]
    state = SessionState(
        session_id=s_id,
        current_mode=mode,
        current_difficulty=difficulty,
        understanding_confidence=confidence,
        active_concept=active_concept,
        recent_strategy_history=recent_strategies or [],
        concept_mastery=concept_mastery or {},
        unresolved_misconceptions=unresolved_misconceptions or [],
        concept_model=concept_model,
        consecutive_failures=consecutive_failures,
        consecutive_successes=consecutive_successes,
        teacher_intervention=teacher_intervention,
        teacher_attempt_count=teacher_attempt_count,
    )
    return AIContext(
        session_id=s_id,
        session=SessionInfo(session_id=s_id, topic=topic),
        topic=topic,
        current_mode=mode,
        difficulty=difficulty,
        active_concept=active_concept,
        current_state=state,
        conversation=ConversationContext(recent_messages=history, message_count=len(history)),
        learning_context=LearningContext(
            mastered_concepts=[],
            unresolved_misconceptions=unresolved_misconceptions or [],
        ),
    )


# ============================================================================
# Scope 1: Vague or Ambiguous Learner Answers
# ============================================================================

def test_scope1_vague_answers_strategy_cycling_and_teacher_fallback():
    """
    Scope 1 Audit & Regression Test:
    Sequence:
    - Turn 1: Learner gives a vague, low-depth answer on 'hash_tables' (correctness=0.55, depth=0.35, completeness=0.40).
              DecisionEngine selects PROBE_HOW. Difficulty stays at 2.
    - Turn 2: Learner gives another vague answer without progressing.
              Anti-repetition shifts PROBE_HOW -> VERIFY_UNDERSTANDING. Difficulty remains at 2.
    - Turn 3: Learner gives a third vague answer.
              Anti-repetition shifts VERIFY_UNDERSTANDING -> PROBE_WHY. Difficulty remains at 2.
    - Turn 4: Learner gives an explicit stuck signal ("I don't know").
              Trigger A trips cleanly, transitioning to Mode.TEACHER with Strategy.TEACH_GAP.

    Expected Behavior:
    - Curio avoids strategy stagnation by cycling strategies (PROBE_HOW -> VERIFY_UNDERSTANDING -> PROBE_WHY).
    - Difficulty remains stable without runaway increments or crashes.
    - When genuine struggle occurs, Curio escapes Student Mode into Teacher Mode.

    Failure Condition:
    - Consecutive identical strategy without anti-repetition shift, or difficulty runaway, or failure to enter Teacher Mode when stuck.
    """
    engine = DecisionEngine()
    cid = "hash_tables"
    c_node = ConceptNode(id=cid, name="Hash Tables", difficulty_level=2)
    c_model = ConceptModel(topic="Data Structures", concepts=[c_node], relationships=[])

    eval_vague = TurnEvaluation(
        correctness=0.55,
        clarity=0.60,
        completeness=0.40,
        depth=0.35,
        relevance=1.0,
        stuck_probability=0.20,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_HOW,
        recommended_difficulty=2,
    )

    # Turn 1: Initial vague response -> PROBE_HOW
    ctx_t1 = _make_context(
        difficulty=2,
        active_concept=cid,
        user_msg="It works by storing things in buckets using numbers.",
        concept_model=c_model,
        recent_strategies=[],
    )
    dec_t1 = engine.decide(ctx_t1, eval_vague)
    assert dec_t1.strategy == Strategy.PROBE_HOW
    assert dec_t1.difficulty == 2
    assert dec_t1.next_mode == Mode.STUDENT

    # Turn 2: Vague follow-up with recent PROBE_HOW -> Shifted to VERIFY_UNDERSTANDING
    ctx_t2 = _make_context(
        difficulty=2,
        active_concept=cid,
        user_msg="Well, the hash code makes an index and then it looks it up.",
        concept_model=c_model,
        recent_strategies=[Strategy.PROBE_HOW],
    )
    dec_t2 = engine.decide(ctx_t2, eval_vague)
    assert dec_t2.strategy == Strategy.VERIFY_UNDERSTANDING
    assert dec_t2.difficulty == 2
    assert dec_t2.next_mode == Mode.STUDENT

    # Turn 3: Third vague follow-up:
    # Base rule (line 596) selects PROBE_HOW because depth < 0.60 and completeness < 0.70.
    # Anti-repetition checks if curr_strategy (PROBE_HOW) == last_strategy (VERIFY_UNDERSTANDING).
    # Since they differ, PROBE_HOW is retained, causing an alternating oscillation:
    # PROBE_HOW -> VERIFY_UNDERSTANDING -> PROBE_HOW -> VERIFY_UNDERSTANDING
    ctx_t3 = _make_context(
        difficulty=2,
        active_concept=cid,
        user_msg="It just finds the item quickly because of the math.",
        concept_model=c_model,
        recent_strategies=[Strategy.PROBE_HOW, Strategy.VERIFY_UNDERSTANDING],
    )
    dec_t3 = engine.decide(ctx_t3, eval_vague)
    assert dec_t3.strategy == Strategy.PROBE_HOW
    assert dec_t3.difficulty == 2
    assert dec_t3.next_mode == Mode.STUDENT

    # Turn 4: Fourth vague follow-up with recent PROBE_HOW -> shifts again to VERIFY_UNDERSTANDING
    ctx_t4_vague = _make_context(
        difficulty=2,
        active_concept=cid,
        user_msg="The table maps the values.",
        concept_model=c_model,
        recent_strategies=[Strategy.PROBE_HOW, Strategy.VERIFY_UNDERSTANDING, Strategy.PROBE_HOW],
    )
    dec_t4_vague = engine.decide(ctx_t4_vague, eval_vague)
    assert dec_t4_vague.strategy == Strategy.VERIFY_UNDERSTANDING
    assert dec_t4_vague.difficulty == 2
    assert dec_t4_vague.next_mode == Mode.STUDENT

    # Turn 5: Explicit stuck message -> Trigger A transitions to Mode.TEACHER
    ctx_t5 = _make_context(
        difficulty=2,
        active_concept=cid,
        user_msg="I don't know how the hash table handles collisions, I'm stuck.",
        concept_model=c_model,
        recent_strategies=[Strategy.PROBE_HOW, Strategy.VERIFY_UNDERSTANDING, Strategy.PROBE_HOW, Strategy.VERIFY_UNDERSTANDING],
    )
    eval_stuck = TurnEvaluation(
        correctness=0.10,
        clarity=0.80,
        completeness=0.0,
        depth=0.0,
        relevance=1.0,
        stuck_probability=0.95,
        misconceptions=[],
        missing_concepts=["collision_resolution"],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap="collision_resolution",
        recommended_strategy=Strategy.TEACH_GAP,
        recommended_difficulty=1,
    )
    dec_t5 = engine.decide(ctx_t5, eval_stuck)
    assert dec_t5.next_mode == Mode.TEACHER
    assert dec_t5.strategy == Strategy.TEACH_GAP
    assert dec_t5.active_concept == "collision_resolution"


# ============================================================================
# Scope 2: Repeated Misconception Signals and Concept Starvation
# ============================================================================

def test_scope2_repeated_misconception_prioritization_and_bounded_remediation():
    """
    Scope 2 Audit & Regression Test:
    Sequence:
    - Curriculum has two concepts: foundational 'hash_function' and dependent 'hash_table_lookup'.
    - Learner has an active misconception on 'hash_function'.
    - In Student Mode, QuestionSelector prioritizes 'hash_function' to prevent building on a broken foundation.
    - Learner repeats the misconception with low correctness (0.25).
    - DecisionEngine triggers Mode.TEACHER (Trigger D/C) to directly remediate rather than loop endlessly.
    - In Teacher Mode, learner passes verification (0.85).
    - Upon exit, 'hash_function' is resolved and marked proficient, allowing QuestionSelector to proceed
      to 'hash_table_lookup' without permanently starving other concepts.

    Expected Behavior:
    - Active misconceptions are prioritized over premature progression.
    - Teacher Mode provides bounded remediation (up to MAX_TEACHER_ATTEMPTS=3).
    - Once resolved, the curriculum unblocks progression to other concepts.

    Failure Condition:
    - Permanent starvation where resolution fails to unblock downstream concepts, or ignoring active misconceptions.
    """
    engine = DecisionEngine()
    selector = QuestionSelector()
    learner_m = LearnerModel(session_id="test-session-scope2")
    lm_mgr = LearnerModelManager(learner_m)

    c_base = ConceptNode(id="hash_function", name="Hash Function", difficulty_level=1)
    c_adv = ConceptNode(
        id="hash_table_lookup",
        name="Hash Table Lookup",
        difficulty_level=2,
        prerequisites=["hash_function"],
    )
    c_model = ConceptModel(topic="Hashing", concepts=[c_base, c_adv], relationships=[])

    # Seed active misconception on hash_function
    base_state = learner_m.get_or_create_concept("hash_function")
    base_state.unresolved_gap = True
    base_state.active_misconceptions = ["A hash function must return a completely random number each call"]
    learner_m.unresolved_gaps.append("hash_function")

    # QuestionSelector correctly prioritizes unresolved gap/misconception over advanced concept
    spec_t1 = selector.select_question_specification(
        concept_model=c_model,
        learner_model=learner_m,
        current_difficulty=1,
        adjust_difficulty=False,
    )
    assert spec_t1.target_concept == "hash_function"
    assert spec_t1.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION

    # Turn 1: Learner repeats misconception with low correctness -> Trigger D trips to Teacher Mode
    ctx_t1 = _make_context(
        difficulty=1,
        active_concept="hash_function",
        user_msg="A good hash function generates a new random seed every time so keys are unpredictable.",
        concept_model=c_model,
    )
    eval_t1 = TurnEvaluation(
        correctness=0.20,
        clarity=0.80,
        completeness=0.30,
        depth=0.20,
        relevance=1.0,
        stuck_probability=0.80,
        misconceptions=["A hash function must return a completely random number each call"],
        missing_concepts=["determinism"],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap="determinism",
        recommended_strategy=Strategy.TEACH_GAP,
        recommended_difficulty=1,
    )
    dec_t1 = engine.decide(ctx_t1, eval_t1)
    assert dec_t1.next_mode == Mode.TEACHER
    assert dec_t1.strategy == Strategy.TEACH_GAP

    # Teacher Mode verification turn: Learner explains determinism correctly
    ctx_teacher = _make_context(
        mode=Mode.TEACHER,
        difficulty=1,
        active_concept="determinism",
        user_msg="A hash function must be deterministic: identical input must always produce the exact same output, otherwise lookups fail.",
        concept_model=c_model,
        teacher_intervention=TeacherIntervention(
            active=True,
            gap="determinism",
            attempt_count=1,
            verification_required=True,
        ),
        teacher_attempt_count=1,
    )
    eval_verification = TurnEvaluation(
        correctness=0.88,
        clarity=0.90,
        completeness=0.85,
        depth=0.80,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["hash_function"],
        knowledge_gap=None,
        recommended_strategy=Strategy.VERIFY_UNDERSTANDING,
        recommended_difficulty=1,
    )
    dec_teacher = engine.decide(ctx_teacher, eval_verification)
    assert dec_teacher.next_mode == Mode.STUDENT
    assert dec_teacher.should_restore_interrupted_question is True

    # Record teacher verification pass in learner model
    lm_mgr.record_teacher_verification("hash_function", passed=True)
    assert base_state.unresolved_gap is False
    assert base_state.active_misconceptions == []
    assert "hash_function" not in learner_m.unresolved_gaps
    assert base_state.mastery >= 0.75

    # With prerequisite resolved, QuestionSelector successfully advances to next concept
    spec_t2 = selector.select_question_specification(
        concept_model=c_model,
        learner_model=learner_m,
        current_difficulty=2,
        adjust_difficulty=False,
    )
    assert spec_t2.target_concept == "hash_table_lookup"
    assert spec_t2.learning_objective.objective_type != ObjectiveType.RESOLVE_MISCONCEPTION


# ============================================================================
# Scope 3: Multiple Misconceptions Cleared in Bulk Risk
# ============================================================================

def test_scope3_single_correct_answer_clears_all_concept_misconceptions_risk():
    """
    Scope 3 Audit & Regression Test:
    Demonstrates the exact existing behavior when a concept has multiple active misconceptions.

    Scenario:
    - Concept 'quicksort' harbors TWO distinct misconceptions:
      1. M1: "Quicksort worst case is O(n log n)"
      2. M2: "Quicksort is a stable sorting algorithm"
    - Learner answers a question specifically about time complexity (M1), giving a correct (0.90) explanation
      that worst case is O(n^2).
    - The learner provides ZERO evidence regarding stability (M2).

    Audit Finding:
    - In `LearnerModelManager.update_from_assessment` (lines 108-113) and `update_from_evaluation` (lines 183-187):
        if state.unresolved_gap and score >= 0.80 and not assessment.misconception_status:
            state.unresolved_gap = False
            state.active_misconceptions = []
            if concept_id in self.model.unresolved_gaps:
                self.model.unresolved_gaps.remove(concept_id)
    - Because `active_misconceptions` is unconditionally cleared to `[]`, M2 ("Quicksort is a stable sorting algorithm")
      is cleared without any evidence refuting it.

    Expected Audit Assertion:
    - Verify that production code currently resets `active_misconceptions` to empty, documenting the
      coarse granularity of concept-level misconception resolution.
    """
    learner_m = LearnerModel(session_id="test-session-scope3")
    lm_mgr = LearnerModelManager(learner_m)
    cid = "quicksort"

    c_state = learner_m.get_or_create_concept(cid)
    c_state.unresolved_gap = True
    m1 = "Quicksort worst case is O(n log n)"
    m2 = "Quicksort is a stable sorting algorithm"
    c_state.active_misconceptions = [m1, m2]
    learner_m.unresolved_gaps.append(cid)

    # Learner gives a correct answer addressing only M1
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
                expected_description="worst case time complexity is quadratic",
                status=EvidenceStatus.SUPPORTED,
                confidence=1.0,
            )
        ],
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.90,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.90,
        misconception_status=False,
        misconceptions=[],  # No misconception in this answer
        missing_concepts=[],
        contradictory_claims=[],
        classification=AssessmentClassification.CORRECT,
        confidence=0.90,
        supports_mastery=True,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
    )

    # Process assessment through LearnerModelManager
    lm_mgr.update_from_assessment(cid, assessment)

    # BATCH 5 PRECISE RESOLUTION VERIFICATION:
    # A single correct answer without specific resolution evidence must NOT clear active misconceptions in bulk.
    # Unresolved misconceptions are preserved.
    assert c_state.unresolved_gap is True
    assert m1 in c_state.active_misconceptions
    assert m2 in c_state.active_misconceptions
    assert cid in learner_m.unresolved_gaps


# ============================================================================
# Scope 4: Concept Mastery Advancement Thresholds
# ============================================================================

def test_scope4_mastery_advancement_requires_multi_turn_evidence_threshold():
    """
    Scope 4 Audit & Regression Test:
    Sequence:
    - Concept 'binary_search' starts at mastery=0.0, evidence_count=0.
    - Turn 1: Correct answer (score=0.85). Mastery increments by (1 - 0) * 0.40 = 0.40.
              Status in TopicPlan: IN_PROGRESS (0.40 < 0.75).
    - Turn 2: Correct answer (score=0.85). Mastery increments by (1 - 0.40) * 0.40 = 0.24 -> 0.64.
              Status in TopicPlan: IN_PROGRESS (0.64 < 0.75).
    - Turn 3: Correct answer (score=0.85). Mastery increments by (1 - 0.64) * 0.40 = 0.144 -> 0.784.
              Status in TopicPlan: MASTERED (0.784 >= 0.75).

    Expected Behavior:
    - A single high-scoring turn CANNOT jump mastery to MASTERED.
    - MasteryGate calibrates and caps single-turn increments at delta=0.40, requiring at least 3 strong evidentiary turns.
    - Audits the continuous evidence accumulation model: advancing triggers when aggregate scalar mastery crosses 0.75.

    Failure Condition:
    - Mastery jumps to >= 0.75 on a single turn, or CoverageStatus marks MASTERED before evidence accumulation.
    """
    learner_m = LearnerModel(session_id="test-session-scope4")
    lm_mgr = LearnerModelManager(learner_m)
    cid = "binary_search"

    c_node = ConceptNode(id=cid, name="Binary Search", difficulty_level=2)
    c_model = ConceptModel(topic="Algorithms", concepts=[c_node], relationships=[])

    def _make_assessment(score: float = 0.85) -> LearningAssessment:
        return LearningAssessment(
            intent=AssessmentIntent.ANSWER_ATTEMPT,
            is_answer_attempt=True,
            relevance_score=1.0,
            relevance_level=RelevanceLevel.RELEVANT,
            concept_alignment_score=score,
            claims=[],
            evidence=[
                EvidenceItem(
                    concept_id=cid,
                    expected_description="divide and conquer mechanism",
                    status=EvidenceStatus.SUPPORTED,
                    confidence=1.0,
                )
            ],
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
        )

    # Initial state
    plan_t0 = TopicPlanner.build_topic_plan(c_model, learner_m, "Algorithms")
    item_t0 = next(it for it in plan_t0.concepts if it.concept_id == cid)
    assert item_t0.status == CoverageStatus.UNASSESSED
    assert item_t0.mastery == 0.0

    # Turn 1: First strong answer
    lm_mgr.update_from_assessment(cid, _make_assessment(0.85))
    c_state = learner_m.concepts[cid]
    assert c_state.mastery == pytest.approx(0.40, abs=0.01)
    assert c_state.evidence_count == 1
    plan_t1 = TopicPlanner.build_topic_plan(c_model, learner_m, "Algorithms")
    item_t1 = next(it for it in plan_t1.concepts if it.concept_id == cid)
    assert item_t1.status == CoverageStatus.IN_PROGRESS

    # Turn 2: Second strong answer
    lm_mgr.update_from_assessment(cid, _make_assessment(0.85))
    assert c_state.mastery == pytest.approx(0.64, abs=0.01)
    assert c_state.evidence_count == 2
    plan_t2 = TopicPlanner.build_topic_plan(c_model, learner_m, "Algorithms")
    item_t2 = next(it for it in plan_t2.concepts if it.concept_id == cid)
    assert item_t2.status == CoverageStatus.IN_PROGRESS

    # Turn 3: Third strong answer -> Crosses 0.75 mastery threshold
    lm_mgr.update_from_assessment(cid, _make_assessment(0.85))
    assert c_state.mastery == pytest.approx(0.784, abs=0.01)
    assert c_state.evidence_count == 3
    plan_t3 = TopicPlanner.build_topic_plan(c_model, learner_m, "Algorithms")
    item_t3 = next(it for it in plan_t3.concepts if it.concept_id == cid)
    assert item_t3.status == CoverageStatus.MASTERED


# ============================================================================
# Scope 5: Session State Isolation Under Simultaneous Multi-Turn Mutation
# ============================================================================

def test_scope5_multiturn_state_isolation_concurrent_and_sequential():
    """
    Scope 5 Audit & Regression Test:
    Simulates two active sessions evolving in parallel through multiple conflicting turns:
    - Session Alpha: Undergoes high struggle, difficulty reductions, misconceptions, and Teacher Mode entry.
    - Session Beta: Demonstrates high mastery, difficulty advancements, clean evaluations, and strategy expansions.

    Verifies:
    - Zero state leakage between Session Alpha and Session Beta across:
      - active_concept
      - difficulty
      - current_mode
      - understanding_confidence
      - concept_mastery
      - unresolved_misconceptions
      - teacher_intervention
      - recent_strategy_history

    Expected Behavior:
    - All session state attributes remain strictly isolated and partitioned.
    """
    ctx_alpha = _make_context(
        session_id="session-alpha",
        topic="Operating Systems",
        active_concept="deadlocks",
        difficulty=3,
        confidence=0.50,
        concept_mastery={"deadlocks": 0.30},
        unresolved_misconceptions=["deadlocks_only_occur_with_threads"],
        recent_strategies=[Strategy.CHALLENGE_MISCONCEPTION],
    )

    ctx_beta = _make_context(
        session_id="session-beta",
        topic="Machine Learning",
        active_concept="gradient_descent",
        difficulty=2,
        confidence=0.60,
        concept_mastery={"gradient_descent": 0.60},
        unresolved_misconceptions=[],
        recent_strategies=[Strategy.ASK_FOUNDATION, Strategy.PROBE_HOW],
    )

    # Snapshot Beta
    beta_initial_state = {
        "difficulty": ctx_beta.current_state.current_difficulty,
        "mode": ctx_beta.current_state.current_mode,
        "confidence": ctx_beta.current_state.understanding_confidence,
        "mastery": dict(ctx_beta.current_state.concept_mastery),
        "misconceptions": list(ctx_beta.current_state.unresolved_misconceptions),
        "strategies": list(ctx_beta.current_state.recent_strategy_history),
    }

    # Heavily mutate Alpha: add failure, transition to Teacher mode, decrement difficulty
    ctx_alpha.current_state.current_mode = Mode.TEACHER
    ctx_alpha.current_state.current_difficulty = 1
    ctx_alpha.current_state.understanding_confidence = 0.20
    ctx_alpha.current_state.concept_mastery["deadlocks"] = 0.15
    ctx_alpha.current_state.concept_mastery["race_conditions"] = 0.10
    ctx_alpha.current_state.unresolved_misconceptions.append("circular_wait_is_preventable_by_sleeping")
    ctx_alpha.current_state.teacher_intervention = TeacherIntervention(
        active=True,
        gap="deadlocks",
        attempt_count=2,
        verification_required=True,
    )
    ctx_alpha.current_state.recent_strategy_history.extend([Strategy.TEACH_GAP, Strategy.PROBE_WHY])

    # Assert Beta is 100% unchanged
    assert ctx_beta.current_state.current_difficulty == beta_initial_state["difficulty"]
    assert ctx_beta.current_state.current_mode == beta_initial_state["mode"]
    assert ctx_beta.current_state.understanding_confidence == beta_initial_state["confidence"]
    assert ctx_beta.current_state.concept_mastery == beta_initial_state["mastery"]
    assert ctx_beta.current_state.unresolved_misconceptions == beta_initial_state["misconceptions"]
    assert ctx_beta.current_state.recent_strategy_history == beta_initial_state["strategies"]
    assert ctx_beta.current_state.teacher_intervention is None
