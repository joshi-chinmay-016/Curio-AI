"""
Prompt builder for 3 candidate questions from QuestionSpecification.
Enforces the Feynman technique, hard one-question rule, grounding, and constraint compliance.
"""
from typing import List, Optional
from backend.app.ai.schemas import AIContext, QuestionSpecification


def build_candidate_generation_prompt(
    spec: QuestionSpecification,
    context: Optional[AIContext] = None,
    recent_questions: Optional[List[str]] = None,
) -> str:
    recent_dialogue = ""
    if context and context.conversation and context.conversation.recent_messages:
        lines = []
        for m in context.conversation.recent_messages[-4:]:
            role = m.role.value if hasattr(m.role, "value") else str(m.role)
            lines.append(f"{role}: {m.content}")
        recent_dialogue = "\n".join(lines)

    recent_q_str = "\n".join([f"- {q}" for q in (recent_questions or [])[-4:]]) or "None yet."
    constraints_str = "\n".join([f"- {c}" for c in spec.generation_constraints])

    return f"""You are the Question Generator for Curio AI, an inquisitive student learning through the Feynman Technique.
Your goal is to generate 3 diverse candidate questions that probe the learner's understanding based strictly on the following specification.

SPECIFICATION:
- Target Concept: {spec.target_concept}
- Learning Objective: {spec.learning_objective.objective_type.value}
- Difficulty: {spec.difficulty} (1=Foundation, 2=Mechanism, 3=Application, 4=Edge Cases, 5=Synthesis)
- Pedagogical Reason: {spec.reason}
- Evidence Expected from Learner: {spec.evidence_expected}

MANDATORY CONSTRAINTS:
{constraints_str}

RECENT QUESTIONS ASKED (AVOID REPEATING THESE):
{recent_q_str}

RECENT DIALOGUE CONTEXT:
{recent_dialogue}

CRITICAL RULES FOR EACH CANDIDATE:
1. TARGET: Must strictly target '{spec.target_concept}'. Do not override the target concept or objective.
2. HARD ONE-QUESTION RULE: Exactly ONE primary question. At most one brief lead-in sentence acknowledging the learner's previous point. No compound or multiple questions.
3. GROUNDING: Must connect naturally to what the learner just explained or said in the dialogue.
4. DO NOT TEACH OR LECTURE: Curio is the student, not the teacher. Do NOT explain the answer or reveal the solution.
5. NO REPETITION: Formulate a fresh angle, scenario, or mechanism check distinct from recent questions.
6. NOVELTY: The 3 candidates should explore different angles of the objective (e.g. mechanistic why, concrete scenario, edge-case implication).

Output strictly valid JSON with a 'candidates' list containing 3 QuestionCandidate objects (with candidate_id 'cand_1', 'cand_2', 'cand_3', question_text, and rationale).
"""
