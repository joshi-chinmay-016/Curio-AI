"""
Unit tests for TurnInterpreter (Phase B).
Verifies:
- Answer attempts
- Clarification requests
- Help requests / stuck signals
- Acknowledgements
- Conceptual questions
- Ready for verification
- Malformed/fallback handling
"""
import pytest
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    CurrentQuestion,
    Mode,
    TurnIntent,
    TurnInterpretation,
)
from backend.app.ai.turn_interpreter import TurnInterpreter


class FaultyProvider(MockLLMProvider):
    """Provider that raises an exception to test defensive fallbacks."""
    def generate_structured(self, prompt, response_model):
        raise RuntimeError("Simulated LLM network timeout or malformed JSON")


def test_turn_interpreter_answer_attempt():
    provider = MockLLMProvider()
    interpreter = TurnInterpreter(provider)
    interp = interpreter.interpret(
        user_message="Because sorting lets us eliminate half the array at each step.",
        mode=Mode.STUDENT,
    )
    assert interp.intent == TurnIntent.ANSWER_ATTEMPT
    assert interp.is_answer_attempt is True
    assert interp.is_help_request is False


def test_turn_interpreter_clarification_request():
    provider = MockLLMProvider()
    interpreter = TurnInterpreter(provider)
    interp = interpreter.interpret(
        user_message="what do you mean by underlying rationale?",
        mode=Mode.STUDENT,
    )
    assert interp.intent == TurnIntent.CLARIFICATION_REQUEST
    assert interp.is_question is True
    assert interp.is_answer_attempt is False


def test_turn_interpreter_help_request():
    provider = MockLLMProvider()
    interpreter = TurnInterpreter(provider)
    interp = interpreter.interpret(
        user_message="I still don't understand. Can you teach me?",
        mode=Mode.STUDENT,
    )
    assert interp.intent == TurnIntent.HELP_REQUEST
    assert interp.is_help_request is True
    assert interp.is_answer_attempt is False


def test_turn_interpreter_acknowledgement_student_mode():
    provider = MockLLMProvider()
    interpreter = TurnInterpreter(provider)
    interp = interpreter.interpret(
        user_message="ok got it",
        mode=Mode.STUDENT,
    )
    assert interp.intent == TurnIntent.ACKNOWLEDGEMENT
    assert interp.is_answer_attempt is False


def test_turn_interpreter_ready_for_verification_teacher_mode():
    provider = MockLLMProvider()
    interpreter = TurnInterpreter(provider)
    interp = interpreter.interpret(
        user_message="I understand now, I'm good now",
        mode=Mode.TEACHER,
    )
    assert interp.intent == TurnIntent.READY_FOR_VERIFICATION
    assert interp.is_answer_attempt is False


def test_turn_interpreter_conceptual_question():
    provider = MockLLMProvider()
    interpreter = TurnInterpreter(provider)
    interp = interpreter.interpret(
        user_message="how does virtual memory translate pages to physical frames?",
        mode=Mode.STUDENT,
    )
    assert interp.intent == TurnIntent.CONCEPTUAL_QUESTION
    assert interp.is_question is True


def test_turn_interpreter_defensive_fallback_on_llm_failure():
    faulty_provider = FaultyProvider()
    interpreter = TurnInterpreter(faulty_provider)

    # Help request fallback
    res1 = interpreter.interpret("I'm totally lost and stuck", mode=Mode.STUDENT)
    assert res1.intent == TurnIntent.HELP_REQUEST
    assert res1.is_help_request is True

    # Clarification fallback
    res2 = interpreter.interpret("what do you mean by that?", mode=Mode.STUDENT)
    assert res2.intent == TurnIntent.CLARIFICATION_REQUEST
    assert res2.is_question is True

    # Teacher acknowledgement fallback
    res3 = interpreter.interpret("ok got it", mode=Mode.TEACHER)
    assert res3.intent == TurnIntent.READY_FOR_VERIFICATION

    # Substantive answer fallback
    res4 = interpreter.interpret(
        "The operating system maintains page tables indexed by process id",
        mode=Mode.STUDENT,
    )
    assert res4.intent == TurnIntent.ANSWER_ATTEMPT
    assert res4.is_answer_attempt is True
