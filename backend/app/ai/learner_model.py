"""
Learner Model and Learning State Manager for Curio AI (Phase D).
Source of truth for demonstrated learner understanding.
Enforces deterministic, bounded mastery updates based strictly on evidence.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.schemas import (
    EvidenceStatus,
    LearningAssessment,
    MasteryDecision,
)
from backend.app.ai.schemas import (
    ConceptState,
    LearnerModel,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)

logger = logging.getLogger("curio.ai.learner_model")


class LearnerModelManager:
    """
    Manages deterministic, evidence-based updates to the LearnerModel.
    Invariants:
    1. Acknowledgements alone NEVER increase mastery or evidence count.
    2. Correct explanations yield controlled, bounded mastery gains.
    3. Strong misconceptions penalize mastery, record misconception count, and mark gap.
    4. Successful Teacher verification resolves gaps and boosts mastery.
    5. Failed Teacher verification increments attempts and preserves unresolved gap.
    6. Irrelevant or off-topic responses NEVER increase mastery.
    """

    def __init__(
        self,
        model: Optional[LearnerModel] = None,
        session_id: str = "default_session",
        mastery_gate: Optional[MasteryGate] = None,
    ):
        self.model = model or LearnerModel(session_id=session_id)
        self.mastery_gate = mastery_gate or MasteryGate()

    def get_or_create_concept_state(self, concept_id: str) -> ConceptState:
        return self.model.get_or_create_concept(concept_id)

    def record_acknowledgement(self, concept_id: str) -> ConceptState:
        """
        Record learner acknowledgement (e.g. 'ok', 'I understand').
        CRITICAL RULE: Acknowledgement ALONE does NOT increase mastery or evidence count.
        """
        state = self.get_or_create_concept_state(concept_id)
        state.attempt_count += 1
        # No change to mastery, confidence, or evidence_count!
        return state

    def update_from_assessment(
        self,
        concept_id: str,
        assessment: LearningAssessment,
    ) -> ConceptState:
        """
        Update concept state strictly governed by MasteryGate.
        Protects against false mastery from irrelevant, incorrect, contradictory, or acknowledgement turns.
        """
        if not concept_id:
            concept_id = "general_understanding"

        decision: MasteryDecision = self.mastery_gate.evaluate(assessment, concept_id)
        state = self.get_or_create_concept_state(concept_id)
        now_str = datetime.now(timezone.utc).isoformat()
        state.last_evaluated = now_str
        state.attempt_count += 1

        score = float(assessment.correctness_score)
        state.recent_scores.append(score)
        if len(state.recent_scores) > 5:
            state.recent_scores = state.recent_scores[-5:]
        self.model.recent_performances.append(score)
        if len(self.model.recent_performances) > 10:
            self.model.recent_performances = self.model.recent_performances[-10:]

        # Track assessed objective
        obj_id = None
        if hasattr(assessment, "metadata") and isinstance(assessment.metadata, dict):
            obj_id = assessment.metadata.get("objective_id")
        if obj_id:
            if obj_id not in state.assessed_objectives:
                state.assessed_objectives.append(obj_id)

        if decision.record_as_misconception:
            state.misconception_count += len(assessment.misconceptions) or 1
            for m in assessment.misconceptions:
                m_desc = m.description if hasattr(m, "description") else str(m)
                if m_desc not in state.active_misconceptions:
                    state.active_misconceptions.append(m_desc)
            state.unresolved_gap = True
            if concept_id not in self.model.unresolved_gaps:
                self.model.unresolved_gaps.append(concept_id)
            state.mastery = max(0.0, min(0.35, state.mastery * 0.7))
            state.confidence = max(0.1, state.confidence * 0.8)
            if obj_id and obj_id in state.mastered_objectives:
                state.mastered_objectives.remove(obj_id)

        elif decision.record_as_gap:
            state.unresolved_gap = True
            if concept_id not in self.model.unresolved_gaps:
                self.model.unresolved_gaps.append(concept_id)
            state.mastery = max(0.0, state.mastery * 0.85)
            state.confidence = max(0.1, state.confidence * 0.75)
            if obj_id and obj_id in state.mastered_objectives:
                state.mastered_objectives.remove(obj_id)

        elif decision.mastery_delta_allowed:
            state.evidence_count += decision.evidence_count_increment
            delta = (1.0 - state.mastery) * decision.allowed_delta
            state.mastery = min(1.0, state.mastery + delta)
            state.confidence = min(1.0, max(state.confidence, score * 0.9))

            if state.unresolved_gap and score >= 0.80 and not assessment.misconception_status:
                self._resolve_misconceptions(concept_id, state, assessment=assessment)

            # Objective mastery requires demonstrated score without active gaps/misconceptions
            if obj_id and score >= 0.75 and not state.unresolved_gap and not state.active_misconceptions:
                if obj_id not in state.mastered_objectives:
                    state.mastered_objectives.append(obj_id)

        self._refresh_overall_mastery()
        return state

    def update_from_evaluation(
        self,
        concept_id: str,
        evaluation: TurnEvaluation,
        interpretation: Optional[TurnInterpretation] = None,
        resolved_misconceptions: Optional[List[str]] = None,
        objective_id: Optional[str] = None,
    ) -> ConceptState:
        """
        Update concept state deterministically based on substantive TurnEvaluation.
        """
        if not concept_id:
            concept_id = "general_understanding"

        state = self.get_or_create_concept_state(concept_id)

        # Track assessed objective
        if objective_id:
            if objective_id not in state.assessed_objectives:
                state.assessed_objectives.append(objective_id)

        # If interpretation indicates pure acknowledgement without answer evidence, do NOT award mastery
        if interpretation and interpretation.intent in (
            TurnIntent.ACKNOWLEDGEMENT,
            TurnIntent.READY_FOR_VERIFICATION,
            TurnIntent.OFF_TOPIC,
            TurnIntent.CLARIFICATION_REQUEST,
        ):
            state.attempt_count += 1
            return state

        # Irrelevant responses NEVER award positive mastery
        if float(getattr(evaluation, "relevance", 1.0)) < 0.65:
            state.attempt_count += 1
            return state

        now_str = datetime.now(timezone.utc).isoformat()
        state.last_evaluated = now_str
        state.attempt_count += 1

        correctness = float(evaluation.correctness)
        state.recent_scores.append(correctness)
        if len(state.recent_scores) > 5:
            state.recent_scores = state.recent_scores[-5:]

        self.model.recent_performances.append(correctness)
        if len(self.model.recent_performances) > 10:
            self.model.recent_performances = self.model.recent_performances[-10:]

        has_misconception = bool(evaluation.misconceptions)

        if has_misconception:
            # Misconceptions prevent fake mastery
            state.misconception_count += len(evaluation.misconceptions)
            for m in evaluation.misconceptions:
                if m not in state.active_misconceptions:
                    state.active_misconceptions.append(m)
            state.unresolved_gap = True
            if concept_id not in self.model.unresolved_gaps:
                self.model.unresolved_gaps.append(concept_id)

            # Cap or degrade mastery on misconception
            state.mastery = max(0.0, min(0.35, state.mastery * 0.7))
            state.confidence = max(0.1, state.confidence * 0.8)
            if objective_id and objective_id in state.mastered_objectives:
                state.mastered_objectives.remove(objective_id)

        elif correctness >= 0.70:
            # Substantive correct answer demonstrates understanding
            state.evidence_count += 1
            delta = (1.0 - state.mastery) * 0.40
            state.mastery = min(1.0, state.mastery + delta)
            state.confidence = min(1.0, max(state.confidence, correctness * 0.9))

            # If it was marked as a gap and now answered correctly without misconception, resolve it
            if state.unresolved_gap and correctness >= 0.80:
                self._resolve_misconceptions(
                    concept_id,
                    state,
                    evaluation=evaluation,
                    resolved_misconceptions=resolved_misconceptions,
                )

            # Objective mastery requires demonstrated score without active gaps/misconceptions
            if objective_id and correctness >= 0.75 and not state.unresolved_gap and not state.active_misconceptions:
                if objective_id not in state.mastered_objectives:
                    state.mastered_objectives.append(objective_id)

        elif correctness >= 0.40:
            # Partial understanding
            state.evidence_count += 1
            delta = (1.0 - state.mastery) * 0.15
            state.mastery = min(0.65, state.mastery + delta)
            state.confidence = max(0.2, min(0.7, state.confidence + 0.05))

        else:
            # Weak or wrong answer without explicit misconception
            state.unresolved_gap = True
            if concept_id not in self.model.unresolved_gaps:
                self.model.unresolved_gaps.append(concept_id)
            state.mastery = max(0.0, state.mastery * 0.85)
            state.confidence = max(0.1, state.confidence * 0.75)
            if objective_id and objective_id in state.mastered_objectives:
                state.mastered_objectives.remove(objective_id)

        self._refresh_overall_mastery()
        return state

    def record_teacher_verification(
        self,
        gap_concept: str,
        passed: bool,
        attempt_count: int = 1,
    ) -> ConceptState:
        """
        Record the outcome of a Teacher Mode verification question.
        Passed -> clears gap, sets proficient mastery, updates evidence.
        Failed -> preserves gap, keeps mastery low.
        """
        cid = gap_concept or "taught_gap"
        state = self.get_or_create_concept_state(cid)
        now_str = datetime.now(timezone.utc).isoformat()
        state.last_evaluated = now_str
        state.attempt_count += 1

        if passed:
            state.unresolved_gap = False
            state.active_misconceptions = []
            state.evidence_count += 1
            # Verification proves understanding of this gap
            state.mastery = max(0.75, state.mastery)
            state.confidence = max(0.70, state.confidence)
            if cid in self.model.unresolved_gaps:
                self.model.unresolved_gaps.remove(cid)
        else:
            state.unresolved_gap = True
            if cid not in self.model.unresolved_gaps:
                self.model.unresolved_gaps.append(cid)
            state.mastery = min(0.30, state.mastery)

        self._refresh_overall_mastery()
        return state

    def _refresh_overall_mastery(self) -> float:
        if not self.model.concepts:
            self.model.overall_mastery = 0.0
            return 0.0
        scores = [c.mastery for c in self.model.concepts.values()]
        self.model.overall_mastery = round(sum(scores) / len(scores), 3)
        return self.model.overall_mastery

    def _resolve_misconceptions(
        self,
        concept_id: str,
        state: ConceptState,
        assessment: Optional[LearningAssessment] = None,
        evaluation: Optional[TurnEvaluation] = None,
        resolved_misconceptions: Optional[List[str]] = None,
    ) -> None:
        """
        Precise, conservative resolution of active misconceptions for a concept.
        Prevents answering one question from clearing unresolved misconceptions
        without evidence that each specific misconception was resolved.
        """
        import re

        active = list(state.active_misconceptions or [])
        if not active:
            state.unresolved_gap = False
            state.active_misconceptions = []
            if concept_id in self.model.unresolved_gaps:
                self.model.unresolved_gaps.remove(concept_id)
            return

        # 1. Determine explicitly resolved misconceptions from argument, assessment metadata, or attributes
        explicit_resolved: Optional[List[str]] = None
        if resolved_misconceptions is not None:
            explicit_resolved = list(resolved_misconceptions)
        elif assessment is not None:
            if hasattr(assessment, "metadata") and isinstance(assessment.metadata, dict):
                if "resolved_misconceptions" in assessment.metadata:
                    raw = assessment.metadata.get("resolved_misconceptions")
                    explicit_resolved = list(raw) if raw is not None else None
            if explicit_resolved is None and hasattr(assessment, "resolved_misconceptions"):
                raw = getattr(assessment, "resolved_misconceptions")
                explicit_resolved = list(raw) if raw is not None else None
        elif evaluation is not None:
            if hasattr(evaluation, "resolved_misconceptions"):
                raw = getattr(evaluation, "resolved_misconceptions")
                explicit_resolved = list(raw) if raw is not None else None

        # 2. Extract supported evidence descriptions from assessment
        supported_evidence_descriptions: List[str] = []
        if assessment is not None and getattr(assessment, "evidence", None):
            for ev in assessment.evidence:
                status_val = getattr(ev, "status", None)
                is_supported = (
                    status_val in (EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIALLY_SUPPORTED)
                    or str(status_val).lower() in (
                        "supported",
                        "partially_supported",
                        "evidencestatus.supported",
                        "evidencestatus.partially_supported",
                    )
                )
                if is_supported and getattr(ev, "expected_description", None):
                    supported_evidence_descriptions.append(str(ev.expected_description))

        def _normalize_text(text: str) -> str:
            t = text.strip().lower()
            t = re.sub(r"^[\s\"'.,;:!?]+|[\s\"'.,;:!?]+$", "", t)
            t = re.sub(r"\s+", " ", t)
            return t

        def _matches_misconception(candidate: str, target: str) -> bool:
            norm_c = _normalize_text(candidate)
            norm_t = _normalize_text(target)
            if not norm_c or not norm_t:
                return False
            if norm_c == norm_t:
                return True
            for prefix in (
                "resolves:",
                "refutes:",
                "resolution of:",
                "counter-evidence for:",
                "resolved misconception:",
                "refuted misconception:",
            ):
                if norm_c.startswith(prefix):
                    stripped = _normalize_text(norm_c[len(prefix):])
                    if stripped == norm_t:
                        return True
            return False

        def is_misconception_evidenced(m: str) -> bool:
            if explicit_resolved is not None:
                for r in explicit_resolved:
                    if _matches_misconception(str(r), m):
                        return True
            for ev_desc in supported_evidence_descriptions:
                if _matches_misconception(ev_desc, m):
                    return True
            return False

        # 3. Apply precise resolution rules uniformly
        # A misconception is ONLY removed if adequate resolution evidence was provided.
        remaining = []
        for m in active:
            if not is_misconception_evidenced(m):
                remaining.append(m)
        state.active_misconceptions = remaining

        # 4. Synchronize unresolved_gap flag and model-level unresolved_gaps list
        if not state.active_misconceptions:
            state.unresolved_gap = False
            if concept_id in self.model.unresolved_gaps:
                self.model.unresolved_gaps.remove(concept_id)
        else:
            state.unresolved_gap = True
            if concept_id not in self.model.unresolved_gaps:
                self.model.unresolved_gaps.append(concept_id)

    def get_weakest_concepts(self, limit: int = 3) -> List[ConceptState]:
        """Return concepts ordered by mastery ascending, prioritizing unresolved gaps."""
        sorted_concepts = sorted(
            self.model.concepts.values(),
            key=lambda c: (0 if c.unresolved_gap else 1, c.mastery, -c.misconception_count),
        )
        return sorted_concepts[:limit]

    def export_mastery_dict(self) -> Dict[str, float]:
        """Export concept_id -> mastery mapping for SessionState synchronization."""
        return {cid: round(c.mastery, 3) for cid, c in self.model.concepts.items()}

    def export_misconception_counts_dict(self) -> Dict[str, int]:
        """Export concept_id -> cumulative misconception count mapping for SessionState synchronization."""
        return {cid: int(c.misconception_count) for cid, c in self.model.concepts.items()}
