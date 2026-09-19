"""
Placeholder nodes for the Curio LangGraph workflow (Phase 0).
These nodes implement deterministic placeholder behavior to validate graph compilation,
boundary isolation, and schema serialization without requiring live LLM calls.
"""
from typing import Any, Dict
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    CurrentQuestion,
    LearningDecision,
    Mode,
    StateUpdates,
    Strategy,
    TurnEvaluation,
)


def placeholder_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder evaluation node.
    Demonstrates contract compliance for TurnEvaluation.
    In Phase 1, this will be replaced with real LLM evaluation logic.
    """
    context: AIContext = state["context"]

    # Provide deterministic evaluation matching the Phase 0 specification
    evaluation = TurnEvaluation(
        correctness=0.85,
        clarity=0.78,
        completeness=0.72,
        depth=0.65,
        relevance=0.95,
        stuck_probability=0.15,
        misconceptions=[],
        missing_concepts=["Stack memory during recursion"],
        undefined_terms=[],
        mastered_concepts=["Purpose of a base case"],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=min(5, max(1, context.difficulty + 1)),
    )
    return {"evaluation": evaluation}


def placeholder_decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder decision node.
    Calculates next mode, strategy, and difficulty from evaluation and context.
    In Phase 1, this will execute the full pedagogical decision engine.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]

    active_concept = context.active_concept or "base_case"
    next_difficulty = evaluation.recommended_difficulty

    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=evaluation.recommended_strategy,
        difficulty=next_difficulty,
        confidence=0.68,
        reason="The learner understands the definition but has not explained the underlying mechanism.",
        active_concept=active_concept,
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )

    state_updates = StateUpdates(
        active_concept=active_concept,
        current_mode=Mode.STUDENT,
        difficulty=next_difficulty,
        confidence=0.68,
        mastered_concepts=evaluation.mastered_concepts,
        unresolved_misconceptions=evaluation.misconceptions,
        current_question=CurrentQuestion(
            id="q_gen_placeholder",
            content="What would happen if the recursive function did not contain a base case?",
            concept=active_concept,
            difficulty=next_difficulty,
        ),
    )

    return {"decision": decision, "state_updates": state_updates}


def placeholder_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder response generation node.
    Produces the learner-facing message based on the decision.
    In Phase 1, this will invoke Student / Teacher / Evaluator prompt handlers.
    """
    decision: LearningDecision = state["decision"]

    content = "What would happen if the recursive function did not contain a base case?"

    response = AIResponse(
        content=content,
        mode=decision.next_mode,
        strategy=decision.strategy,
        difficulty=decision.difficulty,
        confidence=decision.confidence,
        requires_single_question=True,
        metadata={
            "placeholder": True,
            "phase": "0",
        },
    )

    return {"response": response}
