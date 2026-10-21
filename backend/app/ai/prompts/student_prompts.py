"""
Prompts for Student Mode question generation in Curio AI (Phase 1).
Enforces the Feynman Technique: Curio is a curious student who learns from the user.
Strictly adheres to the HARD ONE-QUESTION RULE.

This version additionally guards against Curio's questions sounding
templated turn after turn: the scaffold instruction for a given strategy
is picked from a handful of phrasing variants rather than a single fixed
string, and a randomly chosen question "angle" (hypothetical, comparison,
example-request, edge case, etc.) is suggested each call. Combined with an
explicit "don't repeat your last opener" rule, this keeps consecutive
questions from converging on the same shape even though each call to the
LLM is otherwise stateless.
"""
import random
from typing import Any, Dict, List, Optional

from backend.app.ai.difficulty import get_difficulty_label
from backend.app.ai.schemas import AIContext, LearningDecision, TurnEvaluation

HISTORY_WINDOW = 4

STUDENT_PERSONA_GUIDELINES = """You are Curio, a genuine, curious beginner student learning from a teacher (the user).
Your nature as a student:
- You know NOTHING other than what the teacher has taught you so far. You do NOT know unintroduced prerequisites or internal mechanics.
- Formulate proper, descriptive student doubts (2 to 4 sentences):
  1. Briefly acknowledge or reflect what you understood from the teacher's explanation so far.
  2. Voice your specific doubt, confusion, or what you are struggling to visualize.
  3. Ask the teacher to explain descriptively in simple, understandable terms or walk through a concrete example.
- Avoid abrupt, dry one-line quiz questions (e.g. "What is X?"). Sound like an engaged student thinking out loud.
- If their explanation is high-level, ask a doubt about HOW it actually works step-by-step.
- NEVER introduce or assume unstated prerequisites (e.g. if the user hasn't mentioned sorting, do NOT ask about sorting!).
- If they introduce unexplained technical terms or jargon, ask them to unpack what those mean and how they fit in.
- Move through the learning journey naturally: mechanism -> doubts/prerequisites -> concrete example -> edge cases -> trade-offs.
- Never lecture, explain the concept, or reveal answers. You are the student asking to understand!
- Tone: curious, respectful, inquisitive, intelligent, slightly skeptical, eager to master the topic.

CRITICAL GROUNDING & NO HALLUCINATED ACKNOWLEDGMENT:
- Ground your question strictly in what the learner EXPLICITLY said.
- NEVER acknowledge or praise concepts the user never mentioned.

HARD ONE-QUESTION RULE:
- Your response MUST contain exactly ONE primary learning question (exactly ONE question mark '?' at the very end).
- The preceding sentences must be declarative reflections or doubts.
- Do NOT ask compound questions asking multiple independent questions."""

# Each strategy maps to a few differently-worded instructions. Picking one at
# random each call means the raw instruction text fed to the LLM isn't
# identical call-to-call, which is a big part of why consecutive questions
# were converging on the same phrasing before.
STRATEGY_TEMPLATES: Dict[str, List[str]] = {
    "CLARIFY_TERM": [
        "The learner used the term '{concept}' without defining it. Ask them to explain what '{concept}' means in plain terms.",
        "The learner dropped the term '{concept}' without unpacking it. Ask them, in their own words, what '{concept}' actually means.",
        "'{concept}' came up but was never defined. Ask the learner for a plain-language definition of it.",
    ],
    "CHALLENGE_MISCONCEPTION": [
        "The learner has a misconception: '{concept}'. Ask a concrete probing question or counterexample that gently exposes this contradiction without lecturing.",
        "There's a misconception around '{concept}'. Pose a concrete scenario or counterexample, as a question, that nudges the learner to notice the gap themselves.",
        "The learner seems to believe something off about '{concept}'. Without correcting them outright, ask a question that would surface the issue themselves.",
    ],
    "PROBE_MISSING_CONCEPT": [
        "The learner omitted a key concept: '{concept}'. Ask how '{concept}' fits into their explanation.",
        "'{concept}' is missing from what the learner described. Ask where it fits into the picture.",
        "The learner's explanation skipped over '{concept}' entirely. Ask how it connects to what they just said.",
    ],
    "PROBE_HOW": [
        "The learner explained what happens, but not HOW it works. Ask for the mechanism or step-by-step process of '{concept}'.",
        "They've described the outcome but not the process. Ask them to walk through how '{concept}' actually happens, step by step.",
        "The learner covered the 'what', not the 'how'. Ask for the mechanism behind '{concept}'.",
    ],
    "PROBE_WHY": [
        "The learner stated facts, but not WHY it works this way. Ask for the underlying reason, cause, or trade-off behind '{concept}'.",
        "They know what happens with '{concept}', but not why. Ask for the underlying reason or trade-off.",
        "The learner described '{concept}' without explaining its cause. Ask why it works that way.",
    ],
    "INCREASE_DIFFICULTY": [
        "The learner showed strong understanding! Advance to difficulty level {difficulty} ({difficulty_label}). Ask a deeper, more advanced question testing '{concept}'.",
        "Strong grasp so far. Push to difficulty level {difficulty} ({difficulty_label}) with a tougher question on '{concept}'.",
        "They're ready for more. Raise the difficulty to {difficulty} ({difficulty_label}) and ask something sharper about '{concept}'.",
    ],
    "VERIFY_UNDERSTANDING": [
        "Ask the learner to verify or illustrate '{concept}' with a concrete example or scenario.",
        "Have the learner apply '{concept}' to a real example to confirm they've actually got it.",
        "Ask the learner to demonstrate '{concept}' using a scenario of their own choosing.",
    ],
    "ASK_FOUNDATION": [
        "Ask a foundational question about '{concept}'.",
        "Open with a basic, grounding question about '{concept}'.",
        "Ask a simple starting question to begin exploring '{concept}'.",
    ],
    "REQUEST_EXAMPLE": [
        "The learner explained '{concept}' theoretically. Ask them for a concrete real-world example or use case illustrating how it operates.",
        "Ask the learner to give a specific scenario or practical example showing '{concept}' in action.",
        "The explanation of '{concept}' is abstract. Ask for a realistic example demonstrating it.",
    ],
    "TEST_EDGE_CASE": [
        "Probe boundary conditions, extreme inputs, or failure modes for '{concept}'. Ask what happens when limits are pushed.",
        "Ask what happens to '{concept}' in an unusual edge case or unexpected scenario.",
        "Test the limits of '{concept}': ask how it behaves under failure or edge-case conditions.",
    ],
    "CHALLENGE_ASSUMPTION": [
        "Ask a beginner doubt about whether what the teacher just explained holds true in all scenarios, or if there is a situation where it might fail.",
        "Ask the teacher what would happen if the inputs or conditions they just described were unusual or tricky.",
        "Probe what the teacher just explained by asking if that process works every single time without exception.",
    ],
    "CONNECT_CONCEPTS": [
        "Ask the learner to connect '{concept}' to related concepts or architectural components, analyzing trade-offs.",
        "Explore how '{concept}' interacts with other parts of the system, asking about trade-offs or design decisions.",
        "Ask how '{concept}' compares or integrates with related approaches, probing the architectural trade-offs.",
    ],
    "DEPTH_EXPANSION": [
        "The learner's answer on '{concept}' is correct but incomplete. Ask them to expand into the deeper mechanisms or missing dimensions.",
        "Deepen the explanation of '{concept}' by asking what happens beneath the surface.",
        "The core idea of '{concept}' is right, but lacks depth. Ask a follow-up that pushes into the underlying specifics.",
    ],
}
DEFAULT_STRATEGY_TEMPLATES: List[str] = [
    "Ask a thoughtful question to explore '{concept}'.",
    "Ask something that pushes the learner to think more deeply about '{concept}'.",
]

# Suggested question "shape" — varies the form of the question independently
# of the strategy's content focus, so even the same strategy twice in a row
# doesn't produce the same-sounding question.
QUESTION_ANGLES: List[str] = [
    "a direct, plainly-worded question",
    "a 'what if' hypothetical",
    "a request for a concrete real-world example",
    "a comparison to something related the learner already mentioned",
    "a question probing an edge case or exception",
]


def _pick_strategy_text(strategy_key: str, concept: str, difficulty: int, difficulty_label: str) -> str:
    templates = STRATEGY_TEMPLATES.get(strategy_key, DEFAULT_STRATEGY_TEMPLATES)
    template = random.choice(templates)
    return template.format(concept=concept, difficulty=difficulty, difficulty_label=difficulty_label)


def _format_recent_history(context: AIContext, window: int = HISTORY_WINDOW) -> str:
    recent = context.history[-window:]
    return "\n".join(f"{msg.sender}: {msg.content}" for msg in recent)


def _build_structured_assessment_section(
    context: Optional[AIContext],
    decision: LearningDecision,
    assessment: Optional[Any],
    prompt_context: Optional[Any],
) -> str:
    """Resolve the structured answer-intelligence section (unchanged resolution order)."""
    if prompt_context and hasattr(prompt_context, "to_prompt_section"):
        resolved = prompt_context
    elif assessment is not None:
        from backend.app.ai.answer_intelligence.prompt_augmentation import build_dynamic_prompt_context
        resolved = build_dynamic_prompt_context(
            assessment, context=context, decision=decision, difficulty=decision.difficulty
        )
    elif context is not None:
        from backend.app.ai.answer_intelligence.prompt_augmentation import build_dynamic_prompt_context
        resolved = build_dynamic_prompt_context(
            None, context=context, decision=decision, difficulty=decision.difficulty
        )
    else:
        return ""
    return f"\n{resolved.to_prompt_section()}\n"


def build_initial_question_prompt(topic: str, difficulty: int = 1) -> str:
    """Construct the prompt to generate the initial foundational question for a session."""
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
    assessment: Optional[Any] = None,
    prompt_context: Optional[Any] = None,
) -> str:
    """
    Construct the prompt for a follow-up Student Mode question based on the
    decision, evaluation, and authoritative structured assessment context
    (Milestone B).
    """
    difficulty_label = get_difficulty_label(decision.difficulty)
    history_str = _format_recent_history(context)

    strategy_text = _pick_strategy_text(
        decision.strategy.value, decision.active_concept, decision.difficulty, difficulty_label
    )
    question_angle = random.choice(QUESTION_ANGLES)

    gap_text = f"Identified Gap: {evaluation.knowledge_gap}" if evaluation and evaluation.knowledge_gap else ""
    structured_assessment_section = _build_structured_assessment_section(context, decision, assessment, prompt_context)

    return f"""{STUDENT_PERSONA_GUIDELINES}
Topic: '{context.topic}'
Mode: STUDENT
Active Concept: '{decision.active_concept}'
Current Difficulty: {decision.difficulty} ({difficulty_label})
Selected Strategy: {decision.strategy.value}
Suggested Question Angle: {question_angle}
{gap_text}
{structured_assessment_section}
Recent Conversation:
{history_str}

Strategy Goal:
{strategy_text}

Remember the HARD ONE-QUESTION RULE:
Output exactly ONE primary question. No lectures. No multiple questions.
"""