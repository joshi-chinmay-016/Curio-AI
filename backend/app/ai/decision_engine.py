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
TEACHER_VERIFICATION_PASS_THRESHOLD = 0.70
TEACHER_VERIFICATION_PARTIAL_THRESHOLD = 0.40
TEACHER_VERIFICATION_MAX_STUCK = 0.35

EXPLICIT_TEACH_OR_STUCK_PHRASES = [
    # Explicit teach requests
    "teach me",
    "can you teach me",
    "could you teach me",
    "please teach me",
    "teach me please",
    "teach me this",
    "teach me about",
    "teach this",
    "teach me again",
    "teach me the mechanism",
    "teach me that",
    "please explain",
    "can you explain",
    "could you explain",
    "can you explain this",
    "can you explain that",
    "can you explain that again",
    "can you explain again",
    "explain to me",
    "explain this to me",
    "explain this",
    "explain how",
    "explain the",
    "explain the mechanism",
    "help me understand",
    "can you help me understand",
    "could you help me understand",
    "can you help",
    "could you help",
    "tell me how",
    "tell me why",
    "tell me what",
    "tell me again",
    "can you walk me through this",
    "walk me through",
    "walk me through this",
    "can you clarify",
    "could you clarify",
    "what is",
    "how does",
    "describe",
    "describe the mechanism",
    "how works",
    # Explicit stuck / confusion phrases
    "i don't know",
    "i do not know",
    "idk",
    "not sure",
    "i'm not sure",
    "im not sure",
    "no idea",
    "i have no idea",
    "no clue",
    "i have no clue",
    "i'm stuck",
    "im stuck",
    "i am stuck",
    "stuck",
    "completely stuck",
    "still stuck",
    "i don't understand",
    "i do not understand",
    "i don't understand this",
    "i don't understand the mechanism",
    "i do not understand the mechanism",
    "i'm confused",
    "im confused",
    "i am confused",
    "still confused",
    "i don't get why",
    "i don't get it",
    "i do not get",
    "i don't get the mechanism",
    "don't get the mechanism",
    "help me",
    "i am lost",
    "i'm lost",
    "im lost",
    "totally lost",
    "completely lost",
    "lost on this",
]

EXPLICIT_READY_PHRASES = [
    "i'll explain",
    "ill explain",
    "let me explain",
    "let me try",
    "let me try to explain",
    "i understand now",
    "i understand",
    "i got it",
    "i'll try",
    "ill try",
    "ready to explain",
    "ready to try",
    "i think i understand",
    "i think i understand now",
    "i think i get it",
    "i think i got it",
    "i think i can explain",
]

NON_ANSWER_ACKNOWLEDGMENTS = [
    "yes",
    "yeah",
    "yep",
    "ok",
    "okay",
    "sure",
    "i see",
    "i understand",
    "got it",
    "understood",
    "makes sense",
    "right",
    "alright",
    "i get it",
    "i understand now",
    "let me explain",
    "ill explain",
    "i'll explain",
    "i'll try",
    "ill try",
]

# Retain backward compatibility alias
EXPLICIT_STUCK_PHRASES = EXPLICIT_TEACH_OR_STUCK_PHRASES


class DecisionEngine:
    """
    Deterministic Pedagogical Decision Engine for Student and Teacher Modes.
    The LLM does NOT decide the state transitions; the DecisionEngine owns them.
    """

    @staticmethod
    def _has_explicit_teach_or_stuck_signal(user_msg: str) -> bool:
        if not user_msg:
            return False
        clean = user_msg.lower().strip()
        return any(phrase in clean for phrase in EXPLICIT_TEACH_OR_STUCK_PHRASES)

    @classmethod
    def _has_explicit_stuck_signal(cls, user_msg: str) -> bool:
        return cls._has_explicit_teach_or_stuck_signal(user_msg)

    def decide(self, context: AIContext, evaluation: TurnEvaluation) -> LearningDecision:
        """
        Produce a deterministic LearningDecision from the TurnEvaluation and AIContext.
        """
        current_mode = context.current_mode
        current_difficulty = context.difficulty
        current_confidence = context.current_state.understanding_confidence
        user_msg = context.history[-1].content if context.history else ""
        clean_msg = user_msg.lower().strip()

        # =================================================================
        # 1. TEACHER MODE DECISION LOGIC (Phase 2D & 2E)
        # =================================================================
        if current_mode == Mode.TEACHER or (hasattr(current_mode, "value") and current_mode.value == "TEACHER"):
            words = clean_msg.split()
            word_count = len(words)

            is_teach_or_stuck = self._has_explicit_teach_or_stuck_signal(user_msg)
            is_ready_signal = any(phrase in clean_msg for phrase in EXPLICIT_READY_PHRASES)
            is_acknowledgment = clean_msg in NON_ANSWER_ACKNOWLEDGMENTS or any(clean_msg == phrase for phrase in NON_ANSWER_ACKNOWLEDGMENTS)

            stripped_content = clean_msg
            for phrase in EXPLICIT_READY_PHRASES + NON_ANSWER_ACKNOWLEDGMENTS:
                stripped_content = stripped_content.replace(phrase, " ")
            substantive_word_count = len(stripped_content.split())

            is_bare_ack = (is_ready_signal or is_acknowledgment) and substantive_word_count <= 3
            is_question = (
                "?" in clean_msg
                or clean_msg.startswith("what")
                or clean_msg.startswith("how")
                or clean_msg.startswith("why")
                or clean_msg.startswith("is ")
                or clean_msg.startswith("can ")
                or clean_msg.startswith("could ")
                or clean_msg.startswith("tell me")
                or clean_msg.startswith("explain")
            )
            is_stuck_or_struggle = any(k in clean_msg for k in [
                "i don't know", "i do not know", "no idea", "have no idea", "i'm stuck", "im stuck",
                "completely stuck", "still stuck", "confused", "still confused", "don't understand",
                "do not understand", "still don't understand", "lost", "i'm lost", "im lost", "idk",
                "not sure", "wrong", "fail", "failed"
            ])
            is_clarification_turn = (is_question or is_bare_ack or (is_teach_or_stuck and not is_stuck_or_struggle))

            # A verification pass REQUIRES:
            # 1. Correctness >= TEACHER_VERIFICATION_PASS_THRESHOLD (0.70)
            # 2. Stuck probability < TEACHER_VERIFICATION_MAX_STUCK (0.35)
            # 3. No misconceptions
            # 4. NOT an explicit teach request or stuck signal ("teach me", "i don't know")
            # 5. NOT asking a question ("can you explain?", "is ASGI the server?")
            # 6. NOT a generic bare non-answer acknowledgment ("yes", "ok", "sure", "i understand")
            # 7. Must contain substantive content (>= 3 words)
            is_pass = (
                evaluation.correctness >= TEACHER_VERIFICATION_PASS_THRESHOLD
                and evaluation.stuck_probability < TEACHER_VERIFICATION_MAX_STUCK
                and len(evaluation.misconceptions) == 0
                and not is_teach_or_stuck
                and not is_question
                and not is_bare_ack
                and word_count >= 3
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
            elif (
                not is_clarification_turn
                and evaluation.correctness >= TEACHER_VERIFICATION_PARTIAL_THRESHOLD
                and evaluation.correctness < TEACHER_VERIFICATION_PASS_THRESHOLD
                and len(evaluation.misconceptions) == 0
            ):
                # PARTIAL: Remain in Teacher Mode and probe missing detail (PROBE)
                gap = (
                    evaluation.knowledge_gap
                    or (context.current_state.teacher_intervention.gap if context.current_state.teacher_intervention else "")
                    or context.active_concept
                    or "understanding gap"
                )
                return LearningDecision(
                    next_mode=Mode.TEACHER,
                    strategy=Strategy.PROBE_WHY,
                    difficulty=current_difficulty,
                    confidence=current_confidence,
                    reason=f"Partial verification answer for gap: '{gap}'. Probing missing specifics before concluding teacher intervention.",
                    active_concept=gap,
                    should_offer_termination=False,
                    should_restore_interrupted_question=False,
                )
            else:
                # Clarification turn or failed answer attempt
                curr_attempts = context.current_state.teacher_attempt_count or 0
                if context.current_state.teacher_intervention and context.current_state.teacher_intervention.attempt_count:
                    curr_attempts = max(curr_attempts, context.current_state.teacher_intervention.attempt_count)

                # Clarification questions and readiness affirmations do not consume an attempt limit;
                # struggle and failed answer attempts do consume an attempt.
                next_attempt = curr_attempts if is_clarification_turn else curr_attempts + 1

                gap = (
                    evaluation.knowledge_gap
                    or (context.current_state.teacher_intervention.gap if context.current_state.teacher_intervention else "")
                    or context.active_concept
                    or "understanding gap"
                )

                if next_attempt >= MAX_TEACHER_ATTEMPTS:
                    # Attempt limit reached: Fallback to Student Mode at simpler difficulty
                    # Note: We do NOT mark the concept as mastered!
                    restored_q = context.interrupted_question
                    fallback_diff = max(1, (restored_q.difficulty if restored_q else current_difficulty) - 1)
                    restored_concept = restored_q.concept if restored_q else (context.active_concept or context.topic)

                    return LearningDecision(
                        next_mode=Mode.STUDENT,
                        strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
                        difficulty=fallback_diff,
                        confidence=current_confidence,
                        reason=f"Maximum Teacher attempts ({MAX_TEACHER_ATTEMPTS}) reached for gap '{gap}' without demonstrated understanding. Exiting Teacher Mode to simpler difficulty.",
                        active_concept=restored_concept,
                        should_offer_termination=False,
                        should_restore_interrupted_question=True,
                    )
                else:
                    if is_bare_ack:
                        reason = f"Learner indicated readiness to explain ('{user_msg}'). Prompting for explanation of gap: {gap}."
                    elif is_clarification_turn:
                        reason = f"Learner asked for explanation ('{user_msg}'). Explaining gap: {gap} and asking verification."
                    else:
                        reason = f"Verification failed (attempt {next_attempt}/{MAX_TEACHER_ATTEMPTS}). Adapting explanation for gap: {gap}."

                    return LearningDecision(
                        next_mode=Mode.TEACHER,
                        strategy=Strategy.TEACH_GAP,
                        difficulty=current_difficulty,
                        confidence=current_confidence if is_clarification_turn else round(max(0.0, current_confidence - 0.05), 2),
                        reason=reason,
                        active_concept=gap,
                        should_offer_termination=False,
                        should_restore_interrupted_question=False,
                    )

        # =================================================================
        # 2. STUDENT MODE: STUCK DETECTION & TRANSITION POLICY (Phase 2A)
        # =================================================================
        trigger_a = self._has_explicit_teach_or_stuck_signal(user_msg)
        has_knowledge_gap = bool(evaluation.knowledge_gap and evaluation.knowledge_gap.strip())
        trigger_b = evaluation.stuck_probability >= 0.75 and (
            evaluation.correctness < 0.5 or has_knowledge_gap
        )

        # Trigger C: Repeated failure on the same knowledge gap or consecutive failures
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
        elif context.current_state.consecutive_failures >= 2 and evaluation.correctness < 0.5:
            trigger_c = True

        # Trigger D: Clear major misconception or total failure to understand
        trigger_d = (
            (len(evaluation.misconceptions) > 0 and evaluation.correctness < 0.35)
            or evaluation.correctness < 0.25
            or evaluation.recommended_strategy == Strategy.TEACH_GAP
        )

        if trigger_a or trigger_b or trigger_c or trigger_d:
            gap = (
                evaluation.knowledge_gap
                or (evaluation.misconceptions[0] if evaluation.misconceptions else None)
                or context.active_concept
                or "understanding gap"
            )
            reason_trigger = (
                "explicit stuck signal / teach request" if trigger_a
                else "high stuck probability with evidence" if trigger_b
                else "repeated failure on the concept" if trigger_c
                else "clear major misconception detected"
            )
            is_major_gap = (
                evaluation.correctness < 0.4
                or evaluation.stuck_probability >= 0.7
                or (evaluation.knowledge_gap is not None and evaluation.correctness < 0.5)
                or trigger_d
            )
            next_diff = max(1, current_difficulty - 1) if is_major_gap else current_difficulty
            return LearningDecision(
                next_mode=Mode.TEACHER,
                strategy=Strategy.TEACH_GAP,
                difficulty=next_diff,
                confidence=round(max(0.0, current_confidence - 0.08), 2),
                reason=f"Learner requires teacher intervention ({reason_trigger}). Transitioning to Teacher Mode to explain gap: {gap}.",
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
        if (
            evaluation.correctness >= TEACHER_VERIFICATION_PASS_THRESHOLD
            and evaluation.stuck_probability < TEACHER_VERIFICATION_MAX_STUCK
        ):
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

    if current_mode == LearningMode.TEACHER and evaluation.correctness >= TEACHER_VERIFICATION_PASS_THRESHOLD:
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
