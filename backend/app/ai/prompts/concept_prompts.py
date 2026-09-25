"""
Prompt builder for dynamic concept model generation in Curio AI.
Generates structured concept trees, prerequisites, mechanisms, and common misconceptions.
"""


def build_concept_model_prompt(topic: str, context_notes: str = "") -> str:
    notes_section = f"\nADDITIONAL CONTEXT:\n{context_notes}\n" if context_notes else ""
    return f"""You are the Curriculum & Concept Architect for Curio AI.
Your task is to dynamically build a comprehensive, structured Concept Model for the following topic:

TOPIC: {topic}{notes_section}

REQUIREMENTS:
1. Identify 4 to 8 fundamental and advanced concepts that comprise this topic, ordered logically from foundation (difficulty 1) to synthesis/edge cases (difficulty 4-5).
2. For EACH concept, specify:
   - id: Unique, lowercase, normalized identifier using letters, numbers, and underscores (e.g. "process_scheduling", "paging_mechanism").
   - name: Clear human-readable name.
   - definition: Precise pedagogical definition of the concept.
   - prerequisites: List of concept IDs (from this model) that must be understood first.
   - sub_concepts: Specific sub-ideas or components.
   - applications: Practical real-world uses or engineering scenarios.
   - constraints: Limitations, trade-offs, or requirements.
   - common_misconceptions: Frequent flaws in student mental models.
   - edge_cases: Boundary conditions or tricky scenarios.
   - difficulty_level: Integer from 1 (FOUNDATION) to 5 (SYNTHESIS).
3. Specify causal and mechanistic relationships between concepts:
   - source_concept_id and target_concept_id (must match concept IDs).
   - relation_type: e.g. "PREREQUISITE_OF", "CAUSES", "MECHANISM_FOR", "SPECIALIZES", "PART_OF".
   - description: Brief description of the causal or mechanistic link.

IMPORTANT:
- Do NOT output any question bank. This is a model of understanding, not questions.
- Concept IDs must be lowercase with underscores.
- Prerequisite relationships must be acyclic.
- Output strictly valid JSON conforming to the ConceptModel schema.
"""
