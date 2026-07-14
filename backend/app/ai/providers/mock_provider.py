import json
from typing import Any, Dict, Type
from pydantic import BaseModel
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import TurnEvaluation
from backend.app.schemas.common import LearningStrategy
from backend.app.schemas.report import SessionReportResponse, MasteryLevel

class MockLLMProvider(BaseLLMProvider):
    def generate_structured(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        # Check prompts to identify which model to mock
        prompt_lower = prompt.lower()
        
        if "evaluate" in prompt_lower or "turnevaluation" in response_model.__name__.lower():
            # Mock TurnEvaluation
            user_input = ""
            # Extract user input from prompt if possible
            if "user:" in prompt_lower:
                parts = prompt_lower.split("user:")
                if len(parts) > 1:
                    user_input = parts[-1].strip()

            # Determine response metrics
            correctness = 0.8
            clarity = 0.9
            completeness = 0.8
            depth = 0.7
            stuck_probability = 0.0
            misconceptions = []
            missing_concepts = []
            mastered_concepts = ["Core concept"]
            knowledge_gap = None
            strategy = LearningStrategy.PROBE_WHY
            difficulty = 1

            if any(phrase in user_input for phrase in ["idk", "i don't know", "can you explain", "stuck", "don't understand"]):
                correctness = 0.0
                stuck_probability = 0.95
                knowledge_gap = "User does not understand the current concept."
                strategy = LearningStrategy.TEACH_GAP
            elif "explain recursion" in user_input or "a function calls itself" in user_input:
                correctness = 0.7
                clarity = 0.8
                completeness = 0.5
                depth = 0.4
                stuck_probability = 0.0
                missing_concepts = ["base case"]
                knowledge_gap = "Missing termination criteria (base case)."
                strategy = LearningStrategy.PROBE_MISSING_CONCEPT
            elif "base case" in user_input or "stop condition" in user_input:
                correctness = 1.0
                clarity = 0.9
                completeness = 1.0
                depth = 0.8
                mastered_concepts = ["base case", "recursion"]
                strategy = LearningStrategy.INCREASE_DIFFICULTY
                difficulty = 2

            return response_model(
                correctness=correctness,
                clarity=clarity,
                completeness=completeness,
                depth=depth,
                relevance=1.0,
                stuck_probability=stuck_probability,
                misconceptions=misconceptions,
                missing_concepts=missing_concepts,
                undefined_terms=[],
                mastered_concepts=mastered_concepts,
                knowledge_gap=knowledge_gap,
                recommended_strategy=strategy,
                recommended_difficulty=difficulty
            )
            
        elif "report" in prompt_lower or "sessionreport" in response_model.__name__.lower():
            # Mock SessionReportResponse
            return response_model(
                session_id="00000000-0000-0000-0000-000000000000",
                understanding_score=85.0,
                mastery_level=MasteryLevel.PROFICIENT,
                strengths=["Explain basic self-invocation", "Able to identify call stacks"],
                high_priority_learning_gaps=["Understanding infinite call stack overflows"],
                medium_priority_learning_gaps=["Tail call optimizations"],
                low_priority_learning_gaps=["Iterative equivalents"],
                misconceptions_detected=["Believed stack is infinite"],
                concepts_mastered=["Self Call", "Base Case"],
                teacher_interventions_required=1,
                difficulty_achieved=3,
                personalized_roadmap=["Read about tail recursive functions", "Practice stack limits in browser DevTools"],
                recommended_exercises=["Implement factorial recursively and iteratively"],
                created_at="2026-07-14T17:00:00Z"
            )

        # Fallback empty model
        return response_model()

    def generate_text(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "student" in prompt_lower:
            if "base case" in prompt_lower:
                return "Interesting. What would happen if a recursive function did not have a base case? How would the machine handle it?"
            return "Could you explain how recursion works in your own words?"
        elif "teacher" in prompt_lower:
            return "No problem! A base case is simply a stopping condition. Without it, a recursive function calls itself infinitely, leading to a stack overflow. Can you explain what would happen to the memory stack if there's no base case?"
        elif "evaluator" in prompt_lower:
            return "Session complete! Here is the evaluation report of your understanding."
        return "Can you tell me more about that?"
