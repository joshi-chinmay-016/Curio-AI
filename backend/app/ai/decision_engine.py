"""
Deterministic learning policy and decision engine for Curio AI (Phase 1B).
Owns:
- Strategy selection with strict priority order
- Difficulty transitions (bounded 1-5, max delta 1)
- Student Mode state transition (mode remains STUDENT in Phase 1)
- Basic bounded confidence updates
"""
import logging
from typing import Optional
from backend.app.ai.schemas import (
    AIContext,
    LearningDecision,
    Mode,
    Strategy,
    TurnEvaluation,
)
from backend.app.ai.confidence import calculate_confidence
from backend.app.schemas.common import LearningMode, LearningStrategy

logger = logging.getLogger("curio.ai.decision_engine")


MAX_TEACHER_ATTEMPTS = 3

EXPLICIT_STUCK_PHRASES = [
    "i don't know",
    "i do not know",
    "idk",
    "i'm stuck",
    "im stuck",
    "i am stuck",
    "i don't understand",
    "i do not understand",
    "i'm confused",
    "im confused",
    "i am confused",
    "i have no idea",
    "can you explain this",
    "can you explain",
    "explain to me",
    "i don't get why",
    "i don't get it",
    "i do not get",
    "help me",
]


class DecisionEngine:
    """
    Deterministic Pedagogical Decision Engine for Student and Teacher Modes.
    The LLM does NOT decide the state transitions; the DecisionEngine owns them.
    """

    @staticmethod
    def _has_explicit_stuck_signal(user_msg: str) -> bool:
        if not user_msg:
            return False
        clean = user_msg.lower().strip()
        return any(phrase in clean for phrase in EXPLICIT_STUCK_PHRASES)

    def decide(self, context: AIContext, evaluation: TurnEvaluation) -> LearningDecision:
        """
        Produce a deterministic LearningDecision from the TurnEvaluation and AIContext.
        """
        current_mode = context.current_mode
        current_difficulty = context.difficulty
        current_confidence = context.current_state.understanding_confidence
        user_msg = context.history[-1].content if context.history else ""

        # =================================================================
        # 1. TEACHER MODE DECISION LOGIC (Phase 2D & 2E)
        # =================================================================
        if current_mode == Mode.TEACHER or (hasattr(current_mode, "value") and current_mode.value == "TEACHER"):
            is_explicit_stuck = self._has_explicit_stuck_signal(user_msg)
            is_pass = (
                evaluation.correctness >= 0.7
                and evaluation.stuck_probability < 0.4
                and not is_explicit_stuck
                and len(evaluation.misconceptions) == 0
            )

            if is_pass:
                # Verification PASS: Restore interrupted question and return to Student Mode
                restored_q = context.interrupted_question
                restored_concept = restored_q.concept if restored_q else (context.active_concept or context.topic)
                restored_diff = restored_q.difficulty if restored_q else current_difficulty

                return LearningDecision(
                    next_mode=Mode.STUDENT,
                    strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
                    difficulty=restored_diff,
                    confidence=round(min(1.0, current_confidence + 0.08), 2),
                    reason="Learner verified understanding of the gap. Returning to Student Mode and restoring interrupted question.",
                    active_concept=restored_concept,
                    should_offer_termination=False,
                    should_restore_interrupted_question=True,
                )
            else:
                # Verification FAIL: Check attempt limits
                curr_attempts = context.current_state.teacher_attempt_count or 0
                if context.current_state.teacher_intervention and context.current_state.teacher_intervention.attempt_count:
                    curr_attempts = max(curr_attempts, context.current_state.teacher_intervention.attempt_count)
                next_attempt = curr_attempts + 1

                gap = (
                    (context.current_state.teacher_intervention.gap if context.current_state.teacher_intervention else "")
                    or evaluation.knowledge_gap
                    or context.active_concept
                    or "understanding gap"
                )

                if next_attempt >= MAX_TEACHER_ATTEMPTS:
                    # Attempt limit reached: Fallback to Student Mode at simpler difficulty
                    restored_q = context.interrupted_question
                    fallback_diff = max(1, (restored_q.difficulty if restored_q else current_difficulty) - 1)
                    restored_concept = restored_q.concept if restored_q else (context.active_concept or context.topic)

                    return LearningDecision(
                        next_mode=Mode.STUDENT,
                        strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
                        difficulty=fallback_diff,
                        confidence=current_confidence,
                        reason=f"Maximum Teacher attempts ({MAX_TEACHER_ATTEMPTS}) reached for gap '{gap}'. Exiting Teacher Mode to simpler difficulty.",
                        active_concept=restored_concept,
                        should_offer_termination=False,
                        should_restore_interrupted_question=True,
                    )
                else:
                    # Continue in Teacher Mode for another attempt with adapted explanation
                    return LearningDecision(
                        next_mode=Mode.TEACHER,
                        strategy=Strategy.TEACH_GAP,
                        difficulty=current_difficulty,
                        confidence=round(max(0.0, current_confidence - 0.05), 2),
                        reason=f"Verification failed (attempt {next_attempt}/{MAX_TEACHER_ATTEMPTS}). Adapting explanation for gap: {gap}.",
                        active_concept=gap,
                        should_offer_termination=False,
                        should_restore_interrupted_question=False,
                    )

        # =================================================================
        # 2. STUDENT MODE: STUCK DETECTION & TRANSITION POLICY (Phase 2A)
        # =================================================================
        trigger_a = self._has_explicit_stuck_signal(user_msg)
        has_knowledge_gap = bool(evaluation.knowledge_gap and evaluation.knowledge_gap.strip())
        trigger_b = evaluation.stuck_probability >= 0.75 and (
            evaluation.correctness < 0.5 or has_knowledge_gap
        )

        # Trigger C: Repeated failure on the same knowledge gap
        trigger_c = False
        if has_knowledge_gap:
            current_gap_lower = evaluation.knowledge_gap.strip().lower()
            if context.current_state.teacher_intervention and context.current_state.teacher_intervention.gap:
                prev_gap = context.current_state.teacher_intervention.gap.strip().lower()
                if prev_gap in current_gap_lower or current_gap_lower in prev_gap:
                    trigger_c = True
            elif context.learning_context and context.learning_context.recent_evaluations:
                for prev_eval in reversed(context.learning_context.recent_evaluations):
                    if prev_eval.knowledge_gap:
                        prev_gap = prev_eval.knowledge_gap.strip().lower()
                        if prev_gap in current_gap_lower or current_gap_lower in prev_gap:
                            trigger_c = True
                            break
            elif context.current_state.consecutive_failures >= 1 and evaluation.correctness < 0.5:
                trigger_c = True

        if trigger_a or trigger_b or trigger_c:
            gap = evaluation.knowledge_gap or context.active_concept or "understanding gap"
            reason_trigger = (
                "explicit stuck signal" if trigger_a
                else "high stuck probability with evidence" if trigger_b
                else "repeated failure on the same knowledge gap"
            )
            is_major_gap = (
                evaluation.correctness < 0.4
                or evaluation.stuck_probability >= 0.7
                or (evaluation.knowledge_gap is not None and evaluation.correctness < 0.5)
            )
            next_diff = max(1, current_difficulty - 1) if is_major_gap else current_difficulty
            return LearningDecision(
                next_mode=Mode.TEACHER,
                strategy=Strategy.TEACH_GAP,
                difficulty=next_diff,
                confidence=round(max(0.0, current_confidence - 0.08), 2),
                reason=f"Learner is genuinely stuck ({reason_trigger}). Transitioning to Teacher Mode to explain gap: {gap}.",
                active_concept=gap,
                should_offer_termination=False,
                should_restore_interrupted_question=False,
            )

        # =================================================================
        # 3. NORMAL STUDENT MODE POLICY (Phase 1)
        # =================================================================
        is_strong = (
            evaluation.correctness >= 0.8
            and evaluation.completeness >= 0.7
            and evaluation.stuck_probability < 0.3
            and len(evaluation.misconceptions) == 0
            and len(evaluation.undefined_terms) == 0
            and len(evaluation.missing_concepts) == 0
        )
        is_major_gap = (
            evaluation.correctness < 0.4
            or evaluation.stuck_probability >= 0.7
            or (evaluation.knowledge_gap is not None and evaluation.correctness < 0.5)
        )
        has_misconception = len(evaluation.misconceptions) > 0
        has_undefined_term = len(evaluation.undefined_terms) > 0
        has_missing_concept = len(evaluation.missing_concepts) > 0

        # Strategy Priority
        if has_undefined_term:
            strategy = Strategy.CLARIFY_TERM
            active_concept = evaluation.undefined_terms[0]
            reason = f"Undefined term '{active_concept}' detected. Requesting clarification."
        elif has_misconception:
            strategy = Strategy.CHALLENGE_MISCONCEPTION
            active_concept = evaluation.misconceptions[0]
            reason = f"Misconception detected: '{active_concept}'. Challenging with counterexample."
        elif evaluation.recommended_strategy == Strategy.PROBE_WHY and evaluation.correctness >= 0.7:
            strategy = Strategy.PROBE_WHY
            active_concept = context.active_concept or context.topic
            reason = "Reasoning gap identified. Probing underlying cause/rationale (why)."
        elif evaluation.recommended_strategy == Strategy.PROBE_HOW and evaluation.correctness >= 0.7:
            strategy = Strategy.PROBE_HOW
            active_concept = context.active_concept or context.topic
            reason = "Mechanism gap identified. Probing step-by-step process (how)."
        elif has_missing_concept:
            strategy = Strategy.PROBE_MISSING_CONCEPT
            active_concept = evaluation.missing_concepts[0]
            reason = f"Missing concept '{active_concept}' identified. Probing prerequisite/component."
        elif evaluation.recommended_strategy == Strategy.PROBE_HOW or (
            evaluation.depth < 0.6 and evaluation.completeness < 0.7
        ):
            strategy = Strategy.PROBE_HOW
            active_concept = context.active_concept or context.topic
            reason = "Mechanism gap identified. Probing step-by-step process (how)."
        elif evaluation.recommended_strategy == Strategy.PROBE_WHY or (
            evaluation.depth < 0.8 and not is_strong
        ):
            strategy = Strategy.PROBE_WHY
            active_concept = context.active_concept or context.topic
            reason = "Reasoning gap identified. Probing underlying cause/rationale (why)."
        elif is_strong:
            if current_difficulty < 5 and evaluation.recommended_strategy == Strategy.INCREASE_DIFFICULTY:
                strategy = Strategy.INCREASE_DIFFICULTY
                reason = "Strong understanding demonstrated. Advancing difficulty level."
            else:
                strategy = Strategy.PROBE_WHY
                reason = "Strong understanding demonstrated. Probing deeper reasons."
            active_concept = context.active_concept or context.topic
        else:
            strategy = Strategy.VERIFY_UNDERSTANDING
            active_concept = context.active_concept or context.topic
            reason = "Partial answer. Verifying understanding with concrete application."

        # Difficulty Transitions
        if has_misconception:
            next_difficulty = current_difficulty
        elif evaluation.correctness >= 0.8:
            next_difficulty = min(5, current_difficulty + 1)
        elif is_major_gap:
            next_difficulty = max(1, current_difficulty - 1)
        else:
            next_difficulty = current_difficulty

        delta = next_difficulty - current_difficulty
        if abs(delta) > 1:
            next_difficulty = current_difficulty + (1 if delta > 0 else -1)
        next_difficulty = max(1, min(5, next_difficulty))

        # Basic Bounded Confidence Update
        if is_strong:
            confidence_delta = 0.08
        elif has_misconception:
            confidence_delta = -0.10
        elif is_major_gap:
            confidence_delta = -0.08
        else:
            confidence_delta = 0.00

        new_confidence = round(max(0.0, min(1.0, current_confidence + confidence_delta)), 2)

        return LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=strategy,
            difficulty=next_difficulty,
            confidence=new_confidence,
            reason=reason,
            active_concept=active_concept,
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        )


# =====================================================================
# Phase 0 Backward Compatibility Function
# =====================================================================

def decide_next_action(
    context: AIContext,
    evaluation: TurnEvaluation,
    consecutive_strong: int,
    consecutive_weak: int,
) -> LearningDecision:
    """
    Phase 0 compatibility function for existing tests in test_decision_engine.py.
    """
    current_mode = context.current_mode
    user_msg = context.history[-1].content.lower() if context.history else ""

    stuck_words = ["idk", "i don't know", "i'm stuck", "can you explain", "don't understand", "explain to me"]
    is_stuck_phrase = any(word in user_msg for word in stuck_words)

    next_mode = current_mode
    should_restore_interrupted_question = False
    strategy = evaluation.recommended_strategy
    difficulty = context.difficulty
    reason = ""

    if current_mode == LearningMode.STUDENT:
        if evaluation.stuck_probability > 0.7 or is_stuck_phrase or consecutive_weak >= 2:
            next_mode = LearningMode.TEACHER
            strategy = LearningStrategy.TEACH_GAP
            reason = "User appears stuck. Transitioning to TEACHER mode to explain the gap."
        elif len(evaluation.misconceptions) > 0 and consecutive_weak >= 1:
            next_mode = LearningMode.TEACHER
            strategy = LearningStrategy.TEACH_GAP
            reason = "User repeated misconceptions. Transitioning to TEACHER mode."
        else:
            if evaluation.correctness > 0.7:
                if consecutive_strong >= 2:
                    difficulty = min(5, difficulty + 1)
                    strategy = LearningStrategy.INCREASE_DIFFICULTY
                    reason = "User demonstrated strong understanding. Increasing difficulty."
                else:
                    strategy = LearningStrategy.PROBE_WHY
                    reason = "User gave a solid answer. Probing deeper."
            else:
                strategy = LearningStrategy.PROBE_MISSING_CONCEPT
                reason = "User answer is partially correct or incomplete. Probing missing concepts."

    elif current_mode == LearningMode.TEACHER:
        if evaluation.correctness > 0.7 and evaluation.stuck_probability < 0.3:
            next_mode = LearningMode.STUDENT
            should_restore_interrupted_question = True
            strategy = LearningStrategy.RESTORE_INTERRUPTED_QUESTION
            reason = "User verified understanding of the gap. Returning to STUDENT mode."
        else:
            strategy = LearningStrategy.VERIFY_UNDERSTANDING
            reason = "User is still struggling with the concept. Continuing explanation in TEACHER mode."

    elif current_mode == LearningMode.EVALUATOR:
        next_mode = LearningMode.EVALUATOR
        strategy = LearningStrategy.GENERATE_REPORT
        reason = "Compiling report."

    concept_coverage = evaluation.completeness
    recent_answer_quality = evaluation.correctness
    difficulty_achievement = difficulty / 5.0

    if consecutive_strong + consecutive_weak > 0:
        streak_ratio = consecutive_strong / (consecutive_strong + consecutive_weak)
        streak_depth = min(1.0, consecutive_strong / 5.0) if consecutive_strong > 0 else 0.0
        consistency = 0.5 * streak_ratio + 0.5 * streak_depth
    else:
        consistency = 0.5

    if current_mode == LearningMode.TEACHER and evaluation.correctness > 0.7:
        independent_correction = 1.0
    elif next_mode == LearningMode.STUDENT and len(evaluation.misconceptions) == 0 and evaluation.stuck_probability < 0.3:
        if consecutive_strong > 0:
            independent_correction = min(1.0, 1.0 - evaluation.stuck_probability)
        else:
            independent_correction = 0.0
    else:
        independent_correction = 0.0

    misconception_penalty = 0.15 * len(evaluation.misconceptions)
    help_dependency_penalty = 0.20 if next_mode == LearningMode.TEACHER else 0.0

    confidence = calculate_confidence(
        concept_coverage=concept_coverage,
        recent_answer_quality=recent_answer_quality,
        difficulty_achievement=difficulty_achievement,
        consistency=consistency,
        independent_correction=independent_correction,
        misconception_penalty=misconception_penalty,
        help_dependency_penalty=help_dependency_penalty,
    )

    should_offer_termination = False
    if confidence >= 0.75 and next_mode == LearningMode.STUDENT:
        should_offer_termination = True
        strategy = LearningStrategy.OFFER_TERMINATION
        reason = "Confidence reached 75% or higher. Offering session termination."

    return LearningDecision(
        next_mode=next_mode,
        strategy=strategy,
        difficulty=difficulty,
        confidence=round(confidence, 2),
        reason=reason,
        active_concept=evaluation.missing_concepts[0] if evaluation.missing_concepts else context.active_concept,
        should_offer_termination=should_offer_termination,
        should_restore_interrupted_question=should_restore_interrupted_question,
    )
