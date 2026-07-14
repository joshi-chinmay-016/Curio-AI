from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import AIContext, TurnEvaluation

class AIEvaluator:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def evaluate_turn(self, context: AIContext) -> TurnEvaluation:
        # Construct the evaluation prompt
        history_str = "\n".join([f"{msg.sender}: {msg.content}" for msg in context.history[-5:]])
        user_message = context.history[-1].content if context.history else ""

        prompt = f"""
Evaluate the user's latest response in the context of learning the topic: '{context.topic}'.
Active Concept: {context.active_concept}
Current Question asked by AI: {context.current_question or "None (Initial Turn)"}

Conversation History (recent turns):
{history_str}

Evaluate the user response: "{user_message}"
Provide:
1. Correctness (0.0 to 1.0)
2. Clarity (0.0 to 1.0)
3. Completeness (0.0 to 1.0)
4. Depth (0.0 to 1.0)
5. Relevance (0.0 to 1.0)
6. Stuck Probability (0.0 to 1.0) - High if they say 'I don't know', 'IDK', or seem totally stuck.
7. Misconceptions: list of clear misconceptions (e.g. 'thought stack depth is infinite')
8. Missing Concepts: list of concepts they omitted (e.g. 'base case')
9. Mastered Concepts: list of concepts they demonstrated understanding of.
10. Knowledge Gap: text explaining their gap.
11. Recommended Strategy.
12. Recommended Difficulty.
"""
        evaluation = self.provider.generate_structured(prompt, TurnEvaluation)
        return evaluation
