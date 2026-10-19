import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from typing import Dict, Any

import backend.app.db.base  # Ensure all SQLAlchemy models are registered
from backend.app.ai.schemas import (
    ConceptModel,
    ConceptNode,
    ConceptRelationship,
    RelationshipType,
    LearningObjective,
    CognitiveAction,
    ExpectedEvidenceRequirement,
    EvidenceType,
    AIContext,
    AIResult,
    AIResponse,
    CurrentQuestion,
    LearningDecision,
    Mode,
    StateUpdates,
    Strategy,
    TurnEvaluation,
    TurnInterpretation,
    TurnIntent,
)
from backend.app.ai.nodes.student_nodes import evaluation_node
from backend.app.models.session import Session, SessionState
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.session import SessionCreate, SessionStateBase
from backend.app.schemas.message import MessageCreate
from backend.app.schemas.common import LearningMode, SourceType
from backend.app.services.chat_service import ChatService


def _create_sample_concept_model(topic: str = "Recursion") -> ConceptModel:
    """Helper to create a fully populated ConceptModel with nodes and relationships."""
    c1 = ConceptNode(
        id="base_case",
        name="Base Case",
        description="The terminating condition that halts recursion.",
        prerequisites=[],
        learning_objectives=[
            LearningObjective(
                objective_id="obj_base_case_identify",
                concept_id="base_case",
                action=CognitiveAction.EXPLAIN,
                target="the necessity of a base case to prevent stack overflow",
                expected_evidence=[
                    ExpectedEvidenceRequirement(
                        evidence_id="req_base_1",
                        concept_id="base_case",
                        evidence_type=EvidenceType.DEFINITION,
                        description="States that recursion must terminate",
                    )
                ],
            )
        ],
    )
    c2 = ConceptNode(
        id="recursive_step",
        name="Recursive Step",
        description="The call to the function itself with reduced input.",
        prerequisites=["base_case"],
        learning_objectives=[],
    )
    rel = ConceptRelationship(
        source_concept_id="base_case",
        target_concept_id="recursive_step",
        relation_type="PREREQUISITE_OF",
        description="Base case must be understood before the recursive step.",
    )
    return ConceptModel(
        topic=topic,
        concepts=[c1, c2],
        relationships=[rel],
    )


# =====================================================================
# 1. ConceptModel serialization/deserialization round-trip
# =====================================================================

def test_concept_model_pydantic_v2_round_trip():
    """Verify ConceptModel serializes to JSON-mode dict and validates back losslessly."""
    original = _create_sample_concept_model("Recursion")

    # Pydantic v2 JSON-mode serialization
    dumped = original.model_dump(mode="json")
    assert isinstance(dumped, dict)
    assert dumped["topic"] == "Recursion"
    assert len(dumped["concepts"]) == 2
    assert dumped["concepts"][0]["id"] == "base_case"
    assert dumped["concepts"][0]["name"] == "Base Case"
    assert len(dumped["concepts"][0]["learning_objectives"]) == 1
    assert dumped["relationships"][0]["relation_type"] == "PREREQUISITE_OF"

    # Restoration using model_validate
    restored = ConceptModel.model_validate(dumped)
    assert restored.topic == original.topic
    assert len(restored.concepts) == len(original.concepts)
    assert restored.concepts[0].id == "base_case"
    assert restored.concepts[1].id == "recursive_step"
    assert len(restored.relationships) == 1
    assert restored.relationships[0].source_concept_id == "base_case"
    assert restored.relationships[0].target_concept_id == "recursive_step"
    assert restored.concepts[0].learning_objectives[0].objective_id == "obj_base_case_identify"


# =====================================================================
# 2. Repository creation and update handling of concept_model
# =====================================================================

def test_session_repository_create_and_update_concept_model():
    """Verify SessionRepository handles concept_model in create() and update_state() with change flagging."""
    repo = SessionRepository()
    mock_db = MagicMock()
    user_id = uuid4()
    session_id = uuid4()

    # 1. Create session initializes concept_model to None
    obj_in = SessionCreate(topic="Recursion", source_type=SourceType.GENERAL)

    def mock_flush():
        added_session = mock_db.add.call_args_list[0][0][0]
        added_session.id = session_id

    mock_db.flush.side_effect = mock_flush
    repo.create(mock_db, user_id, obj_in)

    added_state = mock_db.add.call_args_list[1][0][0]
    assert isinstance(added_state, SessionState)
    assert added_state.concept_model is None

    # 2. update_state persists concept_model dictionary
    existing_state = SessionState(
        session_id=session_id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.5,
        concept_model=None,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_state

    sample_model = _create_sample_concept_model("Recursion")
    state_in = SessionStateBase(
        current_mode=LearningMode.STUDENT,
        concept_model=sample_model.model_dump(mode="json"),
    )

    with patch("sqlalchemy.orm.attributes.flag_modified") as mock_flag:
        updated = repo.update_state(mock_db, session_id, state_in)
        assert updated.concept_model is not None
        assert updated.concept_model["topic"] == "Recursion"
        assert len(updated.concept_model["concepts"]) == 2
        mock_flag.assert_any_call(existing_state, "concept_model")
        assert mock_db.commit.called


def test_session_repository_update_state_preserves_omitted_concept_model():
    """Verify omitting concept_model preserves existing valid concept_model."""
    repo = SessionRepository()
    mock_db = MagicMock()
    session_id = uuid4()

    existing_model_dict = _create_sample_concept_model("Recursion").model_dump(mode="json")
    existing_state = SessionState(
        session_id=session_id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.5,
        concept_model=existing_model_dict,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_state

    # Update only difficulty and confidence, omit concept_model
    state_in = SessionStateBase(
        difficulty=3,
        confidence=0.8,
    )

    updated = repo.update_state(mock_db, session_id, state_in)
    assert updated.difficulty == 3
    assert updated.confidence == 0.8
    # concept_model is preserved
    assert updated.concept_model == existing_model_dict


# =====================================================================
# 3. ChatService hydration and persistence across simulated turns
# =====================================================================

def test_chatservice_hydrates_and_persists_concept_model():
    """Verify ChatService hydrates concept_model into AIContext and persists it from StateUpdates."""
    chat_service = ChatService()
    mock_db = MagicMock()
    session_id = uuid4()
    user_id = uuid4()

    sample_model = _create_sample_concept_model("Recursion")
    model_json = sample_model.model_dump(mode="json")

    # Mock DB Session with existing concept_model
    db_session = MagicMock()
    db_session.id = session_id
    db_session.user_id = user_id
    db_session.topic = "Recursion"
    db_session.source_type = "GENERAL"

    db_state = MagicMock()
    db_state.session_id = session_id
    db_state.current_mode = "STUDENT"
    db_state.difficulty = 1
    db_state.confidence = 0.5
    db_state.active_concept = "base_case"
    db_state.current_question_id = None
    db_state.interrupted_question_id = None
    db_state.consecutive_strong_answers = 0
    db_state.consecutive_weak_answers = 0
    db_state.unresolved_misconceptions = []
    db_state.mastered_concepts = []
    db_state.teacher_attempt_count = 0
    db_state.teacher_intervention = None
    db_state.concept_mastery = {}
    db_state.misconception_counts = {}
    db_state.recent_strategy_history = []
    db_state.mode_switch_history = []
    db_state.concept_model = model_json

    db_session.state = db_state
    mock_db.query.return_value.filter.return_value.first.return_value = db_session
    chat_service.session_repo.get = MagicMock(return_value=db_session)
    chat_service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
    chat_service.session_repo.update_state = MagicMock()

    # Hydration check via _build_ai_context
    ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)
    assert ai_context.current_state.concept_model is not None
    assert isinstance(ai_context.current_state.concept_model, ConceptModel)
    assert ai_context.current_state.concept_model.topic == "Recursion"
    assert len(ai_context.current_state.concept_model.concepts) == 2
    assert ai_context.current_state.concept_model.concepts[0].id == "base_case"

    # Persistence check via send_message
    ai_result = AIResult(
        response=AIResponse(
            content="Can you explain what a base case does?",
            mode=Mode.STUDENT,
            strategy=Strategy.ASK_FOUNDATION,
            difficulty=1,
            confidence=0.5,
        ),
        evaluation=TurnEvaluation(
            correctness=1.0,
            clarity=1.0,
            completeness=1.0,
            depth=1.0,
            relevance=1.0,
            stuck_probability=0.0,
            recommended_strategy=Strategy.ASK_FOUNDATION,
            recommended_difficulty=1,
        ),
        decision=LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.ASK_FOUNDATION,
            difficulty=1,
            confidence=0.5,
            reason="Explore base case",
            active_concept="base_case",
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        ),
        state_updates=StateUpdates(
            active_concept="base_case",
            concept_model=sample_model,
        ),
    )
    chat_service.ai_engine = MagicMock()
    chat_service.ai_engine.process = MagicMock(return_value=ai_result)

    mock_msg = MagicMock()
    mock_msg.id = uuid4()
    mock_msg.session_id = session_id
    mock_msg.sender = "USER"
    mock_msg.content = "A base case halts the recursion."
    mock_msg.input_type = "TEXT"
    mock_msg.created_at = None

    with patch.object(chat_service.message_repo, "create_message", return_value=mock_msg):
        with patch.object(chat_service.turn_assessment_repo, "create_assessment"):
            msg_in = MessageCreate(content="A base case halts the recursion.")
            chat_service.send_message(mock_db, session_id, msg_in, user_id=user_id)

    # Verify update_state was called with serialized concept_model
    chat_service.session_repo.update_state.assert_called_once()
    called_state_in = chat_service.session_repo.update_state.call_args[0][2]
    assert called_state_in.concept_model is not None
    assert isinstance(called_state_in.concept_model, dict)
    assert called_state_in.concept_model["topic"] == "Recursion"
    assert called_state_in.concept_model["concepts"][0]["id"] == "base_case"


# =====================================================================
# 4. Stable concept IDs when the topic is unchanged
# =====================================================================

def test_concept_model_ids_remain_stable_across_turns():
    """Verify that when concept_model is restored and topic matches, node IDs are not regenerated."""
    sample_model = _create_sample_concept_model("Recursion")
    original_ids = [c.id for c in sample_model.concepts]

    # Create AIContext with pre-populated concept_model
    context = MagicMock()
    context.session_id = str(uuid4())
    context.topic = "Recursion"
    context.current_state.concept_model = sample_model
    context.current_state.learner_model = None
    context.current_state.concept_mastery = {}
    context.current_state.unresolved_misconceptions = []
    context.current_mode = Mode.STUDENT
    context.active_concept = "base_case"
    context.current_question = None
    context.teacher_intervention = None
    context.document_context = None

    state = {
        "context": context,
        "provider": MagicMock(),
        "messages": [],
    }

    result = evaluation_node(state)
    returned_model = result["concept_model"]
    assert returned_model is not None
    assert [c.id for c in returned_model.concepts] == original_ids


# =====================================================================
# 5. Topic changes invalidating or rebuilding the old graph safely
# =====================================================================

def test_topic_change_invalidates_stale_graph_in_context_building():
    """Verify ChatService._build_ai_context discards stored model when topic mismatches."""
    chat_service = ChatService()
    mock_db = MagicMock()
    session_id = uuid4()

    sample_model = _create_sample_concept_model("Recursion")

    # DB session topic is Photosynthesis, but stored model is Recursion
    db_session = MagicMock()
    db_session.topic = "Photosynthesis"
    db_session.state = MagicMock()
    db_session.state.difficulty = 1
    db_session.state.confidence = 0.5
    db_session.state.active_concept = "chloroplast"
    db_session.state.current_question_id = None
    db_session.state.interrupted_question_id = None
    db_session.state.consecutive_strong_answers = 0
    db_session.state.consecutive_weak_answers = 0
    db_session.state.unresolved_misconceptions = []
    db_session.state.teacher_attempt_count = 0
    db_session.state.teacher_intervention = None
    db_session.state.concept_mastery = {}
    db_state = db_session.state
    db_state.misconception_counts = {}
    db_state.recent_strategy_history = []
    db_state.mode_switch_history = []
    db_state.concept_model = sample_model.model_dump(mode="json")

    ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)
    # Stale model must be discarded (None) because "Recursion" != "Photosynthesis"
    assert ai_context.current_state.concept_model is None


def test_student_nodes_rebuilds_graph_when_topic_changes():
    """Verify evaluation_node rebuilds ConceptModel when topic mismatches."""
    old_recursion_model = _create_sample_concept_model("Recursion")

    mock_provider = MagicMock()
    mock_built_model = _create_sample_concept_model("Photosynthesis")

    context = MagicMock()
    context.session_id = str(uuid4())
    context.topic = "Photosynthesis"
    context.current_state.concept_model = old_recursion_model
    context.current_state.learner_model = None
    context.current_state.concept_mastery = {}
    context.current_state.unresolved_misconceptions = []
    context.current_mode = Mode.STUDENT
    context.active_concept = "chloroplast"
    context.current_question = None
    context.teacher_intervention = None
    context.document_context = None

    state = {
        "context": context,
        "provider": mock_provider,
        "messages": [],
    }

    with patch("backend.app.ai.nodes.student_nodes.ConceptModelBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_model.return_value = mock_built_model
        mock_builder_cls.return_value = mock_builder

        result = evaluation_node(state)
        # Verify builder was called with the new topic
        mock_builder.build_model.assert_called_once_with("Photosynthesis")
        assert result["concept_model"].topic == "Photosynthesis"


# =====================================================================
# 6. Missing or invalid stored model data
# =====================================================================

def test_invalid_stored_model_data_handled_gracefully():
    """Verify corrupt or invalid stored concept_model JSON does not crash ChatService."""
    chat_service = ChatService()
    mock_db = MagicMock()
    session_id = uuid4()

    db_session = MagicMock()
    db_session.topic = "Recursion"
    db_session.state = MagicMock()
    db_session.state.difficulty = 1
    db_session.state.confidence = 0.5
    db_session.state.active_concept = "base_case"
    db_session.state.current_question_id = None
    db_session.state.interrupted_question_id = None
    db_session.state.consecutive_strong_answers = 0
    db_session.state.consecutive_weak_answers = 0
    db_session.state.unresolved_misconceptions = []
    db_session.state.teacher_attempt_count = 0
    db_session.state.teacher_intervention = None
    db_session.state.concept_mastery = {}
    db_session.state.misconception_counts = {}
    db_session.state.recent_strategy_history = []
    db_session.state.mode_switch_history = []
    # Completely invalid schema: concepts is string instead of list, etc.
    db_session.state.concept_model = {"topic": 12345, "concepts": "corrupted_string_data"}

    # Should not raise exception; falls back gracefully to None
    ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)
    assert ai_context.current_state.concept_model is None


# =====================================================================
# 7. Failed model build/evaluation preserves previously valid graph
# =====================================================================

def test_failed_model_update_preserves_existing_valid_graph():
    """Verify that an empty or None concept_model in StateUpdates does not erase existing valid model."""
    chat_service = ChatService()
    mock_db = MagicMock()
    session_id = uuid4()
    user_id = uuid4()

    valid_existing_dict = _create_sample_concept_model("Recursion").model_dump(mode="json")

    db_session = MagicMock()
    db_session.id = session_id
    db_session.user_id = user_id
    db_session.topic = "Recursion"
    db_session.source_type = "GENERAL"

    db_state = MagicMock()
    db_state.concept_model = valid_existing_dict
    db_state.current_mode = "STUDENT"
    db_state.difficulty = 1
    db_state.confidence = 0.5
    db_state.active_concept = "base_case"
    db_state.current_question_id = None
    db_state.interrupted_question_id = None
    db_state.consecutive_strong_answers = 0
    db_state.consecutive_weak_answers = 0
    db_state.unresolved_misconceptions = []
    db_state.mastered_concepts = []
    db_state.teacher_attempt_count = 0
    db_state.teacher_intervention = None
    db_state.concept_mastery = {}
    db_state.misconception_counts = {}
    db_state.recent_strategy_history = []
    db_state.mode_switch_history = []

    db_session.state = db_state
    chat_service.session_repo.get = MagicMock(return_value=db_session)
    chat_service.session_repo.get_by_id_and_user = MagicMock(return_value=db_session)
    chat_service.session_repo.update_state = MagicMock()

    # Engine produces StateUpdates with concept_model=None (simulating failure or omission)
    ai_result = AIResult(
        response=AIResponse(
            content="What is a base case?",
            mode=Mode.STUDENT,
            strategy=Strategy.ASK_FOUNDATION,
            difficulty=1,
            confidence=0.5,
        ),
        evaluation=TurnEvaluation(
            correctness=1.0,
            clarity=1.0,
            completeness=1.0,
            depth=1.0,
            relevance=1.0,
            stuck_probability=0.0,
            recommended_strategy=Strategy.ASK_FOUNDATION,
            recommended_difficulty=1,
        ),
        decision=LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.ASK_FOUNDATION,
            difficulty=1,
            confidence=0.5,
            reason="Explore base case",
            active_concept="base_case",
            should_offer_termination=False,
            should_restore_interrupted_question=False,
        ),
        state_updates=StateUpdates(
            active_concept="base_case",
            concept_model=None,  # Omitted / failed
        ),
    )
    chat_service.ai_engine = MagicMock()
    chat_service.ai_engine.process = MagicMock(return_value=ai_result)

    mock_msg = MagicMock()
    mock_msg.id = uuid4()
    mock_msg.session_id = session_id
    mock_msg.sender = "USER"
    mock_msg.content = "A base case terminates recursion."
    mock_msg.input_type = "TEXT"
    mock_msg.created_at = None

    with patch.object(chat_service.message_repo, "create_message", return_value=mock_msg):
        with patch.object(chat_service.turn_assessment_repo, "create_assessment"):
            msg_in = MessageCreate(content="A base case terminates recursion.")
            chat_service.send_message(mock_db, session_id, msg_in, user_id=user_id)

    # Verify update_state preserved the existing valid concept_model
    called_state_in = chat_service.session_repo.update_state.call_args[0][2]
    assert called_state_in.concept_model == valid_existing_dict


# =====================================================================
# 8. Existing sessions with null concept_model remain compatible
# =====================================================================

def test_legacy_session_with_null_concept_model_is_backward_compatible():
    """Verify legacy sessions where concept_model is None hydrate cleanly and allow on-demand building."""
    chat_service = ChatService()
    mock_db = MagicMock()
    session_id = uuid4()

    db_session = MagicMock()
    db_session.topic = "Recursion"
    db_session.state = MagicMock()
    db_session.state.difficulty = 1
    db_session.state.confidence = 0.5
    db_session.state.active_concept = "base_case"
    db_session.state.current_question_id = None
    db_session.state.interrupted_question_id = None
    db_session.state.consecutive_strong_answers = 0
    db_state = db_session.state
    db_state.consecutive_weak_answers = 0
    db_state.unresolved_misconceptions = []
    db_state.teacher_attempt_count = 0
    db_state.teacher_intervention = None
    db_state.concept_mastery = {}
    db_state.misconception_counts = {}
    db_state.recent_strategy_history = []
    db_state.mode_switch_history = []
    db_state.concept_model = None  # Legacy session before Step 3

    ai_context = chat_service._build_ai_context(mock_db, session_id, db_session)
    assert ai_context.current_state.concept_model is None

    # Verify student_nodes builds a fresh model without failing
    state = {
        "context": ai_context,
        "provider": MagicMock(),
        "messages": [],
    }
    with patch("backend.app.ai.nodes.student_nodes.ConceptModelBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder.build_model.return_value = _create_sample_concept_model("Recursion")
        mock_builder_cls.return_value = mock_builder

        result = evaluation_node(state)
        assert result["concept_model"] is not None
        assert result["concept_model"].topic == "Recursion"
