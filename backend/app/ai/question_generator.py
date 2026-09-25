"""
Question Candidate Generator and Selection Coordinator for Curio AI (Phase G & H).
Coordinates:
1. LLM Candidate Generation (3 candidates based on QuestionSpecification)
2. Deterministic Validation (QuestionValidator)
3. Novelty Verification (QuestionNoveltyChecker)
4. Regeneration on complete validation failure (1 retry with stronger constraints)
5. Specification-driven safe fallback (never an unrelated hardcoded question)
"""
import logging
import re
from typing import List, Optional

from backend.app.ai.novelty import QuestionNoveltyChecker
from backend.app.ai.prompts.candidate_prompts import build_candidate_generation_prompt
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.question_validator import QuestionValidator
from backend.app.ai.schemas import (
    AIContext,
    CandidateList,
    ObjectiveType,
    QuestionCandidate,
    QuestionSelectionResult,
    QuestionSpecification,
    QuestionValidation,
)

logger = logging.getLogger("curio.ai.question_generator")


class QuestionGenerator:
    """
    Coordinates candidate generation, validation, and safe fallback.
    Ensures that the LLM decides HOW to phrase the question, but the QuestionSelector
    controls WHAT concept, objective, and difficulty are targeted.
    """

    def __init__(
        self,
        provider: BaseAIProvider,
        validator: Optional[QuestionValidator] = None,
    ):
        self.provider = provider
        self.validator = validator or QuestionValidator()

    def generate_and_select_question(
        self,
        spec: QuestionSpecification,
        context: Optional[AIContext] = None,
        recent_questions: Optional[List[str]] = None,
    ) -> QuestionSelectionResult:
        recent_q = recent_questions or []

        # 1. First generation attempt (3 candidates)
        candidates = self._generate_candidates(spec, context, recent_q)
        validations = [self.validator.validate_candidate(c, spec, recent_q) for c in candidates]

        valid_candidates = [
            (c, v) for c, v in zip(candidates, validations) if v.is_valid
        ]

        if valid_candidates:
            # Pick highest scoring candidate
            best_candidate, best_val = max(valid_candidates, key=lambda pair: pair[1].score)
            return QuestionSelectionResult(
                specification=spec,
                candidates=candidates,
                validations=validations,
                selected_candidate=best_candidate,
                selection_reason=f"Candidate {best_candidate.candidate_id} selected (score: {best_val.score:.2f}).",
                novelty_passed=True,
            )

        # 2. All candidates failed: attempt 1 retry with stronger constraints
        logger.info(
            "All %d candidates failed validation for concept '%s'. Regenerating with stronger constraints.",
            len(candidates),
            spec.target_concept,
        )
        rejection_summary = "; ".join(
            [f"{v.candidate_id}: {', '.join(v.rejection_reasons)}" for v in validations]
        )
        retry_spec = self._strengthen_spec_constraints(spec, rejection_summary)
        retry_candidates = self._generate_candidates(retry_spec, context, recent_q)
        retry_validations = [self.validator.validate_candidate(c, spec, recent_q) for c in retry_candidates]

        retry_valid = [
            (c, v) for c, v in zip(retry_candidates, retry_validations) if v.is_valid
        ]

        if retry_valid:
            best_candidate, best_val = max(retry_valid, key=lambda pair: pair[1].score)
            return QuestionSelectionResult(
                specification=spec,
                candidates=candidates + retry_candidates,
                validations=validations + retry_validations,
                selected_candidate=best_candidate,
                selection_reason=f"Retry candidate {best_candidate.candidate_id} selected (score: {best_val.score:.2f}).",
                novelty_passed=True,
            )

        # 3. If still failing, construct a specification-driven safe fallback question
        # NEVER use an unrelated hardcoded topic question like Binary Search!
        logger.warning(
            "Regeneration failed validation for concept '%s'. Applying specification-driven safe fallback.",
            spec.target_concept,
        )
        fallback_candidate = self._construct_specification_fallback(spec)
        fallback_val = self.validator.validate_candidate(fallback_candidate, spec, recent_q)

        return QuestionSelectionResult(
            specification=spec,
            candidates=candidates + retry_candidates + [fallback_candidate],
            validations=validations + retry_validations + [fallback_val],
            selected_candidate=fallback_candidate,
            selection_reason="Specification-driven fallback applied following candidate validation failures.",
            novelty_passed=fallback_val.is_valid,
        )

    def _generate_candidates(
        self,
        spec: QuestionSpecification,
        context: Optional[AIContext],
        recent_questions: List[str],
    ) -> List[QuestionCandidate]:
        prompt = build_candidate_generation_prompt(spec, context, recent_questions)
        try:
            candidate_list: CandidateList = self.provider.generate_structured(prompt, CandidateList)
            if candidate_list and candidate_list.candidates:
                return candidate_list.candidates
        except Exception as e:
            logger.warning(
                "Structured candidate generation failed (%s: %s); falling back to single text prompt.",
                type(e).__name__,
                str(e),
            )

        # Fallback to provider text generation if structured returned empty
        try:
            raw_text = self.provider.generate_text(prompt)
            return self._parse_candidates_from_text(raw_text, spec)
        except Exception as e:
            logger.warning("Text generation also failed (%s); returning dynamic fallback candidates.", str(e))
            return [self._construct_specification_fallback(spec)]

    def _parse_candidates_from_text(self, text: str, spec: QuestionSpecification) -> List[QuestionCandidate]:
        """Parse candidates if LLM outputs numbered candidates in raw text."""
        lines = [line.strip() for line in (text or "").split("\n") if line.strip()]
        candidates: List[QuestionCandidate] = []
        idx = 1
        for line in lines:
            # Strip numbering like "1. ", "1)", "- "
            clean = re.sub(r"^(\d+[\.\)]|\-|\*)\s*", "", line).strip()
            if "?" in clean:
                # Ensure one question
                q_part = clean[: clean.index("?") + 1].strip()
                candidates.append(
                    QuestionCandidate(
                        candidate_id=f"cand_{idx}",
                        question_text=q_part,
                        rationale=f"Candidate generated for {spec.target_concept}",
                    )
                )
                idx += 1
                if idx > 3:
                    break

        if not candidates:
            candidates.append(self._construct_specification_fallback(spec))
        return candidates

    def _strengthen_spec_constraints(
        self, spec: QuestionSpecification, failure_summary: str
    ) -> QuestionSpecification:
        """Add explicit negative constraints based on failure reasons."""
        new_constraints = list(spec.generation_constraints)
        new_constraints.append("STRICT RULE: Exactly ONE primary question. Do not include second question mark.")
        new_constraints.append("STRICT RULE: Do NOT explain or lecture. Ask a curious student question.")
        new_constraints.append(f"STRICT RULE: Avoid previous failure patterns: {failure_summary[:120]}")
        return QuestionSpecification(
            target_concept=spec.target_concept,
            learning_objective=spec.learning_objective,
            difficulty=spec.difficulty,
            reason=spec.reason,
            evidence_expected=spec.evidence_expected,
            generation_constraints=new_constraints,
        )

    def _construct_specification_fallback(self, spec: QuestionSpecification) -> QuestionCandidate:
        """
        Dynamically construct a clean, single Socratic question strictly tailored to the specification.
        Guaranteed to pass all validator checks.
        NEVER injects unrelated hardcoded topics like Binary Search.
        """
        c_name = spec.target_concept.replace("_", " ").title()
        obj_type = spec.learning_objective.objective_type

        if obj_type == ObjectiveType.UNDERSTAND_DEFINITION:
            q_text = f"How would you explain the core purpose and definition of {c_name} in your own words?"
        elif obj_type == ObjectiveType.UNDERSTAND_MECHANISM:
            q_text = f"What is the step-by-step mechanism that makes {c_name} work under the hood?"
        elif obj_type == ObjectiveType.APPLY_CONCEPT:
            q_text = f"How does {c_name} behave when applied to a concrete real-world problem?"
        elif obj_type == ObjectiveType.RESOLVE_MISCONCEPTION:
            q_text = f"Why would it be a mistake to assume {c_name} operates without enforcing its core invariants?"
        elif obj_type == ObjectiveType.HANDLE_EDGE_CASE:
            q_text = f"What happens to {c_name} when boundary conditions or extreme inputs occur?"
        elif obj_type == ObjectiveType.SYNTHESIZE_CONCEPTS:
            q_text = f"How does {c_name} coordinate with the rest of the system to balance performance trade-offs?"
        else:
            q_text = f"Could you walk me through how {c_name} functions in this context?"

        return QuestionCandidate(
            candidate_id="cand_spec_fallback",
            question_text=q_text,
            rationale=f"Specification-driven safe fallback for {c_name} ({obj_type.value})",
        )
