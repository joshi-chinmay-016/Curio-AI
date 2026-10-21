"""
Dynamic Mistake Injection Engine for Curio AI.
Implements pedagogical mistake induction with independent verification,
strict demonstrated-understanding gating, 3-way response evaluation
(CAUGHT / MISSED / INCONCLUSIVE), and calibrated mastery protection.
"""
import json
import logging
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("curio.ai.mistake_injection")


class MistakeCandidate(BaseModel):
    """A generated candidate subtle mistake with pedagogical rationale."""
    concept: str
    claim: str = Field(description="The exact subtle false premise or misconception")
    why_false: str = Field(description="The factual counter-reason explaining why the claim is invalid")
    student_question: str = Field(description="Natural 2-3 sentence student question expressing doubt about this claim")


class MistakeVerificationResult(BaseModel):
    """Result of the independent verification pass on a candidate mistake."""
    is_valid: bool = Field(description="True if the claim is unequivocally false, subtle, plausible, and solvable")
    reasoning: str = Field(description="Verification reasoning assessing correctness and safety")


class MistakeEvaluationVerdict(BaseModel):
    """Authoritative evaluation of the learner's response to an injected mistake."""
    verdict: Literal["CAUGHT", "MISSED", "INCONCLUSIVE"]
    explanation: str = Field(description="Why this verdict was reached based on learner's exact words")
    evidence: str = Field(description="Specific phrases or evidence from learner's response")


class InjectedMistakeState(BaseModel):
    """Complete persistent lifecycle state of an injected mistake across turns."""
    active: bool = True
    turn: int
    concept: str
    claim: str
    why_false: str
    question: str
    verified: bool = True
    status: Literal["PENDING", "CAUGHT", "MISSED", "INCONCLUSIVE"] = "PENDING"


class MistakeInjectionEngine:
    """
    Orchestrates the complete lifecycle of Curio's Dynamic Mistake Injection:
    1. Gating & Eligibility
    2. Candidate Generation
    3. Independent Verification
    4. 3-Way Learner Evaluation
    5. Calibrated Mastery Updates
    """

    def __init__(self, provider: Any = None):
        self.provider = provider

    def check_eligibility(
        self,
        mode: str,
        current_difficulty: int,
        turn_number: int,
        last_injected_turn: Optional[int],
        correctness: float,
        completeness: float,
        has_unresolved_misconceptions: bool,
        pending_mistake: Optional[Dict[str, Any]] = None,
        is_stuck_or_remediation: bool = False,
    ) -> bool:
        """
        Improvement 2: Check whether the session is eligible for a mistake injection.
        Requires demonstrated understanding, advanced stage, respected cooldown,
        and no active struggle, teacher intervention, or pending injection.
        """
        # 1. Mode Gate: Only active in STUDENT mode
        if str(mode).upper() != "STUDENT":
            return False

        # 2. Pending Gate: Never inject if an existing injection is awaiting evaluation
        if pending_mistake and pending_mistake.get("active") and pending_mistake.get("status") == "PENDING":
            return False

        # 3. Remediation Gate: Never inject if user is stuck, asking for help, or in remediation
        if is_stuck_or_remediation:
            return False

        # 4. Misconception Gate: Must have zero active unresolved misconceptions
        if has_unresolved_misconceptions:
            return False

        # 5. Understanding Gate: Must demonstrate strong, sound, and complete understanding
        if correctness < 0.70 or completeness < 0.60:
            return False

        # 6. Advanced Stage Gate: Difficulty >= 3 and Turn >= 3
        if current_difficulty < 3 or turn_number < 3:
            return False

        # 7. Cooldown Gate: At least 3 turns since the last injection
        if last_injected_turn is not None and (turn_number - last_injected_turn) < 3:
            return False

        # 8. Cadence Schedule: Suitable frequency (every 3 turns when eligible)
        if turn_number % 3 != 0:
            return False

        return True

    def generate_candidate(
        self,
        topic: str,
        user_explanation: str,
        active_concept: Optional[str] = None,
    ) -> Optional[MistakeCandidate]:
        """
        Improvement 1 & 3: Generate a topic-specific, plausible candidate misconception.
        """
        concept_name = active_concept or topic
        gen_prompt = f"""You are the Curriculum Architect for Curio AI, an educational system using the Feynman technique.
The teacher (user) just explained:
"{user_explanation}"

Task: Formulate ONE subtle, plausible student misconception or tricky edge-case doubt about '{concept_name}' in '{topic}' to test if the teacher notices the flaw.

Requirements:
1. Plausible & Subtle: It must sound like an earnest beginner student's misconception, NOT an obvious or absurd blunder.
2. Strictly False: The claim must be factually invalid under the stated conditions.
3. Natural Student Doubt: Formulate 2-3 sentences where Curio acknowledges what was taught, voices this specific doubt, and ends with exactly ONE question mark.

Respond in exact JSON format:
{{
  "concept": "{concept_name}",
  "claim": "<1 sentence stating the specific false premise or assumption>",
  "why_false": "<1 sentence explaining the algorithmic/physical reason why this is false>",
  "student_question": "<2-3 sentence student question expressing this doubt ending in exactly ONE question mark>"
}}"""
        try:
            if hasattr(self.provider, "generate_structured"):
                # Attempt structured Pydantic generation
                candidate = self.provider.generate_structured(gen_prompt, MistakeCandidate)
                if candidate and candidate.claim and candidate.student_question:
                    return candidate
            elif hasattr(self.provider, "generate_text"):
                raw_text = self.provider.generate_text(gen_prompt)
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return MistakeCandidate(
                        concept=data.get("concept", concept_name),
                        claim=data.get("claim", ""),
                        why_false=data.get("why_false", ""),
                        student_question=data.get("student_question", ""),
                    )
        except Exception as e:
            logger.warning("Candidate mistake generation failed (%s); proceeding safely.", str(e))

        # Dynamic fallback candidate grounded in topic
        return MistakeCandidate(
            concept=concept_name,
            claim=f"Applying {concept_name} on arbitrary partially-ordered inputs always guarantees optimal best-case performance without boundary trade-offs.",
            why_false=f"Partial order or edge-case boundaries introduce additional checks or invalid preconditions in {concept_name}.",
            student_question=f"Wait, I think I understand how {concept_name} operates normally, but if the input is already partially ordered, does it always achieve optimal performance without any trade-offs?",
        )

    def verify_candidate(
        self,
        topic: str,
        candidate: MistakeCandidate,
    ) -> MistakeVerificationResult:
        """
        Improvement 1: Independent verification pass.
        Verifies that the generated claim is genuinely false, subtle, grounded,
        and solvable. If it is actually true or ambiguous, the candidate is rejected.
        """
        verify_prompt = f"""You are the Independent Fact Verifier for Curio AI.
Topic: {topic}
Candidate Concept: {candidate.concept}
Candidate Claim: "{candidate.claim}"
Claim's Purported Flaw: "{candidate.why_false}"

Evaluate this candidate claim with strict rigor:
1. Is the claim FACTUALLY FALSE in the context of {topic}? (If it is actually true or standard correct behavior, it MUST be rejected!)
2. Is the claim clear and unambiguous (not a trick question or purely semantic debate)?
3. Is it safe, respectful, and solvable by someone with a good understanding of {topic}?

Respond in exact JSON format:
{{
  "is_valid": true or false,
  "reasoning": "<1-2 sentences explaining why this claim is genuinely false and suitable, or why it was rejected>"
}}"""
        try:
            if hasattr(self.provider, "generate_structured"):
                result = self.provider.generate_structured(verify_prompt, MistakeVerificationResult)
                if result:
                    return result
            elif hasattr(self.provider, "generate_text"):
                raw_text = self.provider.generate_text(verify_prompt)
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return MistakeVerificationResult(
                        is_valid=bool(data.get("is_valid", False)),
                        reasoning=str(data.get("reasoning", "")),
                    )
        except Exception as e:
            logger.warning("Independent verification pass failed (%s); defaulting to candidate heuristic check.", str(e))

        # Deterministic safety heuristic: candidate must have a non-empty why_false and claim
        if candidate.claim and candidate.why_false and len(candidate.claim) > 10:
            return MistakeVerificationResult(
                is_valid=True,
                reasoning="Heuristic verification passed: non-empty claim and counter-reason.",
            )

        return MistakeVerificationResult(
            is_valid=False,
            reasoning="Candidate claim was empty or ungrounded.",
        )

    def evaluate_response(
        self,
        topic: str,
        user_response: str,
        pending_mistake: InjectedMistakeState,
    ) -> MistakeEvaluationVerdict:
        """
        Improvement 3: 3-Way evaluation distinguishing CAUGHT, MISSED, and INCONCLUSIVE.
        - CAUGHT: User explicitly identifies and refutes the error.
        - MISSED: User agrees with, validates, or repeats the misconception.
        - INCONCLUSIVE: User is vague, asks for clarification, or discusses something else.
        """
        clean_user = user_response.strip()
        lower_user = clean_user.lower()

        # Quick heuristic check for clarification / inconclusive signals
        clarification_signals = [
            "what do you mean", "can you clarify", "could you explain what", "rephrase",
            "not sure what you're asking", "i don't understand the question", "could you elaborate",
            "what are you referring to", "which part", "pardon", "repeat that"
        ]
        if any(sig in lower_user for sig in clarification_signals) and len(clean_user.split()) < 12:
            return MistakeEvaluationVerdict(
                verdict="INCONCLUSIVE",
                explanation="Learner requested clarification or expressed uncertainty about the student's question.",
                evidence=clean_user,
            )

        eval_prompt = f"""You are the Pedagogical Evaluator for Curio AI.
The student (Curio) previously proposed this deliberate, subtle misconception about {topic}:
Claim: "{pending_mistake.claim}"
Why it is false: "{pending_mistake.why_false}"

The teacher (user) responded:
"{clean_user}"

Classify the user's response into EXACTLY ONE of three categories:
1. CAUGHT: The user noticed the error, pointed out that the claim is incorrect/flawed, or explained the correct counter-reason.
2. MISSED: The user explicitly agreed with, confirmed, or validated the false claim (e.g. "Yes, exactly", "That's right", or repeating the flawed premise).
3. INCONCLUSIVE: The user's answer is ambiguous, vague, off-topic, or neither clearly endorses nor clearly refutes the subtle error.

Respond in exact JSON format:
{{
  "verdict": "CAUGHT" or "MISSED" or "INCONCLUSIVE",
  "explanation": "<1 sentence explaining why this verdict was chosen>",
  "evidence": "<the specific phrase from the user's answer demonstrating this>"
}}"""
        try:
            if hasattr(self.provider, "generate_structured"):
                verdict_obj = self.provider.generate_structured(eval_prompt, MistakeEvaluationVerdict)
                if verdict_obj and verdict_obj.verdict in ("CAUGHT", "MISSED", "INCONCLUSIVE"):
                    return verdict_obj
            elif hasattr(self.provider, "generate_text"):
                raw_text = self.provider.generate_text(eval_prompt)
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    v = str(data.get("verdict", "INCONCLUSIVE")).upper()
                    if v not in ("CAUGHT", "MISSED", "INCONCLUSIVE"):
                        v = "INCONCLUSIVE"
                    return MistakeEvaluationVerdict(
                        verdict=v,
                        explanation=str(data.get("explanation", "")),
                        evidence=str(data.get("evidence", clean_user[:100])),
                    )
        except Exception as e:
            logger.warning("LLM response evaluation failed (%s); using deterministic keyword fallback.", str(e))

        # Heuristic fallback
        refute_keywords = ["no", "not", "false", "incorrect", "wrong", "doesn't", "cannot", "actually", "careful", "never"]
        agree_keywords = ["yes", "exactly", "correct", "right", "indeed", "that's true", "precisely"]

        has_refute = any(re.search(rf"\b{re.escape(k)}\b", lower_user) for k in refute_keywords)
        has_agree = any(re.search(rf"\b{re.escape(k)}\b", lower_user) for k in agree_keywords)

        if has_refute and not has_agree:
            return MistakeEvaluationVerdict(
                verdict="CAUGHT",
                explanation="User used refutation terminology correcting the false claim.",
                evidence=clean_user,
            )
        elif has_agree and not has_refute:
            return MistakeEvaluationVerdict(
                verdict="MISSED",
                explanation="User agreed with or validated the flawed premise.",
                evidence=clean_user,
            )

        return MistakeEvaluationVerdict(
            verdict="INCONCLUSIVE",
            explanation="Response does not decisively confirm or refute the subtle mistake.",
            evidence=clean_user,
        )
