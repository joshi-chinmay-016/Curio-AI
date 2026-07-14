from typing import Dict

# Configurable weights for confidence metric calculations
CONFIDENCE_WEIGHTS = {
    "concept_coverage": 0.30,
    "recent_answer_quality": 0.25,
    "difficulty_achievement": 0.20,
    "consistency": 0.15,
    "independent_correction": 0.10
}

def calculate_confidence(
    concept_coverage: float,
    recent_answer_quality: float,
    difficulty_achievement: float,
    consistency: float,
    independent_correction: float,
    misconception_penalty: float = 0.0,
    help_dependency_penalty: float = 0.0,
    weights: Dict[str, float] = None
) -> float:
    if weights is None:
        weights = CONFIDENCE_WEIGHTS

    score = (
        weights["concept_coverage"] * concept_coverage +
        weights["recent_answer_quality"] * recent_answer_quality +
        weights["difficulty_achievement"] * difficulty_achievement +
        weights["consistency"] * consistency +
        weights["independent_correction"] * independent_correction
    )

    # Apply penalties
    score -= misconception_penalty
    score -= help_dependency_penalty

    # Ensure score falls between 0.0 and 1.0
    return max(0.0, min(1.0, score))
