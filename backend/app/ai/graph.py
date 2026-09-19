"""
Internal LangGraph state machine workflow for Curio AI.
This module is strictly an internal implementation detail and must never be exposed
to the backend service layer.
"""
from typing import Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    LearningDecision,
    StateUpdates,
    TurnEvaluation,
)
from backend.app.ai.nodes.placeholder import (
    placeholder_evaluation_node,
    placeholder_decision_node,
    placeholder_response_node,
)


class CurioGraphState(TypedDict, total=False):
    """Internal LangGraph state schema for Curio AI execution."""
    context: AIContext
    evaluation: Optional[TurnEvaluation]
    decision: Optional[LearningDecision]
    response: Optional[AIResponse]
    state_updates: Optional[StateUpdates]
    result: Optional[AIResult]


def build_curio_graph():
    """
    Constructs and compiles the minimal LangGraph workflow for Curio AI:
    START -> evaluation -> decision -> response -> END
    """
    workflow = StateGraph(CurioGraphState)

    workflow.add_node("evaluation", placeholder_evaluation_node)
    workflow.add_node("decision", placeholder_decision_node)
    workflow.add_node("response", placeholder_response_node)

    workflow.add_edge(START, "evaluation")
    workflow.add_edge("evaluation", "decision")
    workflow.add_edge("decision", "response")
    workflow.add_edge("response", END)

    return workflow.compile()
