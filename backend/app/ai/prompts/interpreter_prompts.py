"""
Prompt builder for semantic turn interpretation in Curio AI.
Classifies the learner's intent, identifies referenced concepts, and extracts evidence.
"""
from typing import Optional
from backend.app.ai.schemas import AIContext, CurrentQuestion, Mode


def build_turn_interpretation_prompt(
    user_message: str,
    context: Optional[AIContext] = None,
    current_question: Optional[CurrentQuestion] = None,
    current_mode: Optional[Mode] = None,
) -> str:
    topic = context.topic if context else "General Learning"
    mode_val = current_mode.value if current_mode else (context.current_mode.value if context else "STUDENT")
    
    q_content = ""
    q_concept = ""
    if current_question:
        q_content = current_question.content
        q_concept = current_question.concept
    elif context and context.current_question:
        q_content = context.current_question.content
        q_concept = context.current_question.concept

    recent_dialogue = ""
    if context and context.conversation and context.conversation.recent_messages:
        lines = []
        for m in context.conversation.recent_messages[-4:]:
            role = m.role.value if hasattr(m.role, "value") else str(m.role)
            lines.append(f"{role}: {m.content}")
        recent_dialogue = "\n".join(lines)

    return f"""You are the Turn Interpreter for Curio AI, an adaptive learning system.
Analyze the learner's latest message in the ongoing dialogue.

TOPIC: {topic}
CURRENT LEARNING MODE: {mode_val}
CURRENT QUESTION BEING ASKED: "{q_content}" (Target Concept: {q_concept})

RECENT DIALOGUE:
{recent_dialogue}

LEARNER'S LATEST MESSAGE:
"{user_message}"

TASK:
Determine what the learner intended with this message.
Select exactly ONE intent from:
1. ANSWER_ATTEMPT: The learner is attempting to answer the question or explain a mechanism/concept.
2. CLARIFICATION_REQUEST: The learner is asking what a word, prompt, or concept in the question means (e.g. "what do you mean by underlying rationale?").
3. HELP_REQUEST: The learner says they are stuck, confused, don't know, or asks to be taught/explained (e.g. "I don't know", "I'm stuck", "can you teach me?").
4. CONCEPTUAL_QUESTION: The learner is asking an inquisitive domain question about how/why something works, rather than answering or asking for question clarification.
5. ACKNOWLEDGEMENT: Simple acknowledgement or agreement without substantive evidence (e.g. "ok", "got it", "i see", "yes", "sure").
6. OFF_TOPIC: Unrelated conversational noise or greeting.
7. READY_FOR_VERIFICATION: In TEACHER mode, learner indicates they understand the explanation and are ready to be verified (e.g. "I understand now", "I'm good now", "let me try"). NOT proof of mastery!
8. UNKNOWN: Ambiguous or cannot be determined.

FIELDS TO POPULATE:
- intent: One of the enums above.
- is_answer_attempt: True only if the message attempts an answer or substantive conceptual explanation.
- is_question: True if the learner is asking any question (clarification, conceptual, or help).
- is_help_request: True if the learner is asking for help or signaling they cannot answer.
- referenced_concept: The specific topic or sub-concept mentioned by the learner (or null).
- target: What the learner is targeting (e.g. the question, a term, the teacher explanation).
- answer_evidence: The substantive claims or reasoning provided by the learner (null if no answer attempt).
- requested_action: What the learner wants Curio to do (e.g. "explain", "clarify", "verify", "continue", "none").
- confidence: Float between 0.0 and 1.0 indicating confidence in this classification.

Output strictly valid JSON conforming to the schema.
"""
