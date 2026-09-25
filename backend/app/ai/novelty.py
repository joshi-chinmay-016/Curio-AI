"""
Semantic Novelty Checker for Curio AI questions.
Detects semantic repetition among recent questions using n-gram cosine similarity and token overlap.
Guards against repetitive loops while keeping execution deterministic and fast.
"""
import math
import re
from typing import List, Set, Tuple


class QuestionNoveltyChecker:
    """
    Checks whether a candidate question is sufficiently novel compared to recent questions.
    Acts as a guardrail against repeating prepared or recently asked questions.
    """

    def __init__(self, similarity_threshold: float = 0.80):
        self.similarity_threshold = similarity_threshold

    def is_novel(
        self,
        candidate_question: str,
        recent_questions: List[str],
        threshold: float = None,
    ) -> Tuple[bool, float, str]:
        """
        Evaluate if candidate_question is novel compared to recent_questions.
        Returns:
            (is_novel: bool, max_similarity: float, reason_if_rejected: str)
        """
        if not recent_questions:
            return True, 0.0, ""

        thresh = threshold if threshold is not None else self.similarity_threshold
        clean_cand = self._preprocess(candidate_question)
        if not clean_cand:
            return False, 1.0, "Empty candidate question."

        cand_ngrams = self._get_char_ngrams(clean_cand, n=3)
        cand_tokens = set(clean_cand.split())

        max_sim = 0.0
        most_similar_q = ""

        for past_q in recent_questions[-6:]:
            clean_past = self._preprocess(past_q)
            if not clean_past:
                continue

            past_ngrams = self._get_char_ngrams(clean_past, n=3)
            past_tokens = set(clean_past.split())

            # 1. Cosine similarity of 3-grams
            cosine_sim = self._cosine_sim(cand_ngrams, past_ngrams)

            # 2. Jaccard similarity of key words (words > 3 chars)
            cand_key = {t for t in cand_tokens if len(t) > 3}
            past_key = {t for t in past_tokens if len(t) > 3}
            if cand_key and past_key:
                jaccard_sim = len(cand_key & past_key) / len(cand_key | past_key)
            else:
                jaccard_sim = 0.0

            # Composite similarity
            sim = 0.6 * cosine_sim + 0.4 * jaccard_sim

            if sim > max_sim:
                max_sim = sim
                most_similar_q = past_q

        if max_sim >= thresh:
            return False, round(max_sim, 3), f"Too similar ({max_sim:.2f}) to recent question: '{most_similar_q}'"

        return True, round(max_sim, 3), ""

    @staticmethod
    def _preprocess(text: str) -> str:
        t = (text or "").lower()
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        return " ".join(t.split())

    @staticmethod
    def _get_char_ngrams(text: str, n: int = 3) -> dict:
        ngrams = {}
        for i in range(len(text) - n + 1):
            gram = text[i : i + n]
            ngrams[gram] = ngrams.get(gram, 0) + 1
        return ngrams

    @staticmethod
    def _cosine_sim(vec1: dict, vec2: dict) -> float:
        if not vec1 or not vec2:
            return 0.0
        dot = sum(vec1[k] * vec2[k] for k in vec1 if k in vec2)
        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)
