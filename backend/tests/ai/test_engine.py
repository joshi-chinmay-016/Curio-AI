import sys
import pytest

from backend.app.ai import (
    CurioEngine,
    AIContext,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    Difficulty,
    InputType,
    LearningContext,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    SourceMode,
    Strategy,
)
from backend.app.ai.graph import build_curio_graph


def test_engine_process_sample_context():
    """Test that CurioEngine can process an AIContext and return a valid AIResult."""
    engine = CurioEngine()

    context = AIContext(
        session=SessionInfo(
            session_id="sess_test_01",
            topic="Recursion",
            source_mode=SourceMode.GENERAL,
        ),
        current_state=SessionState(
            session_id="sess_test_01",
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
        conversation=ConversationContext(
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
        ),
        learning_context=LearningContext(
            mastered_concepts=["Recursion definition"],
        ),
    )

    result = engine.process(context)

    assert isinstance(result, AIResult)
    assert result.evaluation is not None
    assert result.decision is not None
    assert result.response is not None
    assert result.state_updates is not None

    # Check Part 15 deterministic flow outputs
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


def test_ai_layer_isolation_no_db_or_fastapi():
    """CRITICAL RULE: The AI engine must not import SQLAlchemy or FastAPI."""
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

    forbidden = ["sqlalchemy", "fastapi", "psycopg2", "alembic"]

    for mod in ai_modules:
        mod_file = getattr(mod, "__file__", "")
        with open(mod_file, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for pkg in forbidden:
                assert f"import {pkg}" not in content, f"Forbidden import '{pkg}' found in {mod_file}"
                assert f"from {pkg}" not in content, f"Forbidden from import '{pkg}' found in {mod_file}"


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
