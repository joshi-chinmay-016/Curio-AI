"""
Answer evaluation layer for Curio AI (Phase 1A).
Receives learner's answer and learning context, and produces a TurnEvaluation.
"""
from backend.app.ai.prompts.evaluator_prompts import build_turn_evaluation_prompt
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import AIContext, TurnEvaluation


class AIEvaluator:
    """
    Semantic evaluator for learner turns.
    Provider-backed to produce calibrated TurnEvaluation metrics.
    """

    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def evaluate_turn(self, context: AIContext) -> TurnEvaluation:
        """
        Evaluate the learner's latest response in the context of the active session.
        Returns TurnEvaluation reflecting the CURRENT TURN.
        """
        prompt = build_turn_evaluation_prompt(context)
        evaluation: TurnEvaluation = self.provider.generate_structured(prompt, TurnEvaluation)
        return evaluation


# Backward compatibility and Phase 1 alias
TurnEvaluator = AIEvaluator
