"""
Focused regression tests for Phase 3 Step 3.5:
Final Student Mode One-Question Enforcement.

Validates all 12 required enforcement scenarios:
1. Valid single-question response remains intact.
2. Obvious two-question candidate is rejected or safely repaired.
3. Compound question with one question mark is handled conservatively.
4. Quoted question mark in technical text is handled without false rejection.
5. Off-topic/redirection prefix combined with the question is verified.
6. Clarification prefix combined with the question is verified.
7. Restored interrupted question passes through final enforcement.
8. Invalid restored question is repaired or replaced safely.
9. Generator fallback still returns a valid single-question response.
10. Recovery is bounded, deterministic, and cannot loop indefinitely.
11. Answer leakage is rejected and not introduced by recovery.
12. Teacher Mode and Evaluator Mode behavior remains unchanged.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    LearningAssessment,
    RelevanceLevel,
)
from backend.app.ai.nodes.student_nodes import response_node
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.question_generator import QuestionGenerator
from backend.app.ai.question_validator import (
    QuestionValidator,
    enforce_single_student_question,
    has_compound_interrogatives,
    mask_technical_question_marks,
    validate_final_student_response,
)
from backend.app.ai.schemas import (
    AIContext,
    AIResponse,
    CandidateList,
    ChatMessage,
    ConversationContext,
    CurrentQuestion,
    LearningDecision,
    LearningObjective,
    Mode,
    ObjectiveType,
    QuestionCandidate,
    QuestionSpecification,
    Role,
    SessionInfo,
    SessionState,
    Strategy,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)


def _make_sample_spec(concept="binary_search", diff=2, obj_type=ObjectiveType.UNDERSTAND_MECHANISM) -> QuestionSpecification:
    obj = LearningObjective(
        objective_type=obj_type,
        target_concept=concept,
        difficulty=diff,
        reason="Testing single question enforcement",
        evidence_expected="Learner explains core mechanism",
    )
    return QuestionSpecification(
        target_concept=concept,
        learning_objective=obj,
        difficulty=diff,
        reason="Testing single question enforcement",
        evidence_expected="Learner explains core mechanism",
        generation_constraints=["Ask exactly ONE question", "Do not lecture"],
    )


def _make_context(topic: str = "Algorithms", active_concept: str = "binary_search") -> AIContext:
    session_info = SessionInfo(session_id="test-session-3-5", topic=topic)
    state = SessionState(
        session_id="test-session-3-5",
        current_mode=Mode.STUDENT,
        current_difficulty=2,
        understanding_confidence=0.6,
        active_concept=active_concept,
        current_question=CurrentQuestion(
            id="q_prev",
            content="How does binary search find a target element?",
            concept=active_concept,
            difficulty=2,
        ),
    )
    conv = ConversationContext(
        recent_messages=[
            ChatMessage(role=Role.ASSISTANT, content="How does binary search find a target element?"),
            ChatMessage(role=Role.USER, content="It checks each element sequentially."),
        ],
        message_count=2,
    )
    return AIContext(session=session_info, current_state=state, conversation=conv)


# =====================================================================
# Scenario 1: Valid single-question response remains intact
# =====================================================================

def test_valid_single_question_remains_intact():
    q = "How does binary search divide the search space on each comparison?"
    is_valid, reasons = validate_final_student_response(q)
    assert is_valid is True
    assert reasons == []

    spec = _make_sample_spec()
    enforced = enforce_single_student_question(content=q, spec=spec)
    assert enforced == q


# =====================================================================
# Scenario 2: Obvious two-question candidate is rejected or safely repaired
# =====================================================================

def test_obvious_two_question_candidate_rejected_and_replaced():
    double_q = "What is paging? How does virtual memory work?"
    is_valid, reasons = validate_final_student_response(double_q)
    assert is_valid is False
    assert any("one-question rule" in r for r in reasons)

    spec = _make_sample_spec(concept="paging", obj_type=ObjectiveType.UNDERSTAND_MECHANISM)
    enforced = enforce_single_student_question(content=double_q, spec=spec)

    # Replaced by specification-driven fallback
    assert enforced.count("?") == 1
    assert "paging" in enforced.lower()
    assert "virtual memory" not in enforced.lower()
    is_valid_enforced, _ = validate_final_student_response(enforced)
    assert is_valid_enforced is True


# =====================================================================
# Scenario 3: Compound question with one question mark handled conservatively
# =====================================================================

def test_compound_question_with_one_question_mark_handled_conservatively():
    # Independent interrogative clause joined by conjunction
    compound_q = "What is a mutex, and how does it prevent race conditions?"
    assert has_compound_interrogatives(compound_q) is True
    is_valid, reasons = validate_final_student_response(compound_q)
    assert is_valid is False
    assert any("Compound question detected" in r for r in reasons)

    spec = _make_sample_spec(concept="mutex", obj_type=ObjectiveType.UNDERSTAND_DEFINITION)
    enforced = enforce_single_student_question(content=compound_q, spec=spec)
    assert enforced.count("?") == 1
    is_valid_enforced, _ = validate_final_student_response(enforced)
    assert is_valid_enforced is True

    # Non-compound single question with compound subject must NOT be falsely rejected
    valid_compound_subject = "What is the time and space complexity of merge sort?"
    assert has_compound_interrogatives(valid_compound_subject) is False
    is_valid_subject, _ = validate_final_student_response(valid_compound_subject)
    assert is_valid_subject is True
    assert enforce_single_student_question(valid_compound_subject, spec) == valid_compound_subject


# =====================================================================
# Scenario 4: Quoted question mark in technical text
# =====================================================================

def test_quoted_question_mark_in_technical_text():
    # Technical literal quote with ?
    regex_q = "In Python regex, what does the '?' quantifier do when placed after a plus sign?"
    masked = mask_technical_question_marks(regex_q)
    assert "[QM_LITERAL]" in masked
    assert masked.count("?") == 1
    is_valid, reasons = validate_final_student_response(regex_q)
    assert is_valid is True
    assert reasons == []

    # Code backtick literal with ?
    ternary_q = "When evaluating the expression `x ? y : z`, what condition is checked first?"
    is_valid_ternary, _ = validate_final_student_response(ternary_q)
    assert is_valid_ternary is True

    # But an actual quoted question clause that introduces a second question is NOT masked
    multi_with_quote = "He asked 'What is recursion?' How do we stop it?"
    is_valid_multi, multi_reasons = validate_final_student_response(multi_with_quote)
    assert is_valid_multi is False
    assert any("one-question rule" in r for r in multi_reasons)


# =====================================================================
# Scenario 5: Off-topic / redirection prefix combined with question
# =====================================================================

def test_off_topic_redirection_prefix_combined_with_question():
    context = _make_context()
    spec = _make_sample_spec()
    assessment = LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.1,
        relevance_level=RelevanceLevel.IRRELEVANT,
        concept_alignment_score=0.1,
        claims=[],
        evidence=[],
        correctness=CorrectnessLevel.INCORRECT,
        correctness_score=0.1,
        completeness=CompletenessLevel.MINIMAL,
        classification=AssessmentClassification.INCORRECT,
        confidence=0.8,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
    )

    state = {
        "context": context,
        "evaluation": TurnEvaluation(
            correctness=0.1, clarity=0.5, completeness=0.1, depth=0.1, relevance=0.1,
            stuck_probability=0.2, misconceptions=[], recommended_strategy=Strategy.CLARIFY_TERM, recommended_difficulty=2
        ),
        "decision": LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.CLARIFY_TERM,
            difficulty=2,
            active_concept="binary_search",
            confidence=0.8,
            reason="Gentle redirection needed",
        ),
        "question_specification": spec,
        "assessment": assessment,
        "interpretation": TurnInterpretation(intent=TurnIntent.OFF_TOPIC),
        "provider": MockLLMProvider(),
    }

    res = response_node(state)
    content = res["response"].content
    assert "That doesn't address the question yet. Let's focus on binary search." in content
    # Invariant: exactly 1 question in the entire user-visible response
    assert content.count("?") == 1
    is_valid, reasons = validate_final_student_response(content)
    assert is_valid is True
    assert reasons == []


# =====================================================================
# Scenario 6: Clarification prefix combined with question
# =====================================================================

def test_clarification_prefix_combined_with_question():
    context = _make_context()
    spec = _make_sample_spec()
    assessment = LearningAssessment(
        intent=AssessmentIntent.CLARIFICATION_REQUEST,
        is_answer_attempt=False,
        relevance_score=0.9,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.8,
        claims=[],
        evidence=[],
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.5,
        completeness=CompletenessLevel.PARTIAL,
        classification=AssessmentClassification.PARTIAL,
        confidence=0.8,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
    )

    state = {
        "context": context,
        "evaluation": TurnEvaluation(
            correctness=0.5, clarity=0.5, completeness=0.5, depth=0.5, relevance=1.0,
            stuck_probability=0.2, misconceptions=[], recommended_strategy=Strategy.PROBE_HOW, recommended_difficulty=2
        ),
        "decision": LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.PROBE_HOW,
            difficulty=2,
            active_concept="binary_search",
            confidence=0.8,
            reason="Clarification requested",
        ),
        "question_specification": spec,
        "assessment": assessment,
        "interpretation": TurnInterpretation(intent=TurnIntent.CLARIFICATION_REQUEST),
        "provider": MockLLMProvider(),
    }

    res = response_node(state)
    content = res["response"].content
    assert "By that, I'm referring to the core mechanism of binary search." in content
    assert content.count("?") == 1
    is_valid, reasons = validate_final_student_response(content)
    assert is_valid is True
    assert reasons == []


# =====================================================================
# Scenario 7: Restored interrupted question passes through final enforcement
# =====================================================================

def test_restored_interrupted_question_passes_through_final_enforcement():
    context = _make_context()
    context.current_state.interrupted_question = CurrentQuestion(
        content="How does binary search decide whether to search left or right?",
        concept="binary_search",
        difficulty=2,
        id="q-interrupted-1",
    )
    spec = _make_sample_spec()

    state = {
        "context": context,
        "evaluation": TurnEvaluation(
            correctness=0.9, clarity=0.9, completeness=0.9, depth=0.8, relevance=1.0,
            stuck_probability=0.0, misconceptions=[], recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION, recommended_difficulty=2
        ),
        "decision": LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            difficulty=2,
            active_concept="binary_search",
            confidence=0.9,
            reason="Teacher intervention resolved",
            should_restore_interrupted_question=True,
        ),
        "question_specification": spec,
        "assessment": None,
        "interpretation": TurnInterpretation(intent=TurnIntent.ACKNOWLEDGEMENT),
        "provider": MockLLMProvider(),
    }

    res = response_node(state)
    content = res["response"].content
    assert "Great job! Now let's return to our original question:" in content
    assert "How does binary search decide whether to search left or right?" in content
    assert content.count("?") == 1
    is_valid, _ = validate_final_student_response(content)
    assert is_valid is True


# =====================================================================
# Scenario 8: Invalid restored question is repaired or replaced safely
# =====================================================================

def test_invalid_restored_question_repaired_or_replaced_safely():
    context = _make_context()
    # Corrupted / compound restored question with multiple question marks
    context.current_state.interrupted_question = CurrentQuestion(
        content="What is binary search? And why does it need sorting? Can we use linked lists?",
        concept="binary_search",
        difficulty=2,
        id="q-interrupted-corrupt",
    )
    spec = _make_sample_spec(concept="binary_search", obj_type=ObjectiveType.UNDERSTAND_MECHANISM)

    state = {
        "context": context,
        "evaluation": TurnEvaluation(
            correctness=0.9, clarity=0.9, completeness=0.9, depth=0.8, relevance=1.0,
            stuck_probability=0.0, misconceptions=[], recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION, recommended_difficulty=2
        ),
        "decision": LearningDecision(
            next_mode=Mode.STUDENT,
            strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            difficulty=2,
            active_concept="binary_search",
            confidence=0.9,
            reason="Teacher intervention resolved",
            should_restore_interrupted_question=True,
        ),
        "question_specification": spec,
        "assessment": None,
        "interpretation": TurnInterpretation(intent=TurnIntent.ACKNOWLEDGEMENT),
        "provider": MockLLMProvider(),
    }

    res = response_node(state)
    content = res["response"].content
    # The transition prefix must be preserved
    assert "Great job! Now let's return to our original question:" in content
    # The corrupted multi-question body must be replaced by a single safe specification fallback
    assert content.count("?") == 1
    assert "linked lists" not in content
    is_valid, _ = validate_final_student_response(content)
    assert is_valid is True


# =====================================================================
# Scenario 9: Generator fallback still returns a valid response
# =====================================================================

def test_generator_fallback_still_returns_valid_response():
    provider = MockLLMProvider()
    generator = QuestionGenerator(provider)
    spec = _make_sample_spec(concept="trie_data_structure", diff=3, obj_type=ObjectiveType.APPLY_CONCEPT)

    # Force all candidate generation attempts to return multi-question text
    invalid_candidate = QuestionCandidate(
        candidate_id="cand_bad",
        question_text="What is a trie? How do prefixes work?",
    )
    with patch.object(QuestionGenerator, "_generate_candidates", return_value=[invalid_candidate]):
        sel_res = generator.generate_and_select_question(spec)
        assert sel_res.selected_candidate is not None
        final_text = sel_res.selected_candidate.question_text
        assert final_text.count("?") == 1
        assert "trie" in final_text.lower()
        is_valid, _ = validate_final_student_response(final_text)
        assert is_valid is True


# =====================================================================
# Scenario 10: Recovery is bounded and cannot loop indefinitely
# =====================================================================

def test_recovery_is_bounded_and_cannot_loop_indefinitely():
    spec = _make_sample_spec(concept="quicksort")

    # Edge cases: empty, whitespace, pure punctuation, deeply nested garbage
    test_cases = [
        "",
        "   ",
        "???",
        "What is quicksort? And what is merge sort? And what is heap sort?",
        "That doesn't address the question yet.\n\nWhat is A? What is B?",
    ]

    for tc in test_cases:
        res = enforce_single_student_question(content=tc, spec=spec)
        assert isinstance(res, str)
        assert res.strip() != ""
        assert res.count("?") == 1
        is_valid, reasons = validate_final_student_response(res)
        assert is_valid is True, f"Failed for input '{tc}': {reasons}"

    # Verify when spec is None, topic fallback is safely returned
    res_no_spec = enforce_single_student_question(content="???", spec=None, fallback_concept="graph_traversal")
    assert res_no_spec.count("?") == 1
    assert "Graph Traversal" in res_no_spec
    is_valid_no_spec, _ = validate_final_student_response(res_no_spec)
    assert is_valid_no_spec is True


# =====================================================================
# Scenario 11: Answer leakage is not introduced by recovery
# =====================================================================

def test_answer_leakage_rejected_and_safe_recovery_applied():
    spec = _make_sample_spec(concept="binary_search")
    leaked_response = "Binary search works by comparing the middle element and halving the array space, right?"
    is_valid, reasons = validate_final_student_response(leaked_response)
    assert is_valid is False
    assert any("Answer leakage" in r for r in reasons)

    enforced = enforce_single_student_question(leaked_response, spec=spec)
    assert "right?" not in enforced
    assert enforced.count("?") == 1
    # Ensure recovery asks a Socratic question without revealing the answer
    is_valid_enforced, _ = validate_final_student_response(enforced)
    assert is_valid_enforced is True


# =====================================================================
# Scenario 12: Teacher Mode and Evaluator Mode behavior remains unchanged
# =====================================================================

def test_teacher_mode_and_evaluator_mode_behavior_unchanged():
    context = _make_context()
    spec = _make_sample_spec()
    evaluation = TurnEvaluation(
        correctness=0.2, clarity=0.5, completeness=0.2, depth=0.1, relevance=1.0,
        stuck_probability=0.8, misconceptions=[], recommended_strategy=Strategy.TEACH_GAP, recommended_difficulty=1
    )

    # Teacher Mode
    state_teacher = {
        "context": context,
        "evaluation": evaluation,
        "decision": LearningDecision(
            next_mode=Mode.TEACHER,
            strategy=Strategy.TEACH_GAP,
            difficulty=1,
            active_concept="binary_search",
            confidence=0.5,
            reason="Teacher intervention needed",
        ),
        "question_specification": spec,
        "assessment": None,
        "interpretation": TurnInterpretation(intent=TurnIntent.HELP_REQUEST),
        "provider": MockLLMProvider(),
    }
    with patch("backend.app.ai.nodes.student_nodes.enforce_single_student_question") as mock_guard:
        res_t = response_node(state_teacher)
        mock_guard.assert_not_called()
        assert res_t["response"].mode == Mode.TEACHER

    # Evaluator Mode
    state_evaluator = {
        "context": context,
        "evaluation": evaluation,
        "decision": LearningDecision(
            next_mode=Mode.EVALUATOR,
            strategy=Strategy.GENERATE_REPORT,
            difficulty=1,
            active_concept="binary_search",
            confidence=0.7,
            reason="Session complete",
        ),
        "question_specification": spec,
        "assessment": None,
        "interpretation": TurnInterpretation(intent=TurnIntent.UNKNOWN),
        "provider": MockLLMProvider(),
    }
    with patch("backend.app.ai.nodes.student_nodes.enforce_single_student_question") as mock_guard:
        res_e = response_node(state_evaluator)
        mock_guard.assert_not_called()
        assert res_e["response"].mode == Mode.EVALUATOR
