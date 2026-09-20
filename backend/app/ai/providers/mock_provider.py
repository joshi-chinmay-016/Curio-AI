"""
Deterministic mock LLM provider for Curio AI tests.
Supports all 8 evaluation cases, strategy-specific questions, and preserves Phase 0 test fixtures.
"""
from typing import Any, Dict, Type
from pydantic import BaseModel
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.schemas import Strategy, TurnEvaluation
from backend.app.schemas.common import LearningStrategy
from backend.app.schemas.report import MasteryLevel, SessionReportResponse


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic provider for unit, integration, and contract tests.
    Does not make any live LLM or external network calls.
    """

    def generate_structured(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        prompt_lower = prompt.lower()

        if "evaluate" in prompt_lower or "turnevaluation" in response_model.__name__.lower():
            # Carefully isolate the user input from the prompt without matching prompt instructions
            user_input = ""
            if "learner's latest response:" in prompt_lower:
                after = prompt_lower.split("learner's latest response:")[1]
                if '"' in after:
                    parts = after.split('"')
                    if len(parts) >= 2:
                        user_input = parts[1].strip()
                if not user_input:
                    user_input = after.split("\n")[0].strip()
            elif "evaluate the user response:" in prompt_lower:
                after = prompt_lower.split("evaluate the user response:")[1]
                if '"' in after:
                    parts = after.split('"')
                    if len(parts) >= 2:
                        user_input = parts[1].strip()
                if not user_input:
                    user_input = after.split("\n")[0].strip()
            elif "user:" in prompt_lower:
                parts = prompt_lower.split("user:")
                if len(parts) > 1:
                    user_input = parts[-1].split("\n")[0].strip()

            # Baseline defaults
            correctness = 0.8
            clarity = 0.9
            completeness = 0.8
            depth = 0.7
            relevance = 1.0
            stuck_probability = 0.0
            misconceptions = []
            missing_concepts = []
            undefined_terms = []
            mastered_concepts = ["Core concept"]
            knowledge_gap = None
            strategy = Strategy.PROBE_WHY
            difficulty = 1

            # Case: Phase 0 baseline test ("stops the function from calling itself forever")
            if "stops the function from calling itself" in user_input:
                return response_model(
                    correctness=0.85,
                    clarity=0.78,
                    completeness=0.72,
                    depth=0.65,
                    relevance=0.95,
                    stuck_probability=0.15,
                    misconceptions=[],
                    missing_concepts=["Stack memory during recursion"],
                    undefined_terms=[],
                    mastered_concepts=["Purpose of a base case"],
                    knowledge_gap=None,
                    recommended_strategy=Strategy.PROBE_WHY,
                    recommended_difficulty=4,
                )

            # Case 1: Strong answer
            if any(k in user_input for k in ["strong", "perfect", "excellent", "termination condition", "base case stops the loop"]):
                correctness = 0.95
                clarity = 0.90
                completeness = 0.90
                depth = 0.85
                relevance = 1.0
                stuck_probability = 0.05
                mastered_concepts = ["Recursion", "Base Case"]
                strategy = Strategy.INCREASE_DIFFICULTY
                difficulty = 2

            # Case 4: Likely misconception (check before general concepts)
            elif any(k in user_input for k in ["misconception", "works on any array", "stack is infinite", "infinite memory"]):
                correctness = 0.35
                clarity = 0.80
                completeness = 0.40
                depth = 0.30
                relevance = 0.90
                stuck_probability = 0.10
                misconceptions = ["Binary search works on unsorted arrays"]
                mastered_concepts = []
                knowledge_gap = "Belief that binary search does not require sorted data."
                strategy = Strategy.CHALLENGE_MISCONCEPTION

            # Case 6: Undefined term
            elif any(k in user_input for k in ["undefined_term", "undefined term", "gizmo", "trampoline", "pointer dereference"]):
                correctness = 0.60
                clarity = 0.50
                completeness = 0.60
                depth = 0.50
                relevance = 0.85
                stuck_probability = 0.15
                undefined_terms = ["trampoline"]
                mastered_concepts = []
                knowledge_gap = "Used undefined technical jargon."
                strategy = Strategy.CLARIFY_TERM

            # Case 7: Irrelevant answer
            elif any(k in user_input for k in ["irrelevant", "the weather is nice", "random text", "off topic"]):
                correctness = 0.05
                clarity = 0.30
                completeness = 0.05
                depth = 0.0
                relevance = 0.05
                stuck_probability = 0.60
                mastered_concepts = []
                knowledge_gap = "Answer was completely unrelated to the topic."
                strategy = Strategy.ASK_FOUNDATION

            # Case 8: Weak/uncertain answer
            elif any(k in user_input for k in ["idk", "i don't know", "can you explain", "stuck", "don't understand", "weak", "uncertain", "not sure"]):
                correctness = 0.0
                clarity = 0.20
                completeness = 0.0
                depth = 0.0
                relevance = 0.50
                stuck_probability = 0.95
                mastered_concepts = []
                knowledge_gap = "User does not understand the current concept."
                strategy = Strategy.ASK_FOUNDATION

            # Case 3: Incorrect answer
            elif any(k in user_input for k in ["incorrect", "wrong", "iterative for loop"]):
                correctness = 0.10
                clarity = 0.50
                completeness = 0.20
                depth = 0.10
                relevance = 0.80
                stuck_probability = 0.20
                missing_concepts = ["self-invocation", "base case"]
                mastered_concepts = []
                knowledge_gap = "Confusing recursion with iterative loops."
                strategy = Strategy.PROBE_WHY

            # Case 2: Partial answer
            elif any(k in user_input for k in ["partial", "somewhat", "calls itself until done"]):
                correctness = 0.65
                clarity = 0.70
                completeness = 0.50
                depth = 0.40
                relevance = 0.90
                stuck_probability = 0.10
                missing_concepts = ["call stack limit"]
                mastered_concepts = ["Self-invocation"]
                knowledge_gap = "Learner understands self-invocation but omitted memory constraints."
                strategy = Strategy.PROBE_MISSING_CONCEPT

            # Case 5: Missing concept
            elif any(k in user_input for k in ["missing_concept", "missing concept", "explain recursion", "a function calls itself"]):
                correctness = 0.70
                clarity = 0.80
                completeness = 0.50
                depth = 0.40
                relevance = 1.0
                stuck_probability = 0.0
                missing_concepts = ["base case"]
                mastered_concepts = ["function self-call"]
                knowledge_gap = "Missing termination criteria (base case)."
                strategy = Strategy.PROBE_MISSING_CONCEPT

            elif "base case" in user_input or "stop condition" in user_input:
                correctness = 1.0
                clarity = 0.9
                completeness = 1.0
                depth = 0.8
                mastered_concepts = ["base case", "recursion"]
                strategy = Strategy.INCREASE_DIFFICULTY
                difficulty = 2

            return response_model(
                correctness=correctness,
                clarity=clarity,
                completeness=completeness,
                depth=depth,
                relevance=relevance,
                stuck_probability=stuck_probability,
                misconceptions=misconceptions,
                missing_concepts=missing_concepts,
                undefined_terms=undefined_terms,
                mastered_concepts=mastered_concepts,
                knowledge_gap=knowledge_gap,
                recommended_strategy=strategy,
                recommended_difficulty=difficulty,
            )

        elif "report" in prompt_lower or "sessionreport" in response_model.__name__.lower():
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
                created_at="2026-07-14T17:00:00Z",
            )

        return response_model()

    def generate_text(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Phase 0 baseline test preservation
        if "base case" in prompt_lower and ("recursion" in prompt_lower or "student" in prompt_lower):
            return "What would happen if the recursive function did not contain a base case?"

        # Initial turn / foundation question
        if "ask_foundation" in prompt_lower or "initial" in prompt_lower:
            if "operating systems" in prompt_lower or "os" in prompt_lower:
                return "What is the main purpose of an operating system?"
            return "What is the core purpose of this topic in your own words?"

        # Strategy-specific student questions
        if "clarify_term" in prompt_lower:
            return "What do you mean by that term in simple words?"
        elif "challenge_misconception" in prompt_lower:
            return "If binary search works on any array, how would you know which half to discard if the array is unsorted?"
        elif "probe_missing_concept" in prompt_lower:
            return "How does the base case fit into that process?"
        elif "probe_how" in prompt_lower:
            return "How does the computer handle each recursive call under the hood?"
        elif "probe_why" in prompt_lower:
            return "Why does that behavior occur in this scenario?"
        elif "increase_difficulty" in prompt_lower:
            return "How would you optimize this using memoization to avoid redundant calculations?"
        elif "verify_understanding" in prompt_lower:
            return "Could you give a concrete example showing how this works?"
        elif "teacher" in prompt_lower:
            return "A base case is simply a stopping condition. Can you explain what happens without it?"
        elif "evaluator" in prompt_lower:
            return "Session complete! Here is the evaluation report."

        return "Could you explain how this works in your own words?"
