"""
Comprehensive Student Mode and Teacher Mode Assessment Regression Suite for Milestone C.
Verifies canonical assessment behavior across all pedagogical scenarios:
- Student Mode: correct, partial, wrong, misconception, irrelevant, help request, acknowledgements.
- Teacher Mode: non-exit on bare acknowledgements ("I understand", "Okay", "Got it", "That makes sense"),
  failure on wrong/irrelevant verification, and successful interrupted-question restoration on verified correctness.
"""
import pytest
from backend.app.ai.decision_engine import DecisionEngine
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
from backend.app.ai.schemas import (
    AIContext,
    ChatMessage,
    CurrentQuestion,
    InputType,
    Mode,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)


@pytest.fixture
def decision_engine():
    return DecisionEngine()


def _make_context(
    current_mode: Mode = Mode.STUDENT,
    active_concept: str = "atomicity",
    interrupted_question: CurrentQuestion = None,
    teacher_attempts: int = 1,
    user_msg: str = "",
) -> AIContext:
    curr_q = CurrentQuestion(
        id="q_curr",
        content="Explain atomicity in database transactions.",
        concept=active_concept,
        difficulty=2,
    )
    intervention = None
    if current_mode == Mode.TEACHER:
        intervention = TeacherIntervention(
            active=True,
            gap=active_concept,
            attempt_count=teacher_attempts,
            verification_required=True,
        )
    history = [ChatMessage(sender="USER", content=user_msg, input_type=InputType.TEXT)] if user_msg else []
    return AIContext(
        topic="DBMS",
        active_concept=active_concept,
        current_mode=current_mode,
        current_question=curr_q,
        interrupted_question=interrupted_question,
        teacher_intervention=intervention,
        history=history,
    )


def _make_eval(
    correctness: float = 0.0,
    completeness: float = 0.0,
    stuck_probability: float = 0.0,
    misconceptions: list = None,
    knowledge_gap: str = None,
) -> TurnEvaluation:
    return TurnEvaluation(
        correctness=correctness,
        completeness=completeness,
        clarity=0.8,
        depth=0.5,
        relevance=1.0,
        stuck_probability=stuck_probability,
        misconceptions=misconceptions or [],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=[],
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=2,
        knowledge_gap=knowledge_gap,
    )


# =========================================================================
# 1. TEACHER MODE NON-EXIT ON ACKNOWLEDGEMENTS (Critical Milestone C Req)
# =========================================================================

@pytest.mark.parametrize("ack_phrase", [
    "I understand.",
    "Okay.",
    "Got it.",
    "That makes sense.",
    "yes",
    "ok",
    "understood",
])
def test_teacher_mode_never_exits_on_bare_acknowledgement(decision_engine, ack_phrase):
    """Teacher Mode must NOT exit simply because learner acknowledges without explanation."""
    int_q = CurrentQuestion(
        id="q_int",
        content="What is the ACID guarantee of atomicity?",
        concept="atomicity",
        difficulty=2,
    )
    context = _make_context(
        current_mode=Mode.TEACHER,
        active_concept="atomicity",
        interrupted_question=int_q,
        teacher_attempts=1,
        user_msg=ack_phrase,
    )

    assessment = LearningAssessment(
        intent=AssessmentIntent.ACKNOWLEDGEMENT,
        is_answer_attempt=False,
        classification=AssessmentClassification.ACKNOWLEDGEMENT,
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
    interpretation = TurnInterpretation(
        intent=TurnIntent.READY_FOR_VERIFICATION,
        is_ready_signal=True,
    )
    evaluation = _make_eval(correctness=0.0, completeness=0.0, stuck_probability=0.1)

    decision = decision_engine.decide(
        context=context,
        evaluation=evaluation,
        interpretation=interpretation,
        assessment=assessment,
    )

    # Must remain in TEACHER mode
    assert decision.next_mode == Mode.TEACHER
    assert not decision.should_restore_interrupted_question
    assert decision.active_concept == "atomicity"


def test_teacher_mode_remains_on_incorrect_verification(decision_engine):
    """Incorrect verification keeps learner in Teacher Mode and adapts."""
    int_q = CurrentQuestion(id="q_int", content="Explain atomicity.", concept="atomicity", difficulty=2)
    context = _make_context(
        current_mode=Mode.TEACHER,
        active_concept="atomicity",
        interrupted_question=int_q,
        teacher_attempts=1,
        user_msg="Atomicity means database is encrypted.",
    )

    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.INCORRECT,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.80,
        concept_alignment_score=0.75,
        correctness=CorrectnessLevel.INCORRECT,
        correctness_score=0.10,
        completeness=CompletenessLevel.MINIMAL,
        completeness_score=0.10,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.90,
    )
    interpretation = TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT)
    evaluation = _make_eval(correctness=0.10, completeness=0.10, stuck_probability=0.2)

    decision = decision_engine.decide(
        context=context,
        evaluation=evaluation,
        interpretation=interpretation,
        assessment=assessment,
    )

    assert decision.next_mode == Mode.TEACHER
    assert not decision.should_restore_interrupted_question


def test_teacher_mode_remains_on_misconception_verification(decision_engine):
    """Misconception in verification keeps learner in Teacher Mode."""
    int_q = CurrentQuestion(id="q_int", content="Explain atomicity.", concept="atomicity", difficulty=2)
    context = _make_context(
        current_mode=Mode.TEACHER,
        active_concept="atomicity",
        interrupted_question=int_q,
        teacher_attempts=1,
        user_msg="Some parts succeed even if another fails.",
    )

    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.MISCONCEPTION,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.85,
        concept_alignment_score=0.80,
        correctness=CorrectnessLevel.MISCONCEPTION,
        correctness_score=0.15,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.30,
        misconceptions=[
            MisconceptionEvidence(concept_id="atomicity", description="partial commit", learner_statement="some succeed")
        ],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.90,
    )
    interpretation = TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT)
    evaluation = _make_eval(correctness=0.15, completeness=0.30, misconceptions=["partial commit"])

    decision = decision_engine.decide(
        context=context,
        evaluation=evaluation,
        interpretation=interpretation,
        assessment=assessment,
    )

    assert decision.next_mode == Mode.TEACHER
    assert not decision.should_restore_interrupted_question


def test_teacher_mode_exits_and_restores_on_verified_substantive_correctness(decision_engine):
    """Teacher Mode successfully restores interrupted question when verification is verified correct."""
    int_q = CurrentQuestion(id="q_int", content="Explain atomicity in full.", concept="atomicity", difficulty=2)
    user_ans = "Atomicity means all operations in a transaction commit together or the entire transaction rolls back completely on any failure."
    context = _make_context(
        current_mode=Mode.TEACHER,
        active_concept="atomicity",
        interrupted_question=int_q,
        teacher_attempts=1,
        user_msg=user_ans,
    )

    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.CORRECT,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.95,
        concept_alignment_score=0.95,
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
    interpretation = TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT)
    evaluation = _make_eval(correctness=0.95, completeness=0.95, stuck_probability=0.0)

    decision = decision_engine.decide(
        context=context,
        evaluation=evaluation,
        interpretation=interpretation,
        assessment=assessment,
    )

    assert decision.next_mode == Mode.STUDENT
    assert decision.should_restore_interrupted_question
    assert decision.strategy == Strategy.RESTORE_INTERRUPTED_QUESTION


# =========================================================================
# 2. STUDENT MODE SCENARIOS
# =========================================================================

def test_student_mode_switches_to_teacher_on_help_request(decision_engine):
    """Explicit help request in Student Mode transitions to Teacher Mode."""
    user_msg = "Can you please explain deadlock? I am completely stuck."
    context = _make_context(current_mode=Mode.STUDENT, active_concept="deadlock", user_msg=user_msg)

    interpretation = TurnInterpretation(
        intent=TurnIntent.HELP_REQUEST,
        is_stuck=True,
        is_help_request=True,
    )
    evaluation = _make_eval(
        correctness=0.0,
        completeness=0.0,
        stuck_probability=0.9,
        knowledge_gap="deadlock",
    )

    decision = decision_engine.decide(
        context=context,
        evaluation=evaluation,
        interpretation=interpretation,
    )

    assert decision.next_mode == Mode.TEACHER
    assert decision.strategy == Strategy.TEACH_GAP


def test_student_mode_probes_on_partial_answer(decision_engine):
    """Partial answer in Student Mode triggers probe for missing detail without granting mastery."""
    user_ans = "All operations execute together as one unit."
    context = _make_context(current_mode=Mode.STUDENT, active_concept="atomicity", user_msg=user_ans)

    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        classification=AssessmentClassification.PARTIAL,
        relevance_level=RelevanceLevel.RELEVANT,
        relevance_score=0.85,
        concept_alignment_score=0.80,
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.55,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.50,
        evidence=[
            EvidenceItem(concept_id="atomicity", expected_description="all-or-nothing", status=EvidenceStatus.SUPPORTED),
            EvidenceItem(concept_id="atomicity", expected_description="rollback on failure", status=EvidenceStatus.MISSING),
        ],
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        confidence=0.85,
    )
    interpretation = TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT)
    evaluation = _make_eval(correctness=0.55, completeness=0.50, stuck_probability=0.1)

    decision = decision_engine.decide(
        context=context,
        evaluation=evaluation,
        interpretation=interpretation,
        assessment=assessment,
    )

    assert decision.next_mode == Mode.STUDENT
    assert decision.strategy in (Strategy.PROBE_WHY, Strategy.PROBE_HOW)
    assert not decision.should_restore_interrupted_question
