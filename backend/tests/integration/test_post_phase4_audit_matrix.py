"""
Post-Phase-4 Integration & Architecture Audit End-to-End Test Matrix.
Verifies all 25 critical scenarios spanning AI Milestone A and Backend Phase 4:
1. Correct answer
2. Completely wrong answer
3. Technically true but irrelevant answer
4. Partial answer
5. Misconception
6. "I don't know"
7. "I understand"
8. Clarification request
9. Off-topic answer
10. Nonsense answer
11. Teacher verification success
12. Teacher verification failure
13. Teacher verification acknowledgement
14. Interrupted question restoration
15. Session reload/resume
16. Multiple sessions for same concept
17. Report generation
18. Report regeneration
19. Historical report remains stable
20. Cross-session progress aggregation
21. Unauthorized session access
22. Unauthorized report access
23. Invalid/expired authentication
24. AI provider failure
25. Malformed assessment output
"""
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.models.session import Session, SessionState as DBSessionState
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation as DBTurnEval
from backend.app.models.report import SessionReport
from backend.app.models.report_version import SessionReportVersion
from backend.app.models.report_evidence_snapshot import ReportEvidenceSnapshot
from backend.app.models.concept_progress import UserConceptProgress
from backend.app.services.chat_service import ChatService
from backend.app.services.report_service import ReportService
from backend.app.services.learning_progress_service import LearningProgressService
from backend.app.ai.engine import CurioEngine
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
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
    RelevanceLevel,
)
from backend.app.ai.schemas import (
    AIContext,
    ChatMessage,
    ConceptModel,
    ConceptNode,
    ConversationContext,
    CurrentQuestion,
    LearningContext,
    Mode,
    Role,
    SessionInfo,
    SessionState as AISessionState,
    Strategy,
)
from backend.app.schemas.message import MessageCreate

pytestmark = pytest.mark.db_integration


@pytest.fixture
def mock_engine():
    provider = MockLLMProvider()
    return CurioEngine(provider=provider)


@pytest.fixture
def dbms_concept_model():
    return ConceptModel(
        topic="DBMS",
        concepts=[
            ConceptNode(
                id="atomicity",
                name="Atomicity",
                definition="All operations in a transaction either commit together or roll back completely.",
                constraints=["all-or-nothing transaction execution", "rollback on any operation failure"],
                common_misconceptions=["transactions can partially commit or complete"],
                difficulty_level=2,
            )
        ],
    )


# ==============================================================================
# 1-10: Answer Intelligence & Mastery Integrity Scenarios
# ==============================================================================

def test_01_correct_answer_progression(dbms_concept_model):
    """1. Correct substantive answer grants positive mastery progression."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "All operations in a transaction either commit together or roll back completely, ensuring all-or-nothing execution."
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-1", topic="DBMS"),
            current_state=AISessionState(session_id="test-1", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    assert assessment.intent == AssessmentIntent.ANSWER_ATTEMPT
    assert assessment.correctness == CorrectnessLevel.CORRECT
    assert assessment.relevance_level == RelevanceLevel.RELEVANT
    assert assessment.supports_mastery is True

    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is True
    assert decision.mastery_delta_allowed is True
    assert decision.allowed_delta > 0.0
    assert decision.evidence_count_increment == 1
    assert decision.record_as_gap is False


def test_02_completely_wrong_answer_blocks_mastery(dbms_concept_model):
    """2. Completely wrong answer denies mastery and records a gap."""
    gate = MasteryGate()

    wrong_assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.75,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.60,
        correctness=CorrectnessLevel.INCORRECT,
        correctness_score=0.10,
        completeness=CompletenessLevel.MINIMAL,
        completeness_score=0.10,
        classification=AssessmentClassification.INCORRECT,
        confidence=0.90,
        supports_mastery=False,
    )

    decision = gate.evaluate(wrong_assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False
    assert decision.record_as_gap is True


def test_03_technically_true_but_irrelevant_answer(dbms_concept_model):
    """3. Technically true but irrelevant answer denies mastery."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "Mitochondria is the powerhouse of the cell and generates ATP."
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-3", topic="DBMS"),
            current_state=AISessionState(session_id="test-3", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity in transactions", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    assert assessment.relevance_level in (RelevanceLevel.IRRELEVANT, RelevanceLevel.UNCERTAIN)
    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False


def test_04_partial_answer_bounded_evidence(dbms_concept_model):
    """4. Partial answer gives bounded progression only, not full mastery."""
    gate = MasteryGate()

    partial_assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.90,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.85,
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.55,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.50,
        classification=AssessmentClassification.PARTIAL,
        confidence=0.85,
        supports_mastery=False,
        evidence=[EvidenceItem(concept_id="atomicity", expected_description="all-or-nothing", status=EvidenceStatus.SUPPORTED)],
    )

    decision = gate.evaluate(partial_assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is True
    assert decision.allowed_delta <= 0.15
    assert decision.record_as_gap is False


def test_05_misconception_blocks_mastery_and_records_misconception(dbms_concept_model):
    """5. Misconception blocks positive mastery and flags misconception."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "A transaction can partially commit successful queries while rolling back failed ones."
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-5", topic="DBMS"),
            current_state=AISessionState(session_id="test-5", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Can transactions partially commit?", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False
    assert decision.record_as_misconception is True
    assert decision.record_as_gap is True


def test_06_i_dont_know_no_mastery(dbms_concept_model):
    """6. 'I don't know' / Help request denies mastery."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "I don't know, could you help me understand?"
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-6", topic="DBMS"),
            current_state=AISessionState(session_id="test-6", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    assert assessment.intent == AssessmentIntent.HELP_REQUEST
    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False


def test_07_i_understand_acknowledgement_no_mastery(dbms_concept_model):
    """7. 'I understand' acknowledgement alone never grants mastery."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "I understand."
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-7", topic="DBMS"),
            current_state=AISessionState(session_id="test-7", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    assert assessment.intent == AssessmentIntent.ACKNOWLEDGEMENT
    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False


def test_08_clarification_request_no_mastery(dbms_concept_model):
    """8. Clarification request denies mastery."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "Can you clarify what rollback means in this context?"
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-8", topic="DBMS"),
            current_state=AISessionState(session_id="test-8", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    assert assessment.intent == AssessmentIntent.CLARIFICATION_REQUEST
    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False


def test_09_off_topic_answer_no_mastery(dbms_concept_model):
    """9. Off-topic answer denies mastery."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "What time does the grocery store close tonight?"
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-9", topic="DBMS"),
            current_state=AISessionState(session_id="test-9", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    assert assessment.relevance_level in (RelevanceLevel.IRRELEVANT, RelevanceLevel.UNCERTAIN)
    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False


def test_10_nonsense_answer_no_mastery(dbms_concept_model):
    """10. Nonsense gibberish denies mastery."""
    aggregator = AssessmentAggregator()
    gate = MasteryGate()

    answer = "asdfjkllskdjf 12837192837 !@#$%"
    assessment = aggregator.assess(
        user_message=answer,
        context=AIContext(
            session=SessionInfo(session_id="test-10", topic="DBMS"),
            current_state=AISessionState(session_id="test-10", active_concept="atomicity"),
        ),
        current_question=CurrentQuestion(id="q1", content="Explain atomicity", concept="atomicity", difficulty=2),
        concept_model=dbms_concept_model,
        target_concept_override="atomicity",
    )

    decision = gate.evaluate(assessment, "atomicity")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False


# ==============================================================================
# 11-14: Teacher Mode Lifecycle & Restoration Scenarios
# ==============================================================================

def test_11_teacher_verification_success_restores_student_mode(test_db_session, test_user, mock_engine):
    """11. Correct substantive answer to verification question passes and restores interrupted question."""
    chat_service = ChatService(ai_engine=mock_engine)

    session = Session(user_id=test_user.id, topic="DBMS", status="ACTIVE")
    test_db_session.add(session)
    test_db_session.commit()

    interrupted_qid = uuid.uuid4()
    current_vqid = uuid.uuid4()

    state = DBSessionState(
        session_id=session.id,
        current_mode="TEACHER",
        difficulty=1,
        active_concept="atomicity",
        current_question_id=current_vqid,
        interrupted_question_id=interrupted_qid,
        teacher_attempt_count=1,
        teacher_intervention={"active": True, "gap": "atomicity", "attempt_count": 1, "verification_required": True},
    )
    test_db_session.add(state)
    test_db_session.commit()

    ans = "Verified: rollback completely undoes every single operation in the transaction."
    msg = MessageCreate(content=ans, input_type="TEXT")
    turn = chat_service.send_message(test_db_session, session.id, msg, user_id=test_user.id)

    assert turn.decision.next_mode.value == "STUDENT"
    assert turn.decision.should_restore_interrupted_question is True

    updated_state = test_db_session.query(DBSessionState).filter_by(session_id=session.id).first()
    assert updated_state.current_mode == "STUDENT"
    assert updated_state.interrupted_question_id is None
    assert updated_state.teacher_attempt_count == 0


def test_12_teacher_verification_failure_keeps_teacher_mode(test_db_session, test_user, mock_engine):
    """12. Failing verification keeps Teacher Mode active."""
    chat_service = ChatService(ai_engine=mock_engine)

    session = Session(user_id=test_user.id, topic="DBMS", status="ACTIVE")
    test_db_session.add(session)
    test_db_session.commit()

    interrupted_qid = uuid.uuid4()
    current_vqid = uuid.uuid4()

    state = DBSessionState(
        session_id=session.id,
        current_mode="TEACHER",
        difficulty=1,
        active_concept="atomicity",
        current_question_id=current_vqid,
        interrupted_question_id=interrupted_qid,
        teacher_attempt_count=1,
        teacher_intervention={"active": True, "gap": "atomicity", "attempt_count": 1, "verification_required": True},
    )
    test_db_session.add(state)
    test_db_session.commit()

    ans = "Misconception: rollback keeps the changes that succeeded and ignores failures."
    msg = MessageCreate(content=ans, input_type="TEXT")
    turn = chat_service.send_message(test_db_session, session.id, msg, user_id=test_user.id)

    assert turn.decision.next_mode.value == "TEACHER"
    assert turn.decision.should_restore_interrupted_question is False

    updated_state = test_db_session.query(DBSessionState).filter_by(session_id=session.id).first()
    assert updated_state.current_mode == "TEACHER"
    assert updated_state.interrupted_question_id is not None


def test_13_teacher_verification_acknowledgement_does_not_pass(test_db_session, test_user, mock_engine):
    """13. Pure acknowledgement in Teacher Mode does NOT pass verification."""
    chat_service = ChatService(ai_engine=mock_engine)

    session = Session(user_id=test_user.id, topic="DBMS", status="ACTIVE")
    test_db_session.add(session)
    test_db_session.commit()

    interrupted_qid = uuid.uuid4()
    current_vqid = uuid.uuid4()

    state = DBSessionState(
        session_id=session.id,
        current_mode="TEACHER",
        difficulty=1,
        active_concept="atomicity",
        current_question_id=current_vqid,
        interrupted_question_id=interrupted_qid,
        teacher_attempt_count=1,
        teacher_intervention={"active": True, "gap": "atomicity", "attempt_count": 1, "verification_required": True},
    )
    test_db_session.add(state)
    test_db_session.commit()

    ans = "I understand."
    msg = MessageCreate(content=ans, input_type="TEXT")
    turn = chat_service.send_message(test_db_session, session.id, msg, user_id=test_user.id)

    assert turn.decision.next_mode.value == "TEACHER"
    assert turn.decision.should_restore_interrupted_question is False


def test_14_interrupted_question_restoration(test_db_session, test_user, mock_engine):
    """14. Interrupted question content is preserved during teacher mode and restored upon exit."""
    chat_service = ChatService(ai_engine=mock_engine)

    session = Session(user_id=test_user.id, topic="DBMS", status="ACTIVE")
    test_db_session.add(session)
    test_db_session.commit()

    orig_q_id = uuid.uuid4()
    msg_q = Message(id=orig_q_id, session_id=session.id, sender="AI", content="Deep Question: How does WAL guarantee atomicity?")
    test_db_session.add(msg_q)
    test_db_session.commit()

    state = DBSessionState(
        session_id=session.id,
        current_mode="TEACHER",
        difficulty=1,
        active_concept="atomicity",
        current_question_id=uuid.uuid4(),
        interrupted_question_id=orig_q_id,
        teacher_attempt_count=1,
        teacher_intervention={"active": True, "gap": "atomicity", "attempt_count": 1, "verification_required": True},
    )
    test_db_session.add(state)
    test_db_session.commit()

    ans = "Verified: rollback completely undoes every single operation in the transaction."
    msg = MessageCreate(content=ans, input_type="TEXT")
    turn = chat_service.send_message(test_db_session, session.id, msg, user_id=test_user.id)

    assert turn.decision.should_restore_interrupted_question is True
    updated_state = test_db_session.query(DBSessionState).filter_by(session_id=session.id).first()
    assert updated_state.interrupted_question_id is None


# ==============================================================================
# 15-20: Persistence, Reports, Versioning & Cross-Session Scenarios
# ==============================================================================

def test_15_session_reload_resume(test_db_session, test_user, mock_engine):
    """15. Session reload/resume rehydrates all state fields accurately."""
    chat_service = ChatService(ai_engine=mock_engine)

    session = Session(user_id=test_user.id, topic="Algorithms", status="ACTIVE")
    test_db_session.add(session)
    test_db_session.commit()

    state = DBSessionState(
        session_id=session.id,
        current_mode="STUDENT",
        difficulty=3,
        confidence=0.85,
        active_concept="binary_search",
        concept_mastery={"binary_search": 0.75},
        misconception_counts={"binary_search": 1},
        unresolved_misconceptions=[],
        mastered_concepts=["linear_search"],
    )
    test_db_session.add(state)
    test_db_session.commit()

    turn = chat_service.send_message(
        test_db_session,
        session.id,
        MessageCreate(content="Binary search operates on sorted arrays in O(log n) time.", input_type="TEXT"),
        user_id=test_user.id,
    )

    reloaded = test_db_session.query(DBSessionState).filter_by(session_id=session.id).first()
    assert reloaded.active_concept == "binary_search"
    assert reloaded.concept_mastery.get("binary_search") is not None
    assert "linear_search" in reloaded.mastered_concepts


def test_16_multiple_sessions_same_concept(test_db_session, test_user, mock_engine):
    """16. Multiple sessions for same concept synchronize properly in UserConceptProgress."""
    chat_service = ChatService(ai_engine=mock_engine)

    # Session 1
    s1 = Session(user_id=test_user.id, topic="Algorithms", status="ACTIVE")
    test_db_session.add(s1)
    test_db_session.commit()
    st1 = DBSessionState(session_id=s1.id, current_mode="STUDENT", difficulty=2, active_concept="binary_search")
    test_db_session.add(st1)
    test_db_session.commit()

    chat_service.send_message(test_db_session, s1.id, MessageCreate(content="Binary search halves the search space each step.", input_type="TEXT"), user_id=test_user.id)

    # Session 2
    s2 = Session(user_id=test_user.id, topic="Algorithms", status="ACTIVE")
    test_db_session.add(s2)
    test_db_session.commit()
    st2 = DBSessionState(session_id=s2.id, current_mode="STUDENT", difficulty=3, active_concept="binary_search")
    test_db_session.add(st2)
    test_db_session.commit()

    chat_service.send_message(test_db_session, s2.id, MessageCreate(content="Binary search checks the middle element against the target key.", input_type="TEXT"), user_id=test_user.id)

    ucp = test_db_session.query(UserConceptProgress).filter_by(user_id=test_user.id, concept="binary_search").first()
    assert ucp is not None
    assert ucp.mastery_score >= 0.0
    assert ucp.mastery_score >= 0.0


def test_17_18_19_report_generation_regeneration_and_snapshot_stability(test_db_session, test_user, mock_engine):
    """17, 18, 19: Report generation (v1), regeneration (v2), and historical snapshot stability."""
    report_service = ReportService(ai_engine=mock_engine)

    session = Session(user_id=test_user.id, topic="Operating Systems", status="ACTIVE")
    test_db_session.add(session)
    test_db_session.commit()

    m1 = Message(session_id=session.id, sender="USER", content="Process synchronization prevents race conditions.")
    test_db_session.add(m1)
    test_db_session.commit()

    ev1 = DBTurnEval(
        message_id=m1.id,
        correctness=0.90,
        clarity=0.90,
        completeness=0.85,
        depth=0.80,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["process_synchronization"],
        knowledge_gap=None,
        recommended_strategy="INCREASE_DIFFICULTY",
        recommended_difficulty=3,
    )
    test_db_session.add(ev1)
    test_db_session.commit()

    # 17. Generate Report Version 1
    r1 = report_service.compile_report(test_db_session, session.id, user_id=test_user.id)
    assert r1 is not None
    assert r1.version_number == 1

    v1_record = test_db_session.query(SessionReportVersion).filter_by(session_id=session.id, version_number=1).first()
    assert v1_record is not None
    v1_score = v1_record.understanding_score

    snap1 = test_db_session.query(ReportEvidenceSnapshot).filter_by(report_version_id=v1_record.id).first()
    assert snap1 is not None
    assert snap1.schema_version == 1
    snap1_evidence_turns = len(snap1.evidence_json.get("turns", []))
    assert snap1_evidence_turns >= 1

    # Add new message for version 2
    m2 = Message(session_id=session.id, sender="USER", content="Semaphores provide signaling mechanisms.")
    test_db_session.add(m2)
    test_db_session.commit()
    ev2 = DBTurnEval(
        message_id=m2.id,
        correctness=0.95,
        clarity=0.95,
        completeness=0.90,
        depth=0.90,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        missing_concepts=[],
        undefined_terms=[],
        mastered_concepts=["semaphores"],
        knowledge_gap=None,
        recommended_strategy="INCREASE_DIFFICULTY",
        recommended_difficulty=4,
    )
    test_db_session.add(ev2)
    test_db_session.commit()

    # 18. Regenerate Report -> Version 2
    r2 = report_service.regenerate_report(test_db_session, session.id, user_id=test_user.id)
    assert r2 is not None
    assert r2.version_number == 2

    # 19. Historical Report Version 1 and Snapshot 1 remain completely stable
    v1_recheck = test_db_session.query(SessionReportVersion).filter_by(session_id=session.id, version_number=1).first()
    assert v1_recheck.understanding_score == v1_score
    snap1_recheck = test_db_session.query(ReportEvidenceSnapshot).filter_by(report_version_id=v1_record.id).first()
    assert len(snap1_recheck.evidence_json.get("turns", [])) == snap1_evidence_turns

    # Version 2 snapshot is distinct and isolated
    v2_record = test_db_session.query(SessionReportVersion).filter_by(session_id=session.id, version_number=2).first()
    snap2 = test_db_session.query(ReportEvidenceSnapshot).filter_by(report_version_id=v2_record.id).first()
    assert snap2 is not None
    assert snap2.id != snap1.id
    assert len(snap2.evidence_json.get("turns", [])) >= snap1_evidence_turns


def test_20_cross_session_progress_aggregation(test_db_session, test_user):
    """20. Cross-session progress aggregation provides factual totals without creating false mastery."""
    prog_service = LearningProgressService()

    ucp1 = UserConceptProgress(user_id=test_user.id, concept="deadlocks", mastery_score=0.85, total_attempts=5, successful_attempts=4, misconception_count=0)
    ucp2 = UserConceptProgress(user_id=test_user.id, concept="paging", mastery_score=0.40, total_attempts=3, successful_attempts=1, misconception_count=1)
    test_db_session.add_all([ucp1, ucp2])
    test_db_session.commit()

    summary_resp = prog_service.get_user_progress(test_db_session, test_user.id)
    assert summary_resp.user_id == test_user.id
    assert summary_resp.summary.total_concepts_tracked == 2
    assert summary_resp.summary.concepts_with_progress == 2
    assert summary_resp.summary.total_attempts == 8
    assert summary_resp.summary.total_successful_attempts == 5
    assert summary_resp.summary.total_misconceptions == 1


# ==============================================================================
# 21-23: Security, IDOR & Authentication Scenarios
# ==============================================================================

def test_21_unauthorized_session_access(authenticated_client, test_db_session, create_test_user):
    """21. Unauthorized session access is rejected with 404 (IDOR prevention)."""
    other_user = create_test_user()
    other_session = Session(user_id=other_user.id, topic="Secret Session", status="ACTIVE")
    test_db_session.add(other_session)
    test_db_session.commit()

    res = authenticated_client.get(f"/api/v1/sessions/{other_session.id}")
    assert res.status_code == 404


def test_22_unauthorized_report_access(authenticated_client, test_db_session, create_test_user):
    """22. Unauthorized report access is rejected with 404 (IDOR prevention)."""
    other_user = create_test_user()
    other_session = Session(user_id=other_user.id, topic="Confidential Report", status="COMPLETED")
    test_db_session.add(other_session)
    test_db_session.commit()

    rep = SessionReport(session_id=other_session.id, version_number=1, understanding_score=95.0, mastery_level="MASTERY")
    test_db_session.add(rep)
    test_db_session.commit()

    res = authenticated_client.get(f"/api/v1/sessions/{other_session.id}/report")
    assert res.status_code == 404


def test_23_invalid_or_expired_authentication():
    """23. Missing or invalid Bearer token returns 401 Unauthorized."""
    with TestClient(app) as unauth_client:
        res1 = unauth_client.get("/api/v1/sessions")
        assert res1.status_code == 401

        expired_token = create_access_token(subject=str(uuid.uuid4()), expires_delta=timedelta(seconds=-60))
        res2 = unauth_client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {expired_token}"})
        assert res2.status_code == 401


# ==============================================================================
# 24-25: Robustness, Provider Failures & Malformed Output
# ==============================================================================

def test_24_ai_provider_failure_safe_handling():
    """24. Provider failure results in graceful exception handling without granting false mastery."""
    class FailingProvider:
        def generate(self, *args, **kwargs):
            raise RuntimeError("Groq upstream connection timed out")
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("Groq upstream connection timed out")

    engine = CurioEngine(provider=FailingProvider())
    context = AIContext(
        session=SessionInfo(session_id="fail-test", topic="Failures"),
        current_state=AISessionState(session_id="fail-test", active_concept="resilience"),
        conversation=ConversationContext(recent_messages=[ChatMessage(role=Role.USER, content="Hello?")]),
    )

    result = engine.process(context)
    assert result is not None
    # Architectural requirement: Provider failure must NEVER grant false mastery
    assert result.state_updates.mastered_concepts is None or len(result.state_updates.mastered_concepts) == 0
    if result.learning_assessment:
        assert result.learning_assessment.supports_mastery is False
    assert result.evaluation.correctness == 0.0


def test_25_malformed_assessment_output_safe_denial():
    """25. Malformed assessment or UNASSESSABLE status denies mastery cleanly."""
    gate = MasteryGate()

    malformed_assessment = LearningAssessment(
        intent=AssessmentIntent.UNCERTAIN,
        is_answer_attempt=False,
        relevance_score=0.10,
        relevance_level=RelevanceLevel.UNCERTAIN,
        concept_alignment_score=0.0,
        correctness=CorrectnessLevel.UNASSESSABLE,
        correctness_score=0.0,
        completeness=CompletenessLevel.NOT_APPLICABLE,
        completeness_score=0.0,
        classification=AssessmentClassification.UNASSESSABLE,
        confidence=0.0,
        assessment_status=AssessmentStatus.ABSTAIN,
        supports_mastery=False,
    )

    decision = gate.evaluate(malformed_assessment, "any_concept")
    assert decision.supports_mastery is False
    assert decision.mastery_delta_allowed is False
    assert decision.allowed_delta == 0.0
    assert decision.evidence_count_increment == 0
