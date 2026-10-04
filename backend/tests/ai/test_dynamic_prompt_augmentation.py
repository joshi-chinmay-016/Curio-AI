"""
Unit tests for Dynamic Prompt Augmentation (AI Milestone B).
Verifies that structured assessment context (evidence, gaps, misconceptions, confidence)
is passed to prompt generation without exposing hidden chain-of-thought.
"""
import pytest
from backend.app.ai.answer_intelligence.prompt_augmentation import (
    DynamicPromptContext,
    build_dynamic_prompt_context,
)
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
from backend.app.ai.prompts.candidate_prompts import build_candidate_generation_prompt
from backend.app.ai.prompts.student_prompts import build_student_question_prompt
from backend.app.ai.prompts.teacher_prompts import build_teacher_prompt
from backend.app.ai.schemas import (
    AIContext,
    LearningDecision,
    LearningObjective,
    Mode,
    ObjectiveType,
    QuestionSpecification,
    Strategy,
)


def test_misconception_dynamic_prompt_context():
    """Verify structured prompt augmentation on active misconception."""
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.90,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.85,
        claims=[],
        evidence=[
            EvidenceItem(
                concept_id="binary_search",
                expected_description="eliminates half the search space on each comparison",
                status=EvidenceStatus.MISSING,
            )
        ],
        correctness=CorrectnessLevel.MISCONCEPTION,
        correctness_score=0.20,
        completeness=CompletenessLevel.MINIMAL,
        completeness_score=0.10,
        misconception_status=True,
        misconceptions=[
            MisconceptionEvidence(
                concept_id="binary_search",
                description="binary search checks every element linearly",
                learner_statement="It checks every element until target is found",
                severity="HIGH",
            )
        ],
        missing_concepts=["eliminates half the search space"],
        classification=AssessmentClassification.MISCONCEPTION,
        confidence=0.92,
        supports_mastery=False,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        recommended_learning_action="CHALLENGE_MISCONCEPTION",
    )

    ctx = build_dynamic_prompt_context(assessment=assessment, difficulty=2)
    assert ctx.learner_intent == "ANSWER_ATTEMPT"
    assert "binary search checks every element linearly" in ctx.misconceptions
    assert "Challenge the misconception" in ctx.prompt_instruction
    assert any("eliminates half the search space" in m for m in ctx.missing_evidence)

    rendered = ctx.to_prompt_section()
    assert "Active Misconceptions: binary search checks every element linearly" in rendered
    assert any("eliminates half the search space" in line for line in rendered.splitlines() if "Missing" in line)
    # Ensure no hidden chain of thought or internal debug dumps
    assert "Chain-of-Thought" not in rendered
    assert "internal_reasoning" not in rendered


def test_partial_evidence_dynamic_prompt_context():
    """Verify structured prompt context when learner provides partial evidence."""
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.80,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.75,
        claims=[],
        evidence=[
            EvidenceItem(
                concept_id="atomicity",
                expected_description="all operations commit together",
                status=EvidenceStatus.SUPPORTED,
            ),
            EvidenceItem(
                concept_id="atomicity",
                expected_description="entire transaction rolls back on failure",
                status=EvidenceStatus.MISSING,
            ),
        ],
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.55,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.50,
        missing_concepts=["entire transaction rolls back on failure"],
        classification=AssessmentClassification.PARTIAL,
        confidence=0.88,
        supports_mastery=False,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        recommended_learning_action="PROBE_MISSING_DETAIL",
    )

    ctx = build_dynamic_prompt_context(assessment=assessment, difficulty=2)
    assert "all operations commit together" in ctx.supported_evidence
    assert "entire transaction rolls back on failure" in ctx.missing_evidence
    assert "partial explanation" in ctx.prompt_instruction.lower()


def test_prompt_template_integration():
    """Verify that student, candidate, and teacher prompts format structured assessment seamlessly."""
    dyn_ctx = DynamicPromptContext(
        active_concept="atomicity",
        learner_intent="ANSWER_ATTEMPT",
        relevance_level="RELEVANT",
        relevance_score=0.85,
        correctness_level="PARTIALLY_CORRECT",
        completeness_level="PARTIAL",
        supported_evidence=["all operations commit together"],
        missing_evidence=["entire transaction rolls back on failure"],
        confidence=0.90,
        prompt_instruction="Acknowledge all-or-nothing, probe rollback behavior.",
    )

    context = AIContext(topic="DBMS", current_mode=Mode.STUDENT, active_concept="atomicity")
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.PROBE_MISSING_CONCEPT,
        difficulty=2,
        active_concept="atomicity",
        confidence=0.90,
        reason="Probing missing concept",
    )

    # 1. Student prompt
    student_prompt = build_student_question_prompt(
        context=context,
        decision=decision,
        prompt_context=dyn_ctx,
    )
    assert "STRUCTURED LEARNER ASSESSMENT CONTEXT" in student_prompt
    assert "all operations commit together" in student_prompt
    assert "entire transaction rolls back on failure" in student_prompt

    # 2. Teacher prompt
    teacher_prompt = build_teacher_prompt(
        context=context,
        gap="atomicity rollback",
        attempt_count=1,
        prompt_context=dyn_ctx,
    )
    assert "STRUCTURED LEARNER ASSESSMENT CONTEXT" in teacher_prompt
    assert "all operations commit together" in teacher_prompt

    # 3. Candidate prompt
    spec = QuestionSpecification(
        target_concept="atomicity",
        learning_objective=LearningObjective(
            objective_type=ObjectiveType.UNDERSTAND_MECHANISM,
            target_concept="atomicity",
            difficulty=2,
            reason="Explain rollback",
            evidence_expected="entire transaction rolls back",
        ),
        difficulty=2,
        reason="Probe rollback",
        evidence_expected="entire transaction rolls back",
        generation_constraints=["No multiple questions"],
    )
    cand_prompt = build_candidate_generation_prompt(
        spec=spec,
        context=context,
        prompt_context=dyn_ctx,
    )
    assert "STRUCTURED LEARNER ASSESSMENT CONTEXT" in cand_prompt
    assert "entire transaction rolls back on failure" in cand_prompt
