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


class DecisionEngine:
    """
    Deterministic Pedagogical Decision Engine for Student Mode.
    The LLM does NOT decide the state transitions; the DecisionEngine owns them.
    """

    def decide(self, context: AIContext, evaluation: TurnEvaluation) -> LearningDecision:
        """
        Produce a deterministic LearningDecision from the TurnEvaluation and AIContext.
        """
        current_difficulty = context.difficulty
        current_confidence = context.current_state.understanding_confidence

        # Determine if answer is strong, partial, or major gap
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

        # -----------------------------------------------------------------
        # 1. Strategy Priority (Section 7.1)
        # -----------------------------------------------------------------
        # 1. undefined_terms present -> CLARIFY_TERM
        # 2. else if misconceptions present -> CHALLENGE_MISCONCEPTION
        # 3. else if important missing_concepts present -> PROBE_MISSING_CONCEPT
        # 4. else if learner needs mechanism -> PROBE_HOW
        # 5. else if learner needs reasoning -> PROBE_WHY
        # 6. else if strong understanding -> INCREASE_DIFFICULTY or deeper strategy
        # 7. else -> appropriate normal Student Mode follow-up
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

        # -----------------------------------------------------------------
        # 2. Difficulty Transitions (Section 8)
        # -----------------------------------------------------------------
        # Strong: current + 1
        # Partial: remain at current
        # Major gap: remain or decrease by 1
        # Misconception: remain at current (challenge misconception)
        # Never change by more than 1. Clamped to [1, 5].
        if has_misconception:
            next_difficulty = current_difficulty
        elif evaluation.correctness >= 0.8:
            next_difficulty = min(5, current_difficulty + 1)
        elif is_major_gap:
            next_difficulty = max(1, current_difficulty - 1)
        else:
            # Partial understanding
            next_difficulty = current_difficulty

        # Ensure single-turn delta <= 1 and clamped [1, 5]
        delta = next_difficulty - current_difficulty
        if abs(delta) > 1:
            next_difficulty = current_difficulty + (1 if delta > 0 else -1)
        next_difficulty = max(1, min(5, next_difficulty))

        # -----------------------------------------------------------------
        # 3. Basic Bounded Confidence Update (Section 9)
        # -----------------------------------------------------------------
        # Strong: increases
        # Partial: remains approximately stable
        # Major gap: decreases
        # Misconception: decreases
        # Clamped to [0.0, 1.0]. No 75% termination in Phase 1.
        if is_strong:
            confidence_delta = 0.08
        elif has_misconception:
            confidence_delta = -0.10
        elif is_major_gap:
            confidence_delta = -0.08
        else:
            # Partial understanding
            confidence_delta = 0.00

        new_confidence = round(max(0.0, min(1.0, current_confidence + confidence_delta)), 2)

        # -----------------------------------------------------------------
        # 4. Mode Invariant (Section 10)
        # -----------------------------------------------------------------
        # For Phase 1: next_mode MUST remain STUDENT.
        next_mode = Mode.STUDENT

        return LearningDecision(
            next_mode=next_mode,
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
