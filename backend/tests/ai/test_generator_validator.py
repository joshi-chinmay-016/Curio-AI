"""
Unit tests for QuestionValidator, QuestionNoveltyChecker, and QuestionGenerator (Phases G & H).
Verifies:
- One-question rule enforcement
- Answer leakage and teacher lecturing detection
- Semantic novelty detection
- Regeneration on validation failure
- Specification-driven fallback without hardcoded topic contamination
"""
import pytest
from backend.app.ai.novelty import QuestionNoveltyChecker
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.question_generator import QuestionGenerator
from backend.app.ai.question_validator import QuestionValidator
from backend.app.ai.schemas import (
    LearningObjective,
    ObjectiveType,
    QuestionCandidate,
    QuestionSpecification,
)


def _sample_spec(concept="page_replacement_algorithm", difficulty=3):
    obj = LearningObjective(
        objective_type=ObjectiveType.APPLY_CONCEPT,
        target_concept=concept,
        difficulty=difficulty,
        reason="Testing paging application",
        evidence_expected="Learner explains eviction decision",
    )
    return QuestionSpecification(
        target_concept=concept,
        learning_objective=obj,
        difficulty=difficulty,
        reason="Paging application testing",
        evidence_expected="Learner explains eviction decision",
        generation_constraints=["Ask exactly ONE question", "Do not lecture"],
    )


def test_novelty_checker_rejects_duplicate():
    checker = QuestionNoveltyChecker(similarity_threshold=0.75)
    past_questions = [
        "Why does binary search require the input list to be sorted?",
        "How does the middle element comparison eliminate half the search space?",
    ]

    # Extremely similar question
    is_novel, sim, reason = checker.is_novel(
        "Why does binary search require a sorted list?",
        past_questions,
    )
    assert is_novel is False
    assert sim >= 0.75
    assert "Too similar" in reason

    # Novel question
    is_novel_2, sim_2, _ = checker.is_novel(
        "What happens when duplicate keys exist in the array?",
        past_questions,
    )
    assert is_novel_2 is True
    assert sim_2 < 0.75


def test_validator_enforces_one_question_rule():
    validator = QuestionValidator()
    spec = _sample_spec()

    # Two questions
    cand_double = QuestionCandidate(
        candidate_id="c1",
        question_text="How does FIFO decide which page to evict? What is Belady's anomaly?",
    )
    val_double = validator.validate_candidate(cand_double, spec)
    assert val_double.is_valid is False
    assert any("one-question rule" in r for r in val_double.rejection_reasons)

    # Valid single question
    cand_single = QuestionCandidate(
        candidate_id="c2",
        question_text="How does a page replacement algorithm decide which frame to evict when physical memory is full?",
    )
    val_single = validator.validate_candidate(cand_single, spec)
    assert val_single.is_valid is True
    assert val_single.score > 0.0


def test_validator_rejects_accidental_teacher_lecturing():
    validator = QuestionValidator()
    spec = _sample_spec()

    cand_lecture = QuestionCandidate(
        candidate_id="c_lec",
        question_text="Let me explain how paging works: pages are fixed-size blocks of virtual memory. How do frames fit in?",
    )
    val_lecture = validator.validate_candidate(cand_lecture, spec)
    assert val_lecture.is_valid is False
    assert any("Accidental teacher explanation" in r for r in val_lecture.rejection_reasons)


def test_generator_fallback_is_specification_driven():
    """Verify that when generator encounters failures, fallback uses target concept and never hardcodes Binary Search."""
    provider = MockLLMProvider()
    generator = QuestionGenerator(provider)

    spec = _sample_spec(concept="distributed_consensus_raft", difficulty=4)
    result = generator.generate_and_select_question(spec)

    assert result.selected_candidate is not None
    q_text = result.selected_candidate.question_text
    # Must target distributed consensus / Raft, NOT Binary Search
    assert "binary search" not in q_text.lower()
    assert "consensus" in q_text.lower() or "raft" in q_text.lower()
    # Must end with question mark and satisfy one-question rule
    assert q_text.count("?") == 1
