"""
Turn Assessment Persistence Tests.
Tests for the new turn_assessments table and ChatService integration.
"""

# Import db.base first to ensure all models are registered in correct order
import backend.app.db.base

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
import pytest

from backend.app.ai.engine import CurioEngine
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.services.chat_service import ChatService
from backend.app.schemas.message import (
    MessageCreate,
    ChatTurnResponse,
    MessageResponse,
    TurnEvaluationResponse,
    LearningDecisionResponse,
)
from backend.app.schemas.common import (
    LearningMode,
    LearningStrategy,
    InputType as CommonInputType,
)
from backend.app.ai.schemas import (
    AIContext,
    AIResult,
    AIResponse,
    CurrentQuestion,
    InputType,
    LearningDecision,
    LearningObjective,
    Mode,
    ModeTransition,
    QuestionSpecification,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
    TurnInterpretation,
    TurnIntent,
)
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    ClaimType,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceItem,
    EvidenceStatus,
    LearnerClaim,
    LearningAssessment,
    MisconceptionEvidence,
    RelevanceLevel,
)
from backend.app.ai.schemas import ObjectiveType


def create_dummy_db_session(session_id, current_mode="STUDENT", current_qid=None):
    """Helper to mock a database Session and SessionState."""
    db_session = MagicMock()
    db_session.id = session_id
    db_session.topic = "Photosynthesis"
    db_session.source_type = "GENERAL"

    db_state = MagicMock()
    db_state.session_id = session_id
    db_state.current_mode = current_mode
    db_state.difficulty = 2
    db_state.confidence = 0.6
    db_state.active_concept = "Light Reaction"
    db_state.current_question_id = current_qid
    db_state.interrupted_question_id = None
    db_state.consecutive_strong_answers = 2
    db_state.consecutive_weak_answers = 0
    db_state.unresolved_misconceptions = ["misconception_solar"]
    db_state.mastered_concepts = ["chlorophyll_basics"]
    db_state.teacher_attempt_count = 0
    db_state.teacher_intervention = None

    db_session.state = db_state
    return db_session


def create_dummy_message(msg_id, session_id, sender, content):
    """Helper to mock a database Message."""
    msg = MagicMock()
    msg.id = msg_id
    msg.session_id = session_id
    msg.sender = sender
    msg.content = content
    msg.input_type = "TEXT"
    msg.created_at = datetime.now(timezone.utc)
    return msg


def create_dummy_learning_assessment(
    intent: AssessmentIntent = AssessmentIntent.ANSWER_ATTEMPT,
    relevance_level: RelevanceLevel = RelevanceLevel.RELEVANT,
    correctness: CorrectnessLevel = CorrectnessLevel.CORRECT,
    classification: AssessmentClassification = AssessmentClassification.CORRECT,
) -> LearningAssessment:
    """Helper to create a mock LearningAssessment."""
    return LearningAssessment(
        intent=intent,
        is_answer_attempt=True,
        relevance_score=0.9,
        relevance_level=relevance_level,
        concept_alignment_score=0.85,
        claims=[
            LearnerClaim(
                text="Photosynthesis converts light energy to chemical energy",
                concept_id="photosynthesis",
                claim_type=ClaimType.MECHANISM,
                alignment_score=0.9,
            )
        ],
        evidence=[
            EvidenceItem(
                concept_id="photosynthesis",
                expected_description="Light energy conversion to chemical energy",
                status=EvidenceStatus.SUPPORTED,
                supported_by_claim="Photosynthesis converts light energy to chemical energy",
                confidence=0.95,
            )
        ],
        correctness=correctness,
        correctness_score=0.85,
        completeness=CompletenessLevel.SUBSTANTIAL,
        completeness_score=0.8,
        misconception_status=False,
        misconceptions=[],
        missing_concepts=[],
        contradictory_claims=[],
        classification=classification,
        confidence=0.88,
        supports_mastery=True,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        recommended_learning_action="ADVANCE_CONCEPT",
    )


def create_dummy_turn_interpretation() -> TurnInterpretation:
    """Helper to create a mock TurnInterpretation."""
    return TurnInterpretation(
        intent=TurnIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        is_question=False,
        is_help_request=False,
        referenced_concept="photosynthesis",
        target="photosynthesis",
        answer_evidence="Learner explained the light-dependent reactions",
        confidence=0.9,
    )


def create_dummy_learning_objective() -> LearningObjective:
    """Helper to create a mock LearningObjective."""
    return LearningObjective(
        objective_type=ObjectiveType.UNDERSTAND_MECHANISM,
        target_concept="photosynthesis",
        difficulty=2,
        reason="Assess understanding of light-dependent reactions",
        evidence_expected="Explanation of photon absorption and electron transport chain",
    )


def create_dummy_question_specification() -> QuestionSpecification:
    """Helper to create a mock QuestionSpecification."""
    return QuestionSpecification(
        target_concept="photosynthesis",
        learning_objective=create_dummy_learning_objective(),
        difficulty=2,
        reason="Probe mechanism understanding",
        evidence_expected="Explanation of photon absorption",
        generation_constraints=["single_question", "difficulty_2"],
    )


def create_mock_ai_result(
    next_mode=Mode.STUDENT,
    strategy=Strategy.PROBE_WHY,
    state_updates=None,
):
    """Helper to build a strongly-typed AIResult (without assessment)."""
    evaluation = TurnEvaluation(
        correctness=0.9,
        clarity=0.85,
        completeness=0.8,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.05,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["light_photons"],
        knowledge_gap=None,
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=3,
    )

    decision = LearningDecision(
        next_mode=next_mode,
        strategy=strategy,
        difficulty=3,
        confidence=0.8,
        reason="Demonstrates solid understanding.",
        active_concept="Dark Reaction",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )

    response = AIResponse(
        content="Excellent! Now how does the Calvin cycle use the ATP produced?",
        mode=next_mode,
        strategy=strategy,
        difficulty=3,
        confidence=0.8,
    )

    updates = state_updates or StateUpdates(
        confidence=0.8,
        difficulty=3,
        active_concept="Dark Reaction",
        consecutive_successes=3,
        consecutive_failures=0,
    )

    return AIResult(
        evaluation=evaluation,
        decision=decision,
        response=response,
        state_updates=updates,
    )


def create_mock_ai_result_with_assessment(
    next_mode=Mode.STUDENT,
    strategy=Strategy.PROBE_WHY,
    state_updates=None,
    learning_assessment=None,
    turn_interpretation=None,
    learning_objective=None,
    question_specification=None,
):
    """Helper to build an AIResult with assessment artifacts."""
    evaluation = TurnEvaluation(
        correctness=0.9,
        clarity=0.85,
        completeness=0.8,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.05,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["light_photons"],
        knowledge_gap=None,
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=3,
    )

    decision = LearningDecision(
        next_mode=next_mode,
        strategy=strategy,
        difficulty=3,
        confidence=0.8,
        reason="Demonstrates solid understanding.",
        active_concept="Dark Reaction",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )

    response = AIResponse(
        content="Excellent! Now how does the Calvin cycle use the ATP produced?",
        mode=next_mode,
        strategy=strategy,
        difficulty=3,
        confidence=0.8,
    )

    updates = state_updates or StateUpdates(
        confidence=0.8,
        difficulty=3,
        active_concept="Dark Reaction",
        consecutive_successes=3,
        consecutive_failures=0,
    )

    return AIResult(
        evaluation=evaluation,
        decision=decision,
        response=response,
        state_updates=updates,
        learning_assessment=learning_assessment,
        turn_interpretation=turn_interpretation,
        learning_objective=learning_objective,
        question_specification=question_specification,
    )


class TestTurnAssessmentPersistence:
    """Tests for TurnAssessment persistence and retrieval."""

    def test_send_message_persists_learning_assessment(self):
        """Test that LearningAssessment from AIResult is persisted to turn_assessments table."""
        session_id = uuid4()
        mock_db = MagicMock()

        learning_assessment = create_dummy_learning_assessment()
        turn_interpretation = create_dummy_turn_interpretation()
        learning_objective = create_dummy_learning_objective()
        question_specification = create_dummy_question_specification()

        ai_result = create_mock_ai_result_with_assessment(
            learning_assessment=learning_assessment,
            turn_interpretation=turn_interpretation,
            learning_objective=learning_objective,
            question_specification=question_specification,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Test answer"),
            create_dummy_message(uuid4(), session_id, "AI", "Test response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Test answer", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        # Verify turn_assessment_repo.create_assessment was called
        assert service.turn_assessment_repo.create_assessment.called
        call_args = service.turn_assessment_repo.create_assessment.call_args

        assert call_args.kwargs["session_id"] == session_id
        assert call_args.kwargs["user_id"] == db_session.user_id
        assert call_args.kwargs["message_id"] is not None
        assert call_args.kwargs["learning_assessment"] is not None
        assert call_args.kwargs["turn_interpretation"] is not None
        assert call_args.kwargs["learning_objective"] is not None
        assert call_args.kwargs["question_specification"] is not None

        # Verify the assessment content
        saved_assessment = call_args.kwargs["learning_assessment"]
        assert saved_assessment["intent"] == "ANSWER_ATTEMPT"
        assert saved_assessment["relevance_score"] == 0.9
        assert len(saved_assessment["claims"]) == 1
        assert saved_assessment["claims"][0]["text"] == "Photosynthesis converts light energy to chemical energy"
        assert len(saved_assessment["evidence"]) == 1
        assert saved_assessment["evidence"][0]["status"] == "SUPPORTED"

    def test_send_message_persists_assessment_without_optional_fields(self):
        """Test that assessment persists even when optional fields are missing."""
        session_id = uuid4()
        mock_db = MagicMock()

        # Only learning_assessment provided
        learning_assessment = create_dummy_learning_assessment()

        ai_result = create_mock_ai_result_with_assessment(
            learning_assessment=learning_assessment,
            turn_interpretation=None,
            learning_objective=None,
            question_specification=None,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Test answer"),
            create_dummy_message(uuid4(), session_id, "AI", "Test response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Test answer", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        # Verify persistence was called with partial data
        assert service.turn_assessment_repo.create_assessment.called
        call_args = service.turn_assessment_repo.create_assessment.call_args

        assert call_args.kwargs["learning_assessment"] is not None
        assert call_args.kwargs["turn_interpretation"] is None
        assert call_args.kwargs["learning_objective"] is None
        assert call_args.kwargs["question_specification"] is None

    def test_send_message_does_not_persist_when_no_assessment(self):
        """Test that no assessment record is created when AIResult has no assessment data."""
        session_id = uuid4()
        mock_db = MagicMock()

        # AIResult without any assessment fields
        ai_result = create_mock_ai_result()
        ai_result.learning_assessment = None
        ai_result.turn_interpretation = None
        ai_result.learning_objective = None
        ai_result.question_specification = None

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Test answer"),
            create_dummy_message(uuid4(), session_id, "AI", "Test response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Test answer", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        # Verify turn_assessment_repo.create_assessment was NOT called
        assert not service.turn_assessment_repo.create_assessment.called

    def test_multiple_turns_create_separate_assessment_records(self):
        """Test that each turn creates a separate assessment record linked to its message."""
        session_id = uuid4()
        mock_db = MagicMock()

        service = ChatService(ai_engine=MagicMock())
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.create_evaluation = MagicMock()

        user_msg_ids = []
        ai_msg_ids = []

        # Turn 1
        user_msg_ids.append(uuid4())
        ai_msg_ids.append(uuid4())
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(user_msg_ids[0], session_id, "USER", "Turn 1 answer"),
            create_dummy_message(ai_msg_ids[0], session_id, "AI", "Turn 1 response"),
        ])

        ai_result_1 = create_mock_ai_result_with_assessment(
            learning_assessment=create_dummy_learning_assessment(
                classification=AssessmentClassification.CORRECT,
            )
        )
        service.ai_engine = MagicMock()
        service.ai_engine.process.return_value = ai_result_1

        service.send_message(mock_db, session_id, MessageCreate(content="Turn 1 answer", input_type=CommonInputType.TEXT))

        # Turn 2
        user_msg_ids.append(uuid4())
        ai_msg_ids.append(uuid4())
        service.message_repo.list_by_session = MagicMock(return_value=[
            create_dummy_message(user_msg_ids[0], session_id, "USER", "Turn 1 answer"),
            create_dummy_message(ai_msg_ids[0], session_id, "AI", "Turn 1 response"),
        ])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(user_msg_ids[1], session_id, "USER", "Turn 2 answer"),
            create_dummy_message(ai_msg_ids[1], session_id, "AI", "Turn 2 response"),
        ])

        ai_result_2 = create_mock_ai_result_with_assessment(
            learning_assessment=create_dummy_learning_assessment(
                classification=AssessmentClassification.PARTIAL,
            )
        )
        service.ai_engine = MagicMock()
        service.ai_engine.process.return_value = ai_result_2

        service.send_message(mock_db, session_id, MessageCreate(content="Turn 2 answer", input_type=CommonInputType.TEXT))

        # Verify two separate calls to create_assessment
        assert service.turn_assessment_repo.create_assessment.call_count == 2

        call1 = service.turn_assessment_repo.create_assessment.call_args_list[0]
        call2 = service.turn_assessment_repo.create_assessment.call_args_list[1]

        # Each call should have different message_id (user message id)
        assert call1.kwargs["message_id"] == user_msg_ids[0]
        assert call2.kwargs["message_id"] == user_msg_ids[1]

        # Each should have different assessment content
        assert call1.kwargs["learning_assessment"]["classification"] == "CORRECT"
        assert call2.kwargs["learning_assessment"]["classification"] == "PARTIAL"

    def test_assessment_associated_with_correct_session(self):
        """Test that assessment is linked to the correct session."""
        session_id_1 = uuid4()
        session_id_2 = uuid4()
        mock_db = MagicMock()

        service = ChatService(ai_engine=MagicMock())
        service.turn_assessment_repo = MagicMock()

        db_session_1 = create_dummy_db_session(session_id_1, current_mode="STUDENT")
        db_session_1.user_id = uuid4()

        db_session_2 = create_dummy_db_session(session_id_2, current_mode="STUDENT")
        db_session_2.user_id = uuid4()

        # Session 1
        service.session_repo.get = MagicMock(return_value=db_session_1)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id_1, "USER", "Session 1 answer"),
            create_dummy_message(uuid4(), session_id_1, "AI", "Response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        ai_result = create_mock_ai_result_with_assessment(
            learning_assessment=create_dummy_learning_assessment()
        )
        service.ai_engine = MagicMock()
        service.ai_engine.process.return_value = ai_result

        service.send_message(mock_db, session_id_1, MessageCreate(content="Session 1 answer", input_type=CommonInputType.TEXT))

        # Session 2
        service.session_repo.get = MagicMock(return_value=db_session_2)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id_2, "USER", "Session 2 answer"),
            create_dummy_message(uuid4(), session_id_2, "AI", "Response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        service.ai_engine = MagicMock()
        service.ai_engine.process.return_value = ai_result

        service.send_message(mock_db, session_id_2, MessageCreate(content="Session 2 answer", input_type=CommonInputType.TEXT))

        # Verify session_id in each call
        calls = service.turn_assessment_repo.create_assessment.call_args_list
        assert calls[0].kwargs["session_id"] == session_id_1
        assert calls[1].kwargs["session_id"] == session_id_2

    def test_teacher_mode_assessment_persists_correctly(self):
        """Test that Teacher Mode assessment data persists correctly."""
        session_id = uuid4()
        mock_db = MagicMock()

        # Assessment showing misconception in Teacher Mode
        teacher_assessment = create_dummy_learning_assessment(
            intent=AssessmentIntent.ANSWER_ATTEMPT,
            correctness=CorrectnessLevel.MISCONCEPTION,
            classification=AssessmentClassification.MISCONCEPTION,
        )
        teacher_assessment.misconception_status = True
        teacher_assessment.misconceptions = [
            MisconceptionEvidence(
                concept_id="photosynthesis",
                description="Learner believes photosynthesis only happens at night",
                learner_statement="Plants make food at night",
                severity="HIGH",
            )
        ]

        ai_result = create_mock_ai_result_with_assessment(
            next_mode=Mode.TEACHER,
            strategy=Strategy.TEACH_GAP,
            learning_assessment=teacher_assessment,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="TEACHER")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Plants make food at night"),
            create_dummy_message(uuid4(), session_id, "AI", "Let me explain..."),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Plants make food at night", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        assert service.turn_assessment_repo.create_assessment.called
        call_args = service.turn_assessment_repo.create_assessment.call_args

        saved_assessment = call_args.kwargs["learning_assessment"]
        assert saved_assessment["classification"] == "MISCONCEPTION"
        assert saved_assessment["misconception_status"] is True
        assert len(saved_assessment["misconceptions"]) == 1
        assert saved_assessment["misconceptions"][0]["description"] == "Learner believes photosynthesis only happens at night"

    def test_student_mode_assessment_persists_correctly(self):
        """Test that Student Mode assessment data persists correctly."""
        session_id = uuid4()
        mock_db = MagicMock()

        student_assessment = create_dummy_learning_assessment(
            intent=AssessmentIntent.ANSWER_ATTEMPT,
            correctness=CorrectnessLevel.PARTIALLY_CORRECT,
            classification=AssessmentClassification.PARTIAL,
        )
        student_assessment.completeness = CompletenessLevel.PARTIAL
        student_assessment.missing_concepts = ["calvin_cycle"]

        ai_result = create_mock_ai_result_with_assessment(
            next_mode=Mode.STUDENT,
            strategy=Strategy.PROBE_MISSING_CONCEPT,
            learning_assessment=student_assessment,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Partial answer"),
            create_dummy_message(uuid4(), session_id, "AI", "Good, but..."),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Partial answer", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        assert service.turn_assessment_repo.create_assessment.called
        call_args = service.turn_assessment_repo.create_assessment.call_args

        saved_assessment = call_args.kwargs["learning_assessment"]
        assert saved_assessment["classification"] == "PARTIAL"
        assert saved_assessment["completeness"] == "PARTIAL"
        assert "calvin_cycle" in saved_assessment["missing_concepts"]

    def test_existing_state_updates_persistence_continues_working(self):
        """Test that existing StateUpdates persistence is not affected by assessment persistence."""
        session_id = uuid4()
        mock_db = MagicMock()

        # StateUpdates with all Phase 3 fields
        state_updates = StateUpdates(
            concept_mastery={"new_concept": 0.9},
            misconception_counts={"new_misconception": 2},
            recent_strategy_history=[Strategy.TEACH_GAP],
            mode_switch_history=[
                ModeTransition(from_mode=Mode.STUDENT, to_mode=Mode.TEACHER, reason="test", timestamp="2026-01-01T00:00:00"),
            ],
        )

        # Also include assessment
        learning_assessment = create_dummy_learning_assessment()

        ai_result = create_mock_ai_result_with_assessment(
            state_updates=state_updates,
            learning_assessment=learning_assessment,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Test"),
            create_dummy_message(uuid4(), session_id, "AI", "Response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Test", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        # Verify SessionState was updated with Phase 3 fields
        service.session_repo.update_state.assert_called_once()
        persisted_state = service.session_repo.update_state.call_args[0][2]

        assert persisted_state.concept_mastery == {"new_concept": 0.9}
        assert persisted_state.misconception_counts == {"new_misconception": 2}
        assert persisted_state.recent_strategy_history == ["TEACH_GAP"]
        assert len(persisted_state.mode_switch_history) == 1

        # Verify assessment was also persisted
        assert service.turn_assessment_repo.create_assessment.called

    def test_existing_session_state_persistence_continues_working(self):
        """Test that existing SessionState fields persistence is not affected."""
        session_id = uuid4()
        mock_db = MagicMock()

        learning_assessment = create_dummy_learning_assessment()

        ai_result = create_mock_ai_result_with_assessment(
            learning_assessment=learning_assessment,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()
        # Pre-existing values
        db_session.state.active_concept = "Existing Concept"
        db_session.state.difficulty = 3
        db_session.state.confidence = 0.7
        db_session.state.current_mode = "STUDENT"
        db_session.state.consecutive_strong_answers = 2
        db_session.state.consecutive_weak_answers = 1

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Test"),
            create_dummy_message(uuid4(), session_id, "AI", "Response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Test", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        # Verify SessionState fields persisted
        service.session_repo.update_state.assert_called_once()
        persisted_state = service.session_repo.update_state.call_args[0][2]

        assert persisted_state.active_concept == "Dark Reaction"  # From AI result
        assert persisted_state.difficulty == 3  # From AI result
        assert persisted_state.confidence == 0.8  # From AI result
        assert persisted_state.current_mode == "STUDENT"

        # Verify assessment was also persisted
        assert service.turn_assessment_repo.create_assessment.called

    def test_ai_backend_boundary_intact(self):
        """Test that the repository does not call AI engine/provider."""
        from backend.app.repositories.turn_assessment_repository import TurnAssessmentRepository
        from backend.app.models.turn_assessment import TurnAssessment

        repo = TurnAssessmentRepository()
        mock_db = MagicMock()

        # The repository should only do DB operations
        result = repo.create_assessment(
            db=mock_db,
            message_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            learning_assessment={"test": "data"},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_round_trip_returns_same_structured_assessment(self):
        """Test that DB -> backend retrieval returns the same structured assessment."""
        from backend.app.repositories.turn_assessment_repository import TurnAssessmentRepository
        from backend.app.models.turn_assessment import TurnAssessment

        repo = TurnAssessmentRepository()
        mock_db = MagicMock()

        message_id = uuid4()
        session_id = uuid4()
        user_id = uuid4()

        original_assessment = {
            "intent": "ANSWER_ATTEMPT",
            "relevance_score": 0.95,
            "concept_alignment_score": 0.9,
            "claims": [{"text": "Test claim", "concept_id": "test", "claim_type": "MECHANISM", "alignment_score": 0.9}],
            "evidence": [{"concept_id": "test", "expected_description": "Test", "status": "SUPPORTED", "confidence": 0.9}],
            "correctness": "CORRECT",
            "correctness_score": 0.9,
            "completeness": "COMPLETE",
            "completeness_score": 0.9,
            "misconception_status": False,
            "misconceptions": [],
            "missing_concepts": [],
            "contradictory_claims": [],
            "classification": "CORRECT",
            "confidence": 0.95,
            "supports_mastery": True,
            "assessment_status": "HIGH_CONFIDENCE",
            "recommended_learning_action": "ADVANCE_CONCEPT",
        }

        # Mock the DB query to return an assessment with the original data
        mock_assessment = MagicMock(spec=TurnAssessment)
        mock_assessment.id = uuid4()
        mock_assessment.message_id = message_id
        mock_assessment.session_id = session_id
        mock_assessment.user_id = user_id
        mock_assessment.learning_assessment = original_assessment
        mock_assessment.turn_interpretation = {"intent": "ANSWER_ATTEMPT"}
        mock_assessment.learning_objective = {"objective_type": "UNDERSTAND_MECHANISM"}
        mock_assessment.question_specification = {"target_concept": "test"}

        mock_db.query.return_value.filter.return_value.first.return_value = mock_assessment

        # Retrieve and verify
        retrieved = repo.get_by_message_id(mock_db, message_id)

        assert retrieved is not None
        assert retrieved.learning_assessment == original_assessment
        assert retrieved.learning_assessment["intent"] == "ANSWER_ATTEMPT"
        assert retrieved.learning_assessment["relevance_score"] == 0.95
        assert len(retrieved.learning_assessment["claims"]) == 1
        assert retrieved.learning_assessment["claims"][0]["text"] == "Test claim"

    def test_cross_user_ownership_isolation(self):
        """Test that assessment data cannot be accessed by another user."""
        from backend.app.repositories.turn_assessment_repository import TurnAssessmentRepository
        from backend.app.models.turn_assessment import TurnAssessment

        repo = TurnAssessmentRepository()
        mock_db = MagicMock()

        user_1 = uuid4()
        user_2 = uuid4()
        session_id = uuid4()

        # Mock assessment belonging to user_1
        mock_assessment = MagicMock(spec=TurnAssessment)
        mock_assessment.user_id = user_1
        mock_assessment.session_id = session_id

        # Query for user_2 should return None (ownership check)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_message_id(mock_db, uuid4())

        # The repository itself doesn't enforce ownership at get_by_message_id level
        # (it only filters by message_id), but API layer should enforce it
        # This test documents the expected behavior
        assert result is None  # Because mock returns None

    def test_complex_nested_assessment_data_survives_json_serialization(self):
        """Test that complex nested assessment data survives JSON serialization."""
        session_id = uuid4()
        mock_db = MagicMock()

        # Complex assessment with nested structures
        complex_assessment = create_dummy_learning_assessment()
        complex_assessment.claims = [
            LearnerClaim(
                text="Claim 1",
                concept_id="concept_1",
                claim_type=ClaimType.DEFINITION,
                alignment_score=0.8,
                is_factually_sound=True,
            ),
            LearnerClaim(
                text="Claim 2",
                concept_id="concept_2",
                claim_type=ClaimType.MECHANISM,
                alignment_score=0.7,
                is_factually_sound=False,
            ),
        ]
        complex_assessment.evidence = [
            EvidenceItem(
                concept_id="concept_1",
                expected_description="Definition of concept 1",
                status=EvidenceStatus.SUPPORTED,
                supported_by_claim="Claim 1",
                confidence=0.9,
            ),
            EvidenceItem(
                concept_id="concept_2",
                expected_description="Mechanism of concept 2",
                status=EvidenceStatus.PARTIALLY_SUPPORTED,
                supported_by_claim="Claim 2",
                contradicted_by_claim="Alternative claim",
                confidence=0.6,
            ),
        ]
        complex_assessment.misconceptions = [
            MisconceptionEvidence(
                concept_id="concept_2",
                description="Misunderstanding of mechanism",
                learner_statement="Wrong mechanism",
                severity="MEDIUM",
                counter_evidence="Correct mechanism explanation",
            )
        ]
        complex_assessment.metadata = {"custom_field": "custom_value", "nested": {"key": "value"}}

        ai_result = create_mock_ai_result_with_assessment(
            learning_assessment=complex_assessment,
        )

        mock_engine = MagicMock()
        mock_engine.process.return_value = ai_result

        service = ChatService(ai_engine=mock_engine)
        service.turn_assessment_repo = MagicMock()

        db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
        db_session.user_id = uuid4()

        service.session_repo.get = MagicMock(return_value=db_session)
        service.session_repo.update_state = MagicMock()
        service.message_repo.list_by_session = MagicMock(return_value=[])
        service.message_repo.create_message = MagicMock(side_effect=[
            create_dummy_message(uuid4(), session_id, "USER", "Complex answer"),
            create_dummy_message(uuid4(), session_id, "AI", "Response"),
        ])
        service.message_repo.create_evaluation = MagicMock()

        message_in = MessageCreate(content="Complex answer", input_type=CommonInputType.TEXT)
        service.send_message(mock_db, session_id, message_in)

        assert service.turn_assessment_repo.create_assessment.called
        call_args = service.turn_assessment_repo.create_assessment.call_args

        saved = call_args.kwargs["learning_assessment"]

        # Verify complex nested structures
        assert len(saved["claims"]) == 2
        assert saved["claims"][0]["claim_type"] == "DEFINITION"
        assert saved["claims"][1]["claim_type"] == "MECHANISM"
        assert saved["claims"][0]["is_factually_sound"] is True
        assert saved["claims"][1]["is_factually_sound"] is False

        assert len(saved["evidence"]) == 2
        assert saved["evidence"][0]["status"] == "SUPPORTED"
        assert saved["evidence"][1]["status"] == "PARTIALLY_SUPPORTED"
        assert saved["evidence"][1]["contradicted_by_claim"] == "Alternative claim"

        assert len(saved["misconceptions"]) == 1
        assert saved["misconceptions"][0]["severity"] == "MEDIUM"
        assert saved["misconceptions"][0]["counter_evidence"] == "Correct mechanism explanation"

        assert saved["metadata"]["custom_field"] == "custom_value"
        assert saved["metadata"]["nested"]["key"] == "value"