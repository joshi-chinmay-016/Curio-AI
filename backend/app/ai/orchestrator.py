import logging
from typing import Optional, Dict, Any
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.evaluator import AIEvaluator
from backend.app.ai.decision_engine import decide_next_action
from backend.app.ai.student import StudentModeHandler
from backend.app.ai.teacher import TeacherModeHandler
from backend.app.ai.schemas import AIContext, TurnEvaluation, LearningDecision, AIResponse
from backend.app.schemas.common import LearningMode, LearningStrategy

logger = logging.getLogger("ai_orchestrator")

class AIOrchestrator:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider
        self.evaluator = AIEvaluator(provider)
        self.student = StudentModeHandler(provider)
        self.teacher = TeacherModeHandler(provider)

    def process_turn(
        self,
        context: AIContext,
        consecutive_strong: int,
        consecutive_weak: int
    ) -> AIResponse:
        logger.info(f"Processing turn for session {context.session_id} in mode {context.current_mode}")

        # 1. Evaluate current answer
        evaluation = self.evaluator.evaluate_turn(context)
        
        # Adjust counters locally for decision engine
        if evaluation.correctness > 0.7:
            consecutive_strong += 1
            consecutive_weak = 0
        else:
            consecutive_weak += 1
            consecutive_strong = 0

        # 2. Make decision
        decision = decide_next_action(
            context,
            evaluation,
            consecutive_strong,
            consecutive_weak
        )

        # 3. Generate response text based on mode and strategy
        content = ""
        if decision.next_mode == LearningMode.STUDENT:
            content = self.student.generate_question(context, decision.strategy.value)
        elif decision.next_mode == LearningMode.TEACHER:
            gap = evaluation.knowledge_gap or "Unidentified understanding gap."
            content = self.teacher.explain_gap(context, gap)
        else:
            content = "The session has been compiled. Switching to report mode."

        metadata = {
            "evaluation": evaluation.model_dump(),
            "decision": decision.model_dump()
        }

        return AIResponse(
            content=content,
            mode=decision.next_mode,
            strategy=decision.strategy,
            difficulty=decision.difficulty,
            confidence=decision.confidence,
            metadata=metadata
        )
