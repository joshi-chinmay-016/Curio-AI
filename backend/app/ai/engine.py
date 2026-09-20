"""
Public Curio AI Engine interface.
This is the ONLY interface that the backend service layer should interact with.
LangGraph workflows, state graphs, nodes, prompts, and providers are encapsulated internally.
"""
import logging
from typing import Any, Optional

from backend.app.ai.graph import build_curio_graph
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    LearningDecision,
    Mode,
    StateUpdates,
    Strategy,
    TurnEvaluation,
)

logger = logging.getLogger("curio.ai.engine")


class CurioEngine:
    """
    CurioEngine processes an incoming AIContext and returns an AIResult.

    Architecture boundary:
        AIContext (Input) -> CurioEngine.process() -> AIResult (Output)
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None, graph: Any = None):
        self.provider = provider or MockLLMProvider()
        self._graph = graph or build_curio_graph(self.provider)

    def process(self, context: AIContext) -> AIResult:
        """
        Process a single turn of learning interaction.

        Args:
            context: Strongly-typed AIContext constructed by the backend service.

        Returns:
            AIResult containing evaluation, decision, response, and recommended state updates.
        """
        logger.info(
            "Processing AI turn for session %s (mode=%s, topic=%s)",
            context.session_id,
            context.current_mode,
            context.topic,
        )

        # 1. Prepare initial graph state
        initial_state = {
            "context": context,
            "provider": self.provider,
        }

        # 2. Invoke internal LangGraph workflow
        final_state = self._graph.invoke(initial_state)

        # 3. Extract components
        evaluation: TurnEvaluation = final_state.get("evaluation")
        decision: LearningDecision = final_state.get("decision")
        response: AIResponse = final_state.get("response")
        state_updates: Optional[StateUpdates] = final_state.get("state_updates")

        # 4. Fallback resolution if a node did not emit state_updates
        if state_updates is None:
            state_updates = StateUpdates(
                current_mode=decision.next_mode if decision else Mode.STUDENT,
                difficulty=decision.difficulty if decision else context.difficulty,
                confidence=decision.confidence if decision else context.current_state.understanding_confidence,
                active_concept=decision.active_concept if decision else context.active_concept,
                mastered_concepts=evaluation.mastered_concepts if evaluation else None,
                unresolved_misconceptions=evaluation.misconceptions if evaluation else None,
            )

        # 5. Construct and validate complete AIResult
        result = AIResult(
            evaluation=evaluation,
            decision=decision,
            response=response,
            state_updates=state_updates,
        )

        return result
