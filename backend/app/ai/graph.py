"""
Internal LangGraph state machine workflow for Curio AI (Phase 1).
This module is strictly an internal implementation detail and must never be exposed
to the backend service layer.
"""
from typing import Any, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    LearningDecision,
    StateUpdates,
    TurnEvaluation,
)
from backend.app.ai.nodes.student_nodes import (
    evaluation_node,
    decision_node,
    response_node,
    state_updates_node,
)


class CurioGraphState(TypedDict, total=False):
    """Internal LangGraph state schema for Curio AI execution."""
    context: AIContext
    provider: Optional[BaseAIProvider]
    evidence: Optional[Any]
    evaluation: Optional[TurnEvaluation]
    session_evaluation: Optional[Any]
    learning_report: Optional[Any]
    decision: Optional[LearningDecision]
    response: Optional[AIResponse]
    state_updates: Optional[StateUpdates]
    result: Optional[AIResult]


def build_curio_graph(provider: Optional[BaseAIProvider] = None):
    """
    Constructs and compiles the LangGraph workflow for Curio AI Student Mode:
    START -> run_evaluation -> run_decision -> run_response -> run_state_updates -> END
    """
    workflow = StateGraph(CurioGraphState)

    workflow.add_node("run_evaluation", evaluation_node)
    workflow.add_node("run_decision", decision_node)
    workflow.add_node("run_response", response_node)
    workflow.add_node("run_state_updates", state_updates_node)

    workflow.add_edge(START, "run_evaluation")
    workflow.add_edge("run_evaluation", "run_decision")
    workflow.add_edge("run_decision", "run_response")
    workflow.add_edge("run_response", "run_state_updates")
    workflow.add_edge("run_state_updates", END)

    return workflow.compile()
