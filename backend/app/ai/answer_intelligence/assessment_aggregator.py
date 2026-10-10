"""
Answer Intelligence Assessment Aggregator for Curio AI.
Executes the principled multi-stage pipeline:
  learner answer
    -> Turn / Intent Understanding
    -> Expected Evidence Derivation
    -> Semantic Relevance Assessment
    -> Claim Extraction
    -> Concept Alignment
    -> Evidence Extraction & Matching
    -> Correctness / Entailment Assessment
    -> Completeness Assessment
    -> Misconception Detection
    -> Confidence & Abstention
    -> LearningAssessment
    -> Mastery Gate
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Optional

from backend.app.ai.answer_intelligence.claim_extractor import ClaimExtractor
from backend.app.ai.answer_intelligence.concept_aligner import ConceptAligner
from backend.app.ai.answer_intelligence.confidence import ConfidenceEngine
from backend.app.ai.answer_intelligence.correctness_model import CorrectnessModel
from backend.app.ai.answer_intelligence.evidence_extractor import EvidenceExtractor
from backend.app.ai.answer_intelligence.intent_classifier import IntentClassifier
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.misconception_detector import MisconceptionDetector
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.providers.local_model import LocalAssessmentProvider
from backend.app.ai.answer_intelligence.relevance_model import SemanticRelevanceModel
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    LearningAssessment,
    RelevanceLevel,
)

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, ConceptModel, CurrentQuestion, LearningObjective, QuestionSpecification

logger = logging.getLogger("curio.ai.answer_intelligence.aggregator")


class AssessmentAggregator:
    """
    Main entry point for Answer Intelligence.
    Orchestrates decoupled assessment stages and returns structured LearningAssessment.
    """

    def __init__(
        self,
        provider: Optional[BaseAssessmentProvider] = None,
        mastery_gate: Optional[MasteryGate] = None,
    ):
        if provider is not None:
            self.provider = provider
        else:
            try:
                from backend.app.ai.answer_intelligence.providers.hybrid_provider import (
                    HybridSemanticProvider,
                )
                self.provider = HybridSemanticProvider()
            except Exception as exc:
                logger.warning(
                    f"HybridSemanticProvider initialization failed ({exc}). Falling back to LocalAssessmentProvider."
                )
                self.provider = LocalAssessmentProvider()
        self.intent_classifier = IntentClassifier(self.provider)
        self.relevance_model = SemanticRelevanceModel(self.provider)
        self.claim_extractor = ClaimExtractor(self.provider)
        self.concept_aligner = ConceptAligner(self.provider)
        self.evidence_extractor = EvidenceExtractor(self.provider)
        self.correctness_model = CorrectnessModel(self.provider)
        self.misconception_detector = MisconceptionDetector(self.provider)
        self.confidence_engine = ConfidenceEngine(self.provider)
        self.mastery_gate = mastery_gate or MasteryGate()

    def assess(
        self,
        user_message: str,
        context: Optional[AIContext] = None,
        current_question: Optional[CurrentQuestion] = None,
        concept_model: Optional[ConceptModel] = None,
        target_concept_override: Optional[str] = None,
        question_specification: Optional[QuestionSpecification] = None,
    ) -> LearningAssessment:
        raw_msg = (user_message or "").strip()
        topic = context.topic if context else "General Learning"

        # Resolve active question & target concept
        curr_q = current_question or (context.current_question if context else None)
        q_text = curr_q.content if curr_q else ""
        curr_mode = getattr(context, "current_mode", None) or (
            context.current_state.current_mode if (context and hasattr(context, "current_state")) else None
        )
        intervention = getattr(context, "teacher_intervention", None) or (
            context.current_state.teacher_intervention if (context and hasattr(context, "current_state")) else None
        )
        intervention_gap = intervention.gap if (intervention and getattr(intervention, "active", False)) else None

        target_concept = (
            target_concept_override
            or (intervention_gap if curr_mode == Mode.TEACHER and intervention_gap else None)
            or (curr_q.concept if curr_q else None)
            or (context.active_concept if context else None)
            or topic
        )

        concept_node = concept_model.get_concept(target_concept) if concept_model else None

        # -------------------------------------------------------------
        # 1. Intent Classification
        # -------------------------------------------------------------
        intent, intent_conf, is_answer_attempt = self.intent_classifier.classify(
            user_message=raw_msg,
            context=context,
            current_question=q_text,
        )

        # Handle non-answer turns immediately
        if intent == AssessmentIntent.EMPTY_RESPONSE:
            assessment = LearningAssessment(
                intent=intent,
                is_answer_attempt=False,
                relevance_score=0.0,
                relevance_level=RelevanceLevel.IRRELEVANT,
                concept_alignment_score=0.0,
                claims=[],
                evidence=[],
                correctness=CorrectnessLevel.UNASSESSABLE,
                correctness_score=0.0,
                completeness=CompletenessLevel.NOT_APPLICABLE,
                completeness_score=0.0,
                classification=AssessmentClassification.OFF_TOPIC,
                confidence=1.0,
                supports_mastery=False,
                assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
                recommended_learning_action="PROMPT_ANSWER",
            )
            return assessment

        if intent in (AssessmentIntent.ACKNOWLEDGEMENT, AssessmentIntent.READY_TO_CONTINUE):
            action = "VERIFY_UNDERSTANDING" if intent == AssessmentIntent.READY_TO_CONTINUE else "PROCEED"
            return LearningAssessment(
                intent=intent,
                is_answer_attempt=False,
                relevance_score=0.0,
                relevance_level=RelevanceLevel.IRRELEVANT,
                concept_alignment_score=0.0,
                claims=[],
                evidence=[],
                correctness=CorrectnessLevel.UNASSESSABLE,
                correctness_score=0.0,
                completeness=CompletenessLevel.NOT_APPLICABLE,
                completeness_score=0.0,
                classification=AssessmentClassification.ACKNOWLEDGEMENT,
                confidence=intent_conf,
                supports_mastery=False,
                assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
                recommended_learning_action=action,
            )

        if intent == AssessmentIntent.HELP_REQUEST:
            return LearningAssessment(
                intent=intent,
                is_answer_attempt=False,
                relevance_score=1.0,
                relevance_level=RelevanceLevel.RELEVANT,
                concept_alignment_score=1.0,
                claims=[],
                evidence=[],
                correctness=CorrectnessLevel.UNASSESSABLE,
                correctness_score=0.0,
                completeness=CompletenessLevel.NOT_APPLICABLE,
                completeness_score=0.0,
                classification=AssessmentClassification.HELP_REQUEST,
                confidence=intent_conf,
                supports_mastery=False,
                assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
                recommended_learning_action="TEACH_GAP",
            )

        if intent == AssessmentIntent.CLARIFICATION_REQUEST:
            return LearningAssessment(
                intent=intent,
                is_answer_attempt=False,
                relevance_score=1.0,
                relevance_level=RelevanceLevel.RELEVANT,
                concept_alignment_score=1.0,
                claims=[],
                evidence=[],
                correctness=CorrectnessLevel.UNASSESSABLE,
                correctness_score=0.0,
                completeness=CompletenessLevel.NOT_APPLICABLE,
                completeness_score=0.0,
                classification=AssessmentClassification.CLARIFICATION,
                confidence=intent_conf,
                supports_mastery=False,
                assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
                recommended_learning_action="CLARIFY_QUESTION",
            )

        if intent == AssessmentIntent.OFF_TOPIC:
            return LearningAssessment(
                intent=intent,
                is_answer_attempt=False,
                relevance_score=0.0,
                relevance_level=RelevanceLevel.IRRELEVANT,
                concept_alignment_score=0.0,
                claims=[],
                evidence=[],
                correctness=CorrectnessLevel.UNASSESSABLE,
                correctness_score=0.0,
                completeness=CompletenessLevel.NOT_APPLICABLE,
                completeness_score=0.0,
                classification=AssessmentClassification.OFF_TOPIC,
                confidence=intent_conf,
                supports_mastery=False,
                assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
                recommended_learning_action="REDIRECT_TO_TARGET",
            )

        obj = context.current_state.current_objective if context else None
        intervention = getattr(context, "teacher_intervention", None) or (
            context.current_state.teacher_intervention if (context and hasattr(context, "current_state")) else None
        )
        intervention_gap = intervention.gap if (intervention and getattr(intervention, "active", False)) else None
        expected = self.evidence_extractor.derive_expected_evidence(
            concept_id=target_concept,
            concept_node=concept_node,
            objective=obj,
            spec=question_specification,
            question_text=q_text,
            topic=topic,
            gap=intervention_gap,
        )

        # -------------------------------------------------------------
        # 3. Semantic Relevance Assessment (MANDATORY BEFORE CORRECTNESS)
        # -------------------------------------------------------------
        relevance_level, relevance_score = self.relevance_model.evaluate_relevance(
            user_message=raw_msg,
            question=q_text,
            target_concept=target_concept,
            topic=topic,
            expected=expected,
        )

        # CRITICAL PRINCIPLE: If irrelevant, do NOT assess correctness or grant mastery!
        if relevance_level == RelevanceLevel.IRRELEVANT or relevance_score < 0.20:
            claims = self.claim_extractor.extract(raw_msg, target_concept)
            return LearningAssessment(
                intent=intent,
                is_answer_attempt=True,
                relevance_score=relevance_score,
                relevance_level=RelevanceLevel.IRRELEVANT,
                concept_alignment_score=0.0,
                claims=claims,
                evidence=[],
                correctness=CorrectnessLevel.UNASSESSABLE,
                correctness_score=0.0,
                completeness=CompletenessLevel.NOT_APPLICABLE,
                completeness_score=0.0,
                classification=AssessmentClassification.IRRELEVANT,
                confidence=0.95,
                supports_mastery=False,
                assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
                recommended_learning_action="REDIRECT_TO_TARGET",
                metadata={"irrelevant_reason": "Answer does not address current question or target concept."},
            )

        # -------------------------------------------------------------
        # 4. Claim Extraction
        # -------------------------------------------------------------
        claims = self.claim_extractor.extract(raw_msg, target_concept)

        # -------------------------------------------------------------
        # 5. Concept Alignment
        # -------------------------------------------------------------
        alignment_score = self.concept_aligner.align(
            claims=claims,
            concept_node=concept_node,
            target_concept=target_concept,
            concept_model=concept_model,
        )

        # -------------------------------------------------------------
        # 6. Evidence Matching
        # -------------------------------------------------------------
        evidence_items = self.evidence_extractor.match(claims, expected)

        # -------------------------------------------------------------
        # 7. Correctness Evaluation
        # -------------------------------------------------------------
        correctness, correctness_score, contradictory = self.correctness_model.evaluate_correctness(
            claims=claims,
            evidence_items=evidence_items,
            expected=expected,
            relevance_level=relevance_level,
        )

        # -------------------------------------------------------------
        # 8. Completeness Evaluation
        # -------------------------------------------------------------
        completeness, completeness_score, missing_concepts = self.correctness_model.evaluate_completeness(
            evidence_items=evidence_items,
            expected=expected,
            relevance_level=relevance_level,
        )

        # -------------------------------------------------------------
        # 9. Misconception Detection
        # -------------------------------------------------------------
        misconceptions = self.misconception_detector.detect(
            user_message=raw_msg,
            claims=claims,
            expected=expected,
            relevance_level=relevance_level,
        )
        has_misconception = len(misconceptions) > 0

        # -------------------------------------------------------------
        # 10. Confidence & Abstention
        # -------------------------------------------------------------
        status, conf = self.confidence_engine.assess_confidence(
            intent=intent,
            relevance=relevance_level,
            relevance_score=relevance_score,
            correctness=correctness,
            claims=claims,
            evidence_items=evidence_items,
        )

        # -------------------------------------------------------------
        # 11. Classification Synthesis
        # -------------------------------------------------------------
        if has_misconception:
            classification = AssessmentClassification.MISCONCEPTION
            correctness = CorrectnessLevel.MISCONCEPTION
            action = "TEACH_MISCONCEPTION"
        elif contradictory:
            classification = AssessmentClassification.CONTRADICTORY
            action = "CHALLENGE_CONTRADICTION"
        elif correctness == CorrectnessLevel.CORRECT:
            if completeness in (CompletenessLevel.COMPLETE, CompletenessLevel.SUBSTANTIAL):
                classification = AssessmentClassification.CORRECT
                action = "ADVANCE_CONCEPT"
            else:
                classification = AssessmentClassification.INCOMPLETE
                action = "PROBE_MISSING_DETAIL"
        elif correctness == CorrectnessLevel.PARTIALLY_CORRECT:
            classification = AssessmentClassification.PARTIAL
            action = "PROBE_MISSING_DETAIL"
        elif correctness == CorrectnessLevel.INCOMPLETE:
            classification = AssessmentClassification.INCOMPLETE
            action = "PROBE_HOW_OR_WHY"
        else:
            classification = AssessmentClassification.INCORRECT
            action = "TEACH_GAP"

        # Construct candidate assessment
        assessment = LearningAssessment(
            intent=intent,
            is_answer_attempt=True,
            relevance_score=relevance_score,
            relevance_level=relevance_level,
            concept_alignment_score=alignment_score,
            claims=claims,
            evidence=evidence_items,
            correctness=correctness,
            correctness_score=correctness_score,
            completeness=completeness,
            completeness_score=completeness_score,
            misconception_status=has_misconception,
            misconceptions=misconceptions,
            missing_concepts=missing_concepts,
            contradictory_claims=contradictory,
            classification=classification,
            confidence=conf,
            supports_mastery=False,  # Evaluated by MasteryGate below
            assessment_status=status,
            recommended_learning_action=action,
        )

        # -------------------------------------------------------------
        # 12. Mastery Gate Evaluation
        # -------------------------------------------------------------
        mastery_decision = self.mastery_gate.evaluate(assessment, target_concept)
        assessment.supports_mastery = mastery_decision.supports_mastery
        assessment.metadata["mastery_decision"] = mastery_decision.model_dump()

        return assessment
