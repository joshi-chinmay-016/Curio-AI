"""
Unit tests for ScoringEngine (Phase 3D) and GapAnalyzer (Phase 3E).
"""
import uuid
import pytest
from backend.app.ai.gap_analyzer import GapAnalyzer
from backend.app.ai.schemas import (
    GapSeverity,
    GapStatus,
    MasteryLevel,
    MisconceptionStatus,
    SessionEvidence,
    Strategy,
    TeacherInterventionEvidence,
    TurnEvaluation,
    TurnEvidence,
)
from backend.app.ai.scoring import ScoringEngine
from backend.app.ai.session_evidence import SessionEvidenceBuilder


def _make_turn(
    turn_idx: int,
    concept: str,
    diff: int,
    correctness: float,
    clarity: float = 0.8,
    completeness: float = 0.8,
    depth: float = 0.7,
    relevance: float = 1.0,
    stuck_prob: float = 0.0,
    misconceptions: list = None,
    missing_concepts: list = None,
    knowledge_gap: str = None,
    mastered: list = None,
) -> TurnEvidence:
    te = TurnEvaluation(
        correctness=correctness,
        clarity=clarity,
        completeness=completeness,
        depth=depth,
        relevance=relevance,
        stuck_probability=stuck_prob,
        misconceptions=misconceptions or [],
        missing_concepts=missing_concepts or [],
        undefined_terms=[],
        mastered_concepts=mastered or [],
        knowledge_gap=knowledge_gap,
        recommended_strategy=Strategy.PROBE_WHY,
        recommended_difficulty=diff,
    )
    return TurnEvidence(
        turn_index=turn_idx,
        question=f"Question {turn_idx}",
        learner_answer=f"Answer {turn_idx}",
        concept=concept,
        difficulty=diff,
        evaluation=te,
    )


def test_scoring_bounds_and_determinism():
    engine = ScoringEngine()
    turn_strong = _make_turn(0, "Recursion", 5, 1.0, 1.0, 1.0, 1.0, 1.0)
    score = engine.calculate_turn_score(turn_strong)
    assert 0.0 <= score <= 100.0

    turn_weak = _make_turn(1, "Recursion", 1, 0.0, 0.0, 0.0, 0.0, 0.0, stuck_prob=0.9)
    score_weak = engine.calculate_turn_score(turn_weak)
    assert score_weak == 0.0

    # Determinism: same input yields exact same output
    assert engine.calculate_turn_score(turn_strong) == score


def test_low_evidence_and_insufficient_evidence_guard():
    engine = ScoringEngine()
    builder = SessionEvidenceBuilder()

    # Only 1 turn with 100% correctness
    ev = builder.build_from_history(
        session_id="s1",
        topic="Binary Search",
        messages=[
            {"sender": "AI", "content": "Q"},
            {"sender": "USER", "content": "A"},
        ],
        evaluations=[
            TurnEvaluation(
                correctness=1.0,
                clarity=1.0,
                completeness=1.0,
                depth=1.0,
                relevance=1.0,
                stuck_probability=0.0,
                mastered_concepts=["Binary Search"],
                recommended_strategy=Strategy.INCREASE_DIFFICULTY,
                recommended_difficulty=2,
            )
        ],
    )
    score = engine.calculate_session_score(ev)
    confidence = engine.calculate_evidence_confidence(ev)
    mastery = engine.determine_mastery_level(score, confidence)

    assert score >= 85.0
    # Insufficient evidence guard: 1 turn cannot have high confidence
    assert confidence < 0.40
    # Must NOT be MASTERY because confidence is low
    assert mastery in [MasteryLevel.DEVELOPING, MasteryLevel.BEGINNER]


def test_strong_evidence_mastery():
    engine = ScoringEngine()
    builder = SessionEvidenceBuilder()

    # 5 strong turns across 2 concepts and increasing difficulty
    evals = [
        TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Divide and Conquer"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=d,
        )
        for d in [1, 2, 3, 4, 5]
    ]
    messages = []
    for i in range(5):
        messages.append({"sender": "AI", "content": f"Q{i}"})
        messages.append({"sender": "USER", "content": f"A{i}"})

    ev = builder.build_from_history(
        session_id="s2",
        topic="Divide and Conquer",
        messages=messages,
        evaluations=evals,
        difficulty_history=[1, 2, 3, 4, 5],
    )
    score = engine.calculate_session_score(ev)
    confidence = engine.calculate_evidence_confidence(ev)
    mastery = engine.determine_mastery_level(score, confidence)

    assert score >= 85.0
    assert confidence >= 0.70
    assert mastery == MasteryLevel.MASTERY


def test_teacher_intervention_penalty():
    engine = ScoringEngine()
    builder = SessionEvidenceBuilder()

    messages = [
        {"sender": "AI", "content": "Q1"},
        {"sender": "USER", "content": "A1"},
        {"sender": "AI", "content": "Teacher explanation\n\nVerification?", "metadata": {"mode": "TEACHER", "gap": "Order"}},
        {"sender": "USER", "content": "Still don't get it."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.2,
            clarity=0.4,
            completeness=0.2,
            depth=0.1,
            relevance=0.8,
            stuck_probability=0.8,
            knowledge_gap="Order",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.2,
            clarity=0.3,
            completeness=0.2,
            depth=0.1,
            relevance=0.5,
            stuck_probability=0.8,
            knowledge_gap="Order",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
    ]
    ev = builder.build_from_history("s3", "Binary Search", messages, evals)
    score = engine.calculate_session_score(ev)
    # Score should be low due to failure and unresolved teacher intervention
    assert score < 40.0


def test_gap_lifecycle_detected_resolved_unresolved():
    analyzer = GapAnalyzer()
    builder = SessionEvidenceBuilder()

    # Case A: Gap resolved via teacher intervention verification pass
    messages_res = [
        {"sender": "AI", "content": "Q1"},
        {"sender": "USER", "content": "A1"},
        {"sender": "AI", "content": "Teacher explanation\n\nVerification?", "metadata": {"mode": "TEACHER", "gap": "Sorted Order"}},
        {"sender": "USER", "content": "Verification answer"},
    ]
    evals_res = [
        TurnEvaluation(
            correctness=0.2,
            clarity=0.5,
            completeness=0.2,
            depth=0.1,
            relevance=0.8,
            stuck_probability=0.8,
            knowledge_gap="Sorted Order",
            recommended_strategy=Strategy.TEACH_GAP,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.9,
            clarity=0.9,
            completeness=0.9,
            depth=0.8,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Sorted Order"],
            recommended_strategy=Strategy.RESTORE_INTERRUPTED_QUESTION,
            recommended_difficulty=2,
        ),
    ]
    ev_res = builder.build_from_history("s_res", "Binary Search", messages_res, evals_res)
    gap_items, resolved, unresolved = analyzer.analyze_gaps(ev_res)

    assert "Sorted Order" in resolved
    assert "Sorted Order" not in unresolved

    # Case B: Gap unresolved
    messages_unres = [
        {"sender": "AI", "content": "Q1"},
        {"sender": "USER", "content": "A1"},
    ]
    evals_unres = [
        TurnEvaluation(
            correctness=0.3,
            clarity=0.5,
            completeness=0.3,
            depth=0.1,
            relevance=0.8,
            stuck_probability=0.4,
            knowledge_gap="Boundary conditions",
            recommended_strategy=Strategy.PROBE_WHY,
            recommended_difficulty=1,
        )
    ]
    ev_unres = builder.build_from_history("s_unres", "Binary Search", messages_unres, evals_unres)
    gap_items_u, resolved_u, unresolved_u = analyzer.analyze_gaps(ev_unres)

    assert "Boundary conditions" in unresolved_u
    assert "Boundary conditions" not in resolved_u


def test_misconception_lifecycle():
    analyzer = GapAnalyzer()
    builder = SessionEvidenceBuilder()

    # Misconception detected in turn 0, challenged, then cleared in turn 1
    messages = [
        {"sender": "AI", "content": "Q1"},
        {"sender": "USER", "content": "Binary search works on unsorted arrays."},
        {"sender": "AI", "content": "If the array is unsorted, how do you eliminate half?"},
        {"sender": "USER", "content": "Ah, you cannot! You need sorted order to eliminate half."},
    ]
    evals = [
        TurnEvaluation(
            correctness=0.3,
            clarity=0.8,
            completeness=0.3,
            depth=0.2,
            relevance=1.0,
            stuck_probability=0.0,
            misconceptions=["Binary search works on unsorted arrays"],
            recommended_strategy=Strategy.CHALLENGE_MISCONCEPTION,
            recommended_difficulty=1,
        ),
        TurnEvaluation(
            correctness=0.95,
            clarity=0.9,
            completeness=0.9,
            depth=0.85,
            relevance=1.0,
            stuck_probability=0.0,
            mastered_concepts=["Sorted order elimination"],
            recommended_strategy=Strategy.INCREASE_DIFFICULTY,
            recommended_difficulty=2,
        ),
    ]
    ev = builder.build_from_history("s_misc", "Binary Search", messages, evals)
    misc_items, resolved_m, unresolved_m = analyzer.analyze_misconceptions(ev)

    assert "Binary search works on unsorted arrays" in resolved_m
    assert "Binary search works on unsorted arrays" not in unresolved_m
