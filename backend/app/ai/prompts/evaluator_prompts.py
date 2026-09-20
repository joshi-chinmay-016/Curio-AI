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


def build_session_evaluation_prompt(evidence: "SessionEvidence") -> str:
    """
    Constructs the prompt for qualitative session evaluation synthesis.
    Instructs the LLM to synthesize strengths, gap nuances, and roadmap recommendations
    STRICTLY grounded in the provided structured evidence.
    """
    turns_summary = []
    for t in evidence.turns:
        turns_summary.append(
            f"Turn {t.turn_index} [Concept: {t.concept}, Diff: {t.difficulty}]:\n"
            f"  Question: {t.question}\n"
            f"  Learner Answer: {t.learner_answer}\n"
            f"  Evaluation: correctness={t.evaluation.correctness}, stuck={t.evaluation.stuck_probability}, "
            f"gaps={t.evaluation.knowledge_gap}, misc={t.evaluation.misconceptions}"
        )

    teacher_summary = []
    for ti in evidence.teacher_interventions:
        teacher_summary.append(
            f"Intervention {ti.intervention_index} [Attempt {ti.attempt_count}, Concept: {ti.related_concept}]:\n"
            f"  Gap: {ti.gap}\n"
            f"  Verification Passed: {ti.verification_passed}\n"
            f"  Verification Answer: {ti.verification_answer}"
        )

    return f"""You are an expert pedagogical session evaluator assessing a complete learning session.
Topic: {evidence.topic}
Total Learner Turns: {evidence.total_learner_turns}
Successful Turns: {evidence.successful_turns}
Failed Turns: {evidence.failed_turns}
Concepts Encountered: {', '.join(evidence.concepts_encountered) if evidence.concepts_encountered else 'None'}

Session Turns:
{chr(10).join(turns_summary) if turns_summary else 'No evaluated turns.'}

Teacher Interventions:
{chr(10).join(teacher_summary) if teacher_summary else 'None.'}

Instructions:
1. Evaluate ONLY the supplied evidence. Do NOT hallucinate concepts, gaps, or answers.
2. Distinguish resolved vs unresolved gaps and misconceptions.
3. If evidence is minimal or insufficient, acknowledge it clearly.
4. Produce structured recommendations and roadmap items that are highly specific to the actual gaps observed.
"""

