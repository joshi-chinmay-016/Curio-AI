import logging
from typing import List
from uuid import UUID
from backend.app.ai.schemas import AIContext, TurnEvaluation, LearningDecision
from backend.app.ai.confidence import calculate_confidence
from backend.app.schemas.common import LearningMode, LearningStrategy

logger = logging.getLogger("decision_engine")

def decide_next_action(
    context: AIContext,
    evaluation: TurnEvaluation,
    consecutive_strong: int,
    consecutive_weak: int
) -> LearningDecision:
    current_mode = context.current_mode
    user_msg = context.history[-1].content.lower() if context.history else ""
    
    # Heuristics for stuck words
    stuck_words = ["idk", "i don't know", "i'm stuck", "can you explain", "don't understand", "explain to me"]
    is_stuck_phrase = any(word in user_msg for word in stuck_words)
    
    # 1. State machine transitions
    next_mode = current_mode
    should_restore_interrupted_question = False
    strategy = evaluation.recommended_strategy
    difficulty = context.difficulty
    reason = ""

    # Mode checks
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
            # Stay in STUDENT mode
            if evaluation.correctness > 0.7:
                # Good answer
                if consecutive_strong >= 2:
                    difficulty = min(5, difficulty + 1)
                    strategy = LearningStrategy.INCREASE_DIFFICULTY
                    reason = "User demonstrated strong understanding. Increasing difficulty."
                else:
                    strategy = LearningStrategy.PROBE_WHY
                    reason = "User gave a solid answer. Probing deeper."
            else:
                # Weak answer, clarify or probe missing concept
                strategy = LearningStrategy.PROBE_MISSING_CONCEPT
                reason = "User answer is partially correct or incomplete. Probing missing concepts."

    elif current_mode == LearningMode.TEACHER:
        if evaluation.correctness > 0.7 and evaluation.stuck_probability < 0.3:
            # User understood the explanation
            next_mode = LearningMode.STUDENT
            should_restore_interrupted_question = True
            strategy = LearningStrategy.RESTORE_INTERRUPTED_QUESTION
            reason = "User verified understanding of the gap. Returning to STUDENT mode."
        else:
            # User is still struggling
            strategy = LearningStrategy.VERIFY_UNDERSTANDING
            reason = "User is still struggling with the concept. Continuing explanation in TEACHER mode."

    elif current_mode == LearningMode.EVALUATOR:
        next_mode = LearningMode.EVALUATOR
        strategy = LearningStrategy.GENERATE_REPORT
        reason = "Compiling report."

    # 2. Calculate Confidence using configurable weights
    # Concept coverage: derived from the completeness of the explanation
    concept_coverage = evaluation.completeness
    recent_answer_quality = evaluation.correctness

    # Difficulty achievement: normalized against max difficulty (5)
    difficulty_achievement = difficulty / 5.0

    # Consistency: scaled by streak ratio and depth of strong answers
    if consecutive_strong + consecutive_weak > 0:
        streak_ratio = consecutive_strong / (consecutive_strong + consecutive_weak)
        streak_depth = min(1.0, consecutive_strong / 5.0) if consecutive_strong > 0 else 0.0
        consistency = 0.5 * streak_ratio + 0.5 * streak_depth
    else:
        consistency = 0.5

    # Independent correction: evaluates whether the user resolves gaps / explains independently without help
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
        help_dependency_penalty=help_dependency_penalty
    )

    # Offer termination threshold
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
        should_restore_interrupted_question=should_restore_interrupted_question
    )
