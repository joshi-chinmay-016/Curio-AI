"""
Phase 7.3 Batch 2: Deterministic Multi-Turn Learning Regression Test Suite.

Tests high-value multi-turn learning behavior:
1. Test A: Incomplete answers followed by successful depth expansion (test_multiturn_incomplete_answer_depth_expansion_to_mastery)
2. Test B: Misconception persistence and evidence-based resolution (test_multiturn_misconception_persists_until_supported_resolution)
   + Specific defect investigation on ChatService.send_message state-merging (test_chat_service_persisted_misconception_clearing_defect)
3. Test C: Mastered concept releases the next core concept (test_multiturn_mastery_advances_to_unassessed_core_concept)
4. Test D: Undefined-term clarification and conceptual resumption (test_multiturn_undefined_term_clarification_resumes_investigation)
5. Test E: Difficulty stability across alternating strong and weak answers (test_difficulty_stability_under_alternating_strong_weak_turns)
6. Session-state isolation between independent sessions (test_learning_progress_isolated_between_two_sessions)

All tests are 100% isolated, using in-memory mocks, zero external network, and zero database access.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
import uuid

import pytest

from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    LearningAssessment,
    MisconceptionEvidence,
    RelevanceLevel,
)
from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.learner_model import LearnerModel, LearnerModelManager
from backend.app.ai.nodes.student_nodes import decision_node, state_updates_node
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConceptCoverageItem,
    ConceptModel,
    ConceptNode,
    ConceptRelationship,
    ConversationContext,
    CoverageStatus,
    CurrentQuestion,
    LearnerModel as SchemaLearnerModel,
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
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)
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
    topic: str = "binary_search",
    active_concept: str = "binary_search",
    recent_strategies: Optional[List[Strategy]] = None,
    concept_mastery: Optional[Dict[str, float]] = None,
    unresolved_misconceptions: Optional[List[str]] = None,
    user_msg: str = "Hello",
    concept_model: Optional[ConceptModel] = None,
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
# Test A: Incomplete Answer Followed by Depth Expansion
# ============================================================================

def test_multiturn_incomplete_answer_depth_expansion_to_mastery():
    """
    Test A: Two-turn progression on concept 'binary_search':
    Turn 1: Relevant, partly correct answer missing substantive mechanism (correctness=0.70, completeness=0.55).
            Engine selects DEPTH_EXPANSION, maintains difficulty (2 -> 2), concept remains 'binary_search'.
    Turn 2: Follow-up providing missing mechanism (correctness=0.88, completeness=0.85).
            Engine recognizes is_strong=True, increments difficulty (2 -> 3), advances mastery.
    """
    engine = DecisionEngine()
    cid = "binary_search"
    c_node = ConceptNode(id=cid, name="Binary Search", difficulty_level=2)
    c_model = ConceptModel(topic="Binary Search", concepts=[c_node], relationships=[])

    # ------------------ TURN 1 ------------------
    ctx_t1 = _make_context(
        difficulty=2,
        confidence=0.50,
        active_concept=cid,
        concept_mastery={cid: 0.20},
        user_msg="Binary search checks the middle and cuts the search in half.",
        concept_model=c_model,
    )
    eval_t1 = TurnEvaluation(
        correctness=0.70,
        clarity=0.80,
        completeness=0.55,
        depth=0.50,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.DEPTH_EXPANSION,
        recommended_difficulty=2,
    )

    dec_t1 = engine.decide(ctx_t1, eval_t1)

    # Assert Turn 1 decision behavior
    assert dec_t1.next_mode == Mode.STUDENT
    assert dec_t1.strategy == Strategy.DEPTH_EXPANSION
    # Incomplete answer does not increment difficulty
    assert dec_t1.difficulty == 2
    assert dec_t1.active_concept == cid

    # Run decision_node to verify QuestionSpecification behavior
    learner_m1 = LearnerModel(session_id=ctx_t1.session_id)
    learner_mgr1 = LearnerModelManager(learner_m1)
    learner_mgr1.update_from_evaluation(cid, eval_t1)
    # Mastery updated from 0.0 + (1 - 0.0) * 0.40 = 0.40 (not yet mastered >= 0.75)
    assert learner_m1.concepts[cid].mastery < 0.75

    state_t1 = {
        "context": ctx_t1,
        "evaluation": eval_t1,
        "concept_model": c_model,
        "learner_model": learner_m1,
    }
    node_res_t1 = decision_node(state_t1)
    spec_t1: QuestionSpecification = node_res_t1["question_specification"]

    assert spec_t1.target_concept == cid
    assert spec_t1.difficulty == 2
    assert spec_t1.learning_objective.objective_type in (
        ObjectiveType.UNDERSTAND_MECHANISM,
        ObjectiveType.APPLY_CONCEPT,
    )

    # ------------------ TURN 2 ------------------
    # Learner now provides the detailed mechanism
    ctx_t2 = _make_context(
        difficulty=2,
        confidence=dec_t1.confidence,
        active_concept=cid,
        recent_strategies=[Strategy.DEPTH_EXPANSION],
        concept_mastery={cid: learner_m1.concepts[cid].mastery},
        user_msg="It computes mid = (low + high) // 2, compares array[mid] with target, and updates low = mid + 1 if target is greater.",
        concept_model=c_model,
    )
    eval_t2 = TurnEvaluation(
        correctness=0.88,
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
        recommended_strategy=Strategy.PROBE_HOW,
        recommended_difficulty=3,
    )

    dec_t2 = engine.decide(ctx_t2, eval_t2)

    # Assert Turn 2 strong answer advancement
    assert dec_t2.next_mode == Mode.STUDENT
    # Strong answer advances difficulty strictly by +1
    assert dec_t2.difficulty == 3
    assert dec_t2.confidence > ctx_t2.current_state.understanding_confidence

    # Learner model update achieves mastery advancement: 0.40 + (1 - 0.40) * 0.40 = 0.64
    learner_mgr1.update_from_evaluation(cid, eval_t2)
    assert learner_m1.concepts[cid].mastery >= 0.60
    assert not learner_m1.concepts[cid].unresolved_gap


# ============================================================================
# Test B: Misconception Persistence & Resolution (Cognitive Pipeline)
# ============================================================================

def test_multiturn_misconception_persists_until_supported_resolution():
    """
    Test B: Multi-turn lifecycle of a misconception:
    Turn 1: Learner introduces misconception -> CHALLENGE_MISCONCEPTION, difficulty decrements or holds, recorded as gap.
    Turn 2: Superficial partial answer does not refute misconception -> gap remains active, mastery blocked, question targets misconception.
    Turn 3: Substantive sound refutation (>= 0.80) -> misconception clears in LearnerModel, mastery permitted.
    """
    engine = DecisionEngine()
    cid = "sorting"
    c_node = ConceptNode(id=cid, name="Sorting", difficulty_level=3)
    c_model = ConceptModel(topic="Sorting", concepts=[c_node], relationships=[])

    learner_m = LearnerModel(session_id="test-session-b")
    learner_mgr = LearnerModelManager(learner_m)

    # ------------------ TURN 1: Misconception Introduced ------------------
    ctx_t1 = _make_context(
        difficulty=3,
        active_concept=cid,
        user_msg="Quicksort is always O(n log n) even when the array is already sorted.",
        concept_model=c_model,
    )
    eval_t1 = TurnEvaluation(
        correctness=0.35,
        clarity=0.80,
        completeness=0.40,
        depth=0.30,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=["Quicksort worst case is O(n log n)"],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap="Quicksort worst case is O(n log n)",
        recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
        recommended_difficulty=2,
    )

    dec_t1 = engine.decide(ctx_t1, eval_t1)
    assert dec_t1.strategy == Strategy.CHALLENGE_MISCONCEPTION
    # Low correctness on misconception decrements difficulty 3 -> 2
    assert dec_t1.difficulty == 2

    learner_mgr.update_from_evaluation(cid, eval_t1)
    c_state = learner_m.concepts[cid]
    assert c_state.unresolved_gap is True
    assert "Quicksort worst case is O(n log n)" in c_state.active_misconceptions
    assert cid in learner_m.unresolved_gaps
    assert c_state.mastery <= 0.35

    # ------------------ TURN 2: Superficial Answer ------------------
    # Learner gives a partial answer without refuting the worst-case misconception
    ctx_t2 = _make_context(
        difficulty=2,
        active_concept=cid,
        recent_strategies=[Strategy.CHALLENGE_MISCONCEPTION],
        unresolved_misconceptions=["Quicksort worst case is O(n log n)"],
        user_msg="Well, quicksort picks a pivot and partitions elements.",
        concept_model=c_model,
    )
    eval_t2 = TurnEvaluation(
        correctness=0.50,
        clarity=0.70,
        completeness=0.40,
        depth=0.35,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],  # Not repeated, but not refuted
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.VERIFY_UNDERSTANDING,
        recommended_difficulty=2,
    )

    # In student_nodes decision_node: unresolved_gap in cand_state keeps answer_driven_need active
    state_t2 = {
        "context": ctx_t2,
        "evaluation": eval_t2,
        "concept_model": c_model,
        "learner_model": learner_m,
    }
    node_res_t2 = decision_node(state_t2)
    spec_t2: QuestionSpecification = node_res_t2["question_specification"]

    # QuestionSelector targets the unresolved misconception
    assert spec_t2.target_concept == cid
    assert spec_t2.learning_objective.objective_type == ObjectiveType.RESOLVE_MISCONCEPTION
    # Misconception remains active in learner model because correctness 0.50 < 0.80
    learner_mgr.update_from_evaluation(cid, eval_t2)
    assert learner_m.concepts[cid].unresolved_gap is True
    assert len(learner_m.concepts[cid].active_misconceptions) > 0

    # ------------------ TURN 3: Substantive Resolution ------------------
    # Learner explains the worst case O(n^2) when already sorted with bad pivot
    ctx_t3 = _make_context(
        difficulty=2,
        active_concept=cid,
        recent_strategies=[Strategy.CHALLENGE_MISCONCEPTION, Strategy.VERIFY_UNDERSTANDING],
        unresolved_misconceptions=["Quicksort worst case is O(n log n)"],
        user_msg="Actually, if Quicksort selects the first element as pivot on an already sorted array, it degrades to O(n^2) because partitions are maximally unbalanced.",
        concept_model=c_model,
    )
    eval_t3 = TurnEvaluation(
        correctness=0.90,
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

    # Update learner model with substantive resolution
    learner_mgr.update_from_evaluation(cid, eval_t3)

    # Verified: learner model clears the misconception and gap
    assert learner_m.concepts[cid].unresolved_gap is False
    assert learner_m.concepts[cid].active_misconceptions == []
    assert cid not in learner_m.unresolved_gaps
    # Progressive mastery reached: 0.15 + (1 - 0.15) * 0.40 = 0.49
    assert learner_m.concepts[cid].mastery >= 0.45


# ============================================================================
# Defect Investigation: ChatService.send_message State-Merging
# ============================================================================

def test_chat_service_persisted_misconception_clearing_defect():
    """
    Defect Investigation: Test whether ChatService.send_message clears resolved misconceptions.
    
    The Batch 1 audit identified:
      existing_misconceptions = db_session.state.unresolved_misconceptions or []
      if updates.unresolved_misconceptions is not None:
          new_misconceptions = list(dict.fromkeys(existing_misconceptions + updates.unresolved_misconceptions))
      else:
          new_misconceptions = list(existing_misconceptions)

    When a misconception is resolved, StateUpdates provides unresolved_misconceptions=[] (or None).
    Because ChatService unions existing_misconceptions with the updates, the resolved misconception
    is never cleared from db_session.state.unresolved_misconceptions.

    Per Phase 7.3 Batch 2 instructions:
    Assert that the resolved misconception is NOT present in the persisted state_update.
    If this fails because of the production union operation, keep the failing regression test,
    do NOT modify production code, and document the failure.
    """
    session_id = uuid.uuid4()
    mock_db = MagicMock()

    # Pre-existing session state has an active misconception from Turn 1
    db_session = MagicMock()
    db_session.id = session_id
    db_session.user_id = "user_123"
    db_session.topic = "Sorting"
    db_session.source_type = "GENERAL"

    db_state = MagicMock()
    db_state.session_id = session_id
    db_state.current_mode = LearningMode.STUDENT
    db_state.difficulty = 2
    db_state.confidence = 0.5
    db_state.active_concept = "quicksort"
    db_state.current_question_id = None
    db_state.interrupted_question_id = None
    db_state.consecutive_strong_answers = 0
    db_state.consecutive_weak_answers = 1
    # Active misconception in DB
    db_state.unresolved_misconceptions = ["Quicksort worst case is O(n log n)"]
    db_state.mastered_concepts = []
    db_state.concept_mastery = {"quicksort": 0.30}
    db_state.misconception_counts = {"Quicksort worst case is O(n log n)": 1}
    db_state.recent_strategy_history = ["CHALLENGE_MISCONCEPTION"]
    db_state.teacher_attempt_count = 0
    db_state.teacher_intervention = None
    db_session.state = db_state

    # Engine returns Turn 3 result: misconception is RESOLVED, updates.unresolved_misconceptions = []
    eval_resolved = TurnEvaluation(
        correctness=0.90,
        clarity=0.90,
        completeness=0.85,
        depth=0.80,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["quicksort"],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=3,
    )
    dec_resolved = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=3,
        confidence=0.75,
        reason="Misconception resolved. Advancing inquiry.",
        active_concept="quicksort",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )
    resp_resolved = AIResponse(
        content="That makes sense. Why does randomized pivot selection prevent that O(n^2) worst case?",
        mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=3,
        confidence=0.75,
    )
    # The engine explicitly communicates that unresolved misconceptions are now empty
    updates_resolved = StateUpdates(
        confidence=0.75,
        difficulty=3,
        active_concept="quicksort",
        consecutive_successes=1,
        consecutive_failures=0,
        unresolved_misconceptions=[],  # Explicitly cleared!
        mastered_concepts=["quicksort"],
    )
    ai_result_resolved = AIResult(
        evaluation=eval_resolved,
        decision=dec_resolved,
        response=resp_resolved,
        state_updates=updates_resolved,
    )

    db_session.document_id = None
    mock_db.query.return_value.filter.return_value.first.return_value = db_session

    mock_engine = MagicMock()
    mock_engine.process.return_value = ai_result_resolved

    service = ChatService(ai_engine=mock_engine)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()

    # Avoid SQLAlchemy model initialization errors by mocking repository methods
    mock_user_msg = MagicMock(id=uuid.uuid4(), session_id=session_id, sender="USER", content="resolving answer")
    mock_ai_msg = MagicMock(id=uuid.uuid4(), session_id=session_id, sender="AI", content=resp_resolved.content)
    service.message_repo.create_message = MagicMock(side_effect=[mock_user_msg, mock_ai_msg])
    service.message_repo.list_by_session = MagicMock(return_value=[])
    service.message_repo.create_evaluation = MagicMock()
    service.turn_assessment_repo.create_assessment = MagicMock()

    # Send resolution message
    service.send_message(
        db=mock_db,
        session_id=session_id,
        message_in=MessageCreate(content="Quicksort degrades to O(n^2) when partitions are unbalanced."),
        user_id="user_123",
    )

    # Inspect the persisted state update passed to session_repo.update_state
    assert service.session_repo.update_state.called
    persisted_state_update = service.session_repo.update_state.call_args[0][2]

    # SPECIFIC DEFECT ASSERTION:
    # A resolved misconception must NOT persist in unresolved_misconceptions after resolution!
    assert "Quicksort worst case is O(n log n)" not in persisted_state_update.unresolved_misconceptions, (
        f"STALE MISCONCEPTION DEFECT DETECTED: ChatService.send_message retained resolved misconception "
        f"in SessionStateBase.unresolved_misconceptions: {persisted_state_update.unresolved_misconceptions}"
    )


def test_chat_service_persisted_misconception_preserved_when_none():
    """
    Case B — No update:
    Existing state contains ["misconception_A"]; the update contains None.
    Expected persisted state: ["misconception_A"].
    """
    session_id = uuid.uuid4()
    mock_db = MagicMock()
    db_session = MagicMock(id=session_id, user_id="user_123", topic="Sorting", source_type="GENERAL", document_id=None)
    db_state = MagicMock(
        session_id=session_id,
        current_mode=LearningMode.STUDENT,
        difficulty=2,
        confidence=0.5,
        active_concept="quicksort",
        current_question_id=None,
        interrupted_question_id=None,
        consecutive_strong_answers=0,
        consecutive_weak_answers=1,
        unresolved_misconceptions=["misconception_A"],
        mastered_concepts=[],
        concept_mastery={},
        misconception_counts={},
        recent_strategy_history=[],
        teacher_attempt_count=0,
        teacher_intervention=None,
    )
    db_session.state = db_state
    mock_db.query.return_value.filter.return_value.first.return_value = db_session

    updates_none = StateUpdates(unresolved_misconceptions=None)
    mock_engine = MagicMock()
    mock_engine.process.return_value = AIResult(
        evaluation=TurnEvaluation(
            correctness=0.7,
            clarity=0.7,
            completeness=0.6,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=[],
            knowledge_gap=None,
            recommended_strategy=Strategy.PROBE_HOW,
            recommended_difficulty=2,
        ),
        decision=LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.PROBE_HOW,
            difficulty=2,
            confidence=0.5,
            reason="Probe",
            active_concept="quicksort",
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        ),
        response=AIResponse(
            content="How does it work?",
            mode=Mode.STUDENT,
            strategy=Strategy.PROBE_HOW,
            difficulty=2,
            confidence=0.5,
        ),
        state_updates=updates_none,
    )

    service = ChatService(ai_engine=mock_engine)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()
    m_user = MagicMock(id=uuid.uuid4(), session_id=session_id, sender="USER", content="test", input_type="TEXT", created_at=datetime.now(timezone.utc))
    m_ai = MagicMock(id=uuid.uuid4(), session_id=session_id, sender="AI", content="How does it work?", input_type="TEXT", created_at=datetime.now(timezone.utc))
    service.message_repo.create_message = MagicMock(side_effect=[m_user, m_ai])
    service.message_repo.list_by_session = MagicMock(return_value=[])
    service.message_repo.create_evaluation = MagicMock()
    service.turn_assessment_repo.create_assessment = MagicMock()

    service.send_message(db=mock_db, session_id=session_id, message_in=MessageCreate(content="test"), user_id="user_123")
    persisted = service.session_repo.update_state.call_args[0][2]
    assert persisted.unresolved_misconceptions == ["misconception_A"]


def test_chat_service_persisted_misconception_replaced_without_stale_union():
    """
    Case C — Authoritative replacement:
    Existing state contains ["misconception_A", "stale_B"]; the update contains ["misconception_C"].
    Expected persisted state: ["misconception_C"].
    """
    session_id = uuid.uuid4()
    mock_db = MagicMock()
    db_session = MagicMock(id=session_id, user_id="user_123", topic="Sorting", source_type="GENERAL", document_id=None)
    db_state = MagicMock(
        session_id=session_id,
        current_mode=LearningMode.STUDENT,
        difficulty=2,
        confidence=0.5,
        active_concept="quicksort",
        current_question_id=None,
        interrupted_question_id=None,
        consecutive_strong_answers=0,
        consecutive_weak_answers=1,
        unresolved_misconceptions=["misconception_A", "stale_B"],
        mastered_concepts=[],
        concept_mastery={},
        misconception_counts={},
        recent_strategy_history=[],
        teacher_attempt_count=0,
        teacher_intervention=None,
    )
    db_session.state = db_state
    mock_db.query.return_value.filter.return_value.first.return_value = db_session

    updates_c = StateUpdates(unresolved_misconceptions=["misconception_C"])
    mock_engine = MagicMock()
    mock_engine.process.return_value = AIResult(
        evaluation=TurnEvaluation(
            correctness=0.3,
            clarity=0.7,
            completeness=0.3,
            depth=0.2,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=["misconception_C"],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=[],
            knowledge_gap=None,
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        ),
        decision=LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.CHALLENGE_MISCONCEPTION,
            difficulty=1,
            confidence=0.3,
            reason="Challenge",
            active_concept="quicksort",
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        ),
        response=AIResponse(
            content="What about C?",
            mode=Mode.STUDENT,
            strategy=Strategy.CHALLENGE_MISCONCEPTION,
            difficulty=1,
            confidence=0.3,
        ),
        state_updates=updates_c,
    )

    service = ChatService(ai_engine=mock_engine)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()
    m_user_c = MagicMock(id=uuid.uuid4(), session_id=session_id, sender="USER", content="test", input_type="TEXT", created_at=datetime.now(timezone.utc))
    m_ai_c = MagicMock(id=uuid.uuid4(), session_id=session_id, sender="AI", content="What about C?", input_type="TEXT", created_at=datetime.now(timezone.utc))
    service.message_repo.create_message = MagicMock(side_effect=[m_user_c, m_ai_c])
    service.message_repo.list_by_session = MagicMock(return_value=[])
    service.message_repo.create_evaluation = MagicMock()
    service.turn_assessment_repo.create_assessment = MagicMock()

    service.send_message(db=mock_db, session_id=session_id, message_in=MessageCreate(content="test"), user_id="user_123")
    persisted = service.session_repo.update_state.call_args[0][2]
    assert persisted.unresolved_misconceptions == ["misconception_C"]
    assert "misconception_A" not in persisted.unresolved_misconceptions
    assert "stale_B" not in persisted.unresolved_misconceptions


# ============================================================================
# Test C: Mastered Concept Releases Next Core Concept
# ============================================================================

def test_multiturn_mastery_advances_to_unassessed_core_concept():
    """
    Test C: Verify topic plan progression:
    - Concept A ('concept_a') is assessed and mastered (mastery >= 0.75, 0 gaps).
    - Concept B ('concept_b') is an unassessed CORE concept whose prerequisites (Concept A) are satisfied.
    - Concept C ('concept_c') is unassessed but has an unmet prerequisite.
    Verify:
    1. The decision node releases target_concept_override for Concept A because it is already mastered.
    2. QuestionSelector selects unassessed core Concept B (Tier 1).
    3. Unmet prerequisite Concept C is NOT selected.
    4. Mastered Concept A is NOT repeated unnecessarily.
    """
    c_a = ConceptNode(id="concept_a", name="Photosynthesis Basics", difficulty_level=1, importance="CORE")
    c_b = ConceptNode(id="concept_b", name="Calvin Cycle", difficulty_level=2, importance="CORE", prerequisites=["concept_a"])
    c_c = ConceptNode(id="concept_c", name="Advanced Photorespiration", difficulty_level=4, importance="CORE", prerequisites=["concept_d"])
    c_d = ConceptNode(id="concept_d", name="RuBisCO Kinetics", difficulty_level=3, importance="CORE")

    c_model = ConceptModel(
        topic="Photosynthesis",
        concepts=[c_a, c_b, c_c, c_d],
        relationships=[
            ConceptRelationship(source_concept_id="concept_a", target_concept_id="concept_b", relationship_type="PREREQUISITE_FOR"),
            ConceptRelationship(source_concept_id="concept_d", target_concept_id="concept_c", relationship_type="PREREQUISITE_FOR"),
        ],
    )

    learner_m = LearnerModel(session_id="test-session-c")
    # Concept A is mastered
    s_a = learner_m.get_or_create_concept("concept_a")
    s_a.mastery = 0.85
    s_a.evidence_count = 2
    s_a.attempt_count = 2
    s_a.unresolved_gap = False
    s_a.active_misconceptions = []

    # Concepts B, C, D are unassessed (mastery = 0.0)
    ctx = _make_context(
        difficulty=2,
        active_concept="concept_a",
        recent_strategies=[Strategy.PROBE_HOW],
        concept_mastery={"concept_a": 0.85},
        concept_model=c_model,
        user_msg="Light reactions produce ATP and NADPH in the thylakoid membrane.",
    )
    # The evaluation for Concept A confirms high understanding
    eval_strong = TurnEvaluation(
        correctness=0.90,
        clarity=0.90,
        completeness=0.85,
        depth=0.80,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["concept_a"],
        knowledge_gap=None,
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=2,
    )

    state = {
        "context": ctx,
        "evaluation": eval_strong,
        "concept_model": c_model,
        "learner_model": learner_m,
    }
    node_res = decision_node(state)
    spec: QuestionSpecification = node_res["question_specification"]

    # In student_nodes.py: is_already_mastered is True (mastery >= 0.75, 0 gaps),
    # so target_concept_override is released to None.
    # QuestionSelector selects concept_b (unassessed core concept whose prerequisites are met).
    assert spec.target_concept == "concept_b", f"Expected 'concept_b' to be selected, got '{spec.target_concept}'"
    assert spec.target_concept != "concept_a", "Mastered concept A should not be selected again"
    assert spec.target_concept != "concept_c", "Concept C has unmet prerequisite concept_d and must not be selected"


# ============================================================================
# Test D: Undefined-Term Clarification and Resumption
# ============================================================================

def test_multiturn_undefined_term_clarification_resumes_investigation():
    """
    Test D: Two turns verifying undefined-term handling:
    Turn 1: Learner uses undefined technical jargon -> Strategy.CLARIFY_TERM targets undefined term.
    Turn 2: Learner explains the term -> CLARIFY_TERM is NOT repeated; engine resumes conceptual probe.
    """
    engine = DecisionEngine()
    cid = "cellular_respiration"
    term = "chemiosmotic_proton_pump"

    # ------------------ TURN 1: Undefined Term ------------------
    ctx_t1 = _make_context(
        difficulty=2,
        active_concept=cid,
        user_msg="ATP is formed because the chemiosmotic_proton_pump activates it.",
    )
    eval_t1 = TurnEvaluation(
        correctness=0.60,
        clarity=0.60,
        completeness=0.50,
        depth=0.40,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[term],
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.CLARIFY_TERM,
        recommended_difficulty=2,
    )

    dec_t1 = engine.decide(ctx_t1, eval_t1)

    assert dec_t1.strategy == Strategy.CLARIFY_TERM
    assert dec_t1.active_concept == term
    assert term in dec_t1.reason

    # ------------------ TURN 2: Term Defined ------------------
    # Learner now provides a clear definition of the term
    ctx_t2 = _make_context(
        difficulty=2,
        active_concept=term,
        recent_strategies=[Strategy.CLARIFY_TERM],
        user_msg="By chemiosmotic proton pump, I mean ATP synthase utilizing the electrochemical H+ gradient across the inner mitochondrial membrane.",
    )
    eval_t2 = TurnEvaluation(
        correctness=0.85,
        clarity=0.90,
        completeness=0.80,
        depth=0.75,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],  # Term is now defined!
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_HOW,
        recommended_difficulty=2,
    )

    dec_t2 = engine.decide(ctx_t2, eval_t2)

    # Strategy must NOT repeat CLARIFY_TERM
    assert dec_t2.strategy != Strategy.CLARIFY_TERM, "Should not repeat CLARIFY_TERM when terms are resolved"
    # Resumes conceptual investigation (e.g. PROBE_HOW or REQUEST_EXAMPLE)
    assert dec_t2.strategy in (
        Strategy.PROBE_HOW,
        Strategy.PROBE_WHY,
        Strategy.REQUEST_EXAMPLE,
        Strategy.DEPTH_EXPANSION,
    )


# ============================================================================
# Test E: Difficulty Stability Across Alternating Answers
# ============================================================================

def test_difficulty_stability_under_alternating_strong_weak_turns():
    """
    Test E: 4 consecutive simulated turns alternating between strong and weak answers.
    Starting difficulty: 3.
    Expected progression: 3 -> 4 -> 3 -> 4 -> 3.
    Asserts:
    1. Each step delta is strictly <= 1.
    2. Difficulty stays within [1, 5].
    3. QuestionSelector with adjust_difficulty=False preserves DecisionEngine's authoritative difficulty.
    """
    engine = DecisionEngine()
    selector = QuestionSelector()
    cid = "recursion"
    c_node = ConceptNode(id=cid, name="Recursion", difficulty_level=3)
    c_model = ConceptModel(topic="Recursion", concepts=[c_node], relationships=[])
    learner_m = LearnerModel(session_id="test-session-e")

    eval_strong = TurnEvaluation(
        correctness=0.85,
        clarity=0.90,
        completeness=0.80,
        depth=0.70,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap=None,
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=4,
    )

    eval_weak = TurnEvaluation(
        correctness=0.35,
        clarity=0.60,
        completeness=0.30,
        depth=0.25,
        relevance=0.80,
        stuck_probability=0.20,
        misconceptions=[],
        missing_concepts=["base_case"],
        undefined_terms=[],
        mastered_concepts=[],
        knowledge_gap="base_case",
        recommended_strategy=Strategy.PROBE_MISSING_CONCEPT,
        recommended_difficulty=2,
    )

    # Turn 0: starting difficulty 3
    curr_diff = 3

    # Sequence of 4 turns: strong, weak, strong, weak
    sequence = [
        ("strong", eval_strong, 4),
        ("weak", eval_weak, 3),
        ("strong", eval_strong, 4),
        ("weak", eval_weak, 3),
    ]

    for turn_idx, (turn_type, evaluation, expected_diff) in enumerate(sequence, start=1):
        ctx = _make_context(
            difficulty=curr_diff,
            active_concept=cid,
            user_msg=f"Turn {turn_idx} {turn_type} answer",
            concept_model=c_model,
        )

        dec = engine.decide(ctx, evaluation)

        # Assert delta <= 1
        delta = abs(dec.difficulty - curr_diff)
        assert delta <= 1, f"Turn {turn_idx} delta {delta} exceeded 1"
        # Assert within bounds [1, 5]
        assert 1 <= dec.difficulty <= 5
        # Assert exact expected difficulty
        assert dec.difficulty == expected_diff, (
            f"Turn {turn_idx} ({turn_type}): expected difficulty {expected_diff}, got {dec.difficulty}"
        )

        # Assert QuestionSelector preserves authoritative difficulty without duplicate adjustment
        spec = selector.select_question_specification(
            concept_model=c_model,
            learner_model=learner_m,
            current_difficulty=dec.difficulty,
            strategy=dec.strategy,
            adjust_difficulty=False,
        )
        assert spec.difficulty == dec.difficulty, (
            f"QuestionSelector modified difficulty ({spec.difficulty} != {dec.difficulty})"
        )

        # Update curr_diff for next turn
        curr_diff = dec.difficulty


# ============================================================================
# Session-State Isolation Test
# ============================================================================

def test_learning_progress_isolated_between_two_sessions():
    """
    Verify complete state isolation between two concurrent sessions:
    - Session A (Photosynthesis) has active misconception, mastery=0.75, difficulty=4, strategy history.
    - Session B (Calculus) has no misconceptions, mastery=0.20, difficulty=1, separate history.
    
    Mutating Session A must not alter Session B across:
    - concept_mastery
    - unresolved_misconceptions
    - difficulty
    - recent_strategy_history
    """
    ctx_a = _make_context(
        session_id="session-a",
        topic="Photosynthesis",
        active_concept="light_reaction",
        difficulty=4,
        confidence=0.70,
        concept_mastery={"light_reaction": 0.75},
        unresolved_misconceptions=["chlorophyll_is_green_because_it_absorbs_green"],
        recent_strategies=[Strategy.ASK_FOUNDATION, Strategy.PROBE_HOW],
    )

    ctx_b = _make_context(
        session_id="session-b",
        topic="Calculus",
        active_concept="derivatives",
        difficulty=1,
        confidence=0.20,
        concept_mastery={"derivatives": 0.20},
        unresolved_misconceptions=[],
        recent_strategies=[Strategy.ASK_FOUNDATION],
    )

    # Snapshot Session B values
    b_mastery_before = dict(ctx_b.current_state.concept_mastery)
    b_misc_before = list(ctx_b.current_state.unresolved_misconceptions)
    b_diff_before = ctx_b.current_state.current_difficulty
    b_history_before = list(ctx_b.current_state.recent_strategy_history)

    # Mutate Session A
    ctx_a.current_state.concept_mastery["light_reaction"] = 0.95
    ctx_a.current_state.concept_mastery["dark_reaction"] = 0.60
    ctx_a.current_state.unresolved_misconceptions.clear()
    ctx_a.current_state.current_difficulty = 5
    ctx_a.current_state.recent_strategy_history.append(Strategy.INCREASE_DIFFICULTY)

    # Assert Session B remains completely untouched
    assert ctx_b.current_state.concept_mastery == b_mastery_before
    assert ctx_b.current_state.unresolved_misconceptions == b_misc_before
    assert ctx_b.current_state.current_difficulty == b_diff_before
    assert ctx_b.current_state.recent_strategy_history == b_history_before

    # Now mutate Session B
    ctx_b.current_state.concept_mastery["derivatives"] = 0.45
    ctx_b.current_state.unresolved_misconceptions.append("derivative_is_integral")
    ctx_b.current_state.current_difficulty = 2

    # Assert Session A remains unchanged
    assert ctx_a.current_state.concept_mastery == {"light_reaction": 0.95, "dark_reaction": 0.60}
    assert ctx_a.current_state.unresolved_misconceptions == []
    assert ctx_a.current_state.current_difficulty == 5
    assert ctx_a.current_state.recent_strategy_history[-1] == Strategy.INCREASE_DIFFICULTY
