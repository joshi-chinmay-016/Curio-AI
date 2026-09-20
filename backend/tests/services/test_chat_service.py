from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
import pytest

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
    Mode,
    StateUpdates,
    Strategy,
    TurnEvaluation,
)


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


def create_mock_ai_result(
    next_mode=Mode.STUDENT,
    strategy=Strategy.PROBE_WHY,
    state_updates=None,
):
    """Helper to build a strongly-typed AIResult."""
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


def test_send_message_invokes_curio_engine_with_canonical_context():
    """Verify CurioEngine.process(context) is invoked with canonical nested AIContext and persisted state."""
    session_id = uuid4()
    q_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    # Mock repositories
    db_session = create_dummy_db_session(session_id, current_mode="STUDENT", current_qid=q_id)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()

    prev_ai_q = create_dummy_message(q_id, session_id, "AI", "What absorbs the light in plant leaves?")
    service.message_repo.list_by_session = MagicMock(return_value=[prev_ai_q])

    user_msg_id = uuid4()
    mock_user_msg = create_dummy_message(user_msg_id, session_id, "USER", "Chlorophyll absorbs sunlight.")
    ai_msg_id = uuid4()
    mock_ai_msg = create_dummy_message(ai_msg_id, session_id, "AI", "Excellent! Now how does the Calvin cycle work?")

    service.message_repo.create_message = MagicMock(side_effect=[mock_user_msg, mock_ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    # Call send_message
    message_in = MessageCreate(content="Chlorophyll absorbs sunlight.", input_type=CommonInputType.TEXT)
    response = service.send_message(mock_db, session_id, message_in)

    # 1. Assert CurioEngine was invoked
    mock_engine.process.assert_called_once()
    context: AIContext = mock_engine.process.call_args[0][0]

    assert isinstance(context, AIContext)
    # Session info
    assert context.session.session_id == str(session_id)
    assert context.session.topic == "Photosynthesis"
    # State fields
    assert context.current_state.understanding_confidence == 0.6
    assert context.current_state.unresolved_misconceptions == ["misconception_solar"]
    assert context.current_state.consecutive_successes == 2
    assert context.current_state.consecutive_failures == 0
    assert context.current_state.active_concept == "Light Reaction"
    assert context.current_state.current_mode == Mode.STUDENT
    assert context.current_state.current_difficulty == 2

    # CurrentQuestion hydration
    assert isinstance(context.current_state.current_question, CurrentQuestion)
    assert context.current_state.current_question.id == str(q_id)
    assert context.current_state.current_question.content == "What absorbs the light in plant leaves?"
    assert context.current_state.current_question.concept == "Light Reaction"
    assert context.current_state.current_question.difficulty == 2

    # Learning context
    assert context.learning_context.mastered_concepts == ["chlorophyll_basics"]
    assert context.learning_context.unresolved_misconceptions == ["misconception_solar"]


def test_send_message_merges_partial_state_updates():
    """Verify that when StateUpdates has None for some fields, existing database state is preserved."""
    session_id = uuid4()
    mock_db = MagicMock()

    # State updates where difficulty, active_concept, and streaks are None
    partial_updates = StateUpdates(
        confidence=0.95,
        current_mode=Mode.TEACHER,
        difficulty=None,
        active_concept=None,
        mastered_concepts=["light_photons"],
        consecutive_successes=None,
        consecutive_failures=None,
    )
    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.TEACH_GAP,
        state_updates=partial_updates,
    )

    service = ChatService(ai_engine=mock_engine)

    db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
    db_session.state.difficulty = 4
    db_session.state.active_concept = "Calvin Cycle"
    db_session.state.confidence = 0.5

    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()
    service.message_repo.list_by_session = MagicMock(return_value=[])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "I don't understand.")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Let me explain step by step.")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="I don't understand.", input_type=CommonInputType.TEXT)
    service.send_message(mock_db, session_id, message_in)

    # Verify what was passed to session_repo.update_state
    service.session_repo.update_state.assert_called_once()
    saved_state = service.session_repo.update_state.call_args[0][2]

    # Non-None fields from updates should be applied
    assert saved_state.confidence == 0.95
    assert saved_state.current_mode == LearningMode.TEACHER
    # None fields in updates should preserve existing DB values
    assert saved_state.difficulty == 4
    assert saved_state.active_concept == "Calvin Cycle"
    # Mastered concepts should include existing plus any new
    assert "chlorophyll_basics" in saved_state.mastered_concepts
    assert "light_photons" in saved_state.mastered_concepts


def test_send_message_explicit_enum_conversions():
    """Verify Mode and Strategy enums are converted to LearningMode and LearningStrategy explicitly."""
    session_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result(
        next_mode=Mode.TEACHER,
        strategy=Strategy.TEACH_GAP,
    )

    service = ChatService(ai_engine=mock_engine)

    db_session = create_dummy_db_session(session_id, current_mode="STUDENT")
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()
    service.message_repo.list_by_session = MagicMock(return_value=[])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "Help me understand.")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Here is a breakdown.")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="Help me understand.", input_type=CommonInputType.TEXT)
    turn_response = service.send_message(mock_db, session_id, message_in)

    # API response checks
    assert isinstance(turn_response.decision.next_mode, LearningMode)
    assert turn_response.decision.next_mode == LearningMode.TEACHER

    assert isinstance(turn_response.decision.strategy, LearningStrategy)
    assert turn_response.decision.strategy == LearningStrategy.TEACH_GAP

    assert isinstance(turn_response.evaluation.recommended_strategy, LearningStrategy)
    assert turn_response.evaluation.recommended_strategy == LearningStrategy.INCREASE_DIFFICULTY


def test_send_message_preserves_api_response_format():
    """Verify ChatService returns an exact ChatTurnResponse with correct payload types."""
    session_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    db_session = create_dummy_db_session(session_id)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()
    service.message_repo.list_by_session = MagicMock(return_value=[])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "Hello")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Welcome!")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="Hello", input_type=CommonInputType.TEXT)
    res = service.send_message(mock_db, session_id, message_in)

    assert isinstance(res, ChatTurnResponse)
    assert isinstance(res.user_message, MessageResponse)
    assert isinstance(res.ai_message, MessageResponse)
    assert isinstance(res.evaluation, TurnEvaluationResponse)
    assert isinstance(res.decision, LearningDecisionResponse)

    assert res.user_message.message_id == user_msg.id
    assert res.user_message.content == "Hello"
    assert res.ai_message.message_id == ai_msg.id
    assert res.ai_message.content == "Welcome!"
    assert res.evaluation.correctness == 0.9


def test_send_message_safe_question_hydration_when_missing():
    """Verify that if current_question_id is None or unfound, current_question is None (no fake data)."""
    session_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    # current_question_id is set to a UUID that does NOT exist in db_history
    unfound_qid = uuid4()
    db_session = create_dummy_db_session(session_id, current_qid=unfound_qid)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()
    # Empty message history
    service.message_repo.list_by_session = MagicMock(return_value=[])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "First answer.")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "First question.")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="First answer.", input_type=CommonInputType.TEXT)
    service.send_message(mock_db, session_id, message_in)

    context: AIContext = mock_engine.process.call_args[0][0]
    assert context.current_state.current_question is None


def test_send_message_raises_when_session_not_found():
    """Verify ValueError is raised if the session does not exist."""
    session_id = uuid4()
    mock_db = MagicMock()

    service = ChatService(ai_engine=MagicMock())
    service.session_repo.get = MagicMock(return_value=None)

    message_in = MessageCreate(content="Hello", input_type=CommonInputType.TEXT)
    with pytest.raises(ValueError, match=f"Active session {session_id} not found."):
        service.send_message(mock_db, session_id, message_in)


def test_get_messages_mapping():
    """Verify get_messages cleanly maps database messages to MessageResponse."""
    session_id = uuid4()
    mock_db = MagicMock()

    service = ChatService(ai_engine=MagicMock())
    m1 = create_dummy_message(uuid4(), session_id, "USER", "Msg 1")
    m2 = create_dummy_message(uuid4(), session_id, "AI", "Msg 2")
    service.message_repo.list_by_session = MagicMock(return_value=[m1, m2])

    responses = service.get_messages(mock_db, session_id)
    assert len(responses) == 2
    assert responses[0].message_id == m1.id
    assert responses[0].sender == "USER"
    assert responses[1].message_id == m2.id
    assert responses[1].sender == "AI"


def test_question_hydration_uuid_vs_string_id_comparison():
    """Verify safe str(message.id) == str(target_id) comparison when types are mismatched (UUID vs str)."""
    session_id = uuid4()
    q_uuid = uuid4()
    int_uuid = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    # Session state has string representations of the UUIDs
    db_session = create_dummy_db_session(session_id)
    db_session.state.current_question_id = str(q_uuid)  # Target is string
    db_session.state.interrupted_question_id = str(int_uuid)  # Target is string

    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()

    # Message objects in history have native UUID objects
    q_msg = create_dummy_message(q_uuid, session_id, "AI", "What is chlorophyll?")  # Message has UUID
    int_msg = create_dummy_message(int_uuid, session_id, "AI", "What is a chloroplast?")  # Message has UUID
    service.message_repo.list_by_session = MagicMock(return_value=[int_msg, q_msg])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "Answer")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Follow up")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="Answer", input_type=CommonInputType.TEXT)
    service.send_message(mock_db, session_id, message_in)

    context: AIContext = mock_engine.process.call_args[0][0]
    assert context.current_state.current_question is not None
    assert context.current_state.current_question.id == str(q_uuid)
    assert context.current_state.current_question.content == "What is chlorophyll?"

    assert context.current_state.interrupted_question is not None
    assert context.current_state.interrupted_question.id == str(int_uuid)
    assert context.current_state.interrupted_question.content == "What is a chloroplast?"


def test_input_type_normalization_lowercase():
    """Verify lowercase 'text' and 'voice' strings are safely normalized to uppercase enums."""
    session_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    db_session = create_dummy_db_session(session_id)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()

    # History contains lowercase input_type strings
    m1 = create_dummy_message(uuid4(), session_id, "USER", "Hello lowercase text")
    m1.input_type = "text"
    m2 = create_dummy_message(uuid4(), session_id, "AI", "Audio response")
    m2.input_type = "voice"
    service.message_repo.list_by_session = MagicMock(return_value=[m1, m2])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "Hi")
    user_msg.input_type = "text"
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Bye")
    ai_msg.input_type = "text"
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="Hi", input_type=CommonInputType.TEXT)
    turn_response = service.send_message(mock_db, session_id, message_in)

    # 1. AIContext ChatMessage normalization
    context: AIContext = mock_engine.process.call_args[0][0]
    assert context.conversation.recent_messages[0].input_type == InputType.TEXT
    assert context.conversation.recent_messages[1].input_type == InputType.VOICE

    # 2. API Response normalization
    assert turn_response.user_message.input_type == CommonInputType.TEXT
    assert turn_response.ai_message.input_type == CommonInputType.TEXT

    # 3. get_messages normalization
    retrieved = service.get_messages(mock_db, session_id)
    assert retrieved[0].input_type == CommonInputType.TEXT
    assert retrieved[1].input_type == CommonInputType.VOICE


def test_input_type_normalization_missing():
    """Verify None or missing input_type safely defaults to TEXT without raising exceptions."""
    session_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    db_session = create_dummy_db_session(session_id)
    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()

    # Message with None and message without input_type attribute
    m1 = create_dummy_message(uuid4(), session_id, "USER", "None input type")
    m1.input_type = None

    m2 = MagicMock(spec=["id", "session_id", "sender", "content", "created_at"])
    m2.id = uuid4()
    m2.session_id = session_id
    m2.sender = "AI"
    m2.content = "Missing attribute"
    m2.created_at = datetime.now(timezone.utc)
    service.message_repo.list_by_session = MagicMock(return_value=[m1, m2])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "Hi")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Bye")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="Hi", input_type=CommonInputType.TEXT)
    turn_response = service.send_message(mock_db, session_id, message_in)

    context: AIContext = mock_engine.process.call_args[0][0]
    assert context.conversation.recent_messages[0].input_type == InputType.TEXT
    assert context.conversation.recent_messages[1].input_type == InputType.TEXT

    retrieved = service.get_messages(mock_db, session_id)
    assert retrieved[0].input_type == CommonInputType.TEXT
    assert retrieved[1].input_type == CommonInputType.TEXT


def test_question_hydration_missing_question_ids():
    """Verify that when question IDs are None, empty, or unfound, hydration safely yields None."""
    session_id = uuid4()
    mock_db = MagicMock()

    mock_engine = MagicMock()
    mock_engine.process.return_value = create_mock_ai_result()

    service = ChatService(ai_engine=mock_engine)

    # 1. Both IDs are explicitly None
    db_session = create_dummy_db_session(session_id)
    db_session.state.current_question_id = None
    db_session.state.interrupted_question_id = None

    service.session_repo.get = MagicMock(return_value=db_session)
    service.session_repo.update_state = MagicMock()

    m1 = create_dummy_message(uuid4(), session_id, "USER", "Msg")
    service.message_repo.list_by_session = MagicMock(return_value=[m1])

    user_msg = create_dummy_message(uuid4(), session_id, "USER", "Hi")
    ai_msg = create_dummy_message(uuid4(), session_id, "AI", "Bye")
    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.message_repo.create_evaluation = MagicMock()

    message_in = MessageCreate(content="Hi", input_type=CommonInputType.TEXT)
    service.send_message(mock_db, session_id, message_in)

    context: AIContext = mock_engine.process.call_args[0][0]
    assert context.current_state.current_question is None
    assert context.current_state.interrupted_question is None

    # 2. Both IDs point to messages not in history
    db_session.state.current_question_id = uuid4()
    db_session.state.interrupted_question_id = uuid4()

    service.message_repo.create_message = MagicMock(side_effect=[user_msg, ai_msg])
    service.send_message(mock_db, session_id, message_in)

    context2: AIContext = mock_engine.process.call_args[0][0]
    assert context2.current_state.current_question is None
    assert context2.current_state.interrupted_question is None

