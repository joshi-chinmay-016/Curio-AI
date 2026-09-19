import json
import pytest
from pydantic import ValidationError

from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    Difficulty,
    InputType,
    LearningContext,
    LearningDecision,
    Mode,
    Role,
    SessionInfo,
    SessionState,
    SourceMode,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    TurnEvaluation,
)


def test_valid_session_state():
    """Test creating a valid SessionState instance."""
    state = SessionState(
        session_id="session_123",
        current_mode=Mode.STUDENT,
        current_difficulty=3,
        understanding_confidence=0.65,
        active_concept="recursion_definition",
        current_question=CurrentQuestion(
            id="q_1",
            content="What is recursion?",
            concept="recursion_definition",
            difficulty=3,
        ),
        consecutive_failures=0,
        consecutive_successes=2,
        teacher_attempt_count=0,
        recent_strategy_history=[Strategy.PROBE_WHY, Strategy.PROBE_HOW],
        misconception_counts={"loop_confusion": 1},
        concept_mastery={"recursion_definition": 0.85, "base_case": 0.52},
        unresolved_misconceptions=[],
        teacher_intervention=None,
    )
    assert state.session_id == "session_123"
    assert state.current_difficulty == 3
    assert state.understanding_confidence == 0.65
    assert state.concept_mastery["recursion_definition"] == 0.85


def test_invalid_confidence():
    """Confidence must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        SessionState(session_id="s1", understanding_confidence=1.5)

    with pytest.raises(ValidationError):
        SessionState(session_id="s1", understanding_confidence=-0.1)


def test_invalid_difficulty():
    """Difficulty must be between 1 and 5."""
    with pytest.raises(ValidationError):
        SessionState(session_id="s1", current_difficulty=0)

    with pytest.raises(ValidationError):
        SessionState(session_id="s1", current_difficulty=6)

    with pytest.raises(ValidationError):
        CurrentQuestion(id="q1", content="test", concept="test", difficulty=6)


def test_valid_turn_evaluation():
    """TurnEvaluation with valid ranges should instantiate cleanly."""
    evaluation = TurnEvaluation(
        correctness=0.85,
        clarity=0.78,
        completeness=0.72,
        depth=0.65,
        relevance=0.95,
        stuck_probability=0.15,
        misconceptions=[],
        missing_concepts=["Stack memory"],
        undefined_terms=[],
        mastered_concepts=["Base case"],
        knowledge_gap=None,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=4,
    )
    assert evaluation.correctness == 0.85
    assert evaluation.recommended_difficulty == 4


def test_invalid_evaluation_score():
    """Turn evaluation metrics must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        TurnEvaluation(
            correctness=1.2,
            clarity=0.8,
            completeness=0.5,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.0,
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=3,
        )

    with pytest.raises(ValidationError):
        TurnEvaluation(
            correctness=0.5,
            clarity=-0.1,
            completeness=0.5,
            depth=0.5,
            relevance=1.0,
            stuck_probability=0.0,
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=3,
        )


def test_valid_learning_decision():
    """Test creating a valid LearningDecision."""
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=3,
        confidence=0.68,
        reason="The learner understands definition but needs mechanism check.",
        active_concept="base_case",
        should_offer_termination=False,
        should_restore_interrupted_question=False,
    )
    assert decision.next_mode == Mode.STUDENT
    assert decision.confidence == 0.68
    assert decision.strategy == Strategy.PROBE_WHY


def test_valid_ai_result():
    """Test full AIResult creation with all nested components."""
    eval_model = TurnEvaluation(
        correctness=0.9,
        clarity=0.9,
        completeness=0.9,
        depth=0.8,
        relevance=1.0,
        stuck_probability=0.0,
        mastered_concepts=["Recursion"],
        recommended_strategy=Strategy.INCREASE_DIFFICULTY,
        recommended_difficulty=3,
    )
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.INCREASE_DIFFICULTY,
        difficulty=3,
        confidence=0.75,
        reason="Mastered concept.",
        active_concept="Recursion",
    )
    response = AIResponse(
        content="Excellent. Let's move on to recursion tree diagrams.",
        mode=Mode.STUDENT,
        strategy=Strategy.INCREASE_DIFFICULTY,
        difficulty=3,
        confidence=0.75,
    )
    updates = StateUpdates(
        difficulty=3,
        confidence=0.75,
        mastered_concepts=["Recursion"],
    )

    result = AIResult(
        evaluation=eval_model,
        decision=decision,
        response=response,
        state_updates=updates,
    )
    assert result.decision.difficulty == 3
    assert result.response.content.startswith("Excellent")


def test_invalid_empty_ai_response():
    """AIResponse content must not be empty."""
    with pytest.raises(ValidationError):
        AIResponse(
            content="",
            mode=Mode.STUDENT,
            strategy=Strategy.PROBE_WHY,
            difficulty=2,
            confidence=0.5,
        )


def test_concept_mastery_validation():
    """concept_mastery dict values must strictly be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        SessionState(
            session_id="s1",
            concept_mastery={"base_case": 1.25},
        )

    with pytest.raises(ValidationError):
        SessionState(
            session_id="s1",
            concept_mastery={"base_case": -0.1},
        )


def test_ai_context_serialization():
    """AIContext must support serialization and deserialization cleanly."""
    context = AIContext(
        session=SessionInfo(
            session_id="sess_001",
            topic="Binary Search",
            source_mode=SourceMode.GENERAL,
        ),
        current_state=SessionState(
            session_id="sess_001",
            current_mode=Mode.STUDENT,
            current_difficulty=2,
            understanding_confidence=0.45,
            active_concept="midpoint_calc",
        ),
        conversation=ConversationContext(
            recent_messages=[
                ChatMessage(role=Role.ASSISTANT, content="How do you compute the middle index?"),
                ChatMessage(role=Role.USER, content="left + (right - left) // 2"),
            ],
            message_count=2,
        ),
        learning_context=LearningContext(
            mastered_concepts=["Search space reduction"],
        ),
    )

    dumped_dict = context.model_dump()
    assert dumped_dict["session"]["topic"] == "Binary Search"
    assert dumped_dict["current_state"]["current_difficulty"] == 2

    dumped_json = context.model_dump_json()
    loaded_data = json.loads(dumped_json)
    assert loaded_data["session"]["session_id"] == "sess_001"

    # Roundtrip validation
    recreated = AIContext.model_validate_json(dumped_json)
    assert recreated.session.topic == "Binary Search"
    assert recreated.conversation.recent_messages[1].content == "left + (right - left) // 2"


def test_ai_result_serialization():
    """AIResult must serialize and deserialize without loss."""
    result = AIResult(
        evaluation=TurnEvaluation(
            correctness=0.85,
            clarity=0.78,
            completeness=0.72,
            depth=0.65,
            relevance=0.95,
            stuck_probability=0.15,
            missing_concepts=["Stack memory"],
            mastered_concepts=["Base case"],
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=4,
        ),
        decision=LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.PROBE_WHY,
            difficulty=4,
            confidence=0.68,
            reason="Mechanisms need further explanation.",
            active_concept="base_case",
        ),
        response=AIResponse(
            content="What would happen if the recursive function did not contain a base case?",
            mode=Mode.STUDENT,
            strategy=Strategy.PROBE_WHY,
            difficulty=4,
            confidence=0.68,
        ),
        state_updates=StateUpdates(
            active_concept="base_case",
            difficulty=4,
            confidence=0.68,
        ),
    )

    json_str = result.model_dump_json()
    parsed = AIResult.model_validate_json(json_str)
    assert parsed.evaluation.correctness == 0.85
    assert parsed.decision.difficulty == 4
    assert parsed.response.content == "What would happen if the recursive function did not contain a base case?"
