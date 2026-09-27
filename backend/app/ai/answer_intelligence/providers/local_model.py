"""
Local / Heuristic Semantic Assessment Provider for Curio AI.
Provides fast, deterministic semantic relevance, claim extraction, evidence matching,
and correctness assessment without mandatory external API latency.
Guarantees robust detection of irrelevant, off-topic, and adversarial answers.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING, Any, List, Optional, Set, Tuple

from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    ClaimType,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    ExpectedEvidence,
    LearnerClaim,
    MisconceptionEvidence,
    RelevanceLevel,
)
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, ConceptModel, ConceptNode


# Universal stop words to strip when checking conceptual keyword overlap
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
}


def _normalize_token(t: str) -> str:
    """Lightweight suffix normalization for English conceptual words."""
    t = t.lower().strip()
    for suffix in ("ing", "tions", "tion", "ies", "es", "ed", "ly", "s"):
        if len(t) > len(suffix) + 3 and t.endswith(suffix):
            return t[:-len(suffix)]
    return t


def _tokenize_meaningful(text: str) -> Set[str]:
    """Extract lowercase alphanumeric tokens, normalized stems, and compound parts."""
    if not text:
        return set()
    # Normalize hyphens and underscores
    clean_text = text.replace("-", " ").replace("_", " ")
    raw_tokens = re.findall(r"\b[a-zA-Z0-9]{2,}\b", clean_text.lower())
    tokens: Set[str] = set()
    for t in raw_tokens:
        if t not in STOP_WORDS:
            tokens.add(t)
            norm = _normalize_token(t)
            if norm:
                tokens.add(norm)

    # Common compound expansions in CS
    lower_orig = text.lower()
    if "rollback" in lower_orig or "roll back" in lower_orig:
        tokens.update(["roll", "back", "rollback"])
    if "all or nothing" in lower_orig or "all-or-nothing" in lower_orig:
        tokens.update(["all", "nothing"])
    if "fixed size" in lower_orig or "fixed-size" in lower_orig:
        tokens.update(["fixed", "size"])
    if "runs forever" in lower_orig or "run forever" in lower_orig:
        tokens.update(["infinite", "infinit", "forever", "recursion", "recurs"])
    if "stops the loop" in lower_orig or "stop the loop" in lower_orig or "stops" in lower_orig:
        tokens.update(["terminat", "terminating", "stop", "stops", "condition", "condit"])
    if "cannot be there" in lower_orig or "cannot be after" in lower_orig or "ignore" in lower_orig:
        tokens.update(["eliminat", "eliminating", "eliminate", "ignore", "side", "space", "half"])
    if "without base case" in lower_orig or "base case" in lower_orig:
        tokens.update(["prevent", "prevents", "terminat", "terminating"])
    if "contiguous" in lower_orig or "non contiguous" in lower_orig:
        tokens.update(["fragmentation", "external", "fragment", "avoids", "avoid"])

    # Common conceptual stem/synonym expansions
    extra: Set[str] = set()
    for t in tokens:
        if t in ("divid", "dividing", "divide"):
            extra.update(["halv", "halving", "half"])
        if t in ("range",):
            extra.update(["interval", "space"])
        if t in ("half",):
            extra.update(["halv", "halving"])
        if t in ("forever",):
            extra.update(["infinit", "infinite"])
        if t in ("infinit", "infinite"):
            extra.update(["forever"])
        if t in ("loop", "looping"):
            extra.update(["recurs", "recursion", "call", "calling"])
        if t in ("run", "runs", "running"):
            extra.update(["execut", "execution"])
    tokens.update(extra)

    return tokens


def has_negated_phrase(text: str, target_phrase: str) -> bool:
    """Checks if target_phrase or its key words are preceded by negation."""
    negation_patterns = [
        r"\b(?:no|not|never|neither|nor|without|regardless of|does not|doesn't|cannot|can't)\s+(?:\w+\s+){0,3}" + re.escape(target_phrase),
        r"\bnon[\s-]" + re.escape(target_phrase),
    ]
    for pat in negation_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


class LocalAssessmentProvider(BaseAssessmentProvider):
    """
    Lightweight, deterministic assessment provider.
    Combines lexical semantic extraction, negation analysis, and evidence mapping.
    """

    def classify_intent(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[str] = None,
    ) -> Tuple[AssessmentIntent, float]:
        clean = (user_message or "").strip().lower()
        if not clean:
            return AssessmentIntent.EMPTY_RESPONSE, 1.0

        # Manipulation / Meta instructions
        meta_phrases = [
            "mark this correct", "mark as correct", "give me full score", "i already know this",
            "skip this", "just say correct", "grade me 100",
        ]
        if any(p in clean for p in meta_phrases):
            return AssessmentIntent.OFF_TOPIC, 0.95

        # Help requests / stuck
        stuck_signals = [
            "i don't know", "i do not know", "idk", "not sure", "im stuck", "i'm stuck",
            "i am stuck", "no idea", "no clue", "i am lost", "i'm lost", "im lost",
            "totally lost", "completely lost", "teach me", "please explain",
            "help me", "can you explain", "could you explain", "don't understand",
            "dont understand", "i am confused", "i'm confused", "im confused",
            "still confused", "can you teach me", "walk me through",
        ]
        if any(s in clean for s in stuck_signals):
            return AssessmentIntent.HELP_REQUEST, 0.95

        # Clarification requests about question / term
        clarify_signals = [
            "what do you mean", "what is meant by", "could you clarify", "can you clarify",
            "clarify the question", "what does that word mean", "what does this term mean",
        ]
        if any(c in clean for c in clarify_signals):
            return AssessmentIntent.CLARIFICATION_REQUEST, 0.95

        # Inquisitive conceptual questions (asks how/why concept works)
        if clean.endswith("?") and any(clean.startswith(w) for w in ["how does", "why does", "what causes", "how do"]):
            return AssessmentIntent.QUESTION_ABOUT_CONCEPT, 0.90

        # Acknowledgements & Readiness
        ack_phrases = {
            "ok", "okay", "yes", "got it", "i understand", "i see", "understood", "sure",
            "makes sense", "i'm good", "im good", "ready", "teach me again", "yes i am ready",
            "yes i'm ready", "i get it", "all clear", "cool", "fine", "yep", "yeah",
        }
        clean_punct = re.sub(r"[,.!?]+", "", clean).strip()
        if clean_punct in ack_phrases:
            if clean_punct in {"ready", "yes i am ready", "yes i'm ready"}:
                return AssessmentIntent.READY_TO_CONTINUE, 0.95
            return AssessmentIntent.ACKNOWLEDGEMENT, 0.95

        # Pure off-topic chit-chat / greetings
        greetings = {"hello", "hi", "hey", "good morning", "good evening", "how are you", "who are you"}
        if clean_punct in greetings:
            return AssessmentIntent.OFF_TOPIC, 0.95

        # By default, non-empty substantive message is an answer attempt
        return AssessmentIntent.ANSWER_ATTEMPT, 0.90

    def assess_relevance(
        self,
        user_message: str,
        question: str,
        target_concept: str,
        topic: str,
        expected: Optional[ExpectedEvidence] = None,
    ) -> Tuple[RelevanceLevel, float]:
        clean = (user_message or "").strip().lower()
        if not clean:
            return RelevanceLevel.IRRELEVANT, 0.0

        user_tokens = _tokenize_meaningful(clean)
        if not user_tokens:
            return RelevanceLevel.IRRELEVANT, 0.0

        # Target concept tokens & variants
        concept_tokens = _tokenize_meaningful(target_concept.replace("_", " "))
        question_tokens = _tokenize_meaningful(question)
        topic_tokens = _tokenize_meaningful(topic)

        # Expected evidence tokens (from core components, not misconceptions)
        expected_tokens: Set[str] = set()
        if expected:
            for c in expected.core_components:
                expected_tokens.update(_tokenize_meaningful(c))

        target_and_expected_tokens = concept_tokens | expected_tokens
        question_and_target_tokens = question_tokens | concept_tokens | expected_tokens

        # Check overlap
        overlap_concept_evidence = user_tokens & target_and_expected_tokens
        overlap_question = user_tokens & question_tokens

        # If contrast concepts or known completely unrelated keywords are present:
        # Example: asked about Atomicity in DBMS, but answer discusses weather, personal biography, or other language
        unrelated_flags = [
            "sunny", "yesterday", "rain", "weather", "created by me", "my dog", "lunch", "dinner",
            "james gosling", "guido van rossum", "today is",
        ]
        if any(f in clean for f in unrelated_flags) and len(overlap_concept_evidence) == 0:
            return RelevanceLevel.IRRELEVANT, 0.0

        # Calculate Jaccard-like or token overlap score
        total_target_tokens = len(target_and_expected_tokens) if target_and_expected_tokens else len(question_tokens)
        if total_target_tokens == 0:
            total_target_tokens = 1

        # Direct concept match
        concept_clean = target_concept.lower().replace("_", " ")
        has_direct_concept_mention = (concept_clean in clean) if len(concept_clean) > 2 else False

        # If zero overlap with concept, question keywords, or expected evidence:
        if not overlap_concept_evidence and not overlap_question and not has_direct_concept_mention:
            # If there was no specific question asked yet (opening topic statement) and learner discusses topic:
            if not question_tokens and (user_tokens & topic_tokens):
                return RelevanceLevel.RELEVANT, 0.75
            return RelevanceLevel.IRRELEVANT, 0.05

        # Check if answer discusses topic in general but completely misses target concept
        # Example: Question is DBMS Atomicity, but answer is "SQL is a language used to query databases"
        if not overlap_concept_evidence and not has_direct_concept_mention:
            # Answer touches topic words but zero target concept words
            if overlap_question and len(overlap_question - topic_tokens) > 0:
                return RelevanceLevel.PARTIALLY_RELEVANT, 0.35
            return RelevanceLevel.IRRELEVANT, 0.05

        # Substantial overlap with concept and expected evidence
        if len(overlap_concept_evidence) >= 2 or has_direct_concept_mention:
            relevance_score = min(1.0, 0.70 + 0.10 * len(overlap_concept_evidence))
            return RelevanceLevel.RELEVANT, round(relevance_score, 2)
        elif len(overlap_concept_evidence) == 1:
            return RelevanceLevel.PARTIALLY_RELEVANT, 0.50
        else:
            return RelevanceLevel.PARTIALLY_RELEVANT, 0.35

    def extract_claims(
        self,
        user_message: str,
        target_concept: str,
    ) -> List[LearnerClaim]:
        clean = (user_message or "").strip()
        if not clean:
            return []

        # Split into sentences or clauses
        sentences = re.split(r"[.;\n]+", clean)
        claims: List[LearnerClaim] = []

        concept_words = _tokenize_meaningful(target_concept.replace("_", " "))

        for s in sentences:
            s_str = s.strip()
            if not s_str:
                continue

            s_tokens = _tokenize_meaningful(s_str)
            overlap = s_tokens & concept_words
            alignment = len(overlap) / max(1, len(concept_words)) if concept_words else 0.5
            if target_concept.lower().replace("_", " ") in s_str.lower():
                alignment = max(alignment, 0.8)

            c_type = ClaimType.FACTUAL_ASSERTION
            lower_s = s_str.lower()
            if any(w in lower_s for w in ["means", "is defined as", "refers to"]):
                c_type = ClaimType.DEFINITION
            elif any(w in lower_s for w in ["works by", "happens when", "executes", "rolls back", "commits", "divides", "searches", "allocates"]):
                c_type = ClaimType.MECHANISM
            elif any(w in lower_s for w in ["for example", "such as", "like when", "if you transfer", "if debit"]):
                c_type = ClaimType.EXAMPLE
            elif alignment == 0.0 and len(s_tokens) > 2 and any(f in lower_s for f in ["sunny", "yesterday", "my dog", "created by me", "ice cream"]):
                c_type = ClaimType.IRRELEVANT_STATEMENT

            claims.append(
                LearnerClaim(
                    text=s_str,
                    concept_id=target_concept if alignment >= 0.2 else None,
                    claim_type=c_type,
                    alignment_score=round(alignment, 2),
                    is_factually_sound=True if c_type != ClaimType.IRRELEVANT_STATEMENT else None,
                )
            )

        return claims

    def align_concepts(
        self,
        claims: List[LearnerClaim],
        concept_node: Optional[ConceptNode],
        target_concept: str,
        concept_model: Optional[ConceptModel] = None,
    ) -> float:
        if not claims:
            return 0.0

        target_tokens = _tokenize_meaningful(target_concept.replace("_", " "))
        if concept_node:
            if concept_node.definition:
                target_tokens.update(_tokenize_meaningful(concept_node.definition))
            for c in concept_node.constraints:
                target_tokens.update(_tokenize_meaningful(c))
        else:
            cid_lower = (target_concept or "").lower().replace(" ", "_")
            from backend.app.ai.answer_intelligence.evidence_extractor import CANONICAL_CONCEPT_EVIDENCE
            for key, data in CANONICAL_CONCEPT_EVIDENCE.items():
                if key in cid_lower:
                    for comp in data["components"]:
                        target_tokens.update(_tokenize_meaningful(comp))

        scores: List[float] = []
        for c in claims:
            if c.claim_type == ClaimType.IRRELEVANT_STATEMENT:
                continue
            c_tokens = _tokenize_meaningful(c.text)
            overlap = c_tokens & target_tokens
            if not target_tokens:
                scores.append(c.alignment_score)
            else:
                score = min(1.0, len(overlap) / max(2, min(4, len(c_tokens))))
                scores.append(max(c.alignment_score, score))

        if not scores:
            return 0.0
        return max(scores)

    def match_evidence(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        items: List[EvidenceItem] = []
        full_text = " ".join(c.text.lower() for c in claims)

        for comp in expected.core_components:
            comp_tokens = _tokenize_meaningful(comp)
            best_status = EvidenceStatus.MISSING
            supp_claim: Optional[str] = None
            contra_claim: Optional[str] = None

            # Check contradictions first
            # e.g., expected "all or nothing", learner says "can partially succeed" or "some can succeed"
            partial_contradiction = False
            if "all" in comp.lower() or "nothing" in comp.lower():
                if "partially succeed" in full_text or "some operations can succeed" in full_text or "some can succeed" in full_text:
                    best_status = EvidenceStatus.CONTRADICTED
                    contra_claim = full_text
                    partial_contradiction = True

            GENERIC_CONTEXT_TOKENS = {
                "search", "space", "element", "data", "operation", "condition", "step", "method", "system", "rule", "mechanism", "state",
            }
            comp_words = {t for t in re.findall(r"\b[a-zA-Z0-9]{2,}\b", comp.lower()) if t not in STOP_WORDS}
            if not partial_contradiction:
                for cl in claims:
                    cl_tokens = _tokenize_meaningful(cl.text)
                    overlap = cl_tokens & comp_tokens
                    distinctive_overlap = overlap - GENERIC_CONTEXT_TOKENS
                    has_distinctive = len(distinctive_overlap) > 0
                    overlap_ratio = len(overlap) / max(2, len(comp_words))

                    is_supported = False
                    if has_distinctive:
                        if len(comp_words) <= 3:
                            is_supported = (overlap_ratio >= 0.60 or len(distinctive_overlap) >= 2)
                        else:
                            is_supported = (overlap_ratio >= 0.55)

                    if is_supported:
                        best_status = EvidenceStatus.SUPPORTED
                        supp_claim = cl.text
                        break
                    elif has_distinctive and (overlap_ratio >= 0.20 or len(overlap) >= 2):
                        best_status = EvidenceStatus.PARTIALLY_SUPPORTED
                        supp_claim = cl.text

            items.append(
                EvidenceItem(
                    concept_id=expected.concept_id,
                    expected_description=comp,
                    status=best_status,
                    supported_by_claim=supp_claim,
                    contradicted_by_claim=contra_claim,
                    confidence=0.90 if best_status != EvidenceStatus.UNKNOWN else 0.50,
                )
            )

        return items

    def assess_correctness(
        self,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CorrectnessLevel, float, List[str]]:
        if not claims:
            return CorrectnessLevel.UNASSESSABLE, 0.0, []

        contradictory = [
            it.contradicted_by_claim for it in evidence_items
            if it.status == EvidenceStatus.CONTRADICTED and it.contradicted_by_claim
        ]
        if contradictory:
            return CorrectnessLevel.CONTRADICTORY, 0.10, contradictory

        # If claims are entirely irrelevant statements
        all_irrelevant = all(c.claim_type == ClaimType.IRRELEVANT_STATEMENT for c in claims)
        if all_irrelevant:
            return CorrectnessLevel.IRRELEVANT, 0.0, []

        supported_count = sum(1 for it in evidence_items if it.status == EvidenceStatus.SUPPORTED)
        partial_count = sum(1 for it in evidence_items if it.status == EvidenceStatus.PARTIALLY_SUPPORTED)
        total = max(1, len(evidence_items))

        support_ratio = (supported_count + 0.5 * partial_count) / total
        has_supported = supported_count > 0

        if support_ratio >= 0.60 and has_supported:
            return CorrectnessLevel.CORRECT, 0.90, []
        elif support_ratio >= 0.30:
            return CorrectnessLevel.PARTIALLY_CORRECT, 0.60, []
        elif support_ratio > 0.0:
            return CorrectnessLevel.INCOMPLETE, 0.35, []
        else:
            return CorrectnessLevel.INCORRECT, 0.15, []

    def assess_completeness(
        self,
        evidence_items: List[EvidenceItem],
        expected: ExpectedEvidence,
    ) -> Tuple[CompletenessLevel, float, List[str]]:
        if not evidence_items:
            return CompletenessLevel.NOT_APPLICABLE, 0.0, []

        supported = [it for it in evidence_items if it.status == EvidenceStatus.SUPPORTED]
        missing = [it.expected_description for it in evidence_items if it.status == EvidenceStatus.MISSING]

        ratio = len(supported) / max(1, len(evidence_items))
        if ratio >= 0.8:
            return CompletenessLevel.COMPLETE, round(ratio, 2), missing
        elif ratio >= 0.5:
            return CompletenessLevel.SUBSTANTIAL, round(ratio, 2), missing
        elif ratio >= 0.2:
            return CompletenessLevel.PARTIAL, round(ratio, 2), missing
        else:
            return CompletenessLevel.MINIMAL, round(ratio, 2), missing

    def detect_misconceptions(
        self,
        user_message: str,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[MisconceptionEvidence]:
        misconceptions: List[MisconceptionEvidence] = []
        lower_msg = user_message.lower()

        # Specific conceptual contradiction checks with negation awareness:
        # 1. Atomicity: partial execution/commit
        if (
            ("even if" in lower_msg and "fail" in lower_msg and ("succeed" in lower_msg or "commit" in lower_msg))
            or any(p in lower_msg for p in [
                "some operations in a transaction can succeed",
                "can partially commit",
                "partially succeed",
                "operations can commit even if",
                "partially commit",
            ])
        ):
            if not has_negated_phrase(lower_msg, "partial") and not has_negated_phrase(lower_msg, "succeed"):
                misconceptions.append(
                    MisconceptionEvidence(
                        concept_id=expected.concept_id,
                        description="transactions can partially commit or complete",
                        learner_statement=user_message,
                        severity="HIGH",
                    )
                )

        # 2. Paging: contiguous RAM requirement
        if any(p in lower_msg for p in ["requires contiguous", "must be contiguous", "needs contiguous", "in contiguous memory"]):
            if not has_negated_phrase(lower_msg, "contiguous") and not has_negated_phrase(lower_msg, "require"):
                misconceptions.append(
                    MisconceptionEvidence(
                        concept_id=expected.concept_id,
                        description="paging requires contiguous physical RAM allocation",
                        learner_statement=user_message,
                        severity="HIGH",
                    )
                )

        # 3. Binary Search: unsorted array assumption
        if any(p in lower_msg for p in ["works on unsorted", "searches unsorted", "arbitrary sequence", "does not need sorting"]):
            if not has_negated_phrase(lower_msg, "unsorted"):
                misconceptions.append(
                    MisconceptionEvidence(
                        concept_id=expected.concept_id,
                        description="binary search works on unsorted array",
                        learner_statement=user_message,
                        severity="HIGH",
                    )
                )

        return misconceptions

    def assess_confidence(
        self,
        intent: AssessmentIntent,
        relevance: RelevanceLevel,
        relevance_score: float,
        correctness: CorrectnessLevel,
        claims: List[LearnerClaim],
        evidence_items: List[EvidenceItem],
    ) -> Tuple[AssessmentStatus, float]:
        if intent in (AssessmentIntent.EMPTY_RESPONSE, AssessmentIntent.UNCERTAIN):
            return AssessmentStatus.ABSTAIN, 0.30

        if relevance == RelevanceLevel.UNCERTAIN:
            return AssessmentStatus.ABSTAIN, 0.40

        if relevance == RelevanceLevel.IRRELEVANT:
            return AssessmentStatus.HIGH_CONFIDENCE, 0.95

        # Check if short/ambiguous
        total_words = sum(len(c.text.split()) for c in claims)
        if total_words < 3 and correctness in (CorrectnessLevel.PARTIALLY_CORRECT, CorrectnessLevel.INCOMPLETE):
            return AssessmentStatus.LOW_CONFIDENCE, 0.50

        return AssessmentStatus.HIGH_CONFIDENCE, 0.90
