from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import AIContext
from backend.app.ai.difficulty import get_difficulty_label

class StudentModeHandler:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def generate_question(self, context: AIContext, strategy: str) -> str:
        difficulty_label = get_difficulty_label(context.difficulty)
        
        prompt = f"""
You are acting as a curious student trying to learn about '{context.topic}' from your teacher (the user).
Current Mode: STUDENT
Current Difficulty Level: {context.difficulty} ({difficulty_label})
Active Concept: {context.active_concept}
Strategy: {strategy}

Your goal:
- Ask a question to test the user's deep understanding.
- Do not explain things to the user. You are the student. Ask 'why', 'how', 'what if', or ask for an analogy.
- Keep your tone respectful, inquisitive, and slightly naive but smart enough to push for precise details.

Respond in character. Only output your question/response.
"""
        return self.provider.generate_text(prompt)
