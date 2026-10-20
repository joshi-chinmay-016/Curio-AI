"""
Guest AI endpoint for Curio AI.
Allows unauthenticated/guest sessions to leverage the real Groq LLM
for authentic, dynamic curious-student interactions across any topic in the world.
"""
import logging
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.ai.providers.groq_provider import GroqLLMProvider

logger = logging.getLogger("curio.api.guest_ai")

router = APIRouter(tags=["Guest AI"])
_provider: Optional[GroqLLMProvider] = None


def get_groq_provider() -> GroqLLMProvider:
    global _provider
    if _provider is None:
        _provider = GroqLLMProvider()
    return _provider


class GuestTurnRequest(BaseModel):
    topic: str
    user_answer: str
    turn_number: int = 1
    current_difficulty: int = 1
    previous_questions: List[str] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)


class GuestTurnResponse(BaseModel):
    ai_response: str
    evaluation: Dict[str, Any]
    decision: Dict[str, Any]


STUDENT_SYSTEM_PROMPT = """You are Curio, an enthusiastic, thoughtful, and inquisitive student learning from a teacher.
The user is teaching you about a topic. Your mission is to master this topic by actively learning, questioning, and resolving doubts.

YOUR STUDENT BEHAVIORS:
1. ACTIVE DOUBT & INQUIRY:
   - Listen to what the teacher explained.
   - If something isn't 100% obvious, raise a genuine student doubt:
     "Wait, why does that happen?", "Hold on, if we do that, wouldn't [X] occur?", "What prevents [Y] from breaking?"
2. CONCRETE EXAMPLES:
   - If an explanation is conceptual or abstract, ask for a concrete example, small walkthrough, or numerical scenario so you can visualize it clearly.
3. EDGE CASES & "WHAT IF":
   - Ask about boundary conditions: "What happens if the input is empty or already sorted?", "What if [unexpected situation] happens?"
4. CAUSAL REASONING & TRADE-OFFS:
   - Ask why this approach was chosen over simpler alternatives: "What are the trade-offs?", "Why do we do this instead of [alternative]?"

STRICT INVARIANTS:
- Ask strictly ONE clear question. Never include multiple question marks.
- NEVER lecture, explain, or teach the user. You are the student learning from them.
- Do NOT repeat or rephrase questions you already asked.
- Keep your tone curious, conversational, and concise (1 to 2 sentences).
- Adapt naturally to ANY topic in the universe (algorithms, biology, quantum physics, philosophy, history, software, etc.).
"""


@router.post("/ai/guest-student-turn", response_model=GuestTurnResponse)
def guest_student_turn(req: GuestTurnRequest):
    topic = req.topic.strip() or "General Topic"
    user_answer = req.user_answer.strip()
    clean_history = req.previous_questions[-6:] if req.previous_questions else []

    provider = get_groq_provider()

    # Formulate student question prompt
    history_str = "\n".join([f"- {q}" for q in clean_history]) if clean_history else "None"
    prompt = f"""Topic you are learning: {topic}

Questions you already asked previously:
{history_str}

The teacher (user) just explained:
"{user_answer}"

Turn number: {req.turn_number}
Current difficulty level: {req.current_difficulty}/5

Respond as Curio the curious student:
- React to what the teacher just explained.
- Ask strictly ONE follow-up student doubt, request for an example, or deep question.
- Never repeat any previous questions.
- Keep it natural, inquisitive, and concise (1-2 sentences)."""

    try:
        raw_response = provider.generate_text(f"{STUDENT_SYSTEM_PROMPT}\n\n{prompt}")
        ai_question = (
            raw_response.strip()
            .replace('"', '')
            .replace('Curio:', '')
            .replace('—', ' - ')
            .replace('–', ' - ')
            .replace('’', "'")
            .replace('‘', "'")
            .replace('“', '"')
            .replace('”', '"')
            .strip()
        )
        
        # Guard: Ensure exactly ONE question mark
        if ai_question.count("?") > 1:
            first_q = ai_question.split("?")[0].strip() + "?"
            ai_question = first_q

        if not ai_question.endswith("?"):
            ai_question += "?"

    except Exception as e:
        logger.warning("Groq guest generation failed (%s). Using fallback question.", e)
        ai_question = f"Wait, could you walk me through a simple concrete example of how {topic} works in practice?"

    # Basic evaluation metrics for UI feedback
    word_count = len(user_answer.split())
    correctness = 0.85 if word_count >= 5 else 0.50
    completeness = min(1.0, max(0.3, word_count / 20.0))
    depth = min(1.0, max(0.2, word_count / 15.0))
    clarity = 0.90 if word_count >= 4 else 0.60

    turn_quality = 0.30 * correctness + 0.20 * completeness + 0.15 * clarity + 0.20 * depth + 0.15

    eval_data = {
        "correctness": correctness,
        "clarity": clarity,
        "completeness": completeness,
        "depth": depth,
        "relevance": 0.95,
        "stuck_probability": 0.05,
        "misconceptions": [],
        "missing_concepts": [],
        "undefined_terms": [],
        "mastered_concepts": [topic] if turn_quality >= 0.75 else [],
        "knowledge_gap": None,
        "recommended_strategy": "PROBE_HOW",
        "recommended_difficulty": min(5, req.current_difficulty + 1) if turn_quality >= 0.80 else req.current_difficulty,
    }

    dec_data = {
        "next_mode": "STUDENT",
        "strategy": "PROBE_HOW",
        "difficulty": eval_data["recommended_difficulty"],
        "confidence": min(100, 30 + req.turn_number * 10),
        "reason": f"Curious student inquiry following up on teacher's explanation of {topic}.",
        "active_concept": topic,
        "should_offer_termination": False,
        "should_restore_interrupted_question": False,
    }

    return GuestTurnResponse(
        ai_response=ai_question,
        evaluation=eval_data,
        decision=dec_data,
    )
