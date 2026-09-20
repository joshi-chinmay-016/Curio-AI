"""
LangGraph nodes for Student Mode execution in Curio AI (Phase 1E).
Orchestrates:
- evaluation_node: TurnEvaluation execution or initial turn default
- decision_node: Deterministic DecisionEngine execution
- response_node: Single-question generation via StudentModeHandler
- state_updates_node: Computation of StateUpdates for backend persistence
"""
import uuid
from typing import Any, Dict
from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.evaluator import AIEvaluator
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    CurrentQuestion,
    LearningDecision,
    Mode,
    Role,
    StateUpdates,
    Strategy,
    TurnEvaluation,
)
from backend.app.ai.student import StudentModeHandler


def evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the learner's response or produces an initial evaluation for new sessions.
    """
    context: AIContext = state["context"]
    provider = state.get("provider") or MockLLMProvider()

    # Check if there are any user messages in recent conversation
    has_user_message = any(
        msg.role == Role.USER or getattr(msg, "sender", "").upper() == "USER"
        for msg in context.conversation.recent_messages
    )

    if not has_user_message:
        # Initial turn: no answer to evaluate yet
        evaluation = TurnEvaluation(
            correctness=0.0,
            clarity=0.0,
            completeness=0.0,
            depth=0.0,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=[],
            missing_concepts=[],
            undefined_terms=[],
            mastered_concepts=[],
            knowledge_gap=None,
            recommended_strategy=Strategy.ASK_FOUNDATION,
            recommended_difficulty=1,
        )
    else:
        evaluator = AIEvaluator(provider)
        evaluation = evaluator.evaluate_turn(context)

    return {"evaluation": evaluation}


def decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the deterministic pedagogical decision engine.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]

    # If this is an initial session turn
    if evaluation.recommended_strategy == Strategy.ASK_FOUNDATION:
        decision = LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.ASK_FOUNDATION,
            difficulty=1,
            confidence=context.current_state.understanding_confidence,
            reason="Initial turn. Asking foundational question on topic.",
            active_concept=context.active_concept or context.topic,
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        )
    else:
        engine = DecisionEngine()
        decision = engine.decide(context, evaluation)

    return {"decision": decision}


def response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates the single Socratic question response via StudentModeHandler.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]
    decision: LearningDecision = state["decision"]
    provider = state.get("provider") or MockLLMProvider()

    student_handler = StudentModeHandler(provider)

    if decision.strategy == Strategy.ASK_FOUNDATION:
        content = student_handler.generate_initial_question(context)
    else:
        content = student_handler.generate_followup_question(context, evaluation, decision)

    response = AIResponse(
        content=content,
        mode=Mode.STUDENT,
        strategy=decision.strategy,
        difficulty=decision.difficulty,
        confidence=decision.confidence,
        requires_single_question=True,
        metadata={
            "phase": "1",
            "active_concept": decision.active_concept,
        },
    )

    return {"response": response}


def state_updates_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the recommended StateUpdates for the backend persistence layer.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]
    decision: LearningDecision = state["decision"]
    response: AIResponse = state["response"]

    # Calculate streaks
    prev_successes = context.current_state.consecutive_successes
    prev_failures = context.current_state.consecutive_failures
    if evaluation.recommended_strategy == Strategy.ASK_FOUNDATION:
        new_successes = prev_successes
        new_failures = prev_failures
    elif evaluation.correctness >= 0.7:
        new_successes = prev_successes + 1
        new_failures = 0
    else:
        new_failures = prev_failures + 1
        new_successes = 0

    # Question representation
    qid = f"q_{uuid.uuid4().hex[:8]}"
    current_q = CurrentQuestion(
        id=qid,
        content=response.content,
        concept=decision.active_concept,
        difficulty=decision.difficulty,
    )

    # Strategy history
    history = list(context.current_state.recent_strategy_history or [])
    history.append(decision.strategy)

    state_updates = StateUpdates(
        active_concept=decision.active_concept,
        current_mode=Mode.STUDENT,
        difficulty=decision.difficulty,
        confidence=decision.confidence,
        mastered_concepts=evaluation.mastered_concepts if evaluation.mastered_concepts else None,
        unresolved_misconceptions=evaluation.misconceptions if evaluation.misconceptions else None,
        current_question=current_q,
        consecutive_successes=new_successes,
        consecutive_failures=new_failures,
        recent_strategy_history=history[-10:],
    )

    return {"state_updates": state_updates}
