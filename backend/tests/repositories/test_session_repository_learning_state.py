import pytest
from unittest.mock import MagicMock
from uuid import uuid4
import backend.app.db.base  # Ensure all SQLAlchemy models are registered
from backend.app.models.session import Session, SessionState
from backend.app.repositories.session_repository import SessionRepository
from backend.app.schemas.session import SessionCreate, SessionStateBase
from backend.app.schemas.common import LearningMode, SourceType


def test_session_repository_create_initializes_learning_state():
    """Verify SessionRepository.create() explicitly initializes all learning-state fields."""
    repo = SessionRepository()
    mock_db = MagicMock()
    user_id = uuid4()
    session_id = uuid4()

    obj_in = SessionCreate(topic="Recursion", source_type=SourceType.GENERAL)

    def mock_flush():
        added_session = mock_db.add.call_args_list[0][0][0]
        added_session.id = session_id

    mock_db.flush.side_effect = mock_flush

    result = repo.create(mock_db, user_id, obj_in)
    assert mock_db.add.call_count >= 2

    # Verify SessionState attributes
    added_state = mock_db.add.call_args_list[1][0][0]
    assert isinstance(added_state, SessionState)
    assert added_state.session_id == session_id
    assert added_state.concept_mastery == {}
    assert added_state.misconception_counts == {}
    assert added_state.recent_strategy_history == []
    assert added_state.mode_switch_history == []
    assert added_state.teacher_attempt_count == 0
    assert added_state.teacher_intervention is None


def test_session_repository_update_state_persists_explicit_learning_state():
    """Verify update_state persists concept_mastery, misconception_counts, and histories when explicitly supplied."""
    repo = SessionRepository()
    mock_db = MagicMock()
    session_id = uuid4()

    existing_state = SessionState(
        session_id=session_id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.2,
        active_concept="Recursion Base Case",
        concept_mastery={},
        misconception_counts={},
        recent_strategy_history=[],
        mode_switch_history=[],
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_state

    state_in = SessionStateBase(
        current_mode=LearningMode.STUDENT,
        difficulty=2,
        confidence=0.7,
        active_concept="Recursive Step",
        concept_mastery={"recursion_intro": 0.9, "base_case": 0.6},
        misconception_counts={"missing_base_case": 2},
        recent_strategy_history=["SOCRATIC_QUESTION", "PROVIDE_HINT"],
        mode_switch_history=[{"from": "STUDENT", "to": "TEACHER", "reason": "misconception"}],
    )

    updated = repo.update_state(mock_db, session_id, state_in)

    assert updated.difficulty == 2
    assert updated.confidence == 0.7
    assert updated.active_concept == "Recursive Step"
    assert updated.concept_mastery == {"recursion_intro": 0.9, "base_case": 0.6}
    assert updated.misconception_counts == {"missing_base_case": 2}
    assert updated.recent_strategy_history == ["SOCRATIC_QUESTION", "PROVIDE_HINT"]
    assert updated.mode_switch_history == [{"from": "STUDENT", "to": "TEACHER", "reason": "misconception"}]
    assert mock_db.commit.called


def test_session_repository_update_state_preserves_omitted_learning_state():
    """Verify update_state does not overwrite existing non-empty learning state with schema defaults when omitted."""
    repo = SessionRepository()
    mock_db = MagicMock()
    session_id = uuid4()

    existing_state = SessionState(
        session_id=session_id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.5,
        active_concept="Binary Search",
        concept_mastery={"binary_search": 0.85},
        misconception_counts={"off_by_one": 1},
        recent_strategy_history=["ASK_FOUNDATION"],
        mode_switch_history=[{"from": "STUDENT", "to": "STUDENT"}],
        unresolved_misconceptions=["infinite_loop"],
        mastered_concepts=["array_indexing"],
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_state

    # Construct state_in omitting concept_mastery, misconception_counts, histories, etc.
    state_in = SessionStateBase(
        current_mode=LearningMode.STUDENT,
        difficulty=3,
        confidence=0.9,
    )

    updated = repo.update_state(mock_db, session_id, state_in)

    # Updated fields
    assert updated.difficulty == 3
    assert updated.confidence == 0.9

    # Preserved fields (must not be wiped to empty defaults!)
    assert updated.concept_mastery == {"binary_search": 0.85}
    assert updated.misconception_counts == {"off_by_one": 1}
    assert updated.recent_strategy_history == ["ASK_FOUNDATION"]
    assert updated.mode_switch_history == [{"from": "STUDENT", "to": "STUDENT"}]
    assert updated.unresolved_misconceptions == ["infinite_loop"]
    assert updated.mastered_concepts == ["array_indexing"]


def test_session_repository_update_state_allows_explicit_empty_resets():
    """Verify update_state honors an intentional explicit reset to empty dicts/lists."""
    repo = SessionRepository()
    mock_db = MagicMock()
    session_id = uuid4()

    existing_state = SessionState(
        session_id=session_id,
        current_mode="STUDENT",
        difficulty=2,
        concept_mastery={"binary_search": 0.85},
        misconception_counts={"off_by_one": 1},
        recent_strategy_history=["ASK_FOUNDATION"],
        mode_switch_history=[{"from": "STUDENT", "to": "STUDENT"}],
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_state

    # Explicitly pass empty collections in the constructor
    state_in = SessionStateBase(
        current_mode=LearningMode.STUDENT,
        concept_mastery={},
        misconception_counts={},
        recent_strategy_history=[],
        mode_switch_history=[],
    )

    updated = repo.update_state(mock_db, session_id, state_in)

    # Since they were explicitly provided in kwargs, they should be reset
    assert updated.concept_mastery == {}
    assert updated.misconception_counts == {}
    assert updated.recent_strategy_history == []
    assert updated.mode_switch_history == []


def test_session_repository_update_state_backward_compatibility_with_mocks():
    """Verify update_state works with mock or non-Pydantic state_in objects lacking model_fields_set."""
    repo = SessionRepository()
    mock_db = MagicMock()
    session_id = uuid4()

    existing_state = SessionState(
        session_id=session_id,
        current_mode="STUDENT",
        difficulty=1,
        confidence=0.0,
        active_concept="Limits",
        teacher_attempt_count=0,
        teacher_intervention=None,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_state

    mock_state_in = MagicMock()
    mock_state_in.current_mode = "TEACHER"
    mock_state_in.difficulty = 2
    mock_state_in.confidence = 0.5
    mock_state_in.active_concept = "Derivative"
    mock_state_in.current_question_id = None
    mock_state_in.interrupted_question_id = None
    mock_state_in.consecutive_strong_answers = 1
    mock_state_in.consecutive_weak_answers = 0
    mock_state_in.unresolved_misconceptions = []
    mock_state_in.mastered_concepts = ["Limits"]
    mock_state_in.concept_mastery = {"Limits": 1.0}
    mock_state_in.misconception_counts = {}
    mock_state_in.recent_strategy_history = ["DIRECT_INSTRUCTION"]
    mock_state_in.mode_switch_history = []
    mock_state_in.teacher_attempt_count = 1
    mock_state_in.teacher_intervention = {"active": True}
    # Ensure model_fields_set is not a set
    mock_state_in.model_fields_set = None

    updated = repo.update_state(mock_db, session_id, mock_state_in)

    assert updated.current_mode == "TEACHER"
    assert updated.difficulty == 2
    assert updated.concept_mastery == {"Limits": 1.0}
    assert updated.recent_strategy_history == ["DIRECT_INSTRUCTION"]
    assert updated.mastered_concepts == ["Limits"]
