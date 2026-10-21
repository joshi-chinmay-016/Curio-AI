"""
Question Validator and Final Student Mode Question Enforcement for Curio AI (Phase 3 Step 3.5).
Validates candidate questions and enforces final response invariant:
- Exactly one clear, independently answerable question
- Handles quoted question marks in technical text without false positives
- Detects compound questions and multi-interrogative prompts
- Prevents answer leakage and accidental teacher lecturing
- Preserves clean declarative prefixes (redirection, clarification, restored transitions)
- Bounded deterministic recovery ensuring no infinite retry loops
"""
import logging
import re
from typing import List, Optional, Tuple

from backend.app.ai.novelty import QuestionNoveltyChecker
from backend.app.ai.schemas import (
    AIContext,
    QuestionCandidate,
    QuestionSpecification,
    QuestionValidation,
    Role,
)

logger = logging.getLogger("curio.ai.question_validator")

TEACHER_LECTURE_PHRASES = [
    "let me explain",
    "the correct answer is",
    "as you know, the answer is",
    "remember that",
    "here is how it works",
    "in other words, the definition is",
    "to summarize,",
]

SHALLOW_ENDINGS = ["right?", "does that make sense?", "isn't it?", "is that correct?"]


def mask_technical_question_marks(text: str) -> str:
    """
    Mask question marks that appear inside technical tokens (e.g. code backticks,
    regex literals, or short quoted characters like '?' or "?") while preserving
    actual natural-language question clauses.
    """
    if not text:
        return ""

    # 1. Mask fenced code blocks: ```...``` or ~~~...~~~
    def _mask_fenced(match):
        return match.group(0).replace("?", "[QM_LITERAL]")

    result = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", _mask_fenced, text)

    # 2. Mask inline code inside backticks: `...`
    def _mask_backticks(match):
        return match.group(0).replace("?", "[QM_LITERAL]")

    result = re.sub(r"`[^`\n]+`", _mask_backticks, result)

    # 3. Mask multiline triple-quoted docstrings / strings: """...""" or '''...'''
    def _mask_triple_quotes(match):
        return match.group(0).replace("?", "[QM_LITERAL]")

    result = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', _mask_triple_quotes, result)

    # 4. Mask short quoted literals or non-interrogative quotes: '...' or "..."
    def _mask_quotes(match):
        quoted = match.group(0)
        inner = quoted[1:-1].strip()
        lower_inner = inner.lower()
        starts_interrogative = bool(
            re.match(r"^(?:what|how|why|when|where|who|which|is|are|can|could|do|does)\b", lower_inner)
        )
        if not starts_interrogative:
            return quoted.replace("?", "[QM_LITERAL]")
        return quoted

    result = re.sub(r"'[^'\n]+'|\"[^\"\n]+\"", _mask_quotes, result)
    return result


def has_compound_interrogatives(text: str) -> bool:
    """
    Detect compound questions that ask multiple independent questions in one prompt,
    even if only one question mark is present.
    """
    lower = text.lower()

    # Pattern 1: Independent clause joined by punctuation and coordinating conjunction with interrogative
    # e.g., "What is X, and how does Y work?" or "Explain X, and why is Y needed?"
    if re.search(
        r"(?:,\s*|;\s*|\.\s+)and\s+(?:what|how|why|where|when|which|can you|could you|explain|describe)\b",
        lower,
    ):
        return True

    # Pattern 2: Addition phrases followed by interrogative
    # e.g., "What is X, and also what is Y?" or "How does X work, as well as why is Y needed?"
    if re.search(
        r"(?:,\s*|;\s*|\s+)and also\s+(?:what|how|why|where|when|which|can you|could you|explain|describe)\b",
        lower,
    ) or re.search(
        r"(?:,\s*|;\s*|\s+)(?:as well as|plus)\s+(?:how|what|why|where|when|which)\b",
        lower,
    ):
        return True

    # Pattern 3: Distinct sentence ending in a period or semicolon followed by a second interrogative clause ending in ?
    # only if the preceding sentence was ALSO an interrogative clause (e.g. "What is virtual memory. How does paging implement it?")
    if re.search(
        r"(?:^|[.!?]\s+)(?:what|how|why|where|when|which|is|are|can|could|do|does)\b[^.!?]*[.;]\s+(?:what|how|why|where|when|which|can you|could you|explain|describe)\b.*?\?",
        lower,
    ):
        return True

    # Pattern 4: Explicit multi-part enumeration
    # e.g., "1. What is X? 2. What is Y?" or "First, how does X work, and second, why is Y needed?"
    if re.search(r"\b(?:1\..*2\.|first,.*second,)\b", lower):
        return True

    return False


def validate_final_student_response(text: str) -> Tuple[bool, List[str]]:
    """
    Validate that a user-facing Student Mode response contains exactly one clear,
    independently answerable learning question and no lecturing or answer leakage.
    Handles optional declarative prefixes separated by double newlines.
    """
    reasons: List[str] = []
    raw = (text or "").strip()
    if not raw:
        return False, ["Response content is empty."]

    # Separate declarative prefixes (if separated by \n\n) from the final question clause
    prefix = ""
    question_part = raw
    if "\n\n" in raw:
        parts = raw.split("\n\n")
        prefix = "\n\n".join(parts[:-1]).strip()
        question_part = parts[-1].strip()

    # Prefix checks: must not contain questions, lecturing, or interrogative clauses
    if prefix:
        masked_prefix = mask_technical_question_marks(prefix)
        if "?" in masked_prefix:
            reasons.append("Introductory prefix contains an unexpected question mark.")
        if has_compound_interrogatives(masked_prefix):
            reasons.append("Introductory prefix contains an interrogative clause.")

    # Question clause checks
    masked_q = mask_technical_question_marks(question_part)
    q_count = masked_q.count("?")
    if q_count == 0:
        reasons.append("Question text contains no question mark.")
    elif q_count > 1:
        reasons.append(f"Violates hard one-question rule: contains {q_count} questions.")

    if has_compound_interrogatives(masked_q):
        reasons.append("Compound question detected: asks multiple independent questions.")

    # Accidental teacher lecturing / explaining
    lower_text = raw.lower()
    if any(p in lower_text for p in TEACHER_LECTURE_PHRASES):
        reasons.append("Accidental teacher explanation or lecturing in Student mode.")

    # Answer leakage: confirmation tag appended to explanatory text (e.g. ", right?", ", does that make sense?")
    words = question_part.split()
    shallow_tag_match = re.search(r"[,.]\s*(?:right|does that make sense|isn't it|is that correct)\?$", question_part.lower())
    if shallow_tag_match and len(words) >= 10:
        reasons.append("Answer leakage: explains the concept and ends with shallow confirmation.")

    return len(reasons) == 0, reasons


def _build_safe_fallback_question(
    spec: Optional[QuestionSpecification] = None,
    fallback_concept: Optional[str] = None,
) -> str:
    """
    Construct a deterministic single Socratic question aligned with the specification
    or fallback concept. Guaranteed to pass structural invariants.
    """
    if spec:
        from backend.app.ai.question_generator import QuestionGenerator

        cand = QuestionGenerator.construct_specification_fallback(spec)
        return cand.question_text

    c_name = (fallback_concept or "this concept").replace("_", " ").title()
    return f"I think I understand the general idea so far, but I'm having trouble visualizing the details. Could you explain how {c_name} works in simple, descriptive terms and walk me through a clear example?"


def enforce_single_student_question(
    content: str,
    spec: Optional[QuestionSpecification] = None,
    fallback_concept: Optional[str] = None,
) -> str:
    """
    Final-boundary enforcement guard for Student Mode responses.
    Ensures that the final user-visible response always contains exactly one
    clear learning question, preserving safe declarative prefixes where possible.
    Bounded and deterministic (no infinite generation or retry loop).
    """
    raw = (content or "").strip()
    if not raw:
        return _build_safe_fallback_question(spec=spec, fallback_concept=fallback_concept)

    is_valid, _ = validate_final_student_response(raw)
    if is_valid:
        return raw

    # 1. Bounded deterministic repair:
    # If the response is a single interrogative sentence ending in a period, restore terminal question mark.
    if "\n\n" not in raw and raw.endswith("."):
        candidate_repair = raw.rstrip(". ") + "?"
        rep_valid, _ = validate_final_student_response(candidate_repair)
        if rep_valid:
            logger.info("Repaired single interrogative response by restoring terminal question mark.")
            return candidate_repair

    # 2. Extract valid declarative prefix if present
    prefix = None
    if "\n\n" in raw:
        parts = raw.split("\n\n")
        candidate_prefix = "\n\n".join(parts[:-1]).strip()
        masked_p = mask_technical_question_marks(candidate_prefix)
        if (
            "?" not in masked_p
            and not has_compound_interrogatives(masked_p)
            and not any(p in candidate_prefix.lower() for p in TEACHER_LECTURE_PHRASES)
        ):
            prefix = candidate_prefix

    # 3. Construct specification-driven or topic-driven fallback question
    fallback_q = _build_safe_fallback_question(spec=spec, fallback_concept=fallback_concept)

    if prefix:
        assembled = f"{prefix}\n\n{fallback_q}"
    else:
        assembled = fallback_q

    # Final structural invariant check on assembled output
    assembled_valid, _ = validate_final_student_response(assembled)
    if assembled_valid:
        return assembled

    # Fallback directly to the standalone safe question if assembled output fails
    return fallback_q


class QuestionValidator:
    """
    Validates candidates deterministically before any question is returned.
    Guarantees no broken, lecturing, leaked, or duplicate questions reach the learner.
    """

    def __init__(self, novelty_checker: QuestionNoveltyChecker = None):
        self.novelty_checker = novelty_checker or QuestionNoveltyChecker(similarity_threshold=0.80)

    def validate_candidate(
        self,
        candidate: QuestionCandidate,
        spec: QuestionSpecification,
        recent_questions: List[str] = None,
        context: Optional[AIContext] = None,
    ) -> QuestionValidation:
        rejection_reasons: List[str] = []
        raw_text = (candidate.question_text or "").strip()
        recent_q = recent_questions or []

        # 1. Non-empty check
        if not raw_text:
            return QuestionValidation(
                candidate_id=candidate.candidate_id,
                is_valid=False,
                rejection_reasons=["Empty candidate question."],
                score=0.0,
            )

        # 2. Hard ONE-QUESTION Rule (quote-aware and compound-aware)
        masked_text = mask_technical_question_marks(raw_text)
        q_count = masked_text.count("?")
        if q_count > 1:
            rejection_reasons.append(f"Violates hard one-question rule: contains {q_count} questions.")
        elif q_count == 0:
            rejection_reasons.append("Violates question requirement: text contains no question mark.")
        elif has_compound_interrogatives(masked_text):
            rejection_reasons.append("Violates hard one-question rule: compound question asks multiple independent things.")

        # 3. Accidental Teacher Lecturing / Explaining
        lower_text = raw_text.lower()
        if any(p in lower_text for p in TEACHER_LECTURE_PHRASES):
            rejection_reasons.append("Accidental teacher explanation or lecturing in Student mode.")

        # Word count check: student question should be descriptive but not a wall of text (typically 20-90 words)
        words = raw_text.split()
        if len(words) > 120:
            rejection_reasons.append(f"Question exceeds descriptive limit ({len(words)} words; max 120).")

        # 4. Answer Leakage
        shallow_tag_match = re.search(r"[,.]\s*(?:right|does that make sense|isn't it|is that correct)\?$", lower_text)
        if shallow_tag_match and len(words) >= 10:
            rejection_reasons.append("Answer leakage: explains the concept and ends with shallow confirmation.")

        # 5. Semantic Novelty Guardrail
        is_novel, sim_score, novelty_reason = self.novelty_checker.is_novel(raw_text, recent_q)
        if not is_novel:
            rejection_reasons.append(novelty_reason)

        # 6. Concept Relevance Check
        target_words = set(re.findall(r"[a-z0-9]+", spec.target_concept.lower()))
        target_words = {w for w in target_words if w not in {"the", "and", "or", "in", "of", "a", "an"}}
        cand_words = set(re.findall(r"[a-z0-9]+", lower_text))

        overlap = len(target_words & cand_words)
        relevance_score = 1.0 if overlap > 0 else 0.7

        # 7. Strict Tabula Rasa / Knowledge Horizon Check
        # A student cannot claim an assumption or ask why something assumes/requires unmentioned terms
        # that the teacher has never introduced in the conversation.
        if context and context.conversation and context.conversation.recent_messages:
            user_texts = [
                m.content.lower() for m in context.conversation.recent_messages
                if getattr(m, "role", None) == Role.USER or getattr(m, "sender", "").upper() == "USER"
            ]
            combined_user_text = " ".join(user_texts)

            # Heuristic 7a: Stating or asking about assumptions on unintroduced terms
            # e.g., "why the algorithm assumes the array is sorted", "why does it assume that...", "what if the assumption that..."
            assume_search = re.search(
                r"\b(?:assumes?|assumption(?: that)?|assumed(?: that)?)\s+(?:the\s+)?([^?.,]+)",
                lower_text,
            )
            if assume_search:
                clause = assume_search.group(1).strip()
                clause_words = [
                    w for w in re.findall(r"[a-z0-9]+", clause)
                    if w not in {"the", "is", "are", "a", "an", "that", "it", "to", "be", "of", "in", "and", "or", "for", "with", "any", "all", "its", "by"}
                ]
                unmentioned = [w for w in clause_words if w not in combined_user_text]
                if unmentioned:
                    rejection_reasons.append(
                        f"Tabula rasa violation: student claims or challenges unintroduced assumption words ({', '.join(unmentioned)}) never stated by teacher."
                    )

            # Heuristic 7b: Leading pop-quiz question about unmentioned prerequisite/condition
            # e.g., "does it require/need the array to be sorted?", "must it be sorted?"
            pop_quiz_match = re.search(
                r"\b(?:does it (?:require|need|rely on)|must (?:the|it) be|is (?:it|the [a-z]+) (?:assumed to be|required to be))\s+([^?.,]+)",
                lower_text,
            )
            if pop_quiz_match:
                clause = pop_quiz_match.group(1).strip()
                clause_words = [
                    w for w in re.findall(r"[a-z0-9]+", clause)
                    if w not in {"the", "is", "are", "a", "an", "that", "it", "to", "be", "of", "in", "and", "or", "for", "with", "any", "all", "its", "by"}
                ]
                unmentioned = [w for w in clause_words if w not in combined_user_text]
                if unmentioned:
                    rejection_reasons.append(
                        f"Tabula rasa violation: student asks leading pop-quiz question about unmentioned requirement ({', '.join(unmentioned)})."
                    )

        # Composite score
        is_valid = len(rejection_reasons) == 0
        score = 0.0
        if is_valid:
            brevity_bonus = 0.2 if 15 <= len(words) <= 90 else 0.0
            score = round(0.8 * relevance_score + brevity_bonus, 3)

        return QuestionValidation(
            candidate_id=candidate.candidate_id,
            is_valid=is_valid,
            rejection_reasons=rejection_reasons,
            score=score,
        )
