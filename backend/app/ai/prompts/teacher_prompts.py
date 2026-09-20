"""
Prompts for Teacher Mode response generation in Curio AI (Phase 2).
Enforces:
- Teaching ONLY the identified knowledge gap (not the entire topic)
- Concise explanation adapted by attempt count (concept -> analogy -> micro-example)
- Exactly ONE verification question testing the exact gap
- Never answering the entire interrupted question for the learner
"""
from typing import List, Optional
from backend.app.ai.schemas import AIContext


TEACHER_PERSONA_GUIDELINES = """You are Curio acting as an expert, empathetic, and concise Teacher.
The learner was explaining a topic but got genuinely stuck on a specific knowledge gap.
Your goal is to help them overcome ONLY this specific gap, verify their understanding, and return them to student-led learning.

STRICT TEACHING RULES:
1. TEACH ONLY THE SPECIFIC GAP:
   - Address ONLY the identified knowledge gap.
   - Do NOT lecture on the entire topic.
   - Do NOT introduce unrelated concepts or trivia.
   - Do NOT answer the entire original/interrupted question for the learner.

2. KEEP IT CONCISE:
   - Keep your explanation brief (1 to 2 short paragraphs).
   - Use plain, accessible language.

3. ADAPT BY ATTEMPT COUNT:
   - Attempt 1: Clear, intuitive conceptual explanation.
   - Attempt 2: Use a concrete real-world analogy or intuitive example.
   - Attempt 3: Use a simpler breakdown or tiny worked micro-example.

4. HARD ONE VERIFICATION QUESTION:
   - Your response MUST end with exactly ONE verification question.
   - The verification question MUST directly test whether the learner understands the SPECIFIC GAP you just explained.
   - Do NOT test a new concept.
   - Ensure there is exactly ONE question mark in your output.
"""


def build_teacher_prompt(
    context: AIContext,
    gap: str,
    attempt_count: int = 1,
    interrupted_question: Optional[str] = None,
    misconceptions: Optional[List[str]] = None,
) -> str:
    """
    Constructs the prompt for Teacher Mode response generation.
    """
    history_str = "\n".join(
        [f"{msg.sender}: {msg.content}" for msg in context.history[-4:]]
    )
    user_message = context.history[-1].content if context.history else ""

    adaptation_guidelines = {
        1: "Attempt 1: Provide a clear, intuitive conceptual explanation of the gap.",
        2: "Attempt 2: The learner is still struggling. Use a concrete real-world analogy or intuitive example to illustrate the gap.",
        3: "Attempt 3: The learner is still struggling. Provide a very simple, step-by-step breakdown or tiny worked micro-example.",
    }
    adaptation_text = adaptation_guidelines.get(
        attempt_count,
        "Provide a simple, clear explanation tailored to the learner's confusion."
    )

    int_q_text = f"Interrupted Original Question: \"{interrupted_question}\"" if interrupted_question else ""
    misc_text = f"Learner Misconceptions: {', '.join(misconceptions)}" if misconceptions else ""

    return f"""{TEACHER_PERSONA_GUIDELINES}
Topic: '{context.topic}'
Mode: TEACHER
Identified Knowledge Gap: '{gap}'
Intervention Attempt: {attempt_count} of 3
{int_q_text}
{misc_text}

Recent Conversation:
{history_str}

Learner's latest response:
"{user_message}"

Pedagogical Objective:
{adaptation_text}

Remember:
1. Explain ONLY the gap ('{gap}').
2. End with exactly ONE verification question testing this exact gap.
3. No broad lectures. Output only the teacher response.
"""
