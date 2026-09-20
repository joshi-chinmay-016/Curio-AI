"""
Teacher Mode handler for Curio AI (Phase 2).
Handles:
- Gap-specific teaching (explaining ONLY the identified gap)
- Attempt-aware adaptation (conceptual -> analogy -> worked example)
- Generating exactly ONE verification question testing the exact gap
- Enforcing that Teacher does not give a broad lecture or answer the original question
"""
import re
from typing import Optional
from backend.app.ai.prompts.teacher_prompts import build_teacher_prompt
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import AIContext, CurrentQuestion, TurnEvaluation


class TeacherModeHandler:
    """
    Handles Teacher Mode behavior and response generation.
    Teaches the specific knowledge gap and asks one verification question.
    """

    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def generate_teacher_response(
        self,
        context: AIContext,
        gap: str,
        attempt_count: int = 1,
        interrupted_question: Optional[CurrentQuestion] = None,
        evaluation: Optional[TurnEvaluation] = None,
    ) -> str:
        """
        Generates a focused teacher response:
        1. Concise explanation of ONLY the specified gap.
        2. Exactly ONE verification question testing that gap.
        """
        int_q_content = interrupted_question.content if interrupted_question else None
        misconceptions = evaluation.misconceptions if evaluation else None

        prompt = build_teacher_prompt(
            context=context,
            gap=gap,
            attempt_count=attempt_count,
            interrupted_question=int_q_content,
            misconceptions=misconceptions,
        )
        raw_output = self.provider.generate_text(prompt)
        return self._enforce_single_verification_question(raw_output, gap)

    def explain_gap(self, context: AIContext, knowledge_gap: str) -> str:
        """
        Backward-compatible method for legacy code and orchestrator.
        """
        return self.generate_teacher_response(context, gap=knowledge_gap, attempt_count=1)

    @staticmethod
    def _enforce_single_verification_question(text: str, gap: str) -> str:
        """
        Ensures the teacher response contains an explanation and ends with
        exactly ONE verification question.
        """
        cleaned = text.strip().strip('"').strip("'")
        if not cleaned:
            return f"Let me explain {gap}. Can you explain how that works in your own words?"

        # Count question marks
        q_indices = [i for i, char in enumerate(cleaned) if char == "?"]
        if len(q_indices) > 1:
            # Keep everything up to the first question mark or truncate secondary questions
            # If the first question is at the end, keep up to that question mark
            # Find the paragraph or sentence boundary before extraneous questions
            # Keep up to the first question mark to satisfy the single question rule
            first_q_end = q_indices[0] + 1
            cleaned = cleaned[:first_q_end].strip()
        elif len(q_indices) == 0:
            # No question mark: append a verification question
            cleaned = cleaned.rstrip(".") + f"\n\nCan you explain how this applies to {gap}?"

        return cleaned
