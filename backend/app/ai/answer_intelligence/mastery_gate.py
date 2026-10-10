"""
Mastery Gate for Curio AI.
Serves as the deterministic guardian protecting the Learner Model from false mastery.
No LLM output or raw evaluation can directly increase mastery without passing through this gate.
"""
import logging
from typing import Optional
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceStatus,
    LearningAssessment,
    MasteryDecision,
    RelevanceLevel,
)

logger = logging.getLogger("curio.ai.answer_intelligence.mastery_gate")


class MasteryGate:
    """
    Evaluates a LearningAssessment and determines what, if any, mastery updates are permitted.
    """

    def __init__(
        self,
        min_relevance_score: float = 0.65,
        min_alignment_score: float = 0.50,
        min_confidence_score: float = 0.60,
    ):
        self.min_relevance_score = min_relevance_score
        self.min_alignment_score = min_alignment_score
        self.min_confidence_score = min_confidence_score

    def evaluate(self, assessment: LearningAssessment, concept_id: str) -> MasteryDecision:
        """
        Determines if the assessment provides sufficient verified evidence to update mastery.
        """
        cid = concept_id or "target_concept"

        # 1. Non-answer intents NEVER support mastery
        if assessment.intent in (
            AssessmentIntent.ACKNOWLEDGEMENT,
            AssessmentIntent.READY_TO_CONTINUE,
            AssessmentIntent.HELP_REQUEST,
            AssessmentIntent.CLARIFICATION_REQUEST,
            AssessmentIntent.QUESTION_ABOUT_CONCEPT,
            AssessmentIntent.OFF_TOPIC,
            AssessmentIntent.EMPTY_RESPONSE,
            AssessmentIntent.UNCERTAIN,
        ):
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=False,
                record_as_misconception=False,
                concept_id=cid,
                reason=f"Intent '{assessment.intent.value}' does not provide substantive answer evidence.",
            )

        # 2. Irrelevant or Off-Topic responses NEVER support mastery
        if (
            assessment.relevance_level in (RelevanceLevel.IRRELEVANT, RelevanceLevel.UNCERTAIN)
            or assessment.relevance_score < self.min_relevance_score
            or assessment.classification in (AssessmentClassification.IRRELEVANT, AssessmentClassification.OFF_TOPIC)
        ):
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=False,
                record_as_misconception=False,
                concept_id=cid,
                reason=f"Response is irrelevant to target concept (relevance={assessment.relevance_score:.2f}). Mastery update denied.",
            )

        # 3. Abstention or Low Confidence NEVER support positive mastery
        if (
            assessment.assessment_status == AssessmentStatus.ABSTAIN
            or assessment.confidence < self.min_confidence_score
        ):
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=False,
                record_as_misconception=False,
                concept_id=cid,
                reason=f"Assessment status is {assessment.assessment_status.value} (conf={assessment.confidence:.2f}). Abstaining from mastery update.",
            )

        # 4. Severe Misconceptions prevent positive mastery and record gap
        if assessment.misconception_status or assessment.misconceptions:
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=True,
                record_as_misconception=True,
                concept_id=cid,
                reason="Active misconception identified. Mastery update blocked and gap recorded.",
            )

        # 5. Contradictory Claims block mastery
        if (
            assessment.correctness == CorrectnessLevel.CONTRADICTORY
            or assessment.classification == AssessmentClassification.CONTRADICTORY
            or assessment.contradictory_claims
        ):
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=True,
                record_as_misconception=False,
                concept_id=cid,
                reason="Learner made contradictory claims regarding target concept. Mastery blocked.",
            )

        # 6. Completely incorrect answers
        if assessment.correctness == CorrectnessLevel.INCORRECT or assessment.correctness_score < 0.35:
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=True,
                record_as_misconception=False,
                concept_id=cid,
                reason="Answer is incorrect for target concept. Mastery blocked and gap recorded.",
            )

        # 7. Low concept alignment
        if assessment.concept_alignment_score < self.min_alignment_score:
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=False,
                allowed_delta=0.0,
                evidence_count_increment=0,
                record_as_gap=False,
                record_as_misconception=False,
                concept_id=cid,
                reason=f"Concept alignment score ({assessment.concept_alignment_score:.2f}) below threshold {self.min_alignment_score}.",
            )

        # Count supported evidence items
        supported_items = sum(1 for it in assessment.evidence if it.status == EvidenceStatus.SUPPORTED)
        has_supported_evidence = supported_items > 0

        # 8. Correct and Complete answer with strong evidence -> Positive Mastery
        if (
            assessment.correctness == CorrectnessLevel.CORRECT
            and assessment.correctness_score >= 0.70
            and has_supported_evidence
        ):
            # Calculate calibrated delta
            delta = 0.40 if assessment.completeness in (CompletenessLevel.COMPLETE, CompletenessLevel.SUBSTANTIAL) else 0.25
            return MasteryDecision(
                supports_mastery=True,
                mastery_delta_allowed=True,
                allowed_delta=delta,
                evidence_count_increment=1,
                record_as_gap=False,
                record_as_misconception=False,
                concept_id=cid,
                reason="Verified substantive evidence of understanding provided. Positive mastery update approved.",
            )

        # 9. Partially correct or incomplete answer -> Bounded partial evidence only if evidence verified
        if (
            has_supported_evidence
            and (
                assessment.correctness in (CorrectnessLevel.PARTIALLY_CORRECT, CorrectnessLevel.INCOMPLETE)
                or assessment.correctness_score >= 0.40
            )
        ):
            return MasteryDecision(
                supports_mastery=False,
                mastery_delta_allowed=True,
                allowed_delta=0.15,
                evidence_count_increment=1,
                record_as_gap=False,
                record_as_misconception=False,
                concept_id=cid,
                reason="Partial understanding demonstrated. Bounded partial progression granted.",
            )

        # Default fallback: safe denial
        return MasteryDecision(
            supports_mastery=False,
            mastery_delta_allowed=False,
            allowed_delta=0.0,
            evidence_count_increment=0,
            record_as_gap=False,
            record_as_misconception=False,
            concept_id=cid,
            reason="Insufficient evidence demonstrated to justify mastery progression.",
        )
