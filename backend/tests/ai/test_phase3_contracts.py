"""
Tests for Phase 3 Evaluation and Report Contracts (3A).
Verifies:
- Schema validation
- Enum validation
- Nested contract validation
- Bounds checking (score 0-100, confidence 0.0-1.0)
- Backward compatibility with AIResult
"""
import uuid
import pytest
from pydantic import ValidationError

from backend.app.ai.schemas import (
     AIResult,
     AIResponse,
     ConceptAssessment,
     ConceptEvidenceItem,
     GapAnalysisItem,
     GapSeverity,
     GapStatus,
     LearningDecision,
     LearningReport,
     MasteryLevel,
     MisconceptionAnalysisItem,
     MisconceptionStatus,
     Mode,
     RoadmapItem,
     SessionEvaluation,
     SessionEvidence,
     StateUpdates,
     Strategy,
     TeacherInterventionEvidence,
     TurnEvaluation,
     TurnEvidence,
)


def test_mastery_level_enum():
    assert MasteryLevel.BEGINNER == "BEGINNER"
    assert MasteryLevel.DEVELOPING == "DEVELOPING"
    assert MasteryLevel.PROFICIENT == "PROFICIENT"
    assert MasteryLevel.MASTERY == "MASTERY"


def test_gap_and_misconception_enums():
    assert GapStatus.DETECTED == "DETECTED"
    assert GapStatus.RESOLVED == "RESOLVED"
    assert GapStatus.UNRESOLVED == "UNRESOLVED"
    assert GapSeverity.HIGH == "HIGH"
    assert MisconceptionStatus.CHALLENGED == "CHALLENGED"


def test_turn_evidence_validation():
    turn_eval = TurnEvaluation(
        correctness=0.9,
        clarity=0.8,
        completeness=0.85,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.0,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=2,
    )
    evidence = TurnEvidence(
        turn_index=0,
        question="What is recursion?",
        learner_answer="A function calling itself.",
        concept="Recursion",
        difficulty=1,
        evaluation=turn_eval,
    )
    assert evidence.turn_index == 0
    assert evidence.concept == "Recursion"
    assert evidence.evaluation.correctness == 0.9

    # Negative turn index should fail
    with pytest.raises(ValidationError):
        TurnEvidence(
            turn_index=-1,
            question="Q",
            learner_answer="A",
            concept="C",
            difficulty=1,
            evaluation=turn_eval,
        )


def test_concept_assessment_validation():
    assessment = ConceptAssessment(
        concept="Binary Search Ordering",
        understanding_score=85.0,
        confidence=0.9,
        mastery_level=MasteryLevel.PROFICIENT,
        strengths=["Elimination principle"],
        gaps=[],
        misconceptions=[],
        evidence_references=["turn_1", "turn_3"],
    )
    assert assessment.understanding_score == 85.0
    assert assessment.mastery_level == MasteryLevel.PROFICIENT

    # Score > 100 or < 0 should fail
    with pytest.raises(ValidationError):
        ConceptAssessment(
            concept="Binary Search Ordering",
            understanding_score=105.0,
            confidence=0.9,
            mastery_level=MasteryLevel.PROFICIENT,
        )
    with pytest.raises(ValidationError):
        ConceptAssessment(
            concept="Binary Search Ordering",
            understanding_score=-5.0,
            confidence=0.9,
            mastery_level=MasteryLevel.PROFICIENT,
        )


def test_session_evaluation_validation():
    session_id = str(uuid.uuid4())
    evaluation = SessionEvaluation(
        session_id=session_id,
        topic="Binary Search",
        understanding_score=78.5,
        mastery_level=MasteryLevel.DEVELOPING,
        evidence_confidence=0.85,
        strengths=["Understands divide and conquer"],
        knowledge_gaps=[
            GapAnalysisItem(
                gap="Off-by-one errors on boundary conditions",
                concept="Boundary Conditions",
                severity=GapSeverity.HIGH,
                status=GapStatus.UNRESOLVED,
                evidence_references=["turn_4"],
            )
        ],
        misconceptions=[
            MisconceptionAnalysisItem(
                misconception="Works on unsorted arrays",
                concept="Ordering Requirement",
                status=MisconceptionStatus.RESOLVED,
                evidence_references=["turn_2", "intervention_1"],
            )
        ],
        resolved_gaps=["Sorted array requirement"],
        unresolved_gaps=["Boundary conditions"],
        resolved_misconceptions=["Works on unsorted arrays"],
        unresolved_misconceptions=[],
        concept_assessments=[
            ConceptAssessment(
                concept="Ordering Requirement",
                understanding_score=90.0,
                confidence=0.9,
                mastery_level=MasteryLevel.PROFICIENT,
                strengths=["Identified monotonic search space"],
                gaps=[],
                misconceptions=[],
                evidence_references=["turn_2", "turn_3"],
            )
        ],
        difficulty_progression=[1, 2, 2, 3],
        teacher_intervention_summary={"total_interventions": 1, "successful": 1},
        recommended_next_steps=[
            RoadmapItem(
                priority=1,
                title="Practice Boundary Conditions",
                description="Review while (low <= high) vs (low < high).",
                target_concept="Boundary Conditions",
                action_type="FILL_GAP",
            )
        ],
    )

    assert evaluation.understanding_score == 78.5
    assert len(evaluation.knowledge_gaps) == 1
    assert evaluation.knowledge_gaps[0].status == GapStatus.UNRESOLVED
    assert len(evaluation.resolved_misconceptions) == 1


def test_learning_report_validation():
    session_id = str(uuid.uuid4())
    report = LearningReport(
        session_id=session_id,
        topic="Binary Search",
        understanding_score=82.0,
        mastery_level=MasteryLevel.PROFICIENT,
        evidence_confidence=0.88,
        strengths=["Core division logic", "Sorted requirement"],
        knowledge_gaps=["Boundary condition edge cases"],
        resolved_gaps=["Sorted array requirement"],
        unresolved_gaps=["Boundary condition edge cases"],
        misconceptions=[],
        resolved_misconceptions=["Works on unsorted arrays"],
        unresolved_misconceptions=[],
        concept_assessments=[],
        difficulty_achieved=3,
        teacher_interventions_required=1,
        recommended_next_steps=[
            RoadmapItem(
                priority=1,
                title="Edge Case Drill",
                description="Practice empty arrays and single element arrays.",
                target_concept="Edge Cases",
                action_type="PRACTICE",
            )
        ],
    )
    assert report.understanding_score == 82.0
    assert report.mastery_level == MasteryLevel.PROFICIENT
    assert report.difficulty_achieved == 3


def test_ai_result_backward_compatibility():
    """Verify that existing AIResult usage without Phase 3 fields remains 100% valid."""
    eval_obj = TurnEvaluation(
        correctness=0.8,
        clarity=0.8,
        completeness=0.8,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=2,
    )
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=2,
        confidence=0.7,
        reason="Good progress",
        active_concept="Concept A",
    )
    response = AIResponse(
        content="Why is that the case?",
        mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=2,
        confidence=0.7,
    )
    updates = StateUpdates()

    result = AIResult(
        evaluation=eval_obj,
        decision=decision,
        response=response,
        state_updates=updates,
    )
    assert result.session_evaluation is None
    assert result.learning_report is None
