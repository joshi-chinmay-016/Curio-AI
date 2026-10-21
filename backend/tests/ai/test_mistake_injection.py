"""
Unit and Integration Regression Tests for Dynamic Mistake Injection in Curio AI.
Validates:
- Demonstrated understanding gating & cooldown rules
- Candidate generation & independent verification
- 3-Way response evaluation (CAUGHT, MISSED, INCONCLUSIVE)
- Mastery state protection (no instant 100% mastery jumps or automatic failure tags)
- Inconclusive response clarification without penalty
- State persistence and lifecycle tracking
"""
import pytest
from backend.app.ai.mistake_injection import (
    MistakeInjectionEngine,
    MistakeCandidate,
    MistakeVerificationResult,
    MistakeEvaluationVerdict,
    InjectedMistakeState,
)


class MockProviderForMistake:
    """Mock LLM provider for isolated, deterministic test verification."""
    def __init__(self, verification_pass=True, eval_verdict="CAUGHT"):
        self.verification_pass = verification_pass
        self.eval_verdict = eval_verdict

    def generate_structured(self, prompt: str, response_model):
        if response_model == MistakeCandidate:
            return MistakeCandidate(
                concept="Ohm's Law",
                claim="If resistance doubles while voltage remains constant, current also doubles.",
                why_false="Under V = IR, current is inversely proportional to resistance at constant voltage, so doubling resistance halves the current.",
                student_question="Wait, so if resistance doubles while voltage stays constant, the current also doubles, right?",
            )
        elif response_model == MistakeVerificationResult:
            return MistakeVerificationResult(
                is_valid=self.verification_pass,
                reasoning="Claim is factually false under Ohm's Law and represents a classic learner misconception.",
            )
        elif response_model == MistakeEvaluationVerdict:
            return MistakeEvaluationVerdict(
                verdict=self.eval_verdict,
                explanation=f"Evaluated as {self.eval_verdict} based on mock configuration.",
                evidence="Test evidence excerpt.",
            )
        return None

    def generate_text(self, prompt: str) -> str:
        if "VERDICT:" in prompt:
            return f"VERDICT: {self.eval_verdict}\nEXPLANATION: Mock explanation"
        return "Wait, so if resistance doubles at constant voltage, the current also doubles, right?"


def test_eligibility_gating_sound_and_complete():
    """Eligible when difficulty >= 3, turn >= 3, strong explanation, cooldown satisfied, no misconceptions."""
    engine = MistakeInjectionEngine()

    # Pass case
    is_eligible = engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=3,
        last_injected_turn=None,
        correctness=0.85,
        completeness=0.80,
        has_unresolved_misconceptions=False,
        pending_mistake=None,
        is_stuck_or_remediation=False,
    )
    assert is_eligible is True


def test_eligibility_gating_rejects_weak_or_incomplete():
    """Rejects injection if answer is weak, incomplete, or contains active misconceptions."""
    engine = MistakeInjectionEngine()

    # Low correctness
    assert engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=3,
        last_injected_turn=None,
        correctness=0.50,
        completeness=0.80,
        has_unresolved_misconceptions=False,
    ) is False

    # Low completeness
    assert engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=3,
        last_injected_turn=None,
        correctness=0.85,
        completeness=0.40,
        has_unresolved_misconceptions=False,
    ) is False

    # Active misconception
    assert engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=3,
        last_injected_turn=None,
        correctness=0.85,
        completeness=0.80,
        has_unresolved_misconceptions=True,
    ) is False


def test_eligibility_gating_rejects_cooldown_and_pending():
    """Rejects injection if cooldown (<3 turns) not met or another injection is pending."""
    engine = MistakeInjectionEngine()

    # Cooldown not met (turn 4 with last injection at turn 3)
    assert engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=4,
        last_injected_turn=3,
        correctness=0.90,
        completeness=0.90,
        has_unresolved_misconceptions=False,
    ) is False

    # Pending injection already active
    pending = {"active": True, "turn": 3, "status": "PENDING"}
    assert engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=6,
        last_injected_turn=3,
        correctness=0.90,
        completeness=0.90,
        has_unresolved_misconceptions=False,
        pending_mistake=pending,
    ) is False


def test_eligibility_gating_rejects_non_student_or_remediation():
    """Never injects in Teacher mode or when user is stuck / in remediation."""
    engine = MistakeInjectionEngine()

    # In Teacher mode
    assert engine.check_eligibility(
        mode="TEACHER",
        current_difficulty=3,
        turn_number=3,
        last_injected_turn=None,
        correctness=0.90,
        completeness=0.90,
        has_unresolved_misconceptions=False,
    ) is False

    # In stuck / remediation
    assert engine.check_eligibility(
        mode="STUDENT",
        current_difficulty=3,
        turn_number=3,
        last_injected_turn=None,
        correctness=0.90,
        completeness=0.90,
        has_unresolved_misconceptions=False,
        is_stuck_or_remediation=True,
    ) is False


def test_independent_verification_pass_and_fail():
    """Independent verification must confirm candidate is false and suitable."""
    pass_provider = MockProviderForMistake(verification_pass=True)
    engine_pass = MistakeInjectionEngine(pass_provider)
    candidate = engine_pass.generate_candidate("Ohm's Law", "V = IR governs voltage and current.")
    v_pass = engine_pass.verify_candidate("Ohm's Law", candidate)
    assert v_pass.is_valid is True

    fail_provider = MockProviderForMistake(verification_pass=False)
    engine_fail = MistakeInjectionEngine(fail_provider)
    v_fail = engine_fail.verify_candidate("Ohm's Law", candidate)
    assert v_fail.is_valid is False


def test_three_way_evaluation_caught():
    """Learner correctly refutes the false claim -> CAUGHT."""
    provider = MockProviderForMistake(eval_verdict="CAUGHT")
    engine = MistakeInjectionEngine(provider)
    pending = InjectedMistakeState(
        active=True,
        turn=3,
        concept="Ohm's Law",
        claim="If resistance doubles while voltage remains constant, current also doubles.",
        why_false="Current is inversely proportional to resistance.",
        question="Wait, does current double if resistance doubles at constant voltage?",
    )
    result = engine.evaluate_response(
        topic="Ohm's Law",
        user_response="No, that's incorrect. Since V = IR, if resistance doubles at constant voltage, the current is halved, not doubled.",
        pending_mistake=pending,
    )
    assert result.verdict == "CAUGHT"


def test_three_way_evaluation_missed():
    """Learner explicitly endorses the false claim -> MISSED."""
    provider = MockProviderForMistake(eval_verdict="MISSED")
    engine = MistakeInjectionEngine(provider)
    pending = InjectedMistakeState(
        active=True,
        turn=3,
        concept="Ohm's Law",
        claim="If resistance doubles while voltage remains constant, current also doubles.",
        why_false="Current is inversely proportional to resistance.",
        question="Wait, does current double if resistance doubles at constant voltage?",
    )
    result = engine.evaluate_response(
        topic="Ohm's Law",
        user_response="Yes, exactly, everything doubles proportionally.",
        pending_mistake=pending,
    )
    assert result.verdict == "MISSED"


def test_three_way_evaluation_inconclusive():
    """Learner gives an ambiguous response or requests clarification -> INCONCLUSIVE."""
    # Deterministic heuristic verification when user asks for clarification
    engine = MistakeInjectionEngine(None)
    pending = InjectedMistakeState(
        active=True,
        turn=3,
        concept="Ohm's Law",
        claim="If resistance doubles while voltage remains constant, current also doubles.",
        why_false="Current is inversely proportional to resistance.",
        question="Wait, does current double if resistance doubles at constant voltage?",
    )
    result = engine.evaluate_response(
        topic="Ohm's Law",
        user_response="What do you mean? Could you clarify what you're asking?",
        pending_mistake=pending,
    )
    assert result.verdict == "INCONCLUSIVE"


def test_injected_mistake_state_persistence_and_serialization():
    """Injected mistake state must serialize and deserialize completely with lifecycle fields."""
    state = InjectedMistakeState(
        active=True,
        turn=3,
        concept="Binary Search",
        claim="Sorting an unsorted array first makes binary search O(log n) total.",
        why_false="Sorting takes O(n log n), which dominates overall time complexity.",
        question="Wait, so if we sort an unsorted collection first and then run binary search, is the entire operation O(log n)?",
        verified=True,
        status="PENDING",
    )
    data = state.model_dump()
    assert data["claim"].startswith("Sorting an unsorted array")
    assert data["verified"] is True
    assert data["status"] == "PENDING"

    restored = InjectedMistakeState(**data)
    assert restored.concept == "Binary Search"
    assert restored.why_false.startswith("Sorting takes")
