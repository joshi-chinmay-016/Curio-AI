"""
Deterministic Scoring and Mastery Engine for Curio AI (Phase 3D).
Calculates:
- Bounded understanding scores (0.0 to 100.0)
- Evidence confidence metrics (0.0 to 1.0)
- Deterministic mastery level mapping
- Concept-level assessments with evidence references
"""
from typing import Dict, List, Tuple
from backend.app.ai.schemas import (
    ConceptAssessment,
    ConceptEvidenceItem,
    MasteryLevel,
    SessionEvidence,
    TurnEvidence,
)


class ScoringEngine:
    """
    Deterministic pedagogical scoring engine.
    Ensures that scores are bounded, explainable, and guarded against insufficient evidence.
    """

    # Dimension weights for turn-level evaluation
    WEIGHT_CORRECTNESS = 0.35
    WEIGHT_COMPLETENESS = 0.20
    WEIGHT_DEPTH = 0.20
    WEIGHT_CLARITY = 0.15
    WEIGHT_RELEVANCE = 0.10

    # Mastery level thresholds
    THRESHOLD_MASTERY = 85.0
    THRESHOLD_PROFICIENT = 70.0
    THRESHOLD_DEVELOPING = 45.0

    # Minimum evidence confidence required for top tiers
    MIN_CONFIDENCE_MASTERY = 0.70
    MIN_CONFIDENCE_PROFICIENT = 0.50

    def calculate_turn_score(self, turn: TurnEvidence) -> float:
        """
        Calculate weighted score (0.0 to 100.0) for a single turn.
        Includes a difficulty scaling factor.
        """
        ev = turn.evaluation
        base_score = (
            ev.correctness * self.WEIGHT_CORRECTNESS
            + ev.completeness * self.WEIGHT_COMPLETENESS
            + ev.depth * self.WEIGHT_DEPTH
            + ev.clarity * self.WEIGHT_CLARITY
            + ev.relevance * self.WEIGHT_RELEVANCE
        ) * 100.0

        # Difficulty scaling: rewarding higher difficulty successfully handled
        # Difficulty 1: 0.85, Diff 2: 0.925, Diff 3: 1.0, Diff 4: 1.075, Diff 5: 1.15
        diff_factor = 0.85 + (turn.difficulty - 1) * 0.075

        # If the answer is weak (correctness < 0.5), higher difficulty doesn't boost a failure
        if ev.correctness < 0.5:
            scaled = base_score
        else:
            scaled = base_score * diff_factor

        # Teacher intervention penalty if stuck
        if ev.stuck_probability > 0.6:
            scaled = min(scaled, 40.0)

        return max(0.0, min(100.0, scaled))

    def calculate_evidence_confidence(self, evidence: SessionEvidence) -> float:
        """
        Calculate evidence confidence reflecting how much structured data exists
        to support the assessment conclusions.

        Factors:
        - Number of evaluated turns (up to 5 turns for full weight)
        - Concept coverage (up to 2 concepts)
        - Difficulty coverage (progression explored)
        """
        if evidence.total_learner_turns == 0:
            return 0.0

        # Turn volume factor: 1 turn = 0.25, 2 = 0.5, 3 = 0.7, 4 = 0.85, 5+ = 1.0
        turns = evidence.total_learner_turns
        if turns == 1:
            return 0.25
        elif turns == 2:
            turn_factor = 0.45
        elif turns == 3:
            turn_factor = 0.70
        elif turns == 4:
            turn_factor = 0.85
        else:
            turn_factor = 1.0

        # Concept coverage factor
        num_concepts = len(evidence.concepts_encountered)
        concept_factor = min(1.0, max(0.5, num_concepts * 0.5))

        # Consistency factor: penalize if score variance is erratic
        consistency_factor = 0.95
        if turns >= 3:
            scores = [self.calculate_turn_score(t) for t in evidence.turns]
            variance = max(scores) - min(scores)
            if variance > 60:
                consistency_factor = 0.80

        confidence = turn_factor * 0.6 + concept_factor * 0.25 + consistency_factor * 0.15
        if turns == 2:
            confidence = min(confidence, 0.48)
        return round(max(0.0, min(1.0, confidence)), 2)

    def determine_mastery_level(
        self, score: float, evidence_confidence: float
    ) -> MasteryLevel:
        """
        Deterministically maps understanding score and evidence confidence to MasteryLevel.
        Enforces insufficient evidence guards to prevent premature mastery claims.
        """
        if score >= self.THRESHOLD_MASTERY:
            if evidence_confidence >= self.MIN_CONFIDENCE_MASTERY:
                return MasteryLevel.MASTERY
            elif evidence_confidence >= self.MIN_CONFIDENCE_PROFICIENT:
                return MasteryLevel.PROFICIENT
            else:
                return MasteryLevel.DEVELOPING

        if score >= self.THRESHOLD_PROFICIENT:
            if evidence_confidence >= self.MIN_CONFIDENCE_PROFICIENT:
                return MasteryLevel.PROFICIENT
            else:
                return MasteryLevel.DEVELOPING

        if score >= self.THRESHOLD_DEVELOPING:
            return MasteryLevel.DEVELOPING

        return MasteryLevel.BEGINNER

    def calculate_session_score(self, evidence: SessionEvidence) -> float:
        """
        Deterministically aggregate turn scores into an overall understanding score (0-100).
        """
        if not evidence.turns:
            return 0.0

        turn_scores = [self.calculate_turn_score(t) for t in evidence.turns]

        # Recent turns have slightly higher weight to reward learning progression
        weighted_sum = 0.0
        total_weight = 0.0

        for i, score in enumerate(turn_scores):
            weight = 1.0 + (i / max(1, len(turn_scores) - 1)) * 0.5
            weighted_sum += score * weight
            total_weight += weight

        avg_score = weighted_sum / max(1.0, total_weight)

        # Penalty if there are unresolved teacher interventions
        unresolved_interventions = sum(
            1 for ti in evidence.teacher_interventions if not ti.verification_passed
        )
        if unresolved_interventions > 0:
            avg_score = max(0.0, avg_score - (unresolved_interventions * 10.0))

        return round(max(0.0, min(100.0, avg_score)), 1)

    def assess_concepts(self, evidence: SessionEvidence) -> List[ConceptAssessment]:
        """
        Produces granular ConceptAssessment objects for each concept encountered in the session.
        """
        assessments: List[ConceptAssessment] = []

        for concept_name, c_item in evidence.concept_evidence_map.items():
            relevant_turns = [
                evidence.turns[i]
                for i in c_item.turns_evaluated
                if i < len(evidence.turns)
            ]
            if not relevant_turns:
                continue

            turn_scores = [self.calculate_turn_score(t) for t in relevant_turns]
            avg_concept_score = sum(turn_scores) / len(turn_scores)

            # Confidence based on turns evaluated for this concept
            c_conf = min(1.0, len(relevant_turns) / 3.0)

            # Mastery level
            c_mastery = self.determine_mastery_level(avg_concept_score, c_conf)

            # Strengths: turns with correctness >= 0.8
            strengths: List[str] = []
            for t in relevant_turns:
                if t.evaluation.correctness >= 0.8:
                    for mc in t.evaluation.mastered_concepts:
                        if mc and mc not in strengths:
                            strengths.append(mc)
            if not strengths and avg_concept_score >= 70.0:
                strengths.append(f"Demonstrated working knowledge of {concept_name}")

            # Evidence references (e.g. ["turn_0", "turn_2"])
            ev_refs = [f"turn_{t.turn_index}" for t in relevant_turns]

            assessments.append(
                ConceptAssessment(
                    concept=concept_name,
                    understanding_score=round(avg_concept_score, 1),
                    confidence=round(c_conf, 2),
                    mastery_level=c_mastery,
                    strengths=strengths,
                    gaps=list(c_item.gaps),
                    misconceptions=list(c_item.misconceptions),
                    evidence_references=ev_refs,
                )
            )

        return assessments
