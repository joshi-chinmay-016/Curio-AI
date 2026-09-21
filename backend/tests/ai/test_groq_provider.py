"""
Unit and integration tests for GroqLLMProvider in Curio AI (Phase 1, Task 4C).
Verifies:
1. Missing API key fallback to MockLLMProvider.
2. Client initialization with mocked Groq SDK.
3. Model, timeout, and retry configuration propagation.
4. Runtime exception fallback to MockLLMProvider.
5. Malformed JSON and schema validation fallback to MockLLMProvider.
6. AIResult contract invariance: AIContext -> CurioEngine.process() -> AIResult.
"""
import json
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from backend.app.ai.engine import CurioEngine
from backend.app.ai.providers.groq_provider import GroqLLMProvider
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    AIResult,
    ChatMessage,
    ConversationContext,
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
    TurnEvaluation,
)
from backend.app.core.config import settings


def _create_dummy_context(topic: str = "Photosynthesis") -> AIContext:
    """Helper to create a canonical AIContext."""
    session = SessionInfo(
        session_id="test_session_123",
        topic=topic,
        source_mode=SourceMode.GENERAL,
    )
    current_state = SessionState(
        session_id="test_session_123",
        current_mode=Mode.STUDENT,
        current_difficulty=2,
        understanding_confidence=0.5,
        active_concept="Light Reactions",
        consecutive_failures=0,
        consecutive_successes=1,
    )
    conversation = ConversationContext(
        recent_messages=[
            ChatMessage(
                role=Role.USER,
                content="Photosynthesis converts solar energy into chemical bonds.",
                input_type=InputType.TEXT,
            )
        ],
        message_count=1,
    )
    learning_context = LearningContext(
        mastered_concepts=["Chlorophyll"],
        unresolved_misconceptions=[],
        recent_evaluations=[],
    )
    return AIContext(
        session=session,
        current_state=current_state,
        conversation=conversation,
        learning_context=learning_context,
    )


# =====================================================================
# 1. Missing API Key Fallback
# =====================================================================

def test_groq_provider_missing_key_operates_in_mock_mode():
    """Verify that GroqLLMProvider with no API key operates safely via MockLLMProvider."""
    with patch.dict("os.environ", {}, clear=True):
        with patch.object(settings, "GROQ_API_KEY", ""):
            provider = GroqLLMProvider(api_key=None)
            assert provider.client is None
            assert provider.api_key == ""

            # Structured generation must succeed using mock fallback
            eval_res = provider.generate_structured("Evaluate user response", TurnEvaluation)
            assert isinstance(eval_res, TurnEvaluation)
            assert 0.0 <= eval_res.correctness <= 1.0

            # Text generation must succeed using mock fallback
            text_res = provider.generate_text("Ask foundational question")
            assert isinstance(text_res, str)
            assert len(text_res) > 0


# =====================================================================
# 2. Client Initialization with Mocked Groq Client
# =====================================================================

@patch("groq.Groq")
def test_groq_provider_client_initialization(mock_groq_cls):
    """Verify that GroqLLMProvider initializes Groq SDK with provided key and default settings."""
    mock_instance = MagicMock()
    mock_groq_cls.return_value = mock_instance

    provider = GroqLLMProvider(api_key="gsk_mock_secret_key_12345")
    assert provider.client == mock_instance
    assert provider.model == "llama-3.3-70b-versatile"
    assert provider.timeout == 30.0
    assert provider.max_retries == 2

    mock_groq_cls.assert_called_once_with(
        api_key="gsk_mock_secret_key_12345",
        timeout=30.0,
        max_retries=2,
    )


# =====================================================================
# 3. Model, Timeout, and Retry Configuration
# =====================================================================

@patch("groq.Groq")
def test_groq_provider_custom_configuration(mock_groq_cls):
    """Verify custom model, timeout, and retry parameters are accepted and passed to Groq API calls."""
    mock_instance = MagicMock()
    mock_groq_cls.return_value = mock_instance

    provider = GroqLLMProvider(
        api_key="gsk_test_custom_config",
        model="llama-3.1-8b-instant",
        timeout=15.0,
        max_retries=4,
    )

    assert provider.model == "llama-3.1-8b-instant"
    assert provider.timeout == 15.0
    assert provider.max_retries == 4

    mock_groq_cls.assert_called_once_with(
        api_key="gsk_test_custom_config",
        timeout=15.0,
        max_retries=4,
    )

    # Mock response for completions.create
    mock_choice = MagicMock()
    mock_choice.message.content = "What is the primary function of chlorophyll?"
    mock_instance.chat.completions.create.return_value.choices = [mock_choice]

    res_text = provider.generate_text("Prompt about light harvesting")
    assert res_text == "What is the primary function of chlorophyll?"

    # Verify create was invoked with custom model and timeout
    mock_instance.chat.completions.create.assert_called_once()
    call_kwargs = mock_instance.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "llama-3.1-8b-instant"
    assert call_kwargs["timeout"] == 15.0


# =====================================================================
# 4. Runtime Exception Fallback
# =====================================================================

@patch("groq.Groq")
def test_groq_provider_runtime_exception_falls_back_to_mock(mock_groq_cls):
    """Verify that network, API, or rate limit exceptions gracefully fall back to MockLLMProvider."""
    mock_instance = MagicMock()
    mock_groq_cls.return_value = mock_instance

    provider = GroqLLMProvider(api_key="gsk_test_runtime_err")

    # Simulate Groq API exception containing simulated key in error string
    mock_instance.chat.completions.create.side_effect = RuntimeError(
        "Connection refused by peer using token gsk_test_runtime_err"
    )

    # 1. Structured generation fallback
    eval_res = provider.generate_structured("Evaluate turn", TurnEvaluation)
    assert isinstance(eval_res, TurnEvaluation)
    assert 0.0 <= eval_res.correctness <= 1.0

    # 2. Text generation fallback
    text_res = provider.generate_text("Ask question")
    assert isinstance(text_res, str)
    assert len(text_res) > 0

    # 3. Verify sanitization redacts key
    sanitized = provider._sanitize_error(
        RuntimeError("Unauthorized with key gsk_test_runtime_err in header")
    )
    assert "gsk_test_runtime_err" not in sanitized
    assert "[REDACTED]" in sanitized


# =====================================================================
# 5. Malformed JSON and Schema Fallback
# =====================================================================

@patch("groq.Groq")
def test_groq_provider_malformed_json_fallback(mock_groq_cls):
    """Verify that non-JSON outputs or schema mismatches from LLM fall back safely to MockLLMProvider."""
    mock_instance = MagicMock()
    mock_groq_cls.return_value = mock_instance

    provider = GroqLLMProvider(api_key="gsk_test_malformed")

    # Case A: Output is not valid JSON
    mock_choice_bad = MagicMock()
    mock_choice_bad.message.content = "Here is my evaluation: correctness is high."
    mock_instance.chat.completions.create.return_value.choices = [mock_choice_bad]

    eval_a = provider.generate_structured("Prompt A", TurnEvaluation)
    assert isinstance(eval_a, TurnEvaluation)

    # Case B: Output is JSON but missing required fields
    mock_choice_missing = MagicMock()
    mock_choice_missing.message.content = json.dumps({"unrelated_field": "test"})
    mock_instance.chat.completions.create.return_value.choices = [mock_choice_missing]

    eval_b = provider.generate_structured("Prompt B", TurnEvaluation)
    assert isinstance(eval_b, TurnEvaluation)

    # Case C: Valid JSON wrapped in markdown code fence is cleaned properly
    valid_payload = {
        "correctness": 0.95,
        "clarity": 0.9,
        "completeness": 0.85,
        "depth": 0.8,
        "relevance": 1.0,
        "stuck_probability": 0.0,
        "misconceptions": [],
        "missing_concepts": [],
        "undefined_terms": [],
        "mastered_concepts": ["Chlorophyll a"],
        "knowledge_gap": None,
        "recommended_strategy": "INCREASE_DIFFICULTY",
        "recommended_difficulty": 3,
    }
    mock_choice_fenced = MagicMock()
    mock_choice_fenced.message.content = f"```json\n{json.dumps(valid_payload)}\n```"
    mock_instance.chat.completions.create.return_value.choices = [mock_choice_fenced]

    eval_c = provider.generate_structured("Prompt C", TurnEvaluation)
    assert isinstance(eval_c, TurnEvaluation)
    assert eval_c.correctness == 0.95
    assert eval_c.recommended_strategy == Strategy.INCREASE_DIFFICULTY


# =====================================================================
# 6. AIResult Contract Invariance
# =====================================================================

@patch("groq.Groq")
def test_curio_engine_contract_invariance_with_groq_provider(mock_groq_cls):
    """Verify that CurioEngine preserves the exact AIContext -> AIResult contract when using GroqLLMProvider."""
    mock_instance = MagicMock()
    mock_groq_cls.return_value = mock_instance

    # Mock structured evaluation response
    valid_eval = {
        "correctness": 0.88,
        "clarity": 0.85,
        "completeness": 0.8,
        "depth": 0.75,
        "relevance": 1.0,
        "stuck_probability": 0.05,
        "misconceptions": [],
        "missing_concepts": [],
        "undefined_terms": [],
        "mastered_concepts": ["Photons"],
        "knowledge_gap": None,
        "recommended_strategy": "INCREASE_DIFFICULTY",
        "recommended_difficulty": 3,
    }
    mock_choice_eval = MagicMock()
    mock_choice_eval.message.content = json.dumps(valid_eval)

    mock_choice_text = MagicMock()
    mock_choice_text.message.content = "How do photons excite electrons in chlorophyll?"

    # First call is generate_structured (evaluation), second call is generate_text (response)
    mock_instance.chat.completions.create.side_effect = [
        MagicMock(choices=[mock_choice_eval]),
        MagicMock(choices=[mock_choice_text]),
    ]

    provider = GroqLLMProvider(api_key="gsk_contract_test")
    engine = CurioEngine(provider=provider)
    context = _create_dummy_context()

    result: AIResult = engine.process(context)

    # Assert invariant typing and structure
    assert isinstance(result, AIResult)
    assert isinstance(result.evaluation, TurnEvaluation)
    assert isinstance(result.decision, LearningDecision)
    assert isinstance(result.response, AIResponse)
    assert isinstance(result.state_updates, StateUpdates)

    assert result.evaluation.correctness == 0.88
    assert result.decision.next_mode in (Mode.STUDENT, Mode.TEACHER, Mode.EVALUATOR)
    assert len(result.response.content) > 0
    assert result.state_updates.difficulty is not None
