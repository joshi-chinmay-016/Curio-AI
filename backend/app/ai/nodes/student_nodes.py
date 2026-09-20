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
    TeacherIntervention,
    TurnEvaluation,
)
from backend.app.ai.session_evaluator import SessionEvaluator
from backend.app.ai.session_evidence import SessionEvidenceBuilder
from backend.app.ai.student import StudentModeHandler
from backend.app.ai.teacher import TeacherModeHandler


def evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the learner's response, produces an initial evaluation for new sessions,
    or runs session-level evaluation when in EVALUATOR mode.
    """
    context: AIContext = state["context"]
    provider = state.get("provider") or MockLLMProvider()

    # Evaluator Mode branch
    if context.current_mode == Mode.EVALUATOR:
        builder = SessionEvidenceBuilder()
        evidence = builder.build_from_history(
            session_id=context.session_id,
            topic=context.topic,
            messages=context.conversation.recent_messages,
            evaluations=context.learning_context.recent_evaluations,
            active_concept=context.active_concept,
        )
        session_evaluator = SessionEvaluator(provider)
        session_eval = session_evaluator.evaluate_session(evidence)
        report = session_evaluator.generate_report(evidence)

        # Synthetic turn evaluation for contract compatibility
        turn_eval = TurnEvaluation(
            correctness=session_eval.understanding_score / 100.0,
            clarity=1.0,
            completeness=1.0,
            depth=1.0,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=session_eval.unresolved_misconceptions,
            missing_concepts=session_eval.unresolved_gaps,
            undefined_terms=[],
            mastered_concepts=session_eval.strengths,
            knowledge_gap=session_eval.unresolved_gaps[0] if session_eval.unresolved_gaps else None,
            recommended_strategy=Strategy.GENERATE_REPORT,
            recommended_difficulty=context.difficulty,
        )
        return {
            "evaluation": turn_eval,
            "session_evaluation": session_eval,
            "learning_report": report,
            "evidence": evidence,
        }

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

    # Evaluator Mode branch
    if context.current_mode == Mode.EVALUATOR:
        s_eval = state.get("session_evaluation")
        decision = LearningDecision(
            next_mode=Mode.EVALUATOR,
            strategy=Strategy.GENERATE_REPORT,
            difficulty=context.difficulty,
            confidence=s_eval.evidence_confidence if s_eval else context.current_state.understanding_confidence,
            reason="Session evaluation requested. Learning report generated.",
            active_concept=context.active_concept or context.topic,
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        )
        return {"decision": decision}

    # If this is an initial session turn
    has_user_message = any(
        msg.role == Role.USER or getattr(msg, "sender", "").upper() == "USER"
        for msg in context.conversation.recent_messages
    )
    if evaluation.recommended_strategy == Strategy.ASK_FOUNDATION and not has_user_message:
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
    Generates response:
    - Report completion response if next_mode == EVALUATOR.
    - Teacher response (explanation + 1 verification question) if next_mode == TEACHER.
    - Restored question if should_restore_interrupted_question is True.
    - Socratic question via StudentModeHandler otherwise.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]
    decision: LearningDecision = state["decision"]
    provider = state.get("provider") or MockLLMProvider()

    if decision.next_mode == Mode.EVALUATOR:
        response = AIResponse(
            content="Session evaluation complete. Your learning report has been generated.",
            mode=Mode.EVALUATOR,
            strategy=Strategy.GENERATE_REPORT,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            requires_single_question=False,
            metadata={"session_id": context.session_id},
        )
    elif decision.next_mode == Mode.TEACHER:
        # Teacher Mode response generation
        teacher_handler = TeacherModeHandler(provider)
        gap = decision.active_concept or evaluation.knowledge_gap or context.active_concept or "understanding gap"
        curr_attempts = context.current_state.teacher_attempt_count or 0
        if context.current_state.teacher_intervention and context.current_state.teacher_intervention.attempt_count:
            curr_attempts = max(curr_attempts, context.current_state.teacher_intervention.attempt_count)
        attempt_count = curr_attempts + 1

        interrupted_q = context.interrupted_question or context.current_question
        content = teacher_handler.generate_teacher_response(
            context=context,
            gap=gap,
            attempt_count=attempt_count,
            interrupted_question=interrupted_q,
            evaluation=evaluation,
        )

        response = AIResponse(
            content=content,
            mode=Mode.TEACHER,
            strategy=decision.strategy,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            requires_single_question=True,
            metadata={
                "active_concept": gap,
                "attempt_count": attempt_count,
                "intervention_gap": gap,
            },
        )
    elif decision.should_restore_interrupted_question:
        # Returning from Teacher Mode to Student Mode: restore interrupted question
        restored_q = context.interrupted_question
        if restored_q:
            content = f"Great job! Now let's return to our original question:\n\n{restored_q.content}"
        else:
            student_handler = StudentModeHandler(provider)
            content = student_handler.generate_followup_question(context, evaluation, decision)

        response = AIResponse(
            content=content,
            mode=Mode.STUDENT,
            strategy=decision.strategy,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            requires_single_question=True,
            metadata={
                "active_concept": decision.active_concept,
                "restored_question_id": restored_q.id if restored_q else None,
            },
        )
    else:
        # Normal Student Mode question generation
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
                "active_concept": decision.active_concept,
            },
        )

    return {"response": response}


def state_updates_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the recommended StateUpdates for the backend persistence layer.
    Handles:
    - Evaluator Mode read-only state updates.
    - Snapshotting current_question into interrupted_question when entering Teacher Mode.
    - Preserving interrupted_question during multi-turn Teacher Mode.
    - Restoring interrupted_question and clearing intervention state when returning to Student Mode.
    - Normal Student Mode updates.
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

    # Strategy history
    history = list(context.current_state.recent_strategy_history or [])
    history.append(decision.strategy)

    qid = f"q_{uuid.uuid4().hex[:8]}"

    if decision.next_mode == Mode.EVALUATOR:
        # Evaluator mode is READ-ONLY with respect to active learning state
        state_updates = StateUpdates(
            active_concept=context.active_concept,
            current_mode=Mode.EVALUATOR,
            difficulty=context.difficulty,
            confidence=decision.confidence,
            current_question=context.current_question,
            interrupted_question=context.interrupted_question,
            teacher_intervention=context.current_state.teacher_intervention,
            teacher_attempt_count=context.current_state.teacher_attempt_count,
            consecutive_successes=context.current_state.consecutive_successes,
            consecutive_failures=context.current_state.consecutive_failures,
            recent_strategy_history=history[-10:],
            mastered_concepts=None,
            unresolved_misconceptions=None,
        )

    elif decision.next_mode == Mode.TEACHER:
        # Entering or continuing Teacher Mode
        is_entering = context.current_mode != Mode.TEACHER and (not hasattr(context.current_mode, "value") or context.current_mode.value != "TEACHER")
        if is_entering:
            # Snapshot current Student question
            interrupted_q = context.current_question
            attempt_count = 1
        else:
            # Preserve existing snapshot
            interrupted_q = context.interrupted_question
            curr_attempts = context.current_state.teacher_attempt_count or 0
            if context.current_state.teacher_intervention and context.current_state.teacher_intervention.attempt_count:
                curr_attempts = max(curr_attempts, context.current_state.teacher_intervention.attempt_count)
            attempt_count = curr_attempts + 1

        current_q = CurrentQuestion(
            id=qid,
            content=response.content,
            concept=decision.active_concept,
            difficulty=decision.difficulty,
        )
        intervention = TeacherIntervention(
            active=True,
            gap=decision.active_concept,
            attempt_count=attempt_count,
            verification_required=True,
        )

        state_updates = StateUpdates(
            active_concept=decision.active_concept,
            current_mode=Mode.TEACHER,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            current_question=current_q,
            interrupted_question=interrupted_q,
            teacher_intervention=intervention,
            teacher_attempt_count=attempt_count,
            consecutive_successes=0,
            consecutive_failures=prev_failures + 1,
            recent_strategy_history=history[-10:],
            mastered_concepts=evaluation.mastered_concepts if evaluation.mastered_concepts else None,
            unresolved_misconceptions=evaluation.misconceptions if evaluation.misconceptions else None,
        )

    elif decision.should_restore_interrupted_question:
        # Exiting Teacher Mode: restore interrupted question and clear intervention state
        restored_q = context.interrupted_question
        current_q = restored_q or CurrentQuestion(
            id=qid,
            content=response.content,
            concept=decision.active_concept,
            difficulty=decision.difficulty,
        )
        cleared_intervention = TeacherIntervention(
            active=False,
            gap="",
            attempt_count=0,
            verification_required=False,
        )

        state_updates = StateUpdates(
            active_concept=current_q.concept if current_q else decision.active_concept,
            current_mode=Mode.STUDENT,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            current_question=current_q,
            interrupted_question=None,
            teacher_intervention=cleared_intervention,
            teacher_attempt_count=0,
            consecutive_successes=new_successes,
            consecutive_failures=new_failures,
            recent_strategy_history=history[-10:],
            mastered_concepts=evaluation.mastered_concepts if evaluation.mastered_concepts else None,
            unresolved_misconceptions=evaluation.misconceptions if evaluation.misconceptions else None,
        )

    else:
        # Normal Student Mode
        current_q = CurrentQuestion(
            id=qid,
            content=response.content,
            concept=decision.active_concept,
            difficulty=decision.difficulty,
        )

        state_updates = StateUpdates(
            active_concept=decision.active_concept,
            current_mode=Mode.STUDENT,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            current_question=current_q,
            interrupted_question=None,
            teacher_intervention=None,
            teacher_attempt_count=0,
            consecutive_successes=new_successes,
            consecutive_failures=new_failures,
            recent_strategy_history=history[-10:],
            mastered_concepts=evaluation.mastered_concepts if evaluation.mastered_concepts else None,
            unresolved_misconceptions=evaluation.misconceptions if evaluation.misconceptions else None,
        )

    return {"state_updates": state_updates}
