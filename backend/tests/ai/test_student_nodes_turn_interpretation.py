"""
Unit tests verifying single-invocation and downstream consumption of TurnInterpreter
within evaluation_node (Phase 2B Step 2).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.app.ai.nodes.student_nodes import evaluation_node
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    LearningContext,
    Mode,
    Role,
    SessionInfo,
    SessionState as AISessionState,
    TurnIntent,
    TurnInterpretation,
)
from backend.app.ai.turn_interpreter import TurnInterpreter


def _build_student_context(user_message: str = "A binary search divides the sorted array in half repeatedly.") -> AIContext:
    session_info = SessionInfo(session_id="test-session-123", topic="Binary Search")
    state = AISessionState(
        session_id="test-session-123",
        current_mode=Mode.STUDENT,
        current_difficulty=1,
        active_concept="binary_search_definition",
        current_question=CurrentQuestion(
            id="q1",
            content="Can you explain how binary search works?",
            concept="binary_search_definition",
            difficulty=1,
        ),
    )
    history = [
        ChatMessage(role=Role.ASSISTANT, content="Can you explain how binary search works?"),
        ChatMessage(role=Role.USER, content=user_message),
    ]
    conversation = ConversationContext(recent_messages=history, message_count=len(history))
    learning_context = LearningContext()
    return AIContext(
        session=session_info,
        current_state=state,
        conversation=conversation,
        learning_context=learning_context,
    )


def test_evaluation_node_invokes_turn_interpreter_exactly_once():
    """Verify TurnInterpreter.interpret() is called exactly once during an evaluation turn."""
    context = _build_student_context("A binary search divides the search space in half each step.")
    provider = MockLLMProvider()
    graph_state = {"context": context, "provider": provider}

    with patch.object(TurnInterpreter, "interpret", autospec=True) as mock_interpret:
        # Return a valid interpretation
        mock_interpret.return_value = TurnInterpretation(
            intent=TurnIntent.ANSWER_ATTEMPT,
            is_answer_attempt=True,
            is_question=False,
            is_help_request=False,
            confidence=0.9,
        )

        res = evaluation_node(graph_state)

        # Assert exactly one call
        assert mock_interpret.call_count == 1, f"Expected 1 interpret() call, got {mock_interpret.call_count}"

        # Verify arguments passed to interpret()
        call_args = mock_interpret.call_args
        assert call_args.kwargs.get("user_message") == "A binary search divides the search space in half each step."
        assert call_args.kwargs.get("mode") == Mode.STUDENT
        assert call_args.kwargs.get("current_question").id == "q1"


def test_evaluation_node_returns_interpretation_downstream():
    """Verify that the interpretation produced by TurnInterpreter is returned in node output."""
    context = _build_student_context("Could you please explain what you mean by logarithmic time?")
    provider = MockLLMProvider()
    graph_state = {"context": context, "provider": provider}

    res = evaluation_node(graph_state)

    assert "interpretation" in res
    interpretation = res["interpretation"]
    assert isinstance(interpretation, TurnInterpretation)
    assert interpretation.intent in (TurnIntent.CLARIFICATION_REQUEST, TurnIntent.CONCEPTUAL_QUESTION, TurnIntent.UNKNOWN, TurnIntent.HELP_REQUEST, TurnIntent.ANSWER_ATTEMPT)
    # Downstream evaluation must be present
    assert "evaluation" in res
    assert res["evaluation"] is not None


def test_evaluation_node_preserves_defensive_fallback_on_faulty_provider():
    """Verify that provider failures during turn interpretation return defensive fallback without raising."""
    context = _build_student_context("I don't understand.")
    
    faulty_provider = MagicMock(spec=MockLLMProvider)
    faulty_provider.generate_structured.side_effect = RuntimeError("Provider timeout or failure")

    graph_state = {"context": context, "provider": faulty_provider}

    # Should not raise exception
    res = evaluation_node(graph_state)

    assert "interpretation" in res
    interpretation = res["interpretation"]
    assert isinstance(interpretation, TurnInterpretation)
    # TurnInterpreter defensive heuristic classifies "I don't understand." as HELP_REQUEST
    assert interpretation.intent in (TurnIntent.HELP_REQUEST, TurnIntent.CLARIFICATION_REQUEST, TurnIntent.UNKNOWN)


def test_evaluation_node_skips_turn_interpretation_on_initial_turn():
    """Verify that when there are no user messages (initial session turn), TurnInterpreter is not called."""
    session_info = SessionInfo(session_id="test-session-init", topic="Binary Search")
    state = AISessionState(session_id="test-session-init", current_mode=Mode.STUDENT)
    # No user messages
    conversation = ConversationContext(recent_messages=[], message_count=0)
    context = AIContext(
        session=session_info,
        current_state=state,
        conversation=conversation,
        learning_context=LearningContext(),
    )
    provider = MockLLMProvider()
    graph_state = {"context": context, "provider": provider}

    with patch.object(TurnInterpreter, "interpret", autospec=True) as mock_interpret:
        res = evaluation_node(graph_state)
        assert mock_interpret.call_count == 0
        assert res["interpretation"].intent == TurnIntent.UNKNOWN
