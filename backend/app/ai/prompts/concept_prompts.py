"""
Prompt builder for dynamic concept model and learning objective generation in Curio AI (Milestone D).
Generates structured concept trees, learning objectives, observable evidence, and relationships.
"""


def build_concept_model_prompt(topic: str, context_notes: str = "") -> str:
    notes_section = f"\nADDITIONAL CONTEXT:\n{context_notes}\n" if context_notes else ""
    return f"""You are the Curriculum & Concept Architect for Curio AI.
Your task is to dynamically build a comprehensive, structured Concept Model (TopicModel) for the following topic:

TOPIC: {topic}{notes_section}

REQUIREMENTS:
1. Identify 4 to 8 fundamental and advanced concepts that comprise this topic, ordered logically from foundation (difficulty 1) to synthesis/edge cases (difficulty 4-5).
2. For EACH concept, specify:
   - id: Unique, lowercase, normalized identifier using letters, numbers, and underscores (e.g. "process_scheduling", "paging_mechanism").
   - name: Clear human-readable name.
   - definition: Precise pedagogical definition of the concept.
   - prerequisites: List of concept IDs (from this model) that must be understood first. Prerequisite relationships MUST form a Directed Acyclic Graph (DAG) with NO cycles.
   - difficulty_level: Integer from 1 (FOUNDATION) to 5 (SYNTHESIS).
   - learning_objectives: 1 to 3 observable learning objectives describing demonstrable abilities. Each must have:
     * objective_id: Unique string id (e.g. "obj_paging_address_translation")
     * description: Clear statement of demonstrable skill (e.g. "Explain how virtual page numbers are translated to physical frame numbers")
     * cognitive_action: One of DEFINE, EXPLAIN, COMPARE, APPLY, DERIVE, ANALYZE, PREDICT, JUSTIFY, EVALUATE, SYNTHESIZE
     * essential: Boolean indicating whether this is essential core knowledge
     * expected_evidence: 1 to 3 expected evidence requirements detailing what a correct explanation must contain:
       - evidence_id: Unique string id (e.g. "ev_page_table_lookup")
       - description: Specific factual or mechanistic requirement (e.g. "Identifies indexing page table with VPN to find PFN")
       - evidence_type: One of DEFINITION, MECHANISM, REASONING, EXAMPLE, APPLICATION, COMPARISON, JUSTIFICATION, DERIVATION, PREDICTION
       - essential: Boolean
   - concept_constraints: Invariants or rules that must hold for this concept (e.g. "Page size must be a power of 2").
   - common_misconceptions: Frequent flaws or invalid beliefs held by learners.
   - applications: Practical real-world uses or scenarios.
   - edge_cases: Boundary conditions or failure modes.
3. Specify relationships between concepts:
   - source_concept_id and target_concept_id (must match existing concept IDs; no self-loops).
   - relation_type: PREREQUISITE_OF, DEPENDS_ON, PART_OF, RELATED_TO, CONTRASTS_WITH, GENERALIZES_TO, SPECIALIZES_TO, CAUSES, REQUIRES, or EXAMPLE_OF.
   - description: Brief description of the connection.

CRITICAL INVARIANTS:
- Do NOT output any question bank. This is a model of knowledge and learning objectives, not questions.
- Concept IDs must be lowercase with underscores.
- Prerequisite relationships MUST be strictly acyclic (no circular dependencies).
- Output strictly valid JSON conforming to the ConceptModel schema.
"""
