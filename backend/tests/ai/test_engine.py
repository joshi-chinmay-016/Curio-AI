import sys
import pytest

from backend.app.ai import (
    CurioEngine,
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    Difficulty,
    InputType,
    LearningContext,
    LearningDecision,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    SourceMode,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
)
from backend.app.ai.graph import build_curio_graph
from backend.app.ai.providers.mock_provider import MockLLMProvider


def _build_base_context(**kwargs) -> AIContext:
    """Helper to build a standard baseline AIContext for engine testing."""
    session_info = SessionInfo(
        session_id=kwargs.get("session_id", "sess_default_01"),
        topic=kwargs.get("topic", "Recursion"),
        source_mode=kwargs.get("source_mode", SourceMode.GENERAL),
    )
    current_state = kwargs.get(
        "current_state",
        SessionState(
            session_id=session_info.session_id,
            current_mode=Mode.STUDENT,
            current_difficulty=3,
            understanding_confidence=0.68,
            active_concept="base_case",
            current_question=CurrentQuestion(
                id="q_123",
                content="Why is a base case necessary?",
                concept="base_case",
                difficulty=3,
            ),
        ),
    )
    conversation = kwargs.get(
        "conversation",
        ConversationContext(
            recent_messages=[
                ChatMessage(
                    role=Role.ASSISTANT,
                    content="Why is a base case necessary?",
                ),
                ChatMessage(
                    role=Role.USER,
                    content="It stops the function from calling itself forever.",
                ),
            ],
            message_count=2,
        ),
    )

    ctx_kwargs = {
        "session": session_info,
        "current_state": current_state,
        "conversation": conversation,
    }
    if "learning_context" in kwargs:
        ctx_kwargs["learning_context"] = kwargs["learning_context"]
    if "source_context" in kwargs:
        ctx_kwargs["source_context"] = kwargs["source_context"]

    return AIContext(**ctx_kwargs)


# =====================================================================
# 1. Complete AIContext Test
# =====================================================================

def test_engine_process_complete_ai_context():
    """
    Test 1: Complete AIContext.
    Verifies CurioEngine processes an AIContext containing all sub-models:
    session info, SessionState with all optional fields filled, conversation messages,
    learning context (with evaluations and intervention), and source context dict.
    """
    engine = CurioEngine()

    session_info = SessionInfo(
        session_id="sess_full_001",
        topic="Binary Trees",
        source_mode=SourceMode.DOCUMENT,
    )
    session_state = SessionState(
        session_id="sess_full_001",
        current_mode=Mode.STUDENT,
        current_difficulty=3,
        understanding_confidence=0.75,
        active_concept="tree_traversal",
        current_question=CurrentQuestion(
            id="q_tree",
            content="Explain in-order traversal.",
            concept="tree_traversal",
            difficulty=3,
        ),
        interrupted_question=CurrentQuestion(
            id="q_prev",
            content="What is a binary tree?",
            concept="tree_definition",
            difficulty=2,
        ),
        consecutive_failures=1,
        consecutive_successes=2,
        teacher_attempt_count=1,
        recent_strategy_history=[Strategy.PROBE_WHY],
        misconception_counts={"bst_confusion": 1},
        concept_mastery={"tree_definition": 0.90, "tree_traversal": 0.60},
        unresolved_misconceptions=["bst_confusion"],
        teacher_intervention=TeacherIntervention(
            active=False,
            gap="BST ordering property",
            attempt_count=1,
            verification_required=True,
        ),
    )
    conversation = ConversationContext(
        recent_messages=[
            ChatMessage(role=Role.ASSISTANT, content="Explain in-order traversal."),
            ChatMessage(role=Role.USER, content="We visit left child, root, then right child."),
        ],
        message_count=2,
    )
    learning_context = LearningContext(
        mastered_concepts=["tree_definition"],
        unresolved_misconceptions=["bst_confusion"],
        recent_evaluations=[
            TurnEvaluation(
                correctness=0.9,
                clarity=0.9,
                completeness=0.8,
                depth=0.7,
                relevance=1.0,
                stuck_probability=0.0,
                recommended_strategy=Strategy.PROBE_WHY,
                recommended_difficulty=3,
            )
        ],
        teacher_intervention=TeacherIntervention(
            active=False,
            gap="BST ordering property",
            attempt_count=1,
            verification_required=True,
        ),
    )
    source_context = {
        "document_id": "doc_algo_101",
        "title": "Introduction to Trees",
        "excerpt": "In-order traversal visits left subtree, root, right subtree.",
    }

    context = AIContext(
        session=session_info,
        current_state=session_state,
        conversation=conversation,
        learning_context=learning_context,
        source_context=source_context,
    )

    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.evaluation is not None
    assert result.decision is not None
    assert result.response is not None
    assert result.state_updates is not None


# =====================================================================
# 2. Missing Optional Source Context Test
# =====================================================================

def test_engine_process_missing_optional_source_context():
    """
    Test 2: Missing optional source context.
    Verifies that when source_context is None, CurioEngine.process() still works smoothly.
    """
    engine = CurioEngine()
    context = _build_base_context(source_context=None)

    assert context.source_context is None

    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.evaluation is not None
    assert result.decision is not None
    assert result.response is not None
    assert result.state_updates is not None


# =====================================================================
# 3. Empty Conversation Test
# =====================================================================

def test_engine_process_empty_conversation():
    """
    Test 3: Empty conversation.
    Verifies that when the conversation has no messages (e.g. at the start of a session),
    CurioEngine returns a valid AIResult.
    """
    engine = CurioEngine()
    empty_conversation = ConversationContext(recent_messages=[], message_count=0)
    context = _build_base_context(conversation=empty_conversation)

    assert len(context.conversation.recent_messages) == 0
    assert context.conversation.message_count == 0

    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.evaluation is not None
    assert result.decision is not None
    assert result.response is not None
    assert result.state_updates is not None
    assert len(result.response.content) > 0


# =====================================================================
# 4. Minimal / Default SessionState Test
# =====================================================================

def test_engine_process_minimal_default_session_state():
    """
    Test 4: Minimal/default SessionState.
    Uses a valid SessionState where all optional fields are omitted/defaulted.
    Verifies that processing does not fail.
    """
    engine = CurioEngine()
    minimal_state = SessionState(session_id="sess_minimal_001")

    # Confirm default values
    assert minimal_state.current_mode == Mode.STUDENT
    assert minimal_state.current_difficulty == 1
    assert minimal_state.understanding_confidence == 0.0
    assert minimal_state.active_concept == ""
    assert minimal_state.current_question is None
    assert minimal_state.interrupted_question is None
    assert minimal_state.consecutive_failures == 0
    assert minimal_state.consecutive_successes == 0
    assert minimal_state.teacher_attempt_count == 0
    assert minimal_state.recent_strategy_history == []
    assert minimal_state.misconception_counts == {}
    assert minimal_state.concept_mastery == {}
    assert minimal_state.unresolved_misconceptions == []
    assert minimal_state.teacher_intervention is None

    context = _build_base_context(current_state=minimal_state)
    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.evaluation is not None
    assert result.decision is not None
    assert result.response is not None
    assert result.state_updates is not None


# =====================================================================
# 5. Missing / Default Learning Context Test
# =====================================================================

def test_engine_process_missing_learning_context():
    """
    Test 5: Missing / empty learning context.
    Verifies that when learning_context is omitted or instantiated empty,
    CurioEngine still produces a valid AIResult.
    """
    engine = CurioEngine()

    # Case A: learning_context omitted in AIContext kwargs (relies on default_factory)
    context_omitted = AIContext(
        session=SessionInfo(session_id="sess_lc_01", topic="Sorting"),
        current_state=SessionState(session_id="sess_lc_01"),
        conversation=ConversationContext(),
    )
    result_omitted = engine.process(context_omitted)
    assert isinstance(result_omitted, AIResult)
    assert result_omitted.response is not None

    # Case B: learning_context explicitly instantiated with all defaults
    context_empty_lc = _build_base_context(learning_context=LearningContext())
    assert context_empty_lc.learning_context.mastered_concepts == []
    assert context_empty_lc.learning_context.unresolved_misconceptions == []
    assert context_empty_lc.learning_context.recent_evaluations == []
    assert context_empty_lc.learning_context.teacher_intervention is None

    result_empty_lc = engine.process(context_empty_lc)
    assert isinstance(result_empty_lc, AIResult)
    assert result_empty_lc.decision is not None


# =====================================================================
# 6. Optional Current / Interrupted Question Test
# =====================================================================

def test_engine_process_optional_questions_permutations():
    """
    Test 6: Optional current/interrupted question.
    Verifies that CurioEngine operates properly across all question permutations:
    - current_question=None and interrupted_question=None
    - current_question present and interrupted_question=None
    - both current_question and interrupted_question present
    """
    engine = CurioEngine()

    # Permutation 1: Both None
    state_none = SessionState(
        session_id="sess_q_none",
        current_question=None,
        interrupted_question=None,
    )
    ctx1 = _build_base_context(current_state=state_none)
    res1 = engine.process(ctx1)
    assert isinstance(res1, AIResult)
    assert res1.response is not None

    # Permutation 2: current_question present, interrupted_question=None
    state_current_only = SessionState(
        session_id="sess_q_curr",
        current_question=CurrentQuestion(
            id="q_curr", content="What is a base case?", concept="base_case", difficulty=2
        ),
        interrupted_question=None,
    )
    ctx2 = _build_base_context(current_state=state_current_only)
    res2 = engine.process(ctx2)
    assert isinstance(res2, AIResult)
    assert res2.response is not None

    # Permutation 3: Both present
    state_both = SessionState(
        session_id="sess_q_both",
        current_question=CurrentQuestion(
            id="q_curr", content="What is a base case?", concept="base_case", difficulty=2
        ),
        interrupted_question=CurrentQuestion(
            id="q_int", content="Explain recursion.", concept="recursion", difficulty=1
        ),
    )
    ctx3 = _build_base_context(current_state=state_both)
    res3 = engine.process(ctx3)
    assert isinstance(res3, AIResult)
    assert res3.response is not None


# =====================================================================
# 7. Optional Confidence / Mastery / Misconception Fields Test
# =====================================================================

def test_engine_process_optional_confidence_mastery_misconceptions():
    """
    Test 7: Optional confidence/mastery/misconception fields.
    Tests valid None/empty/default representations supported by the schemas for:
    - understanding_confidence (0.0, 0.5, 1.0)
    - unresolved_misconceptions (empty list)
    - mastered_concepts (empty list)
    - concept_mastery (empty dict)
    - teacher_intervention (None)
    """
    engine = CurioEngine()

    # Case A: Boundary confidence 0.0, empty collections, None intervention
    state_zero_conf = SessionState(
        session_id="sess_conf_0",
        understanding_confidence=0.0,
        unresolved_misconceptions=[],
        concept_mastery={},
        teacher_intervention=None,
    )
    ctx_a = _build_base_context(
        current_state=state_zero_conf,
        learning_context=LearningContext(
            mastered_concepts=[],
            unresolved_misconceptions=[],
            teacher_intervention=None,
        ),
    )
    res_a = engine.process(ctx_a)
    assert isinstance(res_a, AIResult)
    assert res_a.decision is not None

    # Case B: Boundary confidence 1.0 with populated mastery
    state_max_conf = SessionState(
        session_id="sess_conf_1",
        understanding_confidence=1.0,
        concept_mastery={"recursion": 1.0, "base_case": 0.95},
        unresolved_misconceptions=[],
        teacher_intervention=None,
    )
    ctx_b = _build_base_context(
        current_state=state_max_conf,
        learning_context=LearningContext(
            mastered_concepts=["recursion", "base_case"],
            unresolved_misconceptions=[],
            teacher_intervention=None,
        ),
    )
    res_b = engine.process(ctx_b)
    assert isinstance(res_b, AIResult)
    assert res_b.decision is not None


# =====================================================================
# 8. AIResult Contract Integrity Test
# =====================================================================

def test_ai_result_contract_integrity():
    """
    Test 8: AIResult contract.
    For every successful process call, verifies the result strictly conforms to:
    - evaluation (TurnEvaluation): scores between 0.0 and 1.0
    - decision (LearningDecision): difficulty between 1 and 5, confidence 0.0..1.0
    - response (AIResponse): non-empty content, valid mode, valid strategy
    - state_updates (StateUpdates): contains recommended changes
    """
    engine = CurioEngine()
    context = _build_base_context()

    result = engine.process(context)

    # Top-level contract existence
    assert isinstance(result, AIResult)
    assert isinstance(result.evaluation, TurnEvaluation)
    assert isinstance(result.decision, LearningDecision)
    assert isinstance(result.response, AIResponse)
    assert isinstance(result.state_updates, StateUpdates)

    # Evaluation bounds
    assert 0.0 <= result.evaluation.correctness <= 1.0
    assert 0.0 <= result.evaluation.clarity <= 1.0
    assert 0.0 <= result.evaluation.completeness <= 1.0
    assert 0.0 <= result.evaluation.depth <= 1.0
    assert 0.0 <= result.evaluation.relevance <= 1.0
    assert 0.0 <= result.evaluation.stuck_probability <= 1.0
    assert 1 <= result.evaluation.recommended_difficulty <= 5
    assert isinstance(result.evaluation.recommended_strategy, Strategy)

    # Decision bounds
    assert isinstance(result.decision.next_mode, Mode)
    assert isinstance(result.decision.strategy, Strategy)
    assert 1 <= result.decision.difficulty <= 5
    assert 0.0 <= result.decision.confidence <= 1.0
    assert isinstance(result.decision.reason, str) and len(result.decision.reason) > 0

    # Response bounds
    assert isinstance(result.response.content, str) and len(result.response.content) > 0
    assert isinstance(result.response.mode, Mode)
    assert isinstance(result.response.strategy, Strategy)
    assert 1 <= result.response.difficulty <= 5
    assert 0.0 <= result.response.confidence <= 1.0
    assert isinstance(result.response.requires_single_question, bool)


# =====================================================================
# 9. Engine Isolation Test
# =====================================================================

def test_curio_engine_isolation_from_database_and_fastapi():
    """
    Test 9: Engine isolation.
    Ensures CurioEngine does not require:
    - SQLAlchemy session
    - database connection
    - FastAPI request
    - repository
    - database model
    Verifies that calling CurioEngine requires ONLY AIContext and no external infrastructure.
    """
    # 1. Structural import checks: AI layer must not import persistence or API frameworks
    import backend.app.ai.schemas
    import backend.app.ai.engine
    import backend.app.ai.graph
    import backend.app.ai.nodes.placeholder
    import backend.app.ai.providers.base

    ai_modules = [
        backend.app.ai.schemas,
        backend.app.ai.engine,
        backend.app.ai.graph,
        backend.app.ai.nodes.placeholder,
        backend.app.ai.providers.base,
    ]

    forbidden_packages = [
        "sqlalchemy",
        "fastapi",
        "psycopg2",
        "alembic",
        "backend.app.models",
        "backend.app.repositories",
        "backend.app.db",
    ]

    for mod in ai_modules:
        mod_file = getattr(mod, "__file__", "")
        with open(mod_file, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for pkg in forbidden_packages:
                assert f"import {pkg}" not in content, f"Forbidden import '{pkg}' found in {mod_file}"
                assert f"from {pkg}" not in content, f"Forbidden from import '{pkg}' found in {mod_file}"

    # 2. Runtime invocation check: process executes without any DB or FastAPI objects
    engine = CurioEngine()
    context = _build_base_context()
    result = engine.process(context)
    assert isinstance(result, AIResult)


# =====================================================================
# 10. Provider Mocking Test
# =====================================================================

def test_curio_engine_with_mock_provider_injection():
    """
    Test 10: Provider mocking.
    Verifies provider injection into CurioEngine using MockLLMProvider.
    Ensures tests make NO live LLM or external network calls.
    """
    mock_provider = MockLLMProvider()
    engine = CurioEngine(provider=mock_provider)

    assert engine.provider is mock_provider

    context = _build_base_context()
    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.response is not None
    assert len(result.response.content) > 0


# =====================================================================
# Existing Baseline Tests Preserved
# =====================================================================

def test_engine_process_sample_context():
    """Verify standard Phase 0 deterministic output mapping."""
    engine = CurioEngine()
    context = _build_base_context()

    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.evaluation.correctness == 0.85
    assert result.evaluation.clarity == 0.78
    assert result.evaluation.completeness == 0.72
    assert result.evaluation.depth == 0.65
    assert result.evaluation.relevance == 0.95
    assert result.evaluation.stuck_probability == 0.15
    assert "Stack memory during recursion" in result.evaluation.missing_concepts
    assert "Purpose of a base case" in result.evaluation.mastered_concepts

    assert result.decision.next_mode == Mode.STUDENT
    assert result.decision.strategy == Strategy.PROBE_WHY
    assert result.decision.difficulty == 4
    assert result.decision.confidence == 0.68
    assert result.decision.active_concept == "base_case"
    assert result.decision.should_offer_termination is False
    assert result.decision.should_restore_interrupted_question is False

    assert result.response.content == "What would happen if the recursive function did not contain a base case?"
    assert result.response.mode == Mode.STUDENT
    assert result.response.strategy == Strategy.PROBE_WHY
    assert result.response.difficulty == 4
    assert result.response.confidence == 0.68
    assert result.response.requires_single_question is True


def test_curio_graph_construction():
    """Verify that build_curio_graph constructs and compiles without node/state-key collisions."""
    graph = build_curio_graph()
    assert graph is not None


def test_langgraph_skeleton_direct_execution():
    """Verify the internal compiled LangGraph executes directly and returns graph state."""
    graph = build_curio_graph()

    context = AIContext(
        session_id="sess_graph_test",
        topic="Dynamic Programming",
        current_mode=Mode.STUDENT,
        difficulty=2,
        active_concept="memoization",
        history=[
            ChatMessage(role=Role.USER, content="It stores computed results to avoid repeated calculations."),
        ],
    )

    state = graph.invoke({"context": context})

    assert "evaluation" in state
    assert "decision" in state
    assert "response" in state
    assert "state_updates" in state
    assert state["decision"].strategy == Strategy.PROBE_WHY


def test_legacy_flat_context_initialization():
    """Verify backward compatibility when creating AIContext with legacy flat parameters."""
    context = AIContext(
        session_id="legacy_sess_99",
        topic="Sorting Algorithms",
        current_mode=Mode.STUDENT,
        difficulty=2,
        active_concept="quicksort_partition",
        history=[
            ChatMessage(sender="AI", content="How does partitioning work?"),
            ChatMessage(sender="USER", content="We pick a pivot and put smaller elements to the left."),
        ],
    )

    assert context.session_id == "legacy_sess_99"
    assert context.topic == "Sorting Algorithms"
    assert context.current_mode == Mode.STUDENT
    assert context.difficulty == 2
    assert context.active_concept == "quicksort_partition"
    assert len(context.history) == 2
    assert context.history[0].role == Role.ASSISTANT
    assert context.history[0].sender == "AI"
    assert context.history[1].role == Role.USER
    assert context.history[1].sender == "USER"

    engine = CurioEngine()
    result = engine.process(context)
    assert isinstance(result, AIResult)
    assert result.response.content != ""
