"""
LangGraph nodes for Adaptive Learning Core v1 in Curio AI.
Orchestrates:
- evaluation_node: ConceptModel, LearnerModel hydration, TurnInterpretation, TurnEvaluation
- decision_node: Pedagogical DecisionEngine, QuestionSpecification selection via QuestionSelector
- response_node: Single-question candidate generation, validation, novelty check via QuestionGenerator
- state_updates_node: Computation of StateUpdates with synchronized concept mastery and learner state
"""
import uuid
from typing import Any, Dict, List, Optional

from backend.app.ai.concept_model import ConceptModelBuilder
from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.evaluator import AIEvaluator
from backend.app.ai.learner_model import LearnerModelManager
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.question_generator import QuestionGenerator
from backend.app.ai.question_selector import QuestionSelector
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    ConceptModel,
    CurrentQuestion,
    LearnerModel,
    LearningDecision,
    Mode,
    ObjectiveType,
    QuestionCandidate,
    QuestionSelectionResult,
    QuestionSpecification,
    Role,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)
from backend.app.ai.session_evaluator import SessionEvaluator
from backend.app.ai.session_evidence import SessionEvidenceBuilder
from backend.app.ai.student import StudentModeHandler
from backend.app.ai.teacher import TeacherModeHandler
from backend.app.ai.turn_interpreter import TurnInterpreter


def evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hydrates ConceptModel and LearnerModel, performs TurnInterpretation and TurnEvaluation,
    and updates learner understanding deterministically from evidence.
    """
    context: AIContext = state["context"]
    provider = state.get("provider") or MockLLMProvider()

    # 1. Hydrate or dynamically build ConceptModel
    concept_model: Optional[ConceptModel] = context.current_state.concept_model
    if not concept_model:
        builder = ConceptModelBuilder(provider)
        concept_model = builder.build_model(context.topic)

    # 2. Hydrate or initialize LearnerModel
    learner_model: Optional[LearnerModel] = context.current_state.learner_model
    if not learner_model:
        learner_model = LearnerModel(session_id=context.session_id)
        if context.current_state.concept_mastery:
            for cid, score in context.current_state.concept_mastery.items():
                cs = learner_model.get_or_create_concept(cid)
                cs.mastery = score
        if context.current_state.unresolved_misconceptions:
            learner_model.unresolved_gaps = list(context.current_state.unresolved_misconceptions)
    learner_mgr = LearnerModelManager(learner_model, session_id=context.session_id)

    # 3. Evaluator Mode branch
    if context.current_mode == Mode.EVALUATOR:
        s_builder = SessionEvidenceBuilder()
        evidence = s_builder.build_from_history(
            session_id=context.session_id,
            topic=context.topic,
            messages=context.conversation.recent_messages,
            evaluations=context.learning_context.recent_evaluations,
            active_concept=context.active_concept,
        )
        session_evaluator = SessionEvaluator(provider)
        session_eval = session_evaluator.evaluate_session(evidence)
        report = session_evaluator.generate_report(evidence)

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
            "concept_model": concept_model,
            "learner_model": learner_mgr.model,
            "interpretation": TurnInterpretation(intent=TurnIntent.UNKNOWN),
        }

    # 4. Check if there are user messages in conversation
    user_msgs = [
        msg for msg in context.conversation.recent_messages
        if msg.role == Role.USER or getattr(msg, "sender", "").upper() == "USER"
    ]

    if not user_msgs:
        # Initial turn: no answer to evaluate yet
        interpretation = TurnInterpretation(
            intent=TurnIntent.UNKNOWN,
            is_answer_attempt=False,
            confidence=1.0,
        )
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
        latest_user_msg = user_msgs[-1].content
        curr_q = context.current_question

        # Semantic Turn Interpretation
        interpreter = TurnInterpreter(provider)
        interpretation = interpreter.interpret(
            user_message=latest_user_msg,
            context=context,
            current_question=curr_q,
            mode=context.current_mode,
        )

        target_concept = context.active_concept or (concept_model.concepts[0].id if concept_model.concepts else "core_concept")

        if interpretation.intent == TurnIntent.CLARIFICATION_REQUEST:
            # Learner asking for question/term clarification: NOT an answer attempt
            evaluation = TurnEvaluation(
                correctness=0.5,
                clarity=1.0,
                completeness=0.5,
                depth=0.5,
                relevance=1.0,
                stuck_probability=0.0,
                misconceptions=[],
                missing_concepts=[],
                undefined_terms=[],
                mastered_concepts=[],
                knowledge_gap=None,
                recommended_strategy=Strategy.CLARIFY_TERM,
                recommended_difficulty=context.difficulty,
            )
        elif interpretation.intent in (TurnIntent.ACKNOWLEDGEMENT, TurnIntent.READY_FOR_VERIFICATION):
            # Pure acknowledgement: NO fake mastery, record acknowledgement without increasing mastery
            evaluation = TurnEvaluation(
                correctness=0.0,
                clarity=1.0,
                completeness=0.0,
                depth=0.0,
                relevance=1.0,
                stuck_probability=0.0,
                misconceptions=[],
                missing_concepts=[],
                undefined_terms=[],
                mastered_concepts=[],
                knowledge_gap=None,
                recommended_strategy=Strategy.VERIFY_UNDERSTANDING if context.current_mode == Mode.TEACHER else Strategy.PROBE_WHY,
                recommended_difficulty=context.difficulty,
            )
            learner_mgr.record_acknowledgement(target_concept)
        elif interpretation.intent == TurnIntent.HELP_REQUEST:
            # Explicit struggle: trigger Teacher mode
            evaluation = TurnEvaluation(
                correctness=0.0,
                clarity=0.5,
                completeness=0.0,
                depth=0.0,
                relevance=1.0,
                stuck_probability=0.95,
                misconceptions=[],
                missing_concepts=[],
                undefined_terms=[],
                mastered_concepts=[],
                knowledge_gap=context.active_concept or context.topic,
                recommended_strategy=Strategy.TEACH_GAP,
                recommended_difficulty=max(1, context.difficulty - 1),
            )
            learner_mgr.update_from_evaluation(target_concept, evaluation, interpretation=interpretation)
        else:
            # Substantive turn: evaluate semantics
            evaluator = AIEvaluator(provider)
            evaluation = evaluator.evaluate_turn(context)
            learner_mgr.update_from_evaluation(target_concept, evaluation, interpretation=interpretation)

    return {
        "evaluation": evaluation,
        "interpretation": interpretation,
        "concept_model": concept_model,
        "learner_model": learner_mgr.model,
    }


def decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes pedagogical decision logic:
    - In Teacher mode: manages verification and gap resolution.
    - In Student mode: uses QuestionSelector to determine concept, objective, and difficulty.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]
    interpretation: TurnInterpretation = state.get("interpretation") or TurnInterpretation(intent=TurnIntent.UNKNOWN)
    concept_model: ConceptModel = state.get("concept_model") or ConceptModel(topic=context.topic)
    learner_model: LearnerModel = state.get("learner_model") or LearnerModel(session_id=context.session_id)

    # 1. Evaluator Mode branch
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

    # 2. Check if this is an initial session turn (no user messages)
    has_user_message = any(
        msg.role == Role.USER or getattr(msg, "sender", "").upper() == "USER"
        for msg in context.conversation.recent_messages
    )

    if not has_user_message:
        decision = LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.ASK_FOUNDATION,
            difficulty=1,
            confidence=context.current_state.understanding_confidence,
            reason="Initial session turn: ask foundational question.",
            active_concept=context.active_concept or (concept_model.concepts[0].id if concept_model.concepts else context.topic),
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        )
    else:
        engine = DecisionEngine()
        decision = engine.decide(context, evaluation, interpretation=interpretation)

    # 3. If remaining or entering Student Mode, run QuestionSelector
    spec: Optional[QuestionSpecification] = None
    if decision.next_mode == Mode.STUDENT and not decision.should_restore_interrupted_question:
        selector = QuestionSelector()
        recent_q = [
            m.content for m in context.conversation.recent_messages
            if m.role == Role.ASSISTANT or getattr(m, "sender", "").upper() == "AI"
        ]
        recent_c = [context.active_concept] if context.active_concept else []

        # If probing current concept, preserve active_concept; otherwise let selector advance
        is_probing_active = decision.strategy in (
            Strategy.PROBE_WHY,
            Strategy.PROBE_HOW,
            Strategy.PROBE_MISSING_CONCEPT,
            Strategy.CLARIFY_TERM,
            Strategy.CHALLENGE_MISCONCEPTION,
        ) and bool(context.active_concept or decision.active_concept)
        concept_target = (decision.active_concept or context.active_concept) if is_probing_active else None

        spec = selector.select_question_specification(
            concept_model=concept_model,
            learner_model=learner_model,
            current_difficulty=decision.difficulty,
            current_objective=context.current_state.current_objective,
            latest_interpretation=interpretation,
            latest_evaluation=None,
            recent_question_history=recent_q,
            recent_concept_history=recent_c,
            interrupted_question=context.interrupted_question,
            target_concept_override=concept_target,
        )

        # Synchronize decision with specification
        decision.active_concept = spec.target_concept
        decision.difficulty = spec.difficulty
        if not has_user_message:
            decision.strategy = Strategy.ASK_FOUNDATION

    return {
        "decision": decision,
        "question_specification": spec,
        "learning_objective": spec.learning_objective if spec else None,
    }


def response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates response:
    - Report completion if next_mode == EVALUATOR.
    - Teacher response (exact gap explanation + 1 verification question) if next_mode == TEACHER.
    - Restored question if returning from Teacher Mode.
    - Specification-driven candidate generation & validation if in Student Mode.
    """
    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]
    decision: LearningDecision = state["decision"]
    interpretation: TurnInterpretation = state.get("interpretation") or TurnInterpretation(intent=TurnIntent.UNKNOWN)
    spec: Optional[QuestionSpecification] = state.get("question_specification")
    provider = state.get("provider") or MockLLMProvider()

    recent_q = [
        m.content for m in context.conversation.recent_messages
        if m.role == Role.ASSISTANT or getattr(m, "sender", "").upper() == "AI"
    ]

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
        return {"response": response}

    elif decision.next_mode == Mode.TEACHER:
        # Teacher Mode response generation
        teacher_handler = TeacherModeHandler(provider)
        gap = decision.active_concept or evaluation.knowledge_gap or context.active_concept or "understanding gap"
        curr_attempts = context.current_state.teacher_attempt_count or 0
        if context.current_state.teacher_intervention and context.current_state.teacher_intervention.attempt_count:
            curr_attempts = max(curr_attempts, context.current_state.teacher_intervention.attempt_count)

        is_entering = context.current_mode != Mode.TEACHER and (not hasattr(context.current_mode, "value") or context.current_mode.value != "TEACHER")
        is_clarification = (
            "Learner asked for explanation" in (decision.reason or "")
            or "Learner indicated readiness" in (decision.reason or "")
            or interpretation.intent in (TurnIntent.CLARIFICATION_REQUEST, TurnIntent.READY_FOR_VERIFICATION)
            or (context.history and ("again" in context.history[-1].content.lower() or "?" in context.history[-1].content))
        )
        if is_entering:
            attempt_count = 1
        elif is_clarification:
            attempt_count = max(1, curr_attempts)
        else:
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
                "mode": "TEACHER",
                "latest_intent": interpretation.intent.value,
            },
        )
        return {"response": response}

    elif decision.should_restore_interrupted_question:
        # Exiting Teacher Mode: restore interrupted question
        restored_q = context.interrupted_question
        curr_attempts = context.current_state.teacher_attempt_count or 0
        is_limit_fallback = curr_attempts >= 3 or "Maximum Teacher attempts" in (decision.reason or "")

        if restored_q:
            if is_limit_fallback:
                content = f"Let's pause on that specific detail for now and return to our original question at a simpler level:\n\n{restored_q.content}"
            else:
                content = f"Great job! Now let's return to our original question:\n\n{restored_q.content}"
        else:
            if spec:
                generator = QuestionGenerator(provider)
                sel_res = generator.generate_and_select_question(spec, context, recent_q)
                content = sel_res.selected_candidate.question_text
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
                "mode": "STUDENT",
                "latest_intent": interpretation.intent.value,
            },
        )
        return {"response": response}

    else:
        # Normal Student Mode: Candidate Generation, Validation & Selection
        generator = QuestionGenerator(provider)
        if not spec:
            selector = QuestionSelector()
            concept_model = state.get("concept_model") or ConceptModel(topic=context.topic)
            learner_model = state.get("learner_model") or LearnerModel(session_id=context.session_id)
            spec = selector.select_question_specification(
                concept_model=concept_model,
                learner_model=learner_model,
                current_difficulty=decision.difficulty,
                recent_question_history=recent_q,
            )

        selection_res: QuestionSelectionResult = generator.generate_and_select_question(
            spec=spec,
            context=context,
            recent_questions=recent_q,
        )

        content = selection_res.selected_candidate.question_text

        # If learner asked for clarification, precede with brief clarification
        if interpretation.intent == TurnIntent.CLARIFICATION_REQUEST:
            clean_term = spec.target_concept.replace("_", " ")
            content = f"By that, I'm referring to the core mechanism of {clean_term}.\n\n{content}"

        response = AIResponse(
            content=content,
            mode=Mode.STUDENT,
            strategy=decision.strategy,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            requires_single_question=True,
            metadata={
                "selected_concept": spec.target_concept,
                "objective": spec.learning_objective.objective_type.value,
                "selection_reason": spec.reason,
                "difficulty": spec.difficulty,
                "candidate_count": len(selection_res.candidates),
                "rejected_candidate_reasons": [
                    r for v in selection_res.validations for r in v.rejection_reasons
                ],
                "novelty_result": selection_res.novelty_passed,
                "latest_intent": interpretation.intent.value,
                "learner_evidence": interpretation.answer_evidence,
                "mode": "STUDENT",
                "teacher_intervention_state": None,
            },
        )
        return {
            "response": response,
            "selection_result": selection_res,
        }


def state_updates_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the recommended StateUpdates for the backend persistence layer.
    Synchronizes:
    - concept_model and learner_model
    - current_objective and question_specification
    - concept_mastery and unresolved_misconceptions
    - interrupted_question snapshotting and restoring
    """
    from datetime import datetime, timezone
    from backend.app.ai.schemas import ModeTransition

    context: AIContext = state["context"]
    evaluation: TurnEvaluation = state["evaluation"]
    decision: LearningDecision = state["decision"]
    response: AIResponse = state["response"]
    interpretation: TurnInterpretation = state.get("interpretation") or TurnInterpretation(intent=TurnIntent.UNKNOWN)
    concept_model: Optional[ConceptModel] = state.get("concept_model")
    learner_model: Optional[LearnerModel] = state.get("learner_model")
    spec: Optional[QuestionSpecification] = state.get("question_specification")
    obj = spec.learning_objective if spec else None

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

    # Mode switch history tracking
    history_transitions = list(context.current_state.mode_switch_history or [])
    if context.current_mode != decision.next_mode:
        transition = ModeTransition(
            from_mode=context.current_mode,
            to_mode=decision.next_mode,
            reason=decision.reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
            active_concept=decision.active_concept or context.active_concept,
        )
        history_transitions.append(transition)

    qid = f"q_{uuid.uuid4().hex[:8]}"

    # Synced concept mastery from LearnerModel
    mastery_dict = (
        LearnerModelManager(learner_model).export_mastery_dict()
        if learner_model
        else (context.current_state.concept_mastery or {})
    )

    if decision.next_mode == Mode.EVALUATOR:
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
            mode_switch_history=history_transitions,
            concept_model=concept_model,
            learner_model=learner_model,
            current_objective=obj,
            latest_interpretation=interpretation,
            question_specification=spec,
            concept_mastery=mastery_dict,
        )

    elif decision.next_mode == Mode.TEACHER:
        is_entering = context.current_mode != Mode.TEACHER and (
            not hasattr(context.current_mode, "value") or context.current_mode.value != "TEACHER"
        )
        is_clarification = (
            "Learner asked for explanation" in (decision.reason or "")
            or "Learner indicated readiness" in (decision.reason or "")
            or interpretation.intent in (TurnIntent.CLARIFICATION_REQUEST, TurnIntent.READY_FOR_VERIFICATION)
            or (context.history and ("again" in context.history[-1].content.lower() or "?" in context.history[-1].content))
        )

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
            attempt_count = max(1, curr_attempts) if is_clarification else curr_attempts + 1

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
            mode_switch_history=history_transitions,
            concept_model=concept_model,
            learner_model=learner_model,
            current_objective=obj,
            latest_interpretation=interpretation,
            question_specification=spec,
            concept_mastery=mastery_dict,
        )

    elif decision.should_restore_interrupted_question:
        # Exiting Teacher Mode: restore interrupted question and clear intervention
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

        is_limit_fallback = "Maximum Teacher attempts" in (decision.reason or "")
        if is_limit_fallback:
            mastered = None
            unresolved = list(context.current_state.unresolved_misconceptions or [])
            if decision.active_concept and decision.active_concept not in unresolved:
                unresolved.append(decision.active_concept)
        else:
            mastered = evaluation.mastered_concepts if evaluation.mastered_concepts else ([decision.active_concept] if decision.active_concept else None)
            unresolved = evaluation.misconceptions if evaluation.misconceptions else None
            # Update learner model for resolved gap
            if learner_model:
                lm_mgr = LearnerModelManager(learner_model)
                lm_mgr.record_teacher_verification(decision.active_concept, passed=True)
                mastery_dict = lm_mgr.export_mastery_dict()

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
            mastered_concepts=mastered,
            unresolved_misconceptions=unresolved,
            mode_switch_history=history_transitions,
            concept_model=concept_model,
            learner_model=learner_model,
            current_objective=obj,
            latest_interpretation=interpretation,
            question_specification=spec,
            concept_mastery=mastery_dict,
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
            mode_switch_history=history_transitions,
            concept_model=concept_model,
            learner_model=learner_model,
            current_objective=obj,
            latest_interpretation=interpretation,
            question_specification=spec,
            concept_mastery=mastery_dict,
        )

    return {"state_updates": state_updates}
