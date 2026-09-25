"""
Turn Interpreter for Curio AI (Adaptive Learning Core v1).
Semantic interpretation layer that analyzes user messages, classifies intent,
extracts substantive claims, and guards against prepared-question blind loops.
"""
import logging
import re
from typing import Optional

from backend.app.ai.prompts.interpreter_prompts import build_turn_interpretation_prompt
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.schemas import (
    AIContext,
    CurrentQuestion,
    Mode,
    TurnIntent,
    TurnInterpretation,
)

logger = logging.getLogger("curio.ai.turn_interpreter")


class TurnInterpreter:
    """
    Decoupled turn interpreter.
    Evaluates what the learner meant before any learning-decision or question-generation occurs.
    """

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider

    def interpret(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[CurrentQuestion] = None,
        mode: Optional[Mode] = None,
    ) -> TurnInterpretation:
        """
        Classify intent and extract semantic information from user message.
        Guaranteed to return a valid TurnInterpretation without raising exceptions.
        """
        raw_msg = (user_message or "").strip()
        if not raw_msg:
            return TurnInterpretation(
                intent=TurnIntent.OFF_TOPIC,
                is_answer_attempt=False,
                is_question=False,
                is_help_request=False,
                confidence=1.0,
            )

        active_mode = mode or (context.current_mode if context else Mode.STUDENT)
        curr_q = current_question or (context.current_question if context else None)

        prompt = build_turn_interpretation_prompt(
            user_message=raw_msg,
            context=context,
            current_question=curr_q,
            current_mode=active_mode,
        )

        try:
            interpretation: TurnInterpretation = self.provider.generate_structured(
                prompt, TurnInterpretation
            )
            # Post-validate and sanitize
            return self._sanitize_interpretation(interpretation, raw_msg, active_mode)
        except Exception as e:
            logger.warning(
                "TurnInterpreter structured generation failed (%s: %s); applying safe fallback.",
                type(e).__name__,
                str(e),
            )
            return self._defensive_fallback(raw_msg, active_mode, curr_q)

    def _sanitize_interpretation(
        self,
        interp: TurnInterpretation,
        user_message: str,
        mode: Mode,
    ) -> TurnInterpretation:
        """
        Enforce invariant consistency:
        - Confidence must be within [0.0, 1.0].
        - Flags must match intent.
        - Ready for verification in Teacher mode requires acknowledgement/ready phrases.
        """
        conf = max(0.0, min(1.0, float(interp.confidence or 0.8)))

        # Consistency alignments
        is_ans = interp.is_answer_attempt
        is_q = interp.is_question
        is_help = interp.is_help_request

        if interp.intent == TurnIntent.ANSWER_ATTEMPT:
            is_ans = True
            is_help = False
        elif interp.intent in (TurnIntent.HELP_REQUEST,):
            is_help = True
            is_ans = False
            is_q = True if "?" in user_message else is_q
        elif interp.intent in (TurnIntent.CLARIFICATION_REQUEST, TurnIntent.CONCEPTUAL_QUESTION):
            is_q = True
            is_ans = False
        elif interp.intent in (TurnIntent.ACKNOWLEDGEMENT, TurnIntent.READY_FOR_VERIFICATION):
            is_ans = False
            is_help = False

        # In Teacher Mode, if user says "I understand" / "ready", map to READY_FOR_VERIFICATION
        clean_lower = user_message.lower().strip().rstrip(".!")
        if mode == Mode.TEACHER and interp.intent == TurnIntent.ACKNOWLEDGEMENT:
            if any(p in clean_lower for p in ["i understand", "i get it now", "makes sense now", "ready", "im good", "i'm good"]):
                interp.intent = TurnIntent.READY_FOR_VERIFICATION

        return TurnInterpretation(
            intent=interp.intent,
            is_answer_attempt=is_ans,
            is_question=is_q,
            is_help_request=is_help,
            referenced_concept=interp.referenced_concept,
            target=interp.target,
            answer_evidence=interp.answer_evidence or (user_message if is_ans else None),
            requested_action=interp.requested_action,
            confidence=conf,
        )

    def _defensive_fallback(
        self,
        user_message: str,
        mode: Mode,
        current_question: Optional[CurrentQuestion] = None,
    ) -> TurnInterpretation:
        """
        Defensive semantic heuristics used only when provider call fails.
        Guarantees invalid LLM output never corrupts learning state.
        """
        clean = user_message.lower().strip()
        clean_no_punct = clean.rstrip("?.!").strip()

        # 1. Direct help requests / stuck
        stuck_signals = [
            "don't know", "dont know", "not sure", "im stuck", "i'm stuck",
            "i am stuck", "no idea", "no clue", "lost", "teach me", "please explain",
            "help me", "can you explain", "could you explain", "don't understand",
            "dont understand", "confused",
        ]
        if any(s in clean for s in stuck_signals):
            return TurnInterpretation(
                intent=TurnIntent.HELP_REQUEST,
                is_answer_attempt=False,
                is_question=True if "?" in clean else False,
                is_help_request=True,
                answer_evidence=None,
                requested_action="teach",
                confidence=0.9,
            )

        # 2. Clarification request (asking about the question/word)
        clarification_signals = [
            "what do you mean", "what does that mean", "clarify", "can you clarify",
            "could you clarify", "what is meant by", "meaning of", "which part",
        ]
        if any(c in clean for c in clarification_signals) or (clean.startswith("what ") and "mean" in clean):
            return TurnInterpretation(
                intent=TurnIntent.CLARIFICATION_REQUEST,
                is_answer_attempt=False,
                is_question=True,
                is_help_request=False,
                answer_evidence=None,
                requested_action="clarify",
                confidence=0.9,
            )

        # 3. Acknowledgements and Ready for Verification
        ack_phrases = ["ok", "okay", "yes", "yeah", "yep", "sure", "got it", "i see", "understood", "ok got it"]
        ready_phrases = ["i understand now", "i get it now", "makes sense now", "i'm good now", "im good now", "let me try", "ready", "im good", "i'm good"]

        is_ack = clean_no_punct in ack_phrases or any(p == clean_no_punct or clean_no_punct.startswith(p + " ") or clean_no_punct.endswith(" " + p) for p in ack_phrases)
        is_ready = clean_no_punct in ready_phrases or any(r in clean for r in ready_phrases) or "understand now" in clean

        if mode == Mode.TEACHER:
            if is_ready:
                return TurnInterpretation(
                    intent=TurnIntent.READY_FOR_VERIFICATION,
                    is_answer_attempt=False,
                    is_question=False,
                    is_help_request=False,
                    requested_action="verify",
                    confidence=0.9,
                )
            if is_ack or clean in ["i understand", "i get it"]:
                return TurnInterpretation(
                    intent=TurnIntent.READY_FOR_VERIFICATION,
                    is_answer_attempt=False,
                    is_question=False,
                    is_help_request=False,
                    requested_action="verify",
                    confidence=0.8,
                )

        if is_ack:
            return TurnInterpretation(
                intent=TurnIntent.ACKNOWLEDGEMENT,
                is_answer_attempt=False,
                is_question=False,
                is_help_request=False,
                requested_action="continue",
                confidence=0.85,
            )

        # 4. Inquisitive conceptual question
        if clean.endswith("?") and (clean.startswith("how ") or clean.startswith("why ") or clean.startswith("what is ")):
            return TurnInterpretation(
                intent=TurnIntent.CONCEPTUAL_QUESTION,
                is_answer_attempt=False,
                is_question=True,
                is_help_request=False,
                requested_action="explain",
                confidence=0.8,
            )

        # 5. Default: Substantive answer attempt
        # If the user typed a substantial sentence (> 3 words), treat as answer attempt
        words = clean.split()
        if len(words) >= 3:
            return TurnInterpretation(
                intent=TurnIntent.ANSWER_ATTEMPT,
                is_answer_attempt=True,
                is_question=False,
                is_help_request=False,
                answer_evidence=user_message,
                requested_action=None,
                confidence=0.75,
            )

        return TurnInterpretation(
            intent=TurnIntent.UNKNOWN,
            is_answer_attempt=False,
            is_question=False,
            is_help_request=False,
            confidence=0.5,
        )
