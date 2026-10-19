"""
Focused regression tests for Phase 3 Step 3.2:
Wiring Student Assessment into Question Generation.

Validates:
- Test A: Assessment propagation from response_node to QuestionGenerator.
- Test B: Prompt propagation ensuring assessment findings reach LLM prompt.
- Test C: Missing assessment safety (no fabricated claims when assessment is None).
- Test D: Backward compatibility (omitted assessment, validation, retries, and fallback).
- Test E: Student Mode isolation (Teacher and Evaluator modes remain unaffected).
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.app.ai.answer_intelligence.prompt_augmentation import (
    DynamicPromptContext,
    build_dynamic_prompt_context,
)
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
from backend.app.ai.nodes.student_nodes import response_node
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.question_generator import QuestionGenerator
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
    QuestionSelectionResult,
    QuestionSpecification,
    Role,
    SessionInfo,
    SessionState,
    Strategy,
    TurnEvaluation,
    TurnIntent,
    TurnInterpretation,
)


def _make_sample_assessment() -> LearningAssessment:
    return LearningAssessment(
        intent=AssessmentIntent.ANSWER_ATTEMPT,
        is_answer_attempt=True,
        relevance_score=0.92,
        relevance_level=RelevanceLevel.RELEVANT,
        concept_alignment_score=0.88,
        claims=[],
        evidence=[
            EvidenceItem(
                concept_id="binary_search",
                expected_description="requires elements to be in sorted order",
                status=EvidenceStatus.SUPPORTED,
            ),
            EvidenceItem(
                concept_id="binary_search",
                expected_description="halves search interval on every step",
                status=EvidenceStatus.MISSING,
            ),
        ],
        correctness=CorrectnessLevel.PARTIALLY_CORRECT,
        correctness_score=0.55,
        completeness=CompletenessLevel.PARTIAL,
        completeness_score=0.50,
        misconception_status=True,
        misconceptions=[
            MisconceptionEvidence(
                concept_id="binary_search",
                description="checks every element sequentially until target is found",
                learner_statement="It checks elements one by one until finding it",
                severity="HIGH",
            )
        ],
        missing_concepts=["halves search interval on every step"],
        classification=AssessmentClassification.MISCONCEPTION,
        confidence=0.90,
        supports_mastery=False,
        assessment_status=AssessmentStatus.HIGH_CONFIDENCE,
        recommended_learning_action="CHALLENGE_MISCONCEPTION",
    )


def _make_sample_spec(concept: str = "binary_search", diff: int = 2) -> QuestionSpecification:
    return QuestionSpecification(
        target_concept=concept,
        learning_objective=LearningObjective(
            objective_type=ObjectiveType.UNDERSTAND_MECHANISM,
            target_concept=concept,
            difficulty=diff,
            reason="Probe step-by-step mechanism",
            evidence_expected="Learner explains interval halving",
        ),
        difficulty=diff,
        reason="Probe interval halving",
        evidence_expected="Learner explains interval halving",
        generation_constraints=["Ask exactly ONE question", "Do not reveal the answer"],
    )


def _make_context(topic: str = "Algorithms", active_concept: str = "binary_search") -> AIContext:
    session_info = SessionInfo(session_id="sess_wiring_test", topic=topic)
    state = SessionState(
        session_id="sess_wiring_test",
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
# Test A: Assessment propagation from response_node to QuestionGenerator
# =====================================================================

def test_response_node_propagates_assessment_to_generator():
    """Test A: Verify response_node passes the populated assessment to QuestionGenerator."""
    context = _make_context()
    spec = _make_sample_spec()
    assessment = _make_sample_assessment()
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.CHALLENGE_MISCONCEPTION,
        difficulty=2,
        active_concept="binary_search",
        confidence=0.6,
        reason="Challenge sequential check misconception",
    )
    evaluation = TurnEvaluation(
        correctness=0.35,
        clarity=0.8,
        completeness=0.4,
        depth=0.3,
        relevance=0.9,
        stuck_probability=0.1,
        misconceptions=["checks every element sequentially"],
        recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
        recommended_difficulty=2,
    )

    state = {
        "context": context,
        "evaluation": evaluation,
        "decision": decision,
        "question_specification": spec,
        "assessment": assessment,
        "interpretation": TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT),
        "provider": MockLLMProvider(),
    }

    with patch.object(QuestionGenerator, "generate_and_select_question") as mock_gen:
        mock_cand = QuestionCandidate(
            candidate_id="cand_1",
            question_text="If binary search checks one by one, how is it faster than linear search?",
        )
        mock_gen.return_value = QuestionSelectionResult(
            specification=spec,
            candidates=[mock_cand],
            validations=[],
            selected_candidate=mock_cand,
            selection_reason="Valid test candidate",
            novelty_passed=True,
        )

        result = response_node(state)

        mock_gen.assert_called_once()
        _, kwargs = mock_gen.call_args
        # Assert assessment is passed and is the exact assessment object from state
        assert "assessment" in kwargs
        assert kwargs["assessment"] is assessment
        assert result["response"].mode == Mode.STUDENT


# =====================================================================
# Test B: Prompt propagation of genuine assessment findings
# =====================================================================

def test_candidate_generation_embeds_assessment_findings_in_prompt():
    """Test B: Verify QuestionGenerator forwards assessment and findings reach the prompt."""
    spec = _make_sample_spec()
    context = _make_context()
    assessment = _make_sample_assessment()

    recorded_prompts = []

    class RecordingProvider(MockLLMProvider):
        def generate_structured(self, prompt, response_model):
            recorded_prompts.append(prompt)
            return super().generate_structured(prompt, response_model)

    provider = RecordingProvider()
    generator = QuestionGenerator(provider)

    result = generator.generate_and_select_question(
        spec=spec,
        context=context,
        recent_questions=["What is the runtime of binary search?"],
        assessment=assessment,
    )

    assert result.selected_candidate is not None
    assert len(recorded_prompts) >= 1

    first_prompt = recorded_prompts[0]
    # 1. Assessment section header present
    assert "STRUCTURED LEARNER ASSESSMENT CONTEXT" in first_prompt
    # 2. Supported evidence reaches prompt
    assert "requires elements to be in sorted order" in first_prompt
    # 3. Missing evidence reaches prompt
    assert "halves search interval on every step" in first_prompt
    # 4. Misconception reaches prompt
    assert "checks every element sequentially until target is found" in first_prompt
    # 5. Target concept and intent present
    assert "Target Concept: binary_search" in first_prompt
    assert "Learner Intent: ANSWER_ATTEMPT" in first_prompt


# =====================================================================
# Test C: Missing assessment safety (no fabricated claims)
# =====================================================================

def test_missing_assessment_handled_safely_without_fabricated_claims():
    """Test C: Verify absent assessment does not fabricate claims about understanding or misconceptions."""
    context = _make_context()
    spec = _make_sample_spec()

    # 1. Direct prompt augmentation test with assessment=None
    ctx_none = build_dynamic_prompt_context(None, context=context, difficulty=1)
    assert ctx_none.assessment_available is False
    prompt_sec = ctx_none.to_prompt_section()

    # Assert honest "Not evaluated" instead of claiming "None detected" or "None identified"
    assert "Active Misconceptions: None detected" not in prompt_sec
    assert "Missing / Unproven Concepts: None identified" not in prompt_sec
    assert "Active Misconceptions: Not evaluated" in prompt_sec
    assert "Missing / Unproven Concepts: Not evaluated" in prompt_sec
    assert "Demonstrated Understanding: Not evaluated" in prompt_sec

    # 2. Generator test with assessment=None
    recorded_prompts = []

    class RecordingProvider(MockLLMProvider):
        def generate_structured(self, prompt, response_model):
            recorded_prompts.append(prompt)
            return super().generate_structured(prompt, response_model)

    provider = RecordingProvider()
    generator = QuestionGenerator(provider)

    result = generator.generate_and_select_question(
        spec=spec,
        context=context,
        assessment=None,
    )

    assert result.selected_candidate is not None
    prompt_text = recorded_prompts[0]
    assert "Active Misconceptions: None detected" not in prompt_text
    assert "Active Misconceptions: Not evaluated" in prompt_text


# =====================================================================
# Test D: Backward compatibility with omitted assessment & fallbacks
# =====================================================================

def test_backward_compatibility_with_omitted_assessment_and_fallback():
    """Test D: Verify existing calls without assessment still function through validation and fallback."""
    provider = MockLLMProvider()
    generator = QuestionGenerator(provider)
    spec = _make_sample_spec(concept="hash_table", diff=3)

    # Calling with only spec (omitting context, recent_q, and assessment)
    res = generator.generate_and_select_question(spec)
    assert res.selected_candidate is not None
    assert res.selected_candidate.question_text.count("?") == 1
    assert "hash" in res.selected_candidate.question_text.lower()


# =====================================================================
# Test E: Student Mode isolation (Teacher & Evaluator unaffected)
# =====================================================================

def test_student_mode_isolation_unrelated_modes_untouched():
    """Test E: Verify response_node preserves Teacher and Evaluator modes without calling question generator."""
    context = _make_context()
    spec = _make_sample_spec()
    assessment = _make_sample_assessment()
    evaluation = TurnEvaluation(
        correctness=0.2,
        clarity=0.5,
        completeness=0.2,
        depth=0.1,
        relevance=1.0,
        stuck_probability=0.8,
        misconceptions=[],
        recommended_strategy=Strategy.TEACH_GAP,
        recommended_difficulty=1,
    )

    # 1. Teacher Mode branch
    state_teacher = {
        "context": context,
        "evaluation": evaluation,
        "decision": LearningDecision(
            next_mode=Mode.TEACHER,
            strategy=Strategy.TEACH_GAP,
            difficulty=1,
            active_concept="binary_search",
            confidence=0.4,
            reason="Teacher intervention needed",
        ),
        "question_specification": spec,
        "assessment": assessment,
        "interpretation": TurnInterpretation(intent=TurnIntent.HELP_REQUEST),
        "provider": MockLLMProvider(),
    }

    with patch.object(QuestionGenerator, "generate_and_select_question") as mock_gen:
        res_t = response_node(state_teacher)
        mock_gen.assert_not_called()
        assert res_t["response"].mode == Mode.TEACHER

    # 2. Evaluator Mode branch
    state_evaluator = {
        "context": context,
        "evaluation": evaluation,
        "decision": LearningDecision(
            next_mode=Mode.EVALUATOR,
            strategy=Strategy.GENERATE_REPORT,
            difficulty=1,
            active_concept="binary_search",
            confidence=0.7,
            reason="Session evaluation complete",
        ),
        "question_specification": spec,
        "assessment": assessment,
        "interpretation": TurnInterpretation(intent=TurnIntent.UNKNOWN),
        "provider": MockLLMProvider(),
    }

    with patch.object(QuestionGenerator, "generate_and_select_question") as mock_gen:
        res_e = response_node(state_evaluator)
        mock_gen.assert_not_called()
        assert res_e["response"].mode == Mode.EVALUATOR


def test_state_updates_node_emits_misconception_counts_from_learner_model():
    """Verify state_updates_node exports cumulative misconception counts from learner model into StateUpdates."""
    from backend.app.ai.learner_model import LearnerModelManager
    from backend.app.ai.nodes.student_nodes import state_updates_node
    from backend.app.ai.schemas import AIResponse, ConceptModel, ConceptNode, LearnerModel

    mgr = LearnerModelManager()
    mgr.update_from_evaluation(
        "binary_search",
        TurnEvaluation(
            correctness=0.3,
            clarity=0.5,
            completeness=0.3,
            depth=0.2,
            relevance=1.0,
            stuck_probability=0.2,
            misconceptions=["Always checks linearly"],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        ),
        interpretation=TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT),
    )

    spec = _make_sample_spec()
    context = _make_context()
    evaluation = TurnEvaluation(
        correctness=0.4,
        clarity=0.6,
        completeness=0.4,
        depth=0.3,
        relevance=1.0,
        stuck_probability=0.1,
        misconceptions=["Always checks linearly"],
        recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
        recommended_difficulty=1,
    )
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.CHALLENGE_MISCONCEPTION,
        difficulty=1,
        active_concept="binary_search",
        confidence=0.4,
        reason="Challenge misconception",
    )
    response = AIResponse(
        content="What happens if the array is unsorted?",
        mode=Mode.STUDENT,
        strategy=Strategy.CHALLENGE_MISCONCEPTION,
        difficulty=1,
        confidence=0.4,
    )

    state = {
        "context": context,
        "evaluation": evaluation,
        "decision": decision,
        "response": response,
        "question_specification": spec,
        "assessment": _make_sample_assessment(),
        "interpretation": TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT),
        "concept_model": ConceptModel(topic="Binary Search", concepts=[ConceptNode(id="binary_search", name="Binary Search")]),
        "learner_model": mgr.model,
    }

    res = state_updates_node(state)
    updates = res["state_updates"]

    assert updates.misconception_counts is not None
    assert updates.misconception_counts.get("binary_search") == 1


def test_state_updates_node_missing_learner_model_preserves_existing_counts():
    """Verify that when learner_model is None, state_updates_node preserves existing session misconception counts."""
    from backend.app.ai.nodes.student_nodes import state_updates_node
    from backend.app.ai.schemas import AIResponse

    spec = _make_sample_spec()
    context = _make_context()
    context.current_state.misconception_counts = {"existing_concept": 3}

    evaluation = TurnEvaluation(
        correctness=0.8,
        clarity=0.8,
        completeness=0.8,
        depth=0.7,
        relevance=1.0,
        stuck_probability=0.0,
        misconceptions=[],
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=1,
    )
    decision = LearningDecision(
        next_mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=1,
        active_concept="binary_search",
        confidence=0.6,
        reason="Probe deeper why",
    )
    response = AIResponse(
        content="Could you explain why?",
        mode=Mode.STUDENT,
        strategy=Strategy.PROBE_WHY,
        difficulty=1,
        confidence=0.6,
    )

    state = {
        "context": context,
        "evaluation": evaluation,
        "decision": decision,
        "response": response,
        "question_specification": spec,
        "assessment": _make_sample_assessment(),
        "interpretation": TurnInterpretation(intent=TurnIntent.ANSWER_ATTEMPT),
        "concept_model": None,
        "learner_model": None,
    }

    res = state_updates_node(state)
    updates = res["state_updates"]

    # Must preserve existing {"existing_concept": 3} rather than resetting to {}
    assert updates.misconception_counts == {"existing_concept": 3}


