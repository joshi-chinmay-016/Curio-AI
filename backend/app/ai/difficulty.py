DIFFICULTY_LEVELS = {
    1: "Definition",
    2: "Mechanism",
    3: "Application",
    4: "Edge Cases",
    5: "Synthesis / Trade-offs"
}

def get_difficulty_label(level: int) -> str:
    return DIFFICULTY_LEVELS.get(level, "Unknown")
