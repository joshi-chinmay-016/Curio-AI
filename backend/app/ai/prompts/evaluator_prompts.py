"""
Prompts for TurnEvaluation in Curio AI (Phase 1).
Instructs the evaluator model to evaluate the learner's explanation for the current turn.
"""
from backend.app.ai.schemas import AIContext


def build_turn_evaluation_prompt(context: AIContext) -> str:
    """
    Constructs the evaluation prompt for the learner's latest turn.
    Scores and annotations reflect the CURRENT TURN only.
    """
    history_str = "\n".join(
        [f"{msg.sender}: {msg.content}" for msg in context.history[-6:]]
    )
    user_message = context.history[-1].content if context.history else ""
    current_q = context.current_question.content if context.current_question else "None (Initial Turn)"

    return f"""You are an expert pedagogical evaluator assessing a learner's explanation.
Topic: {context.topic}
Active Concept: {context.active_concept or context.topic}
Current Question asked by AI: {current_q}
Current Difficulty Level: {context.difficulty}

Recent Conversation History:
{history_str}

Learner's latest response:
"{user_message}"

Evaluate the learner's latest response for this CURRENT TURN ONLY. Do not assume permanent mastery.
Provide a JSON object matching TurnEvaluation:
- correctness (float, 0.0 to 1.0): How accurate is the explanation?
- clarity (float, 0.0 to 1.0): How clear and well-expressed is it?
- completeness (float, 0.0 to 1.0): Did it cover the required components?
- depth (float, 0.0 to 1.0): Does it explain underlying reasons or mechanisms?
- relevance (float, 0.0 to 1.0): Is it relevant to the question and topic?
- stuck_probability (float, 0.0 to 1.0): High (>= 0.7) if the learner expresses confusion, says "I don't know", or asks for help.
- misconceptions (list of str): Specific erroneous beliefs or false assumptions expressed in the answer.
- missing_concepts (list of str): Essential concepts or components omitted from the answer.
- undefined_terms (list of str): Technical jargon or terms used by the learner that were not explained or defined.
- mastered_concepts (list of str): Specific concepts the learner demonstrated clear understanding of in this turn.
- knowledge_gap (str or null): Brief description of the learner's primary understanding gap, if any.
- recommended_strategy (str): Pedagogical strategy recommendation:
  CLARIFY_TERM, CHALLENGE_MISCONCEPTION, PROBE_MISSING_CONCEPT, PROBE_HOW, PROBE_WHY, INCREASE_DIFFICULTY, or VERIFY_UNDERSTANDING.
- recommended_difficulty (int, 1 to 5): Recommended difficulty level for the next question.
"""
