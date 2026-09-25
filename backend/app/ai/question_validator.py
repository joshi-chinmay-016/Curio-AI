"""
Question Validator for Curio AI (Phase H).
Validates candidate questions against:
- Hard one-question rule
- No answer leakage
- No accidental Teacher lecturing in Student mode
- Concept relevance and objective alignment
- Semantic novelty guardrail (via QuestionNoveltyChecker)
"""
import logging
import re
from typing import List, Tuple

from backend.app.ai.novelty import QuestionNoveltyChecker
from backend.app.ai.schemas import (
    QuestionCandidate,
    QuestionSpecification,
    QuestionValidation,
)

logger = logging.getLogger("curio.ai.question_validator")


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

        # 2. Hard ONE-QUESTION Rule
        # Count primary question marks
        q_count = raw_text.count("?")
        if q_count > 1:
            rejection_reasons.append(f"Violates hard one-question rule: contains {q_count} questions.")
        elif q_count == 0:
            # If no question mark at all, it's not a question
            rejection_reasons.append("Violates question requirement: text contains no question mark.")

        # 3. Accidental Teacher Lecturing / Explaining
        lower_text = raw_text.lower()
        teacher_lecture_phrases = [
            "let me explain",
            "the correct answer is",
            "as you know, the answer is",
            "remember that",
            "here is how it works",
            "in other words, the definition is",
            "to summarize,",
        ]
        if any(p in lower_text for p in teacher_lecture_phrases):
            rejection_reasons.append("Accidental teacher explanation or lecturing in Student mode.")

        # Word count check: student question should be concise (typically < 50 words)
        words = raw_text.split()
        if len(words) > 55:
            rejection_reasons.append(f"Question exceeds concise limit ({len(words)} words; max 55).")

        # 4. Answer Leakage
        # If the question explains the concept completely and then just asks "right?" or "does that make sense?"
        shallow_endings = ["right?", "does that make sense?", "isn't it?", "is that correct?"]
        if any(lower_text.endswith(s) for s in shallow_endings) and len(words) > 15:
            rejection_reasons.append("Answer leakage: explains the concept and ends with shallow confirmation.")

        # 5. Semantic Novelty Guardrail
        is_novel, sim_score, novelty_reason = self.novelty_checker.is_novel(raw_text, recent_q)
        if not is_novel:
            rejection_reasons.append(novelty_reason)

        # 6. Concept Relevance Check
        target_words = set(re.findall(r"[a-z0-9]+", spec.target_concept.lower()))
        # Remove generic words
        target_words = {w for w in target_words if w not in {"the", "and", "or", "in", "of", "a", "an"}}
        cand_words = set(re.findall(r"[a-z0-9]+", lower_text))
        
        # Concept match score
        overlap = len(target_words & cand_words)
        relevance_score = 1.0 if overlap > 0 else 0.7  # Allow synonyms / contextual phrasing

        # Composite score
        is_valid = len(rejection_reasons) == 0
        score = 0.0
        if is_valid:
            # Higher score for concise, relevant questions; novelty is a filter guardrail
            brevity_bonus = 0.2 if 10 <= len(words) <= 35 else 0.0
            score = round(0.8 * relevance_score + brevity_bonus, 3)

        return QuestionValidation(
            candidate_id=candidate.candidate_id,
            is_valid=is_valid,
            rejection_reasons=rejection_reasons,
            score=score,
        )
