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

            # Case: Verification Pass (Teacher Mode - Binary Search & FastAPI ASGI)
            elif any(k in user_input for k in [
                "ignore everything after 10",
                "greater than 10",
                "cannot be after",
                "because 7 is smaller",
                "stops the loop",
                "verification pass",
                "verified",
                "asgi server handles the incoming network communication",
                "asgi server handles incoming",
                "passes the request to the fastapi",
                "uvicorn is an asgi server",
            ]):
                correctness = 0.95
                clarity = 0.90
                completeness = 0.90
                depth = 0.85
                relevance = 1.0
                stuck_probability = 0.05
                misconceptions = []
                missing_concepts = []
                undefined_terms = []
                mastered_concepts = ["ASGI request handling mechanism" if "asgi" in user_input or "fastapi" in prompt_lower else "Order-based elimination"]
                knowledge_gap = None
                strategy = Strategy.RESTORE_INTERRUPTED_QUESTION

            # Case: Non-answer acknowledgments and ready signals (NOT a pass!)
            elif any(user_input == k or user_input.startswith(k + " ") or user_input.endswith(" " + k) for k in [
                "yes", "yeah", "yep", "ok", "okay", "sure", "i see", "i understand", "i understand now",
                "got it", "understood", "makes sense", "right", "alright", "i get it",
                "let me explain", "ill explain", "i'll explain", "i'll try", "ill try", "ready to explain"
            ]) or user_input in ["yes", "ok", "okay", "sure", "i understand", "i understand now", "i got it", "let me explain"]:
                correctness = 0.15
                clarity = 0.40
                completeness = 0.10
                depth = 0.0
                relevance = 0.50
                stuck_probability = 0.50
                misconceptions = []
                missing_concepts = ["Active concept explanation"]
                undefined_terms = []
                mastered_concepts = []
                knowledge_gap = "Learner acknowledged or signaled readiness without explaining the concept."
                strategy = Strategy.PROBE_WHY

            # Case 4: Likely misconception (check before general concepts)
            elif any(k in user_input for k in ["misconception", "works on any array", "stack is infinite", "infinite memory", "fastapi is a database", "directly opens the tcp"]):
                correctness = 0.20
                clarity = 0.80
                completeness = 0.20
                depth = 0.10
                relevance = 0.80
                stuck_probability = 0.30
                misconceptions = ["FastAPI is a database" if "database" in user_input else "Binary search works on unsorted arrays"]
                mastered_concepts = []
                knowledge_gap = "Major misconception regarding the fundamental mechanism."
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

            # Case 8: Explicit Teach / Struggle / Clarification / Question
            elif any(k in user_input for k in [
                "teach me",
                "can you teach me",
                "could you teach me",
                "please teach me",
                "teach this",
                "can you explain",
                "could you explain",
                "explain that again",
                "explain this",
                "explain how",
                "explain the mechanism",
                "help me understand",
                "tell me how",
                "tell me why",
                "tell me what",
                "walk me through",
                "what is",
                "how does",
                "describe",
                "idk",
                "i don't know",
                "i do not know",
                "not sure",
                "no idea",
                "i have no idea",
                "stuck",
                "i'm stuck",
                "im stuck",
                "don't understand",
                "do not understand",
                "confused",
                "i'm lost",
                "im lost",
                "weak",
                "uncertain",
            ]):
                correctness = 0.0
                clarity = 0.30
                completeness = 0.0
                depth = 0.0
                relevance = 0.80
                stuck_probability = 0.95
                mastered_concepts = []
                knowledge_gap = "Learner requested teaching or expressed struggle with the mechanism."
                strategy = Strategy.TEACH_GAP

            # Case: Verification Fail (Teacher Mode)
            elif any(k in user_input for k in ["still don't understand", "still stuck", "failed verification", "still confused", "still don't get it"]):
                correctness = 0.10
                clarity = 0.40
                completeness = 0.10
                depth = 0.0
                relevance = 0.70
                stuck_probability = 0.90
                misconceptions = []
                missing_concepts = []
                undefined_terms = []
                mastered_concepts = []
                knowledge_gap = "Still struggling to understand the mechanism."
                strategy = Strategy.TEACH_GAP

            # Case 3: Incorrect answer
            elif any(k in user_input for k in ["incorrect", "wrong", "iterative for loop", "left = mid + 1", "set left", "deletes the process"]):
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
            elif any(k in user_input for k in ["partial", "somewhat", "calls itself until done", "handles the requests", "handles requests"]):
                correctness = 0.55
                clarity = 0.70
                completeness = 0.50
                depth = 0.40
                relevance = 0.90
                stuck_probability = 0.10
                missing_concepts = ["call stack limit" if "calls itself" in user_input else "ASGI interface contract"]
                mastered_concepts = ["Self-invocation"] if "calls itself" in user_input else []
                knowledge_gap = "Learner understands self-invocation but omitted memory constraints." if "calls itself" in user_input else "Learner understands request handling generally but omitted the ASGI interface role."
                strategy = Strategy.PROBE_WHY

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

        # Teacher Mode responses with attempt-aware adaptation
        if "mode: teacher" in prompt_lower or "expert, empathetic, and concise teacher" in prompt_lower:
            if "fastapi" in prompt_lower or "asgi" in prompt_lower:
                if "intervention attempt: 2" in prompt_lower or "explain that again" in prompt_lower or "explain again" in prompt_lower:
                    return "Think of Uvicorn and FastAPI like a waiter and a chef: Uvicorn (the ASGI server) listens to the network, receives the customer's order, and delivers it to FastAPI to prepare the response.\n\nHow does the ASGI server communicate the incoming request to the FastAPI application?"
                elif "intervention attempt: 3" in prompt_lower:
                    return "When an HTTP request arrives, Uvicorn accepts the TCP socket, parses the HTTP bytes into an ASGI scope dictionary, and invokes the FastAPI application callable `app(scope, receive, send)`.\n\nWhat role does the ASGI server play in receiving the network communication and passing the request?"
                return "FastAPI is an ASGI application framework that does not handle raw network sockets directly; it relies on an ASGI server (like Uvicorn) to manage network connections and pass HTTP events into FastAPI via the ASGI interface.\n\nWhat role does the ASGI server play in this request mechanism?"
            elif "intervention attempt: 2" in prompt_lower:
                return "Think of a dictionary: because words are in alphabetical order, if you open to 'M' looking for 'Apple', you know 'Apple' must be in the first half.\n\nWhy does this alphabetical order guarantee 'Apple' isn't in the second half?"
            elif "intervention attempt: 3" in prompt_lower:
                return "Consider [2, 5, 8, 12, 16]. The middle is 8. If our target is 5, since 5 < 8 and the list is sorted, 5 cannot possibly be in [12, 16].\n\nWhy does knowing the list is sorted allow us to discard [12, 16] without checking them?"
            elif any(k in prompt_lower for k in ["binary search", "sorted", "sorting", "ordering"]):
                return "Sorting gives us an ordering we can rely on. If the middle value is larger than the target, every value after the middle is also larger, so that entire half can be eliminated.\n\nNow suppose the middle value is 10 and the target is 7. Why can we ignore everything after 10?"
            
            # Dynamic teacher response for other topics/gaps
            import re
            m_gap = re.search(r"identified knowledge gap:\s*['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            gap_str = m_gap.group(1).strip() if m_gap else "this concept"
            m_top = re.search(r"topic:\s*['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            top_str = m_top.group(1).strip() if m_top else "the topic"
            if "recursion" in top_str.lower() or "base case" in gap_str.lower():
                return "A base case is simply a stopping condition that prevents infinite execution. Can you explain what would happen if a recursive function ran without a base case?"
            return f"In {top_str}, understanding {gap_str} is essential because it governs how the system behaves under boundary conditions.\n\nCan you explain why {gap_str} is necessary for {top_str} to function correctly?"

        # Phase 0 baseline test preservation
        if "base case" in prompt_lower and ("recursion" in prompt_lower or "student" in prompt_lower):
            return "What would happen if the recursive function did not contain a base case?"

        # Initial turn / foundation question
        if "ask_foundation" in prompt_lower or "initial" in prompt_lower:
            import re
            m = re.search(r"topic:\s*['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            topic_str = m.group(1).strip() if m else ""
            if "operating system" in topic_str.lower() or topic_str.lower() == "os":
                return "What is the main purpose of an operating system?"
            if "dbms" in topic_str.lower() or "database" in topic_str.lower():
                return "What is the primary role of a Database Management System (DBMS) in managing data?"
            if "machine learning" in topic_str.lower() or "ml" in topic_str.lower():
                return "How would you explain what machine learning is and how it differs from traditional programming?"
            if topic_str and topic_str.lower() not in ("general topic", "general concept", "this topic"):
                return f"Can you explain in simple words what {topic_str} is and what core problem it solves?"
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
            import re
            m_top = re.search(r"topic:\s*['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            top_str = m_top.group(1).strip() if m_top else ""
            if top_str and top_str.lower() not in ("recursion", "binary search", "general concept"):
                return f"Why is that mechanism essential in {top_str}?"
            return "Why does that behavior occur in this scenario?"
        elif "increase_difficulty" in prompt_lower:
            return "How would you optimize this using memoization to avoid redundant calculations?"
        elif "verify_understanding" in prompt_lower:
            return "Could you give a concrete example showing how this works?"
        elif "evaluator" in prompt_lower:
            return "Session complete! Here is the evaluation report."

        return "Could you explain how this works in your own words?"
