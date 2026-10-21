"""
Guest AI endpoint for Curio AI.
Provides full Groq LLM-driven generation for:
- Authentic curious-student questioning across any topic
- Teacher Mode: Explaining strictly the stuck gap with analogies, examples, and non-empty acknowledgement verification
- Dynamic Mistake Injection: Challenging mistakes as a student, and injecting subtle edge-case misconceptions on advanced turns
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
    mode: str = "STUDENT"
    gap: Optional[str] = None
    interrupted_question: Optional[Dict[str, Any]] = None
    injected_mistake: Optional[Dict[str, Any]] = None
    teacher_attempt_count: int = 1
    is_stuck_request: bool = False
    is_readiness_signal: bool = False
    is_answering_verification: bool = False
    consecutive_failures: int = 0


class GuestTurnResponse(BaseModel):
    ai_response: str
    evaluation: Dict[str, Any]
    decision: Dict[str, Any]
    injected_mistake: Optional[Dict[str, Any]] = None


STUDENT_SYSTEM_PROMPT = """You are Curio, a genuine, curious beginner student learning from a teacher (the user).
You are NOT an examiner, professor, or interviewer. You do NOT already know the answers or textbook facts.
You are learning from what the user teaches you, turn by turn, just like a real student.

YOUR CORE NATURE AS A STUDENT:
1. TABULA RASA & KNOWLEDGE HORIZON:
   - You only know what the teacher has taught you so far in this conversation.
   - You do NOT know unintroduced prerequisites, edge cases, formulas, or technical jargon.
   - NEVER introduce or ask about concepts, prerequisites, or rules the teacher has not mentioned yet!
     * For example, if the teacher says "Binary Search is an algorithm used to find an element in an array", you DO NOT know that the array must be sorted! You only know it searches an array. Your natural doubt is: "Wait, how does it actually find the element? Does it check them one by one, or what does it do?"
2. REAL-TIME DETERMINISTIC QUESTIONING:
   - Formulate your question directly and strictly based on what the teacher JUST explained:
     * If they just gave the basic definition/purpose -> Ask HOW it actually works step-by-step under the hood.
     * If they just explained the steps/mechanism -> Raise a genuine beginner doubt about that mechanism (e.g. "Wait, how can you just throw away half? How do we know the element isn't in that half?"), which naturally drives the teacher to explain the prerequisite!
     * If they just introduced a rule or prerequisite -> Ask what happens if that rule is broken (e.g. "Wait, so does it only work if it's sorted? What happens if someone gives it an unsorted list?").
     * If the concept is clear -> Ask for a small concrete example with real values to picture the steps in action.
     * If an example was walked through -> Ask about edge cases and boundary limits (e.g. what if the item isn't in the list at all, or the list is empty or has duplicates?).
     * If edge cases are covered -> Ask about performance scaling and trade-offs compared to alternatives.
3. CONVERSATIONAL & PROPER STUDENT QUESTIONING:
   - Ask thoughtful, descriptive questions that sound like an authentic, curious student (2 to 4 sentences):
     * Briefly reflect what you understood from what the teacher just taught you.
     * Voice your specific doubt, confusion, or what you are struggling to picture or understand.
     * Ask the teacher to explain descriptively in simple, understandable terms or clarify with a concrete walkthrough.
   - Strictly ONE question mark '?' at the very end of your response.
   - Do NOT ask dry, one-line quiz queries! Ask like an engaged human student actively learning.
   - NEVER lecture, summarize, or reveal answers. You are the student learning from the teacher!
   - Adapt naturally to ANY topic in the universe."""

TEACHER_SYSTEM_PROMPT = """You are Curio in Teacher Mode — the world's most gifted, intuitive, and pedagogical teacher.
The student (user) got stuck on a specific gap or prerequisite in this topic.

CORE TEACHER INVARIANTS:
1. EXPLAIN ONLY THE SPECIFIC GAP:
   - Explain strictly the specific part where the student was stuck.
   - Do NOT re-explain the entire topic or give a wall of theory.
2. VIVID REAL-WORLD ANALOGY:
   - Provide an unforgettable, intuitive real-world analogy for why this specific mechanism or rule works.
3. CONCRETE MICRO-EXAMPLE:
   - Walk through a 2-3 step micro-example illustrating the mechanism in action.
4. CLOSING:
   - Ask if this clarifies the specific doubt, and tell them: "When you feel ready to teach again, let me know and we'll do a quick verification!"
"""


def clean_text(text: str) -> str:
    return (
        text.strip()
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


def is_too_similar_to_history(candidate: str, history: List[str]) -> bool:
    if not history:
        return False
    c_norm = re.sub(r'[^a-z0-9 ]', '', candidate.lower()).strip()
    if not c_norm:
        return True
    c_words = set(c_norm.split())
    for prev in history:
        p_norm = re.sub(r'[^a-z0-9 ]', '', prev.lower()).strip()
        if not p_norm:
            continue
        if c_norm == p_norm:
            return True
        if len(c_norm) > 20 and len(p_norm) > 20 and (c_norm in p_norm or p_norm in c_norm):
            return True
        p_words = set(p_norm.split())
        overlap = len(c_words.intersection(p_words))
        total = len(c_words.union(p_words))
        if total > 0 and (overlap / total) >= 0.35:
            return True
    return False


@router.post("/ai/guest-student-turn", response_model=GuestTurnResponse)
def guest_student_turn(req: GuestTurnRequest):
    topic = req.topic.strip() or "General Topic"
    user_answer = req.user_answer.strip()
    clean_history = req.previous_questions[-6:] if req.previous_questions else []
    history_str = "\n".join([f"- {q}" for q in clean_history]) if clean_history else "None"
    provider = get_groq_provider()

    current_mode = req.mode.upper()
    current_gap = req.gap or f"{topic} core mechanism"
    interrupted_q_content = req.interrupted_question.get("content") if req.interrupted_question else f"Now, how does {topic} execute in practice?"

    is_explicit_stuck = req.is_stuck_request or any(phrase in user_answer.lower() for phrase in [
        "i'm stuck", "im stuck", "i am stuck", "can you teach me", "teach me", "can you explain", "don't know", "dont know", "help me"
    ])

    # =========================================================================
    # 1. TEACHER MODE HANDLING
    # =========================================================================
    if current_mode == "TEACHER" or is_explicit_stuck:
        # Case A: User gives readiness signal ("I understand", "Got it", "Let me teach")
        # NEVER accept empty acknowledgements without verification!
        if req.is_readiness_signal and not is_explicit_stuck:
            verify_prompt = f"""You are Curio in Teacher Mode.
Topic: {topic}
The learner was stuck on this gap: "{current_gap}".
The learner just stated they understand: "{user_answer}".

Pose ONE targeted, concrete verification problem or micro-example on "{current_gap}".
Ask the learner to answer or solve it so they prove genuine understanding before returning to Student Mode.
Keep it friendly, concise, and encourage them to show their reasoning."""
            try:
                raw_v = provider.generate_text(verify_prompt)
                ai_text = clean_text(raw_v)
            except Exception as e:
                logger.warning("Groq verification prompt generation failed (%s)", e)
                ai_text = f"Awesome! To make sure we've locked this in before returning to student mode:\n\nIn your own words, how does the core mechanism of {current_gap} work in practice?"

            return GuestTurnResponse(
                ai_response=ai_text,
                evaluation={
                    "correctness": 0.5,
                    "clarity": 0.9,
                    "completeness": 0.4,
                    "depth": 0.3,
                    "relevance": 0.95,
                    "stuck_probability": 0.1,
                    "misconceptions": [],
                    "missing_concepts": [current_gap],
                    "undefined_terms": [],
                    "mastered_concepts": [],
                    "knowledge_gap": current_gap,
                    "recommended_strategy": "VERIFY_UNDERSTANDING",
                    "recommended_difficulty": req.current_difficulty,
                },
                decision={
                    "next_mode": "TEACHER",
                    "strategy": "VERIFY_UNDERSTANDING",
                    "difficulty": req.current_difficulty,
                    "confidence": 50,
                    "reason": f"Learner indicated readiness. Posing verification question on gap '{current_gap}'.",
                    "active_concept": current_gap,
                    "should_offer_termination": False,
                    "should_restore_interrupted_question": False,
                },
            )

        # Case B: User answers verification question
        if req.is_answering_verification:
            eval_prompt = f"""You are an expert pedagogy evaluator.
Topic: {topic}
Gap being verified: "{current_gap}"
Learner's verification answer:
"{user_answer}"

Evaluate if the learner has demonstrated a sound conceptual grasp of "{current_gap}".
Reply in exact format:
VERDICT: PASS or FAIL
REASON: <one sentence explanation>"""
            verdict = "PASS"
            reason = "Demonstrated clear understanding of the gap."
            try:
                raw_eval = provider.generate_text(eval_prompt)
                if "VERDICT: FAIL" in raw_eval.upper():
                    verdict = "FAIL"
                if "REASON:" in raw_eval:
                    reason = raw_eval.split("REASON:")[1].strip()
            except Exception as e:
                logger.warning("Groq evaluation failed (%s)", e)
                verdict = "PASS" if len(user_answer.split()) >= 4 else "FAIL"

            if verdict == "PASS":
                # PASS: Toggle back to STUDENT MODE and restore interrupted question!
                restore_text = f"Spot on! {reason}\n\nNow let's switch back to student mode and pick up right where you got stuck:\n\n{interrupted_q_content}"
                return GuestTurnResponse(
                    ai_response=restore_text,
                    evaluation={
                        "correctness": 0.95,
                        "clarity": 0.9,
                        "completeness": 0.9,
                        "depth": 0.85,
                        "relevance": 1.0,
                        "stuck_probability": 0.05,
                        "misconceptions": [],
                        "missing_concepts": [],
                        "undefined_terms": [],
                        "mastered_concepts": [current_gap],
                        "knowledge_gap": None,
                        "recommended_strategy": "RESTORE_INTERRUPTED_QUESTION",
                        "recommended_difficulty": req.current_difficulty,
                    },
                    decision={
                        "next_mode": "STUDENT",
                        "strategy": "RESTORE_INTERRUPTED_QUESTION",
                        "difficulty": req.current_difficulty,
                        "confidence": 75,
                        "reason": f"Learner verified understanding of '{current_gap}'. Restoring interrupted question.",
                        "active_concept": topic,
                        "should_offer_termination": False,
                        "should_restore_interrupted_question": True,
                    },
                )
            else:
                # FAIL: Stay in TEACHER MODE and provide adapted explanation
                next_attempt = req.teacher_attempt_count + 1
                adapt_prompt = f"""You are Curio in Teacher Mode.
Topic: {topic}
Gap: "{current_gap}"
Learner's answer was incorrect or incomplete: "{user_answer}".
This is Attempt {next_attempt}/3.

Provide an adapted pedagogical explanation:
- Gently clarify the exact mistake in their answer.
- Give a simpler intuitive analogy or a step-by-step trace.
- End with a new, simpler verification question."""
                try:
                    raw_adapt = provider.generate_text(adapt_prompt)
                    ai_text = clean_text(raw_adapt)
                except Exception as e:
                    logger.warning("Groq adapted explanation failed (%s)", e)
                    ai_text = f"Let's look at {current_gap} from another angle with a simple step-by-step example:\n\nCould you tell me what happens during the very first step of {current_gap}?"

                return GuestTurnResponse(
                    ai_response=ai_text,
                    evaluation={
                        "correctness": 0.2,
                        "clarity": 0.5,
                        "completeness": 0.2,
                        "depth": 0.1,
                        "relevance": 0.8,
                        "stuck_probability": 0.7,
                        "misconceptions": [f"Unresolved {current_gap}"],
                        "missing_concepts": [current_gap],
                        "undefined_terms": [],
                        "mastered_concepts": [],
                        "knowledge_gap": current_gap,
                        "recommended_strategy": "TEACH_GAP",
                        "recommended_difficulty": req.current_difficulty,
                    },
                    decision={
                        "next_mode": "TEACHER",
                        "strategy": "TEACH_GAP",
                        "difficulty": req.current_difficulty,
                        "confidence": 40,
                        "reason": f"Verification failed. Adapting explanation for gap '{current_gap}'.",
                        "active_concept": current_gap,
                        "should_offer_termination": False,
                        "should_restore_interrupted_question": False,
                    },
                )

        # Case C: Initial Teacher Mode entry (Learner clicked I'm Stuck or asked for teaching)
        # Explain strictly the specific gap, not the entire topic!
        teach_prompt = f"""{TEACHER_SYSTEM_PROMPT}

Topic: {topic}
Specific gap where student was stuck: "{current_gap}"
Learner's statement: "{user_answer}"

Generate a master teacher explanation of strictly "{current_gap}":
1. Intuitive breakdown of why this specific part exists and how it works.
2. Vivid real-world analogy.
3. Simple 2-3 step micro-example.
4. Closing: "Does this clear up why {current_gap} works this way? When you feel ready to teach again, let me know and we'll do a quick verification!"
"""
        try:
            raw_t = provider.generate_text(teach_prompt)
            ai_text = clean_text(raw_t)
        except Exception as e:
            logger.warning("Groq teacher explanation failed (%s)", e)
            ai_text = f"Let's focus on the exact mechanism of **{current_gap}** in **{topic}**.\n\nThink of it with a simple analogy: before we can look something up efficiently, the underlying foundation must be organized in order. In practice, each step narrows down the possibilities until you find the exact result.\n\nDoes this clear up why {current_gap} works this way? When you're ready, let me know and we'll verify it!"

        return GuestTurnResponse(
            ai_response=ai_text,
            evaluation={
                "correctness": 0.3,
                "clarity": 0.8,
                "completeness": 0.2,
                "depth": 0.2,
                "relevance": 0.95,
                "stuck_probability": 0.9,
                "misconceptions": [],
                "missing_concepts": [current_gap],
                "undefined_terms": [],
                "mastered_concepts": [],
                "knowledge_gap": current_gap,
                "recommended_strategy": "TEACH_GAP",
                "recommended_difficulty": req.current_difficulty,
            },
            decision={
                "next_mode": "TEACHER",
                "strategy": "TEACH_GAP",
                "difficulty": req.current_difficulty,
                "confidence": 45,
                "reason": f"Explaining specific gap '{current_gap}' in Teacher Mode.",
                "active_concept": current_gap,
                "should_offer_termination": False,
                "should_restore_interrupted_question": False,
            },
        )

    # =========================================================================
    # 2. STUDENT MODE HANDLING (With Dynamic Mistake Injection & Challenge)
    # =========================================================================
    # Evaluate learner's answer
    word_count = len(user_answer.split())
    has_mistake = False
    misconception_desc = ""

    # Check if user previously had an injected mistake active
    if req.injected_mistake and req.injected_mistake.get("active"):
        inj_concept = req.injected_mistake.get("concept", topic)
        inj_mistake = req.injected_mistake.get("misconception", "")

        eval_inj_prompt = f"""The student (Curio) intentionally asked a tricky edge-case question containing a subtle misconception:
"{inj_mistake}"

The teacher (user) answered:
"{user_answer}"

Did the user catch and correct the subtle mistake, or did they agree with / miss the mistake?
Reply in exact format:
VERDICT: CAUGHT or MISSED
EXPLANATION: <one sentence>"""
        try:
            res_inj = provider.generate_text(eval_inj_prompt)
            is_caught = "VERDICT: CAUGHT" in res_inj.upper()
        except Exception:
            is_caught = any(w in user_answer.lower() for w in ["no", "not", "false", "incorrect", "actually", "doesn't", "wrong", "cannot", "careful"])

        if is_caught:
            # Praise the user enthusiastically as an enlightened student!
            praise_prompt = f"""You are Curio, an inquisitive student learning {topic}.
You previously proposed this subtle misconception: "{inj_mistake}".
The teacher brilliantly caught it and explained: "{user_answer}".

Respond enthusiastically:
- Praise them for catching that subtle edge case.
- State what you learned from their correction in 1 sentence.
- Ask strictly ONE follow-up student question diving deeper into the next mechanism or trade-off."""
            try:
                praise_resp = provider.generate_text(f"{STUDENT_SYSTEM_PROMPT}\n\n{praise_prompt}")
                praise_q = clean_text(praise_resp)
                if not praise_q.endswith("?"):
                    praise_q += "?"
            except Exception:
                praise_q = f"Whoa, great catch! You're totally right about that subtle edge case. So how does {topic} handle that scenario in practice?"

            return GuestTurnResponse(
                ai_response=praise_q,
                evaluation={
                    "correctness": 0.98,
                    "clarity": 0.95,
                    "completeness": 0.95,
                    "depth": 0.90,
                    "relevance": 1.0,
                    "stuck_probability": 0.05,
                    "misconceptions": [],
                    "missing_concepts": [],
                    "undefined_terms": [],
                    "mastered_concepts": [inj_concept],
                    "knowledge_gap": None,
                    "recommended_strategy": "DEPTH_EXPANSION",
                    "recommended_difficulty": min(5, req.current_difficulty + 1),
                },
                decision={
                    "next_mode": "STUDENT",
                    "strategy": "DEPTH_EXPANSION",
                    "difficulty": min(5, req.current_difficulty + 1),
                    "confidence": min(100, 70 + req.turn_number * 5),
                    "reason": f"Learner brilliantly caught injected subtle misconception on '{inj_concept}'.",
                    "active_concept": inj_concept,
                    "should_offer_termination": False,
                    "should_restore_interrupted_question": False,
                },
                injected_mistake=None,
            )

    # Check if user made an explicit factual error or mistake in their explanation
    eval_user_prompt = f"""You are an educational evaluator for {topic}.
The student asked a question, and the user explained:
"{user_answer}"

Evaluate whether this explanation contains an EXPLICIT FACTUAL ERROR or FALSE CLAIM (e.g., claiming an algorithm works on arbitrary unsorted data, asserting a backward formula, or stating an incorrect time complexity).
CRITICAL: A brief, high-level, or introductory definition (e.g., stating the general purpose on turn 1 without listing all prerequisites or mechanisms yet) is SOUND and must NOT be marked as a misconception! Do NOT penalize omissions, brevity, or missing prerequisites as misconceptions.

Reply in exact format:
SOUND: YES or NO
MISCONCEPTION: <description of EXPLICIT false statement if NO, or NONE>"""
    try:
        eval_res = provider.generate_text(eval_user_prompt)
        if "SOUND: NO" in eval_res.upper():
            has_mistake = True
            if "MISCONCEPTION:" in eval_res:
                misconception_desc = eval_res.split("MISCONCEPTION:")[1].strip()
    except Exception:
        has_mistake = False

    # USER MADE A MISTAKE:
    # Rule: If this is the FIRST time the mistake occurs (consecutive_failures == 0):
    # DO NOT TOGGLE TO TEACHER MODE! Challenge the mistake like a student!
    if has_mistake and req.consecutive_failures < 1:
        challenge_prompt = f"""You are Curio, an inquisitive student learning {topic}.
The user just explained:
"{user_answer}"
You noticed an inconsistency or error: "{misconception_desc}".

Do NOT act like a teacher. As a curious student, ask strictly ONE question pointing out the confusion or doubt:
"Wait, hold on — if [X], wouldn't [Y] happen? How does that work?"
Keep it genuine, polite, and exactly ONE question."""
        try:
            raw_c = provider.generate_text(f"{STUDENT_SYSTEM_PROMPT}\n\n{challenge_prompt}")
            ai_question = clean_text(raw_c)
            if not ai_question.endswith("?"):
                ai_question += "?"
        except Exception:
            ai_question = f"Wait, hold on — if that's the case, wouldn't that cause unexpected behavior in edge cases? Can you help me understand how that works?"

        return GuestTurnResponse(
            ai_response=ai_question,
            evaluation={
                "correctness": 0.45,
                "clarity": 0.7,
                "completeness": 0.4,
                "depth": 0.3,
                "relevance": 0.9,
                "stuck_probability": 0.25,
                "misconceptions": [misconception_desc or f"Mistake in {topic}"],
                "missing_concepts": [],
                "undefined_terms": [],
                "mastered_concepts": [],
                "knowledge_gap": misconception_desc or topic,
                "recommended_strategy": "CHALLENGE_MISCONCEPTION",
                "recommended_difficulty": req.current_difficulty,
            },
            decision={
                "next_mode": "STUDENT",
                "strategy": "CHALLENGE_MISCONCEPTION",
                "difficulty": req.current_difficulty,
                "confidence": max(10, 50 - req.consecutive_failures * 10),
                "reason": f"Misconception detected: '{misconception_desc}'. Challenging as a student to give user a chance to rectify.",
                "active_concept": misconception_desc or topic,
                "should_offer_termination": False,
                "should_restore_interrupted_question": False,
            },
        )

    # USER PERSISTED IN MISTAKE (consecutive_failures >= 1):
    # Now toggle to TEACHER MODE to explain the gap!
    if has_mistake and req.consecutive_failures >= 1:
        teach_gap = misconception_desc or f"{topic} core mechanism"
        teach_prompt = f"""{TEACHER_SYSTEM_PROMPT}

Topic: {topic}
Gap where student is stuck: "{teach_gap}"
Learner's repeated misconception: "{user_answer}"

Generate a master teacher explanation:
1. Explain strictly "{teach_gap}" (not the whole topic).
2. Vivid real-world analogy.
3. Simple 2-3 step micro-example.
4. Closing: ask if this clears it up, and ask them to let you know when they are ready to verify it."""
        try:
            raw_t = provider.generate_text(teach_prompt)
            ai_text = clean_text(raw_t)
        except Exception:
            ai_text = f"Let's pause the questions for a moment and look at **{teach_gap}**.\n\nThink of it like this: if the foundational invariant isn't satisfied, the mechanism cannot guarantee the right output.\n\nDoes this clear up why {teach_gap} works this way? Whenever you're ready, let me know and we'll verify it!"

        return GuestTurnResponse(
            ai_response=ai_text,
            evaluation={
                "correctness": 0.25,
                "clarity": 0.6,
                "completeness": 0.2,
                "depth": 0.1,
                "relevance": 0.85,
                "stuck_probability": 0.8,
                "misconceptions": [teach_gap],
                "missing_concepts": [teach_gap],
                "undefined_terms": [],
                "mastered_concepts": [],
                "knowledge_gap": teach_gap,
                "recommended_strategy": "TEACH_GAP",
                "recommended_difficulty": max(1, req.current_difficulty - 1),
            },
            decision={
                "next_mode": "TEACHER",
                "strategy": "TEACH_GAP",
                "difficulty": max(1, req.current_difficulty - 1),
                "confidence": 35,
                "reason": f"Misconception persisted across turns. Transitioning to Teacher Mode to explain gap: {teach_gap}.",
                "active_concept": teach_gap,
                "should_offer_termination": False,
                "should_restore_interrupted_question": False,
            },
        )

    # PROACTIVE DYNAMIC MISTAKE INJECTION:
    # Trigger on advanced turns (difficulty >= 3 or turn >= 3, and strong answer) ~20% of the time
    should_inject_mistake = (
        req.current_difficulty >= 3
        and word_count >= 6
        and req.turn_number >= 3
        and (req.turn_number % 3 == 0)
        and not has_mistake
    )

    if should_inject_mistake:
        inject_prompt = f"""You are Curio, an inquisitive student learning {topic}.
The teacher (user) just explained:
"{user_answer}"

Intentionally propose ONE subtle, plausible student misconception or tricky edge-case question to test if the teacher catches it!
Requirements:
- Sound like a curious student having a doubt about an edge case: acknowledge what they taught, express your doubt, and ask for clarification.
- It must be plausible and tricky, but factually false or an invalid assumption.
- Exactly ONE question mark at the end (2-3 sentences)."""
        try:
            raw_inj = provider.generate_text(f"{STUDENT_SYSTEM_PROMPT}\n\n{inject_prompt}")
            ai_question = clean_text(raw_inj)
            if not ai_question.endswith("?"):
                ai_question += "?"
        except Exception:
            ai_question = f"Wait, so if the input is already partially ordered, does {topic} always run in best-case time complexity, right?"

        injected_meta = {
            "active": True,
            "turn": req.turn_number,
            "misconception": ai_question,
            "concept": topic,
            "counter_reason": "Edge case where the assumption fails.",
        }

        return GuestTurnResponse(
            ai_response=ai_question,
            evaluation={
                "correctness": 0.90,
                "clarity": 0.90,
                "completeness": 0.85,
                "depth": 0.80,
                "relevance": 0.95,
                "stuck_probability": 0.05,
                "misconceptions": [],
                "missing_concepts": [],
                "undefined_terms": [],
                "mastered_concepts": [topic],
                "knowledge_gap": None,
                "recommended_strategy": "TEST_EDGE_CASE",
                "recommended_difficulty": req.current_difficulty,
            },
            decision={
                "next_mode": "STUDENT",
                "strategy": "TEST_EDGE_CASE",
                "difficulty": req.current_difficulty,
                "confidence": min(100, 50 + req.turn_number * 8),
                "reason": f"Proactively injecting subtle edge-case misconception to test deep understanding of {topic}.",
                "active_concept": topic,
                "should_offer_termination": False,
                "should_restore_interrupted_question": False,
            },
            injected_mistake=injected_meta,
        )

    # Progressive Pedagogical Stages (Tabula Rasa student learning naturally based strictly on what teacher taught)
    lower_ans = user_answer.lower()
    all_past_text = " ".join([m.get("content", "") if isinstance(m, dict) else str(m) for m in req.previous_questions] + [user_answer]).lower()

    # Did the teacher explain how it works / steps / mechanism?
    has_mechanism = any(k in all_past_text for k in [
        "half", "halv", "divid", "split", "mid", "middle", "compar", "check", 
        "pivot", "pointer", "move", "pass", "recurs", "loop", "left", "right", "swap", 
        "step", "first", "then", "after", "look at", "convert", "transform", "produce",
        "absorb", "react", "bind", "transfer", "occur", "cause", "work by", "process",
        "cycle", "stage", "chain", "flow", "execute", "function", "operat", "pathway"
    ])
    # Did the teacher explain prerequisites / requirements / invariants / conditions?
    has_prereq = any(k in all_past_text for k in [
        "sort", "order", "prereq", "invariant", "requir", "must be", "assum", "condition",
        "depend", "need", "substrate", "light", "water", "temperature", "membrane",
        "presence of", "before", "input", "start with", "environment", "rule"
    ])
    # Did the teacher give a concrete example / walkthrough?
    has_example = any(k in all_past_text for k in [
        "example", "instance", "suppose", "say we", "for example", "consider",
        "such as", "walkthrough", "case where", "like a", "imagine"
    ]) or re.search(r'\b\d+\b', all_past_text) is not None
    # Did the teacher cover edge cases / limits / failures?
    has_edge = any(k in all_past_text for k in [
        "empty", "not found", "duplicate", "null", "missing", "zero", "single",
        "boundary", "worst case", "infinite", "-1", "cross", "fail", "break",
        "without", "lack", "deprive", "excess", "dark", "night", "limit", "overflow", "drought"
    ])

    if not has_mechanism:
        # Teacher ONLY gave definition or purpose:
        stage_desc = (
            "STAGE 1 (Definition/Purpose provided): The teacher stated what the concept is or what problem it solves. "
            "You DO NOT know the internal mechanics, steps, or prerequisites yet. "
            "Ask HOW it actually works step-by-step or what the initial mechanism is to make that happen. "
            "CRITICAL: DO NOT assume, mention, or leak unintroduced prerequisites, advanced terminology, or parameters!"
        )
        current_strategy = "PROBE_HOW"
        current_difficulty = 1
    elif not has_prereq:
        # Teacher explained the mechanism, but NOT prerequisites/conditions:
        stage_desc = (
            "STAGE 2 (Mechanism Doubts): The teacher described the steps or core process. "
            "Raise a genuine beginner doubt about THAT specific step (e.g. how does it decide which path to take, "
            "or why does that specific reaction/operation take place?). "
            "CRITICAL: Do NOT guess unmentioned prerequisites. Let your doubt naturally lead the teacher to introduce required conditions."
        )
        current_strategy = "PROBE_WHY"
        current_difficulty = 2
    elif not has_example:
        # Teacher introduced the prerequisite/rule:
        stage_desc = (
            "STAGE 3 (Prerequisite Understood -> Request Example): The teacher explained the requirement, condition, or rule. "
            "Ask for a small concrete example, scenario, or walkthrough so you can trace the steps in action."
        )
        current_strategy = "REQUEST_EXAMPLE"
        current_difficulty = 3
    elif not has_edge:
        # Walkthrough clear:
        stage_desc = (
            "STAGE 4 (Walkthrough Clear -> Edge Cases): The normal flow is clear. "
            "Ask about tricky edge cases, boundary limits, missing inputs, extreme conditions, or what happens when things fail."
        )
        current_strategy = "TEST_EDGE_CASE"
        current_difficulty = 4
    else:
        # Edge cases covered:
        stage_desc = (
            "STAGE 5 (Synthesis & Trade-offs): Edge cases and mechanisms are covered. "
            "Ask about efficiency, scaling, bottlenecks, limitations, or trade-offs compared to alternative approaches."
        )
        current_strategy = "CONNECT_CONCEPTS"
        current_difficulty = 5

    prompt = f"""Topic you are learning: {topic}

Questions you already asked previously:
{history_str}

The teacher (user) just explained:
"{user_answer}"

Current turn: {req.turn_number}
Pedagogical guidance: {stage_desc}

You are Curio, an innocent, humble beginner student learning this topic for the very first time. You know NOTHING other than what the teacher just said.
CRITICAL INSTRUCTIONS:
1. PURE STUDENT VOICE: You are NOT an examiner or teacher. NEVER ask leading pop-quiz questions like "Does it require X?", "Is it arranged in any particular way?", or "What condition is needed?". You have no idea what conditions or arrangements exist!
2. PROPER DESCRIPTIVE STUDENT QUESTION (2 TO 4 SENTENCES):
   - First, briefly reflect what you understood so far from the teacher's explanation.
   - Next, express your genuine doubt, confusion, or what you are struggling to picture or understand.
   - Then, ask the teacher to explain descriptively in simple, understandable terms, clarify the mechanism, or walk through a concrete example.
   - Avoid dry, one-line queries. Formulate an engaged, descriptive question just like a real student.
3. ZERO LEAKAGE: Never mention terms, prerequisites, or rules that the teacher has NOT mentioned yet!
4. Exactly ONE question mark '?' at the very end of your entire response. Preceding sentences must be declarative reflections or doubts.
5. Never repeat or rephrase any previous questions from history: {history_str}"""

    try:
        raw_response = provider.generate_text(f"{STUDENT_SYSTEM_PROMPT}\n\n{prompt}")
        ai_question = clean_text(raw_response)
        if ai_question.count("?") > 1:
            first_q = ai_question.split("?")[0].strip() + "?"
            ai_question = first_q
        if not ai_question.endswith("?"):
            ai_question += "?"
    except Exception as e:
        logger.warning("Groq guest generation failed (%s). Using fallback question.", e)
        ai_question = f"I think I understand the general purpose so far, but I'm having trouble visualizing the mechanism. Could you walk me through how {topic} actually works step by step from the beginning?"

    # HARD PROGRAMMATIC TABULA RASA & ANTI-EXAMINER GUARD:
    # 1. If teacher has not explained mechanism, AI must NOT ask about ordering, arrangement, prerequisites, or conditions:
    leading_prereq_terms = [
        "sorted", "sort", "order", "ordered", "arranged", "arrange",
        "condition", "prerequisite", "prereq", "particular way", "format", "organized"
    ]
    has_teacher_mentioned_prereq = any(w in all_past_text for w in ["sorted", "sort", "order", "arranged", "condition", "prerequisite"])
    
    if not has_mechanism and any(w in ai_question.lower() for w in leading_prereq_terms):
        logger.warning("Intercepted leading prerequisite question '%s'. Enforcing genuine beginner student doubt.", ai_question)
        ai_question = f"I understand what {topic} is used for, but I'm having trouble picturing how it actually works under the hood. Could you explain what happens first and walk me through the step-by-step process?"

    elif not has_teacher_mentioned_prereq and any(w in ai_question.lower() for w in ["sorted", "sort", "ordered", "arranged in"]):
        logger.warning("Intercepted leaked prerequisite 'sorted/arranged' before teacher introduced it. Replacing.")
        ai_question = f"I follow the main idea on paper, but I'm having trouble picturing it with real values. Could you walk me through a small, concrete example so I can clearly see how {topic} works in action?"

    # STRICT ANTI-REPETITION ENFORCEMENT
    if is_too_similar_to_history(ai_question, req.previous_questions):
        logger.info("Generated question is too similar to past questions. Attempting alternative.")
        retry_prompt = f"""You already asked questions too similar to: "{ai_question}".
Never repeat previous questions! Ask a completely DIFFERENT beginner student question about {topic} asking the teacher to explain: {stage_desc}.
Remember: sound like an innocent student who wants to understand. Strictly ONE question mark."""
        try:
            raw_retry = provider.generate_text(f"{STUDENT_SYSTEM_PROMPT}\n\n{retry_prompt}")
            ai_retry = clean_text(raw_retry)
            if ai_retry.count("?") > 1:
                ai_retry = ai_retry.split("?")[0].strip() + "?"
            if not ai_retry.endswith("?"):
                ai_retry += "?"
            if not is_too_similar_to_history(ai_retry, req.previous_questions):
                ai_question = ai_retry
        except Exception:
            pass

    # If still repeating, pick a guaranteed novel question from the universal pool
    if is_too_similar_to_history(ai_question, req.previous_questions):
        universal_pool = [
            f"I think I follow the general idea so far, but I'm having trouble visualizing the mechanism. Could you walk me through how {topic} actually works step-by-step under the hood?",
            f"I understand the theory on paper, but I learn best from concrete illustrations. Could you walk me through a simple, descriptive example so I can picture how {topic} works in practice?",
            f"I see how the process runs, but does {topic} require certain conditions or setup before starting? What happens if someone tries to run it without meeting those requirements?",
            f"I understand how it works on a small scale, but I'm curious about performance. How does {topic} scale as the workload grows, and what are its biggest resource bottlenecks?",
            f"I feel like I grasp the standard path, but I want to be prepared for tricky situations. What edge cases, boundary conditions, or failure modes should we watch out for in {topic}?",
            f"Now that I understand how {topic} operates, what are its biggest trade-offs or limitations compared to alternative approaches?",
            f"Hold on, I want to make sure I don't form the wrong mental model. What is the single biggest pitfall or misconception people have when working with {topic}?",
            f"Under what specific circumstances would you recommend NOT using {topic}, and what would you use instead?",
        ]
        for cand in universal_pool:
            if not is_too_similar_to_history(cand, req.previous_questions):
                ai_question = cand
                break

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
        "mastered_concepts": [topic] if (req.turn_number >= 5 and turn_quality >= 0.85) else [],
        "knowledge_gap": None,
        "recommended_strategy": current_strategy,
        "recommended_difficulty": current_difficulty,
    }

    dec_data = {
        "next_mode": "STUDENT",
        "strategy": current_strategy,
        "difficulty": current_difficulty,
        "confidence": min(100, 30 + req.turn_number * 12),
        "reason": f"Curious student inquiry following up on teacher's explanation at {stage_desc.split(':')[0]}.",
        "active_concept": topic,
        "should_offer_termination": False,
        "should_restore_interrupted_question": False,
    }

    return GuestTurnResponse(
        ai_response=ai_question,
        evaluation=eval_data,
        decision=dec_data,
        injected_mistake=None,
    )
