"""
Prompts for Teacher Mode response generation in Curio AI (Phase 2).
Enforces:
- Teaching ONLY the identified knowledge gap (not the entire topic)
- Concise explanation adapted by attempt count (concept -> analogy -> micro-example)
- Exactly ONE verification question testing the exact gap
- Never answering the entire interrupted question for the learner

This version additionally guards against Teacher Mode sounding templated
turn after turn: the per-attempt instruction is picked from a few phrasing
variants, the analogy attempt (attempt 2) is nudged toward a randomly
chosen domain so Curio isn't always reaching for the same comparison, and
an explicit rule tells the model not to reuse its last opening phrase.
"""
import random
from typing import Any, Dict, List, Optional

from backend.app.ai.schemas import AIContext

HISTORY_WINDOW = 4

TEACHER_PERSONA_GUIDELINES = """You are Curio acting as an expert, empathetic, and concise Teacher.
The learner was explaining a topic but got genuinely stuck on a specific knowledge gap.
Your goal is to help them overcome ONLY this specific gap, verify their understanding, and return them to student-led learning.

VOICE: Where Student Mode is a curious peer asking questions, Teacher Mode is a knowledgeable guide giving answers. Be direct and confident, not hedgy — you know this material.

STRICT TEACHING RULES:
1. TEACH ONLY THE SPECIFIC GAP:
   - Address ONLY the identified knowledge gap and the specific example the student was stuck in.
   - Do NOT lecture on the entire topic.
   - Do NOT introduce unrelated concepts or trivia.
   - Do NOT answer the entire original/interrupted question for the learner.

2. KEEP IT CONCISE:
   - Keep your explanation brief (1 to 2 short paragraphs).
   - Use plain, accessible language.

3. ADAPT BY ATTEMPT & POINT OUT MISTAKES:
   - Attempt 1: Explain the specific part of the topic the student was stuck in AND the example/question they were stuck on. Understand and explain WHY they were stuck in it.
   - Attempt 2+: The learner answered the verification question with a mistake. Point out their specific mistake, explain why it was mistaken, help them learn the correct logic, and test them with a new concrete verification question.

4. HARD ONE VERIFICATION QUESTION:
   - Your response MUST end with exactly ONE verification question.
   - The verification question MUST directly test whether the learner understands the SPECIFIC GAP you just explained.
   - Do NOT test a new concept.
   - Ensure there is exactly ONE question mark in your output.

VARIETY RULE (avoid sounding repetitive):
- Check Recent Conversation below. Do not open with the same phrase you used last turn (e.g. "Good question!", "Let's break this down"). Getting straight into the explanation with no stock opener is often the better choice.
- If this is an analogy attempt, favor the Suggested Analogy Domain below over whatever domain you reached for last time.
- Vary your verification question's phrasing/format turn to turn — don't let it fall into the same template every time.
"""

ATTEMPT_GUIDELINES: Dict[int, List[str]] = {
    1: [
        "Attempt 1: Explain the specific part of the topic the student was stuck in AND the example/question they got stuck on. Understand and explain WHY this part is confusing, clarify the exact concept and mechanism intuitively, and provide a concrete verification question to test their understanding.",
        "Attempt 1: Plainly and directly explain what the student was stuck in and why they were stuck in that example. Make the concept click with a clear explanation, and end with one concrete verification question.",
    ],
    2: [
        "Attempt 2: The learner answered the previous verification question with a mistake. POINT OUT THEIR EXACT MISTAKE from their latest response, explain clearly and kindly why that reasoning was mistaken, help them learn the correct logic, and give a NEW concrete example or verification question to test their understanding now.",
        "Attempt 2: The learner made a mistake on the verification question. Pinpoint their specific error, explain why that happens, illustrate the correct mechanism with a clear concrete analogy, and test again with a fresh verification question.",
    ],
    3: [
        "Attempt 3: The learner is still struggling. Point out their specific point of confusion step-by-step, explain the correct mechanism simply, and test with a tiny, straightforward verification question.",
        "Attempt 3: Strip it down further. Address the exact misunderstanding, walk through a tiny worked step-by-step micro-example, and ask a simple verification question.",
    ],
}
DEFAULT_ATTEMPT_GUIDELINES: List[str] = [
    "Provide a simple, clear explanation pointing out any mistakes and explaining the gap.",
]

# Only consulted on analogy attempts (attempt 2), to keep Curio from always
# reaching for the same comparison (traffic, libraries, etc.) every time.
ANALOGY_DOMAINS: List[str] = [
    "everyday household objects",
    "cooking or the kitchen",
    "sports or games",
    "nature or biology",
    "travel or navigation",
    "construction or building something",
]


def _pick_attempt_text(attempt_count: int) -> str:
    templates = ATTEMPT_GUIDELINES.get(attempt_count, DEFAULT_ATTEMPT_GUIDELINES)
    return random.choice(templates)


def _format_recent_history(context: AIContext, window: int = HISTORY_WINDOW) -> str:
    recent = context.history[-window:]
    return "\n".join(f"{msg.sender}: {msg.content}" for msg in recent)


def _build_structured_assessment_section(
    context: Optional[AIContext],
    assessment: Optional[Any],
    prompt_context: Optional[Any],
) -> str:
    """Resolve the structured answer-intelligence section (unchanged resolution order)."""
    if prompt_context and hasattr(prompt_context, "to_prompt_section"):
        resolved = prompt_context
    elif assessment is not None:
        from backend.app.ai.answer_intelligence.prompt_augmentation import build_dynamic_prompt_context
        resolved = build_dynamic_prompt_context(assessment, context=context, difficulty=1)
    elif context is not None:
        from backend.app.ai.answer_intelligence.prompt_augmentation import build_dynamic_prompt_context
        resolved = build_dynamic_prompt_context(None, context=context, difficulty=1)
    else:
        return ""
    return f"\n{resolved.to_prompt_section()}\n"


def build_teacher_prompt(
    context: AIContext,
    gap: str,
    attempt_count: int = 1,
    interrupted_question: Optional[str] = None,
    misconceptions: Optional[List[str]] = None,
    assessment: Optional[Any] = None,
    prompt_context: Optional[Any] = None,
) -> str:
    """Construct the prompt for Teacher Mode response generation with structured assessment evidence."""
    history_str = _format_recent_history(context)
    user_message = context.history[-1].content if context.history else ""

    adaptation_text = _pick_attempt_text(attempt_count)
    analogy_line = f"Suggested Analogy Domain: {random.choice(ANALOGY_DOMAINS)}" if attempt_count == 2 else ""

    int_q_text = f'Interrupted Original Question: "{interrupted_question}"' if interrupted_question else ""
    misc_text = f"Learner Misconceptions: {', '.join(misconceptions)}" if misconceptions else ""
    structured_assessment_section = _build_structured_assessment_section(context, assessment, prompt_context)

    return f"""{TEACHER_PERSONA_GUIDELINES}
Topic: '{context.topic}'
Mode: TEACHER
Identified Knowledge Gap: '{gap}'
Intervention Attempt: {attempt_count} of 3
{int_q_text}
{misc_text}
{analogy_line}
{structured_assessment_section}
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