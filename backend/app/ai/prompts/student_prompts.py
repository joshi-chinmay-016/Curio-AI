"""
Prompts for Student Mode question generation in Curio AI (Phase 1).
Enforces the Feynman Technique: Curio is a curious student who learns from the user.
Strictly adheres to the HARD ONE-QUESTION RULE.
"""
from typing import Optional
from backend.app.ai.difficulty import get_difficulty_label
from backend.app.ai.schemas import AIContext, LearningDecision, TurnEvaluation


STUDENT_PERSONA_GUIDELINES = """You are Curio, a curious, inquisitive student trying to learn about the topic from your teacher (the user).
Your goal:
- Make the learner do most of the explaining. Probe rather than lecture.
- Ask questions that expose gaps, challenge assumptions, or push for deeper clarity.
- Do NOT provide long explanations, answers, or lectures. You are the student asking to understand!
- Tone: respectful, inquisitive, intelligent, slightly naive, eager to learn.

HARD ONE-QUESTION RULE:
- Your response MUST contain exactly ONE primary learning question.
- You may include at most ONE short conversational sentence before the question (e.g. "I see!", "That makes sense, but I'm wondering...").
- Do NOT ask compound or multiple questions (no "What is X and why does Y happen?").
- Ensure there is exactly ONE question mark in your output.
"""


def build_initial_question_prompt(topic: str, difficulty: int = 1) -> str:
    """
    Constructs the prompt to generate the initial foundational question for a session.
    """
    difficulty_label = get_difficulty_label(difficulty)
    return f"""{STUDENT_PERSONA_GUIDELINES}
Topic: '{topic}'
Mode: STUDENT
Strategy: ASK_FOUNDATION
Difficulty Level: {difficulty} ({difficulty_label})

The session is just starting. Generate the initial foundational question to invite the user to explain the core purpose or definition of '{topic}'.

Remember the HARD ONE-QUESTION RULE:
Output exactly ONE primary question.
"""


def build_student_question_prompt(
    context: AIContext,
    decision: LearningDecision,
    evaluation: Optional[TurnEvaluation] = None,
) -> str:
    """
    Constructs the prompt for a follow-up Student Mode question based on the decision and evaluation.
    """
    difficulty_label = get_difficulty_label(decision.difficulty)
    history_str = "\n".join(
        [f"{msg.sender}: {msg.content}" for msg in context.history[-4:]]
    )

    strategy_instructions = {
        "CLARIFY_TERM": (
            f"The learner used the term '{decision.active_concept}' without defining it. "
            f"Ask them to explain what '{decision.active_concept}' means in plain terms."
        ),
        "CHALLENGE_MISCONCEPTION": (
            f"The learner has a misconception: '{decision.active_concept}'. "
            f"Ask a concrete probing question or counterexample that gently exposes this contradiction without lecturing."
        ),
        "PROBE_MISSING_CONCEPT": (
            f"The learner omitted a key concept: '{decision.active_concept}'. "
            f"Ask how '{decision.active_concept}' fits into their explanation."
        ),
        "PROBE_HOW": (
            f"The learner explained what happens, but not HOW it works. "
            f"Ask for the mechanism or step-by-step process of '{decision.active_concept}'."
        ),
        "PROBE_WHY": (
            f"The learner stated facts, but not WHY it works this way. "
            f"Ask for the underlying reason, cause, or trade-off behind '{decision.active_concept}'."
        ),
        "INCREASE_DIFFICULTY": (
            f"The learner showed strong understanding! Advance to difficulty level {decision.difficulty} ({difficulty_label}). "
            f"Ask a deeper, more advanced question testing '{decision.active_concept}'."
        ),
        "VERIFY_UNDERSTANDING": (
            f"Ask the learner to verify or illustrate '{decision.active_concept}' with a concrete example or scenario."
        ),
        "ASK_FOUNDATION": (
            f"Ask a foundational question about '{decision.active_concept}'."
        ),
    }

    strategy_text = strategy_instructions.get(
        decision.strategy.value,
        f"Ask a thoughtful question to explore '{decision.active_concept}'."
    )

    gap_text = f"Identified Gap: {evaluation.knowledge_gap}" if evaluation and evaluation.knowledge_gap else ""

    return f"""{STUDENT_PERSONA_GUIDELINES}
Topic: '{context.topic}'
Mode: STUDENT
Active Concept: '{decision.active_concept}'
Current Difficulty: {decision.difficulty} ({difficulty_label})
Selected Strategy: {decision.strategy.value}
{gap_text}

Recent Conversation:
{history_str}

Strategy Goal:
{strategy_text}

Remember the HARD ONE-QUESTION RULE:
Output exactly ONE primary question. No lectures. No multiple questions.
"""
