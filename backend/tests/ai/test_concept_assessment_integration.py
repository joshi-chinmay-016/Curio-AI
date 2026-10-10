"""
Integration tests for Concept Model and Answer Intelligence pipeline (Milestone D).
Verifies:
1. Concept Model learning objectives and expected evidence flow into ExpectedEvidence.
2. Canonical LearningAssessment structure is maintained.
3. MasteryGate remains sole authority; ConceptModel never directly grants mastery.
4. Correct, partial, and contradictory answers evaluate accurately against dynamic objectives.
5. Invalid concept models cannot grant mastery or corrupt assessment safety.
"""
import pytest
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.evidence_extractor import EvidenceExtractor
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.prompt_augmentation import build_dynamic_prompt_context
from backend.app.ai.answer_intelligence.providers.local_model import LocalAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceStatus,
    LearningAssessment,
)
from backend.app.ai.concept_model import ConceptModelBuilder
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    CognitiveAction,
    ConceptConstraint,
    ConceptModel,
    ConceptNode,
    ConstraintType,
    ConversationContext,
    CurrentQuestion,
    EvidenceType,
    ExpectedEvidenceRequirement,
    LearningContext,
    LearningObjective,
    SessionState,
    QuestionSpecification,
    ValidationStatus,
)


def create_sample_concept_model() -> ConceptModel:
    """Builds a rich, validated ConceptModel with explicit objectives, evidence, and constraints."""
    obj1 = LearningObjective(
        objective_id="obj_binary_search_bounds",
        concept_id="binary_search_mechanism",
        description="Explain how binary search eliminates half the remaining search space using midpoint comparison",
        cognitive_action=CognitiveAction.EXPLAIN,
        essential=True,
        expected_evidence=[
            ExpectedEvidenceRequirement(
                evidence_id="ev_halving",
                concept_id="binary_search_mechanism",
                description="eliminates half the search space or elements on one side greater or lesser than target",
                evidence_type=EvidenceType.MECHANISM,
                essential=True,
            ),
            ExpectedEvidenceRequirement(
                evidence_id="ev_ordered",
                concept_id="binary_search_mechanism",
                description="requires sorted array or ordered sequence",
                evidence_type=EvidenceType.REASONING,
                essential=True,
            ),
        ],
    )
    node = ConceptNode(
        id="binary_search_mechanism",
        name="Binary Search Mechanism",
        definition="An efficient search algorithm on ordered collections.",
        difficulty_level=2,
        learning_objectives=[obj1],
        concept_constraints=[
            ConceptConstraint(
                constraint_id="const_sorted",
                concept_id="binary_search_mechanism",
                rule="requires sorted array or ordered sequence",
                constraint_type=ConstraintType.PREREQUISITE_CONDITION,
                essential=True,
            )
        ],
        common_misconceptions=[
            "works on unsorted array or arbitrary sequence",
        ],
    )
    return ConceptModel(
        topic="Binary Search",
        concepts=[node],
        relationships=[],
        validation_status=ValidationStatus.VALID,
    )


def test_concept_model_evidence_flows_into_expected_evidence():
    model = create_sample_concept_model()
    node = model.get_concept("binary_search_mechanism")
    obj = node.learning_objectives[0]

    provider = LocalAssessmentProvider()
    extractor = EvidenceExtractor(provider)

    expected = extractor.derive_expected_evidence(
        concept_id=node.id,
        concept_node=node,
        objective=obj,
    )

    # Both expected evidence requirements and constraints must be extracted into core_components
    assert any("eliminates half" in c.lower() for c in expected.core_components)
    assert any("sorted" in c.lower() for c in expected.core_components)
    assert any("unsorted" in m.lower() for m in expected.common_misconceptions)


def test_assessment_aggregator_evaluates_against_dynamic_objective():
    model = create_sample_concept_model()
    aggregator = AssessmentAggregator(provider=LocalAssessmentProvider())

    # 1. Full correct answer containing both halving and sorting requirements
    full_answer = "Binary search requires a sorted array and compares the target with the middle element, eliminating half the search space on each step."
    assessment_full: LearningAssessment = aggregator.assess(
        user_message=full_answer,
        concept_model=model,
        target_concept_override="binary_search_mechanism",
    )

    assert assessment_full.is_answer_attempt is True
    assert assessment_full.correctness in (CorrectnessLevel.CORRECT, CorrectnessLevel.PARTIALLY_CORRECT)
    assert len(assessment_full.evidence) >= 1
    # Check that LearningAssessment is canonical
    assert isinstance(assessment_full, LearningAssessment)
    assert hasattr(assessment_full, "supports_mastery")

    # 2. Contradictory answer asserting it works on unsorted lists
    contra_answer = "Binary search works on an unsorted array by picking random elements."
    assessment_contra: LearningAssessment = aggregator.assess(
        user_message=contra_answer,
        concept_model=model,
        target_concept_override="binary_search_mechanism",
    )

    assert assessment_contra.supports_mastery is False


def test_concept_model_never_independently_grants_mastery():
    """Verify that MasteryGate remains the sole authority for mastery updates."""
    model = create_sample_concept_model()
    gate = MasteryGate()

    # Create a partial assessment (missing essential evidence)
    partial_assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.9,
        concept_alignment_score=0.85,
        claims=[],
        evidence=[],
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.5,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.5,
        classification=AssessmentClassification.PARTIAL,
        confidence=0.8,
        supports_mastery=False,
    )

    # Even though concept model is 100% valid, MasteryGate must reject mastery
    decision = gate.evaluate(partial_assessment, "binary_search_mechanism")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False
    assert decision.allowed_delta == 0.0


def test_invalid_concept_model_does_not_corrupt_assessment():
    """An invalid or incomplete concept model must still allow safe fallback assessment."""
    invalid_model = ConceptModel(
        topic="Uncertain Topic",
        concepts=[],
        relationships=[],
        validation_status=ValidationStatus.INVALID,
        limitations=["Generation failed"],
    )

    aggregator = AssessmentAggregator(provider=LocalAssessmentProvider())
    assessment = aggregator.assess(
        user_message="I understand the basics of this topic.",
        concept_model=invalid_model,
        target_concept_override="uncertain_topic_core",
    )

    # Assessment completes safely without throwing exceptions
    assert assessment is not None
    assert isinstance(assessment, LearningAssessment)
    # Cannot grant mastery on arbitrary vague statement with invalid model
    assert assessment.supports_mastery is False


def test_prompt_augmentation_integrates_subgraph_context():
    """Prompt context should contain active objective and compact concept context."""
    model = create_sample_concept_model()
    node = model.get_concept("binary_search_mechanism")
    obj = node.learning_objectives[0]

    state = SessionState(
        session_id="test_session",
        active_concept="binary_search_mechanism",
        concept_model=model,
        current_objective=obj,
    )
    context = AIContext(
        session_id="test_session",
        topic="Binary Search",
        active_concept="binary_search_mechanism",
        current_state=state,
        conversation=ConversationContext(),
        learning_context=LearningContext(),
    )

    aggregator = AssessmentAggregator(provider=LocalAssessmentProvider())
    assessment = aggregator.assess(
        user_message="Binary search eliminates half the elements.",
        concept_model=model,
        target_concept_override="binary_search_mechanism",
    )

    prompt_ctx = build_dynamic_prompt_context(
        assessment=assessment,
        context=context,
        difficulty=2,
    )

    rendered = prompt_ctx.to_prompt_section()
    assert "Target Concept: binary_search_mechanism" in rendered
    assert "Active Learning Objective:" in rendered
    assert "Concept Context:" in rendered
    assert "Binary Search Mechanism" in rendered
    # Must remain token-efficient (under 2000 characters)
    assert len(rendered) < 2000
