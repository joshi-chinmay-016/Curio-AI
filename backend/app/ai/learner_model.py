"""
Learner Model and Learning State Manager for Curio AI (Phase D).
Source of truth for demonstrated learner understanding.
Enforces deterministic, bounded mastery updates based strictly on evidence.
"""
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

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
    """

    def __init__(self, model: Optional[LearnerModel] = None, session_id: str = "default_session"):
        self.model = model or LearnerModel(session_id=session_id)

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

    def update_from_evaluation(
        self,
        concept_id: str,
        evaluation: TurnEvaluation,
        interpretation: Optional[TurnInterpretation] = None,
    ) -> ConceptState:
        """
        Update concept state deterministically based on substantive TurnEvaluation.
        """
        if not concept_id:
            concept_id = "general_understanding"

        state = self.get_or_create_concept_state(concept_id)

        # If interpretation indicates pure acknowledgement without answer evidence, do NOT award mastery
        if interpretation and interpretation.intent in (
            TurnIntent.ACKNOWLEDGEMENT,
            TurnIntent.READY_FOR_VERIFICATION,
            TurnIntent.OFF_TOPIC,
            TurnIntent.CLARIFICATION_REQUEST,
        ):
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

        elif correctness >= 0.70:
            # Substantive correct answer demonstrates understanding
            state.evidence_count += 1
            delta = (1.0 - state.mastery) * 0.40
            state.mastery = min(1.0, state.mastery + delta)
            state.confidence = min(1.0, max(state.confidence, correctness * 0.9))

            # If it was marked as a gap and now answered correctly without misconception, resolve it
            if state.unresolved_gap and correctness >= 0.80:
                state.unresolved_gap = False
                state.active_misconceptions = []
                if concept_id in self.model.unresolved_gaps:
                    self.model.unresolved_gaps.remove(concept_id)

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
