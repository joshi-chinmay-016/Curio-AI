from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import AIContext

class TeacherModeHandler:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def explain_gap(self, context: AIContext, knowledge_gap: str) -> str:
        prompt = f"""
You are acting as an expert teacher. The user has run into a knowledge gap while trying to explain '{context.topic}'.
Knowledge Gap identified: {knowledge_gap}

Instructions:
1. Explain ONLY this gap. Do not explain the entire topic.
2. Use simple, clear language. Use an analogy if helpful.
3. Keep it brief (1-2 paragraphs).
4. At the end, ask a follow-up question requiring the user to demonstrate their understanding of this specific gap.

Only output your response/explanation.
"""
        return self.provider.generate_text(prompt)
