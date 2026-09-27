"""
Unit and integration tests for Answer Intelligence and Learning Assessment layer.
Verifies compliance with Milestones A specifications, including regression cases,
MasteryGate invariance, teacher mode verification, and provider abstraction.
"""
import pytest
from backend.app.ai.answer_intelligence.assessment_aggregator import AssessmentAggregator
from backend.app.ai.answer_intelligence.mastery_gate import MasteryGate
from backend.app.ai.answer_intelligence.schemas import (
    AssessmentClassification,
    AssessmentIntent,
    AssessmentStatus,
    CompletenessLevel,
    CorrectnessLevel,
    EvidenceStatus,
    LearningAssessment,
    RelevanceLevel,
)
from backend.app.ai.engine import CurioEngine
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    ConceptModel,
    ConceptNode,
    CurrentQuestion,
    LearningObjective,
    Mode,
    ObjectiveType,
    QuestionSpecification,
    Role,
    StateUpdates,
    Strategy,
    TeacherIntervention,
    ChatMessage,
)


@pytest.fixture
def atomicity_concept_model():
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


@pytest.fixture
def binary_search_concept_model():
    return ConceptModel(
        topic="Binary Search",
        concepts=[
            ConceptNode(
                id="binary_search_efficiency",
                name="Binary Search Efficiency",
                definition="Binary search achieves logarithmic time complexity by repeatedly halving the search interval.",
                constraints=["halving search interval", "logarithmic reduction of search space", "O(log n) time complexity"],
                common_misconceptions=["binary search works on unsorted array"],
                difficulty_level=2,
            )
        ],
    )


class TestExactFailureRegressions:
    """Tests corresponding to Section 33: The exact failure we are fixing."""

    def test_backend_technology_python_only_denies_mastery(self, atomicity_concept_model):
        """
        Question: 'What is the most important condition required for atomicity in DBMS?'
        Answer: 'It is a backend technology used by Python only.'
        Expected: intent=ANSWER_ATTEMPT, relevance=IRRELEVANT, correctness!=CORRECT, supports_mastery=False
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(
            id="q1",
            content="What is the single most important condition required for atomicity in DBMS?",
            concept="atomicity",
            difficulty=2,
        )
        assessment = aggregator.assess(
            user_message="It is a backend technology used by Python only.",
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert assessment.intent == AssessmentIntent.ANSWER_ATTEMPT
        assert assessment.relevance_level == RelevanceLevel.IRRELEVANT
        assert assessment.relevance_score <= 0.20
        assert assessment.correctness != CorrectnessLevel.CORRECT
        assert not assessment.supports_mastery

    def test_java_created_by_james_gosling_denies_mastery(self, atomicity_concept_model):
        """
        Answer: 'Java was created by James Gosling.'
        Expected: NOT mastery, NOT correct for target, no positive concept update
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(id="q1", content="What is atomicity?", concept="atomicity", difficulty=2)
        assessment = aggregator.assess(
            user_message="Java was created by James Gosling.",
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert assessment.relevance_level == RelevanceLevel.IRRELEVANT
        assert not assessment.supports_mastery
        assert assessment.classification == AssessmentClassification.IRRELEVANT

    def test_yesterday_was_sunny_denies_mastery(self, atomicity_concept_model):
        """
        Answer: 'Because yesterday was sunny.'
        Expected: IRRELEVANT, no mastery, no positive state update
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(id="q1", content="What is atomicity?", concept="atomicity", difficulty=2)
        assessment = aggregator.assess(
            user_message="Because yesterday was sunny.",
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert assessment.relevance_level == RelevanceLevel.IRRELEVANT
        assert not assessment.supports_mastery


class TestTechnicallyTrueButIrrelevant:
    """Tests corresponding to Section 34: Technically true but irrelevant statement."""

    def test_database_indexing_irrelevant_to_atomicity(self, atomicity_concept_model):
        """
        Question: 'What is atomicity?'
        Answer: 'Database indexing can make lookups faster.'
        Factually true in DBMS, but completely irrelevant to atomicity.
        Must NOT be classified as correct for target, must NOT grant mastery.
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(id="q1", content="What is atomicity?", concept="atomicity", difficulty=2)
        assessment = aggregator.assess(
            user_message="Database indexing can make lookups faster.",
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert assessment.relevance_level == RelevanceLevel.IRRELEVANT
        assert not assessment.supports_mastery
        assert assessment.correctness != CorrectnessLevel.CORRECT


class TestCorrectAnswer:
    """Tests corresponding to Section 35: Genuinely correct answers."""

    def test_genuine_demonstration_grants_mastery(self, atomicity_concept_model):
        """
        Question: 'What is atomicity?'
        Answer: 'Atomicity means a transaction behaves as an all-or-nothing unit:
                 either the required operations commit or the transaction is rolled back.'
        Expected: HIGH relevance, HIGH concept alignment, strong evidence, CORRECT, supports_mastery=True
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(id="q1", content="What is atomicity?", concept="atomicity", difficulty=2)
        ans = (
            "Atomicity means a transaction behaves as an all-or-nothing unit: "
            "either the required operations commit or the transaction is rolled back."
        )
        assessment = aggregator.assess(
            user_message=ans,
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert assessment.intent == AssessmentIntent.ANSWER_ATTEMPT
        assert assessment.relevance_level == RelevanceLevel.RELEVANT
        assert assessment.relevance_score >= 0.70
        assert assessment.concept_alignment_score >= 0.60
        assert assessment.correctness == CorrectnessLevel.CORRECT
        assert not assessment.misconception_status
        assert assessment.supports_mastery


class TestMisconceptionDetection:
    """Tests corresponding to Section 36: Misconception detection."""

    def test_partial_commit_misconception_detected(self, atomicity_concept_model):
        """
        Question: 'What is atomicity?'
        Answer: 'Atomicity means a transaction can partially commit even if another operation fails.'
        Expected: HIGH relevance, INCORRECT / MISCONCEPTION, misconception detected, supports_mastery=False
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(id="q1", content="What is atomicity?", concept="atomicity", difficulty=2)
        ans = "Atomicity means a transaction can partially commit even if another operation fails."
        assessment = aggregator.assess(
            user_message=ans,
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert assessment.relevance_level == RelevanceLevel.RELEVANT
        assert assessment.misconception_status
        assert len(assessment.misconceptions) > 0
        assert not assessment.supports_mastery


class TestPartialAnswer:
    """Tests corresponding to Section 37: Partial and incomplete answers."""

    def test_partial_binary_search_answer(self, binary_search_concept_model):
        """
        Question: 'Why is binary search efficient?'
        Answer: 'Because it keeps dividing the search range.'
        Expected: relevant, partially correct, missing evidence identified, supports_mastery=False
        """
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(
            id="q1",
            content="Why is binary search efficient?",
            concept="binary_search_efficiency",
            difficulty=2,
        )
        assessment = aggregator.assess(
            user_message="Because it keeps dividing the search range.",
            concept_model=binary_search_concept_model,
            current_question=q,
            target_concept_override="binary_search_efficiency",
        )

        assert assessment.relevance_level == RelevanceLevel.RELEVANT
        assert assessment.correctness in (CorrectnessLevel.PARTIALLY_CORRECT, CorrectnessLevel.INCOMPLETE)
        assert not assessment.supports_mastery
        assert len(assessment.missing_concepts) > 0


class TestAcknowledgementRule:
    """Tests corresponding to Section 23 & 40: Acknowledgements must never prove understanding."""

    @pytest.mark.parametrize("ack_msg", [
        "Okay.", "Yes.", "Got it.", "I understand.", "I am good.",
        "Teach me again.", "Makes sense.", "Ready.", "Understood",
    ])
    def test_acknowledgements_never_grant_mastery(self, atomicity_concept_model, ack_msg):
        aggregator = AssessmentAggregator()
        q = CurrentQuestion(id="q1", content="Explain atomicity.", concept="atomicity", difficulty=2)
        assessment = aggregator.assess(
            user_message=ack_msg,
            concept_model=atomicity_concept_model,
            current_question=q,
            target_concept_override="atomicity",
        )

        assert not assessment.supports_mastery
        assert assessment.correctness == CorrectnessLevel.UNASSESSABLE


class TestTeacherVerificationEngineIntegration:
    """Tests corresponding to Section 38, 39, 40: Teacher Mode verification through CurioEngine."""

    def test_teacher_mode_acknowledgement_remains_in_teacher_mode(self, atomicity_concept_model):
        """
        During Teacher Mode verification, answering 'Okay, I understand' must NOT exit Teacher Mode.
        Must remain in Teacher Mode and ask substantive verification.
        """
        engine = CurioEngine()
        context = AIContext(
            topic="DBMS",
            current_mode=Mode.TEACHER,
            active_concept="atomicity",
            current_question=CurrentQuestion(
                id="q_verif",
                content="How does atomicity guarantee that an interrupted bank transfer doesn't lose money?",
                concept="atomicity",
                difficulty=2,
            ),
            interrupted_question=CurrentQuestion(
                id="q_orig",
                content="Explain how DBMS guarantees the ACID properties in distributed transactions.",
                concept="acid_properties",
                difficulty=3,
            ),
            teacher_intervention=TeacherIntervention(
                active=True,
                gap="atomicity",
                attempt_count=1,
                verification_required=True,
            ),
            messages=[
                ChatMessage(role=Role.USER, content="Okay, I understand."),
            ],
        )

        result = engine.process(context)
        assert result.decision.next_mode == Mode.TEACHER
        assert not result.decision.should_restore_interrupted_question
        assert result.response.mode == Mode.TEACHER

    def test_teacher_mode_failed_verification_remains_in_teacher_mode(self, atomicity_concept_model):
        """
        During Teacher Mode verification, an incorrect/unsubstantiated answer ('Because sorting makes searching faster')
        must remain in Teacher Mode.
        """
        engine = CurioEngine()
        context = AIContext(
            topic="DBMS",
            current_mode=Mode.TEACHER,
            active_concept="atomicity",
            current_question=CurrentQuestion(
                id="q_verif",
                content="Explain why failure causes a complete rollback.",
                concept="atomicity",
                difficulty=2,
            ),
            interrupted_question=CurrentQuestion(
                id="q_orig",
                content="Original question",
                concept="acid_properties",
                difficulty=3,
            ),
            teacher_intervention=TeacherIntervention(
                active=True,
                gap="atomicity",
                attempt_count=1,
                verification_required=True,
            ),
            messages=[
                ChatMessage(role=Role.USER, content="Because sorting makes searching faster."),
            ],
        )

        result = engine.process(context)
        assert result.decision.next_mode == Mode.TEACHER
        assert not result.decision.should_restore_interrupted_question

    def test_teacher_mode_successful_verification_restores_interrupted_question(self, atomicity_concept_model):
        """
        During Teacher Mode verification, a correct explanation demonstrates understanding:
        Teacher Mode exits, interrupted question is restored, and Student Mode resumes.
        """
        engine = CurioEngine()
        context = AIContext(
            topic="DBMS",
            current_mode=Mode.TEACHER,
            active_concept="atomicity",
            current_question=CurrentQuestion(
                id="q_verif",
                content="Explain what happens if any operation fails in an atomic transaction.",
                concept="atomicity",
                difficulty=2,
            ),
            interrupted_question=CurrentQuestion(
                id="q_orig",
                content="Original interrupted question about distributed databases.",
                concept="distributed_databases",
                difficulty=3,
            ),
            teacher_intervention=TeacherIntervention(
                active=True,
                gap="atomicity",
                attempt_count=1,
                verification_required=True,
            ),
            messages=[
                ChatMessage(
                    role=Role.USER,
                    content="If any operation fails, the entire transaction rolls back completely with all or nothing execution.",
                ),
            ],
        )

        result = engine.process(context)
        assert result.decision.next_mode == Mode.STUDENT
        assert result.decision.should_restore_interrupted_question
        assert result.state_updates.current_mode == Mode.STUDENT
        assert result.state_updates.interrupted_question is None
        assert result.state_updates.teacher_intervention.active is False


class TestIrrelevantRedirectionInStudentMode:
    """Tests that irrelevant answers in Student Mode gently redirect without false praise or mastery."""

    def test_irrelevant_answer_does_not_advance_mastery(self, atomicity_concept_model):
        engine = CurioEngine()
        context = AIContext(
            topic="DBMS",
            current_mode=Mode.STUDENT,
            active_concept="atomicity",
            current_question=CurrentQuestion(
                id="q1",
                content="What is the single most important condition required for atomicity in DBMS?",
                concept="atomicity",
                difficulty=2,
            ),
            messages=[
                ChatMessage(role=Role.USER, content="Java was created by James Gosling."),
            ],
        )

        result = engine.process(context)
        # Should stay in student mode, redirect to target concept, and NOT advance mastery
        assert result.decision.next_mode == Mode.STUDENT
        assert result.state_updates.concept_mastery.get("atomicity", 0.0) == 0.0
        assert not result.learning_assessment.supports_mastery
        assert "doesn't address the question" in result.response.content or "atomicity" in result.response.content.lower()


class TestAbstentionAndConfidence:
    """Tests corresponding to Section 18 & 41: Confidence and abstention."""

    def test_abstention_blocks_mastery(self):
        gate = MasteryGate()
        assessment = LearningAssessment(
            intent=AssessmentIntent.ANSWER_ATTEMPT,
            is_answer_attempt=True,
            relevance_score=0.90,
            relevance_level=RelevanceLevel.RELEVANT,
            concept_alignment_score=0.90,
            claims=[],
            evidence=[],
            correctness=CorrectnessLevel.CORRECT,
            correctness_score=0.90,
            completeness=CompletenessLevel.COMPLETE,
            completeness_score=0.90,
            classification=AssessmentClassification.CORRECT,
            confidence=0.30,  # Below threshold
            assessment_status=AssessmentStatus.ABSTAIN,
        )

        decision = gate.evaluate(assessment, "atomicity")
        assert not decision.supports_mastery
        assert not decision.mastery_delta_allowed
        assert "Abstaining" in decision.reason
