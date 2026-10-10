"""
Comprehensive Mastery Gate Safety & Confidence Calibration Tests for Milestone C.
Verifies all safety invariants ensuring MasteryGate is the sole authority preventing false mastery.
"""
import pytest
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    LearningAssessment,
    MisconceptionEvidence,
    RelevanceLevel,
)


@pytest.fixture
def gate():
    return MasteryGate()


def test_gate_denies_non_answer_intents(gate):
    """Verify non-answer intents strictly deny mastery with delta = 0.0."""
    non_answers = [
        AssessmentIntent.ACKNOWLEDGEMENT,
        AssessmentIntent.READY_TO_CONTINUE,
        AssessmentIntent.HELP_REQUEST,
        AssessmentIntent.CLARIFICATION_REQUEST,
        AssessmentIntent.OFF_TOPIC,
        AssessmentIntent.EMPTY_RESPONSE,
        AssessmentIntent.UNCERTAIN,
    ]
    for intent in non_answers:
        assessment = LearningAssessment(
            intent=intent,
            is_answer_attempt=False,
            classification=AssessmentClassification.OFF_TOPIC if intent == AssessmentIntent.OFF_TOPIC else AssessmentClassification.IRRELEVANT,
            relevance_level=RelevanceLevel.IRRELEVANT,
            relevance_score=0.0,
            concept_alignment_score=0.0,
            correctness=CorrectnessLevel.INCORRECT,
            correctness_score=0.0,
            completeness=CompletenessLevel.NOT_APPLICABLE,
            completeness_score=0.0,
            assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
            confidence=0.95,
        )
        decision = gate.evaluate(assessment, "atomicity")
        assert not decision.supports_mastery
        assert not decision.mastery_delta_allowed
        assert decision.allowed_delta == 0.0
        assert decision.evidence_count_increment == 0


def test_gate_denies_irrelevant_responses(gate):
    """Verify irrelevant or off-topic responses strictly deny mastery."""
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.IRRELEVANT,
        relevance_level=RelevanceLevel.IRRELEVANT,
        relevance_score=0.10,
        concept_alignment_score=0.05,
        correctness=CorrectnessLevel.INCORRECT,
        correctness_score=0.0,
        completeness=CompletenessLevel.NOT_APPLICABLE,
        completeness_score=0.0,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.95,
    )
    decision = gate.evaluate(assessment, "deadlock")
    assert not decision.supports_mastery
    assert not decision.mastery_delta_allowed
    assert decision.allowed_delta == 0.0


def test_gate_denies_abstained_and_low_confidence(gate):
    """Verify abstentions and low-confidence assessments deny positive mastery."""
    # Abstention
    abstained = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.CORRECT,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.85,
        concept_alignment_score=0.80,
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.90,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.90,
        assessment_status=AssessmentStatus.ABSTAIN,
        confidence=0.45,
    )
    decision = gate.evaluate(abstained, "atomicity")
    assert not decision.supports_mastery
    assert not decision.mastery_delta_allowed
    assert decision.allowed_delta == 0.0

    # Low confidence (< 0.60 threshold)
    low_conf = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.CORRECT,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.85,
        concept_alignment_score=0.80,
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.85,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.85,
        assessment_status=AssessmentStatus.LOW_CONFIDENCE,
        confidence=0.55,
    )
    decision2 = gate.evaluate(low_conf, "atomicity")
    assert not decision2.supports_mastery
    assert not decision2.mastery_delta_allowed
    assert decision2.allowed_delta == 0.0


def test_gate_denies_misconceptions_and_records_gap(gate):
    """Verify responses with misconceptions deny mastery and record a gap."""
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.MISCONCEPTION,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.90,
        concept_alignment_score=0.85,
        correctness=CorrectnessLevel.MISCONCEPTION,
        correctness_score=0.10,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.30,
        misconception_status=True,
        misconceptions=[
            MisconceptionEvidence(
                concept_id="atomicity",
                description="partial commit succeeds",
                learner_statement="some operations commit",
            )
        ],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.90,
    )
    decision = gate.evaluate(assessment, "atomicity")
    assert not decision.supports_mastery
    assert not decision.mastery_delta_allowed
    assert decision.record_as_gap
    assert decision.record_as_misconception


def test_gate_denies_contradictory_claims(gate):
    """Verify contradictory claims deny mastery and record gap."""
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.CONTRADICTORY,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.85,
        concept_alignment_score=0.80,
        correctness=CorrectnessLevel.CONTRADICTORY,
        correctness_score=0.20,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.30,
        contradictory_claims=["all commit together vs some succeed"],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.85,
    )
    decision = gate.evaluate(assessment, "atomicity")
    assert not decision.supports_mastery
    assert not decision.mastery_delta_allowed
    assert decision.record_as_gap


def test_gate_partial_answer_requires_supported_evidence(gate):
    """Verify partially correct answer without verified supported evidence grants NO delta."""
    # Partial correctness but ZERO supported evidence items
    unsupported_partial = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.PARTIAL,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.75,
        concept_alignment_score=0.70,
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.50,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.40,
        evidence=[
            EvidenceItem(concept_id="atomicity", expected_description="all-or-nothing", status=EvidenceStatus.MISSING),
        ],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.85,
    )
    decision = gate.evaluate(unsupported_partial, "atomicity")
    assert not decision.supports_mastery
    assert not decision.mastery_delta_allowed
    assert decision.allowed_delta == 0.0

    # Partial correctness WITH supported evidence item -> bounded delta allowed
    supported_partial = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.PARTIAL,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.80,
        concept_alignment_score=0.75,
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.55,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.50,
        evidence=[
            EvidenceItem(concept_id="atomicity", expected_description="all-or-nothing", status=EvidenceStatus.SUPPORTED),
        ],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.85,
    )
    decision2 = gate.evaluate(supported_partial, "atomicity")
    assert not decision2.supports_mastery
    assert decision2.mastery_delta_allowed
    assert decision2.allowed_delta == 0.15


def test_gate_grants_mastery_only_on_correct_with_evidence(gate):
    """Verify positive mastery is authorized when correctness is CORRECT with verified evidence."""
    correct_assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.CORRECT,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.95,
        concept_alignment_score=0.90,
        correctness=CorrectnessLevel.CORRECT,
        correctness_score=0.95,
        completeness=CompletenessLevel.COMPLETE,
        completeness_score=0.95,
        evidence=[
            EvidenceItem(concept_id="atomicity", expected_description="all-or-nothing", status=EvidenceStatus.SUPPORTED),
            EvidenceItem(concept_id="atomicity", expected_description="rollback on failure", status=EvidenceStatus.SUPPORTED),
        ],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.95,
    )
    decision = gate.evaluate(correct_assessment, "atomicity")
    assert decision.supports_mastery
    assert decision.mastery_delta_allowed
    assert decision.allowed_delta == 0.40
    assert decision.evidence_count_increment == 1
    assert not decision.record_as_gap
