"""
Student Mode handler and Question Generator for Curio AI (Phase 1C & 1D).
Implements the Feynman Technique: Curio is a curious student who learns from the user.
Enforces the HARD ONE-QUESTION RULE: exactly one primary learning question per response.
"""
import re
from typing import Optional
from backend.app.ai.prompts.student_prompts import (
    build_initial_question_prompt,
    build_student_question_prompt,
)
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    LearningDecision,
    Mode,
    Strategy,
    TurnEvaluation,
)


class StudentModeHandler:
    """
    Handles Student Mode behavior and question generation.
    Generates single, focused Socratic questions that probe understanding.
    """

    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def generate_initial_question(self, context: AIContext) -> str:
        """
        Generate the foundational question for a new session where no user answer exists yet.
        Strategy: ASK_FOUNDATION, Difficulty: 1.
        """
        prompt = build_initial_question_prompt(context.topic, difficulty=1)
        raw_output = self.provider.generate_text(prompt)
        return self._enforce_single_question(raw_output)

    def generate_followup_question(
        self,
        context: AIContext,
        evaluation: TurnEvaluation,
        decision: LearningDecision,
    ) -> str:
        """
        Generate a follow-up Student Mode question based on TurnEvaluation and LearningDecision.
        """
        prompt = build_student_question_prompt(context, decision, evaluation)
        raw_output = self.provider.generate_text(prompt)
        return self._enforce_single_question(raw_output)

    def generate_question(
        self,
        context: AIContext,
        strategy: str,
        evaluation: Optional[TurnEvaluation] = None,
    ) -> str:
        """
        Backward-compatible question generation method.
        """
        try:
            strat_enum = Strategy(strategy)
        except ValueError:
            strat_enum = Strategy.PROBE_WHY

        decision = LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=strat_enum,
            difficulty=context.difficulty,
            confidence=context.current_state.understanding_confidence,
            reason="Follow-up question generation.",
            active_concept=context.active_concept or context.topic,
        )
        return self.generate_followup_question(context, evaluation, decision)

    @staticmethod
    def _enforce_single_question(text: str) -> str:
        """
        Enforce the HARD ONE-QUESTION RULE:
        - Exactly one primary learning question.
        - At most one short conversational lead-in sentence.
        - Strips extraneous trailing questions or markdown artifacts.
        """
        cleaned = text.strip().strip('"').strip("'")
        if not cleaned:
            return "Could you explain that in more detail?"

        # If there are multiple question marks, truncate after the first question
        q_indices = [i for i, char in enumerate(cleaned) if char == "?"]
        if len(q_indices) > 1:
            # Keep up to the first question mark
            first_q_end = q_indices[0] + 1
            cleaned = cleaned[:first_q_end].strip()
        elif len(q_indices) == 0:
            # If no question mark exists, append one if it sounds like a question, or rephrase
            cleaned = cleaned.rstrip(".") + "?"

        return cleaned
