"""
Dynamic Concept Model Builder, Graph Validator, and Graph Utilities for Curio AI.
Milestone D: Generic, topic-independent knowledge representation, learning objectives,
expected evidence, and prerequisite dependency graphs.
"""
import collections
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from backend.app.ai.prompts.concept_prompts import build_concept_model_prompt
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.schemas import (
    CognitiveAction,
    ConceptConstraint,
    ConceptModel,
    ConceptNode,
    ConceptRelationship,
    ConstraintType,
    EvidenceType,
    ExpectedEvidenceRequirement,
    LearningObjective,
    MisconceptionDefinition,
    RelationshipType,
    TopicModel,
    ValidationStatus,
)

logger = logging.getLogger("curio.ai.concept_model")


def normalize_concept_id(raw_id: str) -> str:
    """Normalize a concept ID into a clean snake_case identifier."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw_id or "").strip().lower()).strip("_")
    return cleaned or "core_concept"


def validate_topic_input(topic: str) -> Tuple[bool, str, str]:
    """
    Validate and sanitize user-supplied topic input.
    Rejects empty, excessively long, or adversarial prompt-injection inputs.
    Returns: (is_valid, sanitized_topic, error_message)
    """
    if not topic or not topic.strip():
        return False, "", "Topic cannot be empty or whitespace."

    cleaned = topic.strip()
    if len(cleaned) < 2:
        return False, "", "Topic is too short to construct a learning model."

    if len(cleaned) > 300:
        return False, "", "Topic text exceeds the maximum allowed length of 300 characters."

    # Adversarial instruction / prompt injection heuristic checks
    adversarial_patterns = [
        r"ignore\s+(previous|all)\s+instructions",
        r"system\s*prompt",
        r"override\s+system",
        r"you\s+are\s+now\s+a",
        r"reveal\s+secret",
        r"disregard\s+above",
        r"<\s*script\s*>",
    ]
    for pattern in adversarial_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return False, "", "Topic input contains disallowed instructions or characters."

    return True, cleaned, ""


class ValidationResult(BaseModel):
    """Encapsulates the structural, graph, and semantic validation outcomes of a ConceptModel."""
    is_valid: bool
    status: ValidationStatus = ValidationStatus.VALID
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    cycles: List[List[str]] = Field(default_factory=list)


class ConceptModelValidator:
    """
    Validates ConceptModels across structural integrity, dependency graph acyclicity,
    and semantic coherence without topic-specific rules.
    """

    def __init__(
        self,
        max_concepts: int = 12,
        max_objectives_per_concept: int = 5,
        max_relationships: int = 30,
    ):
        self.max_concepts = max_concepts
        self.max_objectives_per_concept = max_objectives_per_concept
        self.max_relationships = max_relationships

    def validate(self, model: ConceptModel) -> ValidationResult:
        """Run complete structural and graph validation on a ConceptModel."""
        errors: List[str] = []
        warnings: List[str] = []

        if not model.concepts:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID,
                errors=["ConceptModel contains zero concepts."],
            )

        if len(model.concepts) > self.max_concepts:
            warnings.append(f"Model contains {len(model.concepts)} concepts (max recommended: {self.max_concepts}).")

        # 1. Structural checks & Unique IDs
        seen_ids: Set[str] = set()
        for idx, node in enumerate(model.concepts):
            if not node.id:
                errors.append(f"Concept at index {idx} has an empty ID.")
            elif node.id in seen_ids:
                errors.append(f"Duplicate concept ID found: '{node.id}'.")
            else:
                seen_ids.add(node.id)

            if len(node.learning_objectives) > self.max_objectives_per_concept:
                warnings.append(
                    f"Concept '{node.id}' has {len(node.learning_objectives)} objectives (max: {self.max_objectives_per_concept})."
                )

        # 2. Reference Integrity
        for node in model.concepts:
            for prereq in node.prerequisites:
                if prereq not in seen_ids:
                    errors.append(f"Concept '{node.id}' references non-existent prerequisite '{prereq}'.")
                if prereq == node.id:
                    errors.append(f"Concept '{node.id}' has a self-loop prerequisite dependency.")

        for rel in model.relationships:
            if rel.source_concept_id not in seen_ids:
                errors.append(f"Relationship references unknown source '{rel.source_concept_id}'.")
            if rel.target_concept_id not in seen_ids:
                errors.append(f"Relationship references unknown target '{rel.target_concept_id}'.")
            if rel.source_concept_id == rel.target_concept_id:
                errors.append(f"Self-loop relationship on concept '{rel.source_concept_id}'.")

        # 3. Directed Prerequisite Graph Cycle Detection
        cycles = self.detect_prerequisite_cycles(model)
        if cycles:
            cycle_desc = "; ".join([" -> ".join(c) for c in cycles])
            errors.append(f"Prerequisite dependency cycles detected: {cycle_desc}")

        if errors:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID,
                errors=errors,
                warnings=warnings,
                cycles=cycles,
            )

        if warnings:
            return ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID_INCOMPLETE,
                warnings=warnings,
            )

        return ValidationResult(is_valid=True, status=ValidationStatus.VALID)

    def detect_prerequisite_cycles(self, model: ConceptModel) -> List[List[str]]:
        """
        Detects cycles in directed prerequisite dependencies using Tarjan's / DFS path tracking.
        Only directed prerequisite edges (PREREQUISITE_OF, REQUIRES, node.prerequisites) are subject to DAG checks.
        Returns a list of cycle paths, e.g. [['a', 'b', 'c', 'a']].
        """
        adj: Dict[str, Set[str]] = collections.defaultdict(set)
        for prereq, dependent in model.get_all_prerequisite_edges():
            adj[prereq].add(dependent)

        all_nodes = [c.id for c in model.concepts]
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting (in stack), 2: visited
        cycles: List[List[str]] = []
        path: List[str] = []

        def dfs(node: str):
            visited[node] = 1
            path.append(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited or visited[neighbor] == 0:
                    dfs(neighbor)
                elif visited[neighbor] == 1:
                    # Cycle found! Extract subpath from neighbor to node
                    idx = path.index(neighbor)
                    cycle_path = path[idx:] + [neighbor]
                    cycles.append(cycle_path)
            path.pop()
            visited[node] = 2

        for node in all_nodes:
            if visited.get(node, 0) == 0:
                dfs(node)

        return cycles

    def heal_prerequisite_cycles(self, model: ConceptModel) -> ConceptModel:
        """
        Safely heals cycles by removing offending back-edges while preserving all concepts.
        """
        cycles = self.detect_prerequisite_cycles(model)
        if not cycles:
            return model

        broken_edges: Set[Tuple[str, str]] = set()
        for cycle in cycles:
            if len(cycle) >= 2:
                # Break the closing back-edge (last node to first node of cycle)
                back_src, back_tgt = cycle[-2], cycle[-1]
                broken_edges.add((back_src, back_tgt))

        # Prune from node.prerequisites
        for node in model.concepts:
            node.prerequisites = [
                p for p in node.prerequisites
                if (p, node.id) not in broken_edges
            ]

        # Prune from relationships
        model.relationships = [
            r for r in model.relationships
            if (r.source_concept_id, r.target_concept_id) not in broken_edges
        ]

        logger.info("Healed prerequisite cycles by removing edges: %s", broken_edges)
        return model


# ---------------------------------------------------------------------------
# Generic Graph Utilities (Phase D5)
# ---------------------------------------------------------------------------

def get_topological_sort(model: ConceptModel) -> List[str]:
    """
    Returns concept IDs ordered by prerequisite dependency (foundations first).
    Uses Kahn's algorithm with tie-breaking by difficulty level then concept ID.
    If cycles exist, returns best-effort ordering without infinite looping.
    """
    adj: Dict[str, Set[str]] = collections.defaultdict(set)
    in_degree: Dict[str, int] = {c.id: 0 for c in model.concepts}
    difficulty_map = {c.id: c.difficulty_level for c in model.concepts}

    for prereq, dependent in model.get_all_prerequisite_edges():
        if prereq in in_degree and dependent in in_degree:
            adj[prereq].add(dependent)

    for prereq, deps in adj.items():
        for dep in deps:
            in_degree[dep] += 1

    # Zero in-degree queue sorted by difficulty level, then id
    queue = [cid for cid, deg in in_degree.items() if deg == 0]
    queue.sort(key=lambda cid: (difficulty_map.get(cid, 1), cid))

    sorted_ids: List[str] = []
    while queue:
        curr = queue.pop(0)
        sorted_ids.append(curr)
        for dep in sorted(adj.get(curr, set()), key=lambda cid: (difficulty_map.get(cid, 1), cid)):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    # Append any remaining disconnected or cycle nodes
    remaining = [c.id for c in model.concepts if c.id not in sorted_ids]
    remaining.sort(key=lambda cid: (difficulty_map.get(cid, 1), cid))
    sorted_ids.extend(remaining)

    return sorted_ids


def get_transitive_prerequisites(model: ConceptModel, concept_id: str) -> List[str]:
    """Returns all direct and indirect prerequisites for a concept in topological order."""
    cid_norm = normalize_concept_id(concept_id)
    adj: Dict[str, Set[str]] = collections.defaultdict(set)
    for prereq, dependent in model.get_all_prerequisite_edges():
        adj[dependent].add(prereq)  # Reverse graph to traverse upwards to prereqs

    visited: Set[str] = set()
    queue = list(adj.get(cid_norm, set()))
    while queue:
        curr = queue.pop(0)
        if curr not in visited and curr != cid_norm:
            visited.add(curr)
            for p in adj.get(curr, set()):
                if p not in visited and p != cid_norm:
                    queue.append(p)

    # Return sorted according to topological order of the model
    full_order = get_topological_sort(model)
    return [c for c in full_order if c in visited]


def get_dependent_concepts(model: ConceptModel, concept_id: str) -> List[str]:
    """Returns all concepts that directly or transitively depend on the given concept."""
    cid_norm = normalize_concept_id(concept_id)
    adj: Dict[str, Set[str]] = collections.defaultdict(set)
    for prereq, dependent in model.get_all_prerequisite_edges():
        adj[prereq].add(dependent)

    visited: Set[str] = set()
    queue = list(adj.get(cid_norm, set()))
    while queue:
        curr = queue.pop(0)
        if curr not in visited and curr != cid_norm:
            visited.add(curr)
            for d in adj.get(curr, set()):
                if d not in visited and d != cid_norm:
                    queue.append(d)

    full_order = get_topological_sort(model)
    return [c for c in full_order if c in visited]


def get_related_concepts(model: ConceptModel, concept_id: str) -> List[str]:
    """Returns concepts connected to this concept via non-prerequisite relationship edges."""
    cid_norm = normalize_concept_id(concept_id)
    related: Set[str] = set()
    for rel in model.relationships:
        if rel.relation_type not in (RelationshipType.PREREQUISITE_OF.value, "PREREQUISITE_OF", RelationshipType.REQUIRES.value, "REQUIRES"):
            if normalize_concept_id(rel.source_concept_id) == cid_norm:
                related.add(normalize_concept_id(rel.target_concept_id))
            elif normalize_concept_id(rel.target_concept_id) == cid_norm:
                related.add(normalize_concept_id(rel.source_concept_id))
    return sorted(list(related))


def get_isolated_concepts(model: ConceptModel) -> List[str]:
    """Identifies concepts with no prerequisite edges in or out."""
    connected_ids: Set[str] = set()
    for prereq, dep in model.get_all_prerequisite_edges():
        connected_ids.add(prereq)
        connected_ids.add(dep)
    return [c.id for c in model.concepts if c.id not in connected_ids]


def extract_assessment_subgraph(model: ConceptModel, active_concept_id: str) -> Dict[str, Any]:
    """
    Extracts a concise, token-efficient assessment context centered on the active concept.
    Includes active node, direct prerequisites, objectives, expected evidence, constraints, and misconceptions.
    Avoids sending the entire graph into LLM prompts on every turn.
    """
    node = model.get_concept(active_concept_id)
    if not node:
        return {"active_concept": None, "found": False, "concept_id": active_concept_id}

    direct_prereqs = model.get_prerequisites(node.id)
    objs = model.get_objectives_for_concept(node.id)
    ev_reqs = model.get_expected_evidence_for_concept(node.id)

    return {
        "found": True,
        "active_concept": {
            "id": node.id,
            "name": node.name,
            "definition": node.definition,
            "difficulty": node.difficulty_level,
        },
        "direct_prerequisites": direct_prereqs,
        "learning_objectives": [
            {
                "id": o.objective_id,
                "description": o.description,
                "cognitive_action": o.cognitive_action.value if hasattr(o.cognitive_action, "value") else str(o.cognitive_action),
                "essential": o.essential,
            }
            for o in objs
        ],
        "expected_evidence": [
            {
                "id": e.evidence_id,
                "description": e.description,
                "type": e.evidence_type.value if hasattr(e.evidence_type, "value") else str(e.evidence_type),
                "essential": e.essential,
            }
            for e in ev_reqs
        ],
        "constraints": [c.rule if hasattr(c, "rule") else str(c) for c in (node.concept_constraints or node.constraints)],
        "misconceptions": [
            m.description if hasattr(m, "description") else str(m)
            for m in (node.misconception_definitions or node.common_misconceptions)
        ],
    }


def summarize_for_prompt(model: ConceptModel, active_concept_id: Optional[str] = None, max_chars: int = 1500) -> str:
    """
    Builds a concise markdown summary of the ConceptModel for prompt augmentation.
    If active_concept_id is provided, focuses heavily on the active concept subgraph.
    """
    if active_concept_id:
        subgraph = extract_assessment_subgraph(model, active_concept_id)
        if subgraph.get("found", False) and isinstance(subgraph.get("active_concept"), dict):
            ac = subgraph["active_concept"]
            lines = [
                f"### Active Learning Target: {ac['name']} (`{ac['id']}`)",
                f"**Definition**: {ac['definition']}",
                f"**Direct Prerequisites**: {', '.join(subgraph['direct_prerequisites']) or 'None (Foundational)'}",
            ]
            if subgraph["learning_objectives"]:
                lines.append("**Learning Objectives**:")
                for o in subgraph["learning_objectives"][:3]:
                    lines.append(f"- [{o['cognitive_action']}] {o['description']} (Essential: {o['essential']})")
            if subgraph["expected_evidence"]:
                lines.append("**Expected Evidence Requirements**:")
                for e in subgraph["expected_evidence"][:3]:
                    lines.append(f"- ({e['type']}) {e['description']}")
            if subgraph["constraints"]:
                lines.append(f"**Key Constraints**: {'; '.join(subgraph['constraints'][:2])}")
            if subgraph["misconceptions"]:
                lines.append(f"**Known Misconceptions**: {'; '.join(subgraph['misconceptions'][:2])}")
            summary = "\n".join(lines)
            return summary[:max_chars]

    # Global overview
    lines = [f"### Topic Knowledge Architecture: {model.topic}"]
    topo_order = get_topological_sort(model)
    lines.append(f"**Prerequisite Progression**: {' -> '.join(topo_order)}")
    for c in model.concepts[:6]:
        prereqs = f" (prereqs: {', '.join(c.prerequisites)})" if c.prerequisites else " (foundation)"
        lines.append(f"- **{c.name}** [Diff {c.difficulty_level}]{prereqs}: {c.definition}")
    summary = "\n".join(lines)
    return summary[:max_chars]


# ---------------------------------------------------------------------------
# ConceptModelBuilder (Phase D3)
# ---------------------------------------------------------------------------

class ConceptModelBuilder:
    """
    Dynamically builds structured, validated ConceptModels from arbitrary topic strings.
    Topic-independent; works for Computer Science, Physics, Economics, Biology, etc.
    """

    def __init__(
        self,
        provider: BaseAIProvider,
        max_concepts: int = 10,
        max_objectives_per_concept: int = 3,
        max_relationships: int = 20,
        max_retries: int = 2,
    ):
        self.provider = provider
        self.max_concepts = max_concepts
        self.max_objectives_per_concept = max_objectives_per_concept
        self.max_relationships = max_relationships
        self.max_retries = max_retries
        self.validator = ConceptModelValidator(
            max_concepts=max_concepts,
            max_objectives_per_concept=max_objectives_per_concept,
            max_relationships=max_relationships,
        )

    def build_model(self, topic: str, context_notes: str = "") -> ConceptModel:
        """
        Build and validate a ConceptModel for any topic.
        Guaranteed to return a well-formed, acyclic model.
        """
        is_valid, clean_topic, err_msg = validate_topic_input(topic)
        if not is_valid:
            logger.info("Topic input '%s' invalid (%s); constructing fallback model.", topic, err_msg)
            fallback = self._construct_fallback_model(clean_topic or "General Knowledge")
            fallback.limitations.append(f"Input validation notice: {err_msg}")
            return fallback

        prompt = build_concept_model_prompt(clean_topic, context_notes)

        # Attempt structured generation with bounded retries
        for attempt in range(1, self.max_retries + 1):
            try:
                raw_model: ConceptModel = self.provider.generate_structured(prompt, ConceptModel)
                sanitized = self._validate_and_sanitize(raw_model, clean_topic)
                val_res = self.validator.validate(sanitized)

                if val_res.is_valid:
                    sanitized.validation_status = val_res.status
                    return sanitized

                # If cycles exist, heal them
                if val_res.cycles:
                    logger.warning("Attempt %d: Healing prerequisite cycles in generated model for '%s'", attempt, clean_topic)
                    healed = self.validator.heal_prerequisite_cycles(sanitized)
                    healed_res = self.validator.validate(healed)
                    if healed_res.is_valid:
                        healed.validation_status = ValidationStatus.VALID_INCOMPLETE
                        healed.limitations.append("Cycle detected and automatically healed in prerequisite graph.")
                        return healed

                logger.warning("Attempt %d: Validation failed for topic '%s' (%s)", attempt, clean_topic, val_res.errors)

            except Exception as e:
                logger.warning(
                    "ConceptModel generation attempt %d failed for topic '%s' (%s: %s)",
                    attempt,
                    clean_topic,
                    type(e).__name__,
                    str(e),
                )

        # Fallback if generation or validation fails
        logger.info("Constructing dynamic fallback model for topic '%s'", clean_topic)
        return self._construct_fallback_model(clean_topic)

    def _validate_and_sanitize(self, model: ConceptModel, topic: str) -> ConceptModel:
        """
        Sanitize and normalize concept IDs, eliminate duplicate IDs,
        ensure valid difficulties, harmonize learning objectives, and prune phantom references.
        """
        seen_ids: Set[str] = set()
        sanitized_concepts: List[ConceptNode] = []

        for node in (model.concepts or [])[:self.max_concepts]:
            norm_id = normalize_concept_id(node.id)
            if not norm_id or norm_id in seen_ids:
                suffix = 2
                base_id = norm_id or "concept"
                while f"{base_id}_{suffix}" in seen_ids:
                    suffix += 1
                norm_id = f"{base_id}_{suffix}"

            seen_ids.add(norm_id)
            diff = max(1, min(5, int(node.difficulty_level or 1)))

            # Sanitize learning objectives
            sanitized_objs: List[LearningObjective] = []
            for o_idx, obj in enumerate((node.learning_objectives or [])[:self.max_objectives_per_concept]):
                obj_id = obj.objective_id or f"obj_{norm_id}_{o_idx + 1}"
                ev_reqs: List[ExpectedEvidenceRequirement] = []
                for e_idx, ev in enumerate(obj.expected_evidence or []):
                    ev_reqs.append(
                        ExpectedEvidenceRequirement(
                            evidence_id=ev.evidence_id or f"ev_{norm_id}_{o_idx + 1}_{e_idx + 1}",
                            objective_id=obj_id,
                            description=ev.description or f"Demonstrates understanding of {node.name}",
                            evidence_type=ev.evidence_type or EvidenceType.MECHANISM,
                            essential=ev.essential,
                        )
                    )

                sanitized_objs.append(
                    LearningObjective(
                        objective_id=obj_id,
                        concept_id=norm_id,
                        description=obj.description or f"Explain principles of {node.name}",
                        cognitive_action=obj.cognitive_action or CognitiveAction.EXPLAIN,
                        essential=obj.essential,
                        expected_evidence=ev_reqs,
                    )
                )

            # Sanitize constraints
            sanitized_constraints: List[ConceptConstraint] = []
            for c_idx, c in enumerate(node.concept_constraints or []):
                sanitized_constraints.append(
                    ConceptConstraint(
                        constraint_id=c.constraint_id or f"const_{norm_id}_{c_idx + 1}",
                        concept_id=norm_id,
                        rule=c.rule or str(c),
                        constraint_type=c.constraint_type or ConstraintType.INVARIANT,
                        essential=c.essential,
                    )
                )

            # Sanitize misconceptions
            sanitized_misc: List[MisconceptionDefinition] = []
            for m_idx, m in enumerate(node.misconception_definitions or []):
                sanitized_misc.append(
                    MisconceptionDefinition(
                        misconception_id=m.misconception_id or f"misc_{norm_id}_{m_idx + 1}",
                        concept_id=norm_id,
                        description=m.description or str(m),
                        why_it_is_incorrect=m.why_it_is_incorrect or "",
                    )
                )

            sanitized_concepts.append(
                ConceptNode(
                    id=norm_id,
                    name=node.name.strip() if node.name else norm_id.replace("_", " ").title(),
                    definition=node.definition.strip() if node.definition else "",
                    prerequisites=[normalize_concept_id(p) for p in node.prerequisites if normalize_concept_id(p) != norm_id],
                    sub_concepts=list(node.sub_concepts or []),
                    applications=list(node.applications or []),
                    constraints=list(node.constraints or []),
                    common_misconceptions=list(node.common_misconceptions or []),
                    misconception_definitions=sanitized_misc,
                    learning_objectives=sanitized_objs,
                    expected_evidence=list(node.expected_evidence or []),
                    concept_constraints=sanitized_constraints,
                    edge_cases=list(node.edge_cases or []),
                    difficulty_level=diff,
                    generation_confidence=float(node.generation_confidence or 1.0),
                )
            )

        # Filter out prerequisites that do not exist in the concept set
        valid_id_set = {c.id for c in sanitized_concepts}
        for c in sanitized_concepts:
            c.prerequisites = [p for p in c.prerequisites if p in valid_id_set]

        # If zero concepts extracted, build dynamic fallback
        if not sanitized_concepts:
            return self._construct_fallback_model(topic)

        # Sanitize relationships
        sanitized_rels: List[ConceptRelationship] = []
        for rel in (model.relationships or [])[:self.max_relationships]:
            src = normalize_concept_id(rel.source_concept_id)
            tgt = normalize_concept_id(rel.target_concept_id)
            if src in valid_id_set and tgt in valid_id_set and src != tgt:
                sanitized_rels.append(
                    ConceptRelationship(
                        source_concept_id=src,
                        target_concept_id=tgt,
                        relation_type=rel.relation_type or "PREREQUISITE_OF",
                        description=rel.description or "",
                    )
                )

        return ConceptModel(
            topic=topic,
            topic_id=f"topic_{normalize_concept_id(topic)}",
            topic_title=topic.title(),
            topic_description=f"Structured concept architecture for {topic}.",
            concepts=sanitized_concepts,
            relationships=sanitized_rels,
            validation_status=ValidationStatus.VALID,
            metadata=dict(model.metadata or {}),
        )

    def _construct_fallback_model(self, topic: str) -> ConceptModel:
        """
        Dynamically constructs a generic, topic-independent 4-tier ConceptModel for any domain.
        Tier 1: Fundamentals (Diff 1)
        Tier 2: Mechanism & Processes (Diff 2)
        Tier 3: Applications & Invariants (Diff 3)
        Tier 4: Constraints & Boundary Conditions (Diff 4)
        """
        slug = normalize_concept_id(topic)

        # 1. Fundamentals
        c1_id = f"{slug}_foundation"
        c1 = ConceptNode(
            id=c1_id,
            name=f"{topic} Fundamentals",
            definition=f"Foundational terminology, core definitions, and primary properties of {topic}.",
            prerequisites=[],
            difficulty_level=1,
            learning_objectives=[
                LearningObjective(
                    objective_id=f"obj_{c1_id}_def",
                    concept_id=c1_id,
                    description=f"Define the foundational concepts and terminology of {topic}",
                    cognitive_action=CognitiveAction.DEFINE,
                    essential=True,
                    expected_evidence=[
                        ExpectedEvidenceRequirement(
                            evidence_id=f"ev_{c1_id}_def",
                            objective_id=f"obj_{c1_id}_def",
                            description=f"Articulates core definition and primary purpose of {topic}",
                            evidence_type=EvidenceType.DEFINITION,
                            essential=True,
                        )
                    ],
                )
            ],
            concept_constraints=[
                ConceptConstraint(
                    constraint_id=f"const_{c1_id}_1",
                    concept_id=c1_id,
                    rule=f"Core definitions of {topic} must be established before analyzing processes",
                    constraint_type=ConstraintType.PREREQUISITE_CONDITION,
                    essential=True,
                )
            ],
            common_misconceptions=[f"Confusing foundational definitions of {topic} with superficial rules."],
            misconception_definitions=[
                MisconceptionDefinition(
                    misconception_id=f"misc_{c1_id}_1",
                    concept_id=c1_id,
                    description=f"Confusing foundational definitions of {topic} with superficial rules.",
                    why_it_is_incorrect="Superficial rules lack structural causal power.",
                )
            ],
        )

        # 2. Mechanism
        c2_id = f"{slug}_mechanism"
        c2 = ConceptNode(
            id=c2_id,
            name=f"{topic} Mechanism & Principles",
            definition=f"The underlying mechanism, causal interactions, or operational workflow of {topic}.",
            prerequisites=[c1_id],
            difficulty_level=2,
            learning_objectives=[
                LearningObjective(
                    objective_id=f"obj_{c2_id}_mech",
                    concept_id=c2_id,
                    description=f"Explain the primary mechanism and operational steps of {topic}",
                    cognitive_action=CognitiveAction.EXPLAIN,
                    essential=True,
                    expected_evidence=[
                        ExpectedEvidenceRequirement(
                            evidence_id=f"ev_{c2_id}_mech",
                            objective_id=f"obj_{c2_id}_mech",
                            description=f"Traces the causal mechanism or step-by-step process of {topic}",
                            evidence_type=EvidenceType.MECHANISM,
                            essential=True,
                        )
                    ],
                )
            ],
            concept_constraints=[
                ConceptConstraint(
                    constraint_id=f"const_{c2_id}_1",
                    concept_id=c2_id,
                    rule=f"State transitions or causal steps in {topic} must preserve structural consistency",
                    constraint_type=ConstraintType.INVARIANT,
                    essential=True,
                )
            ],
            common_misconceptions=[f"Assuming {topic} operates without state or ordered transitions."],
            misconception_definitions=[
                MisconceptionDefinition(
                    misconception_id=f"misc_{c2_id}_1",
                    concept_id=c2_id,
                    description=f"Assuming {topic} operates without state or ordered transitions.",
                    why_it_is_incorrect=f"{topic} fundamentally relies on defined sequence and state invariants.",
                )
            ],
        )

        # 3. Application
        c3_id = f"{slug}_application"
        c3 = ConceptNode(
            id=c3_id,
            name=f"{topic} Applications & Invariants",
            definition=f"Applying {topic} to concrete problems and preserving core invariants in practical contexts.",
            prerequisites=[c2_id],
            difficulty_level=3,
            learning_objectives=[
                LearningObjective(
                    objective_id=f"obj_{c3_id}_apply",
                    concept_id=c3_id,
                    description=f"Apply {topic} to solve standard problems and preserve system invariants",
                    cognitive_action=CognitiveAction.APPLY,
                    essential=True,
                    expected_evidence=[
                        ExpectedEvidenceRequirement(
                            evidence_id=f"ev_{c3_id}_apply",
                            objective_id=f"obj_{c3_id}_apply",
                            description=f"Demonstrates practical application of {topic} to problem scenarios",
                            evidence_type=EvidenceType.APPLICATION,
                            essential=True,
                        )
                    ],
                )
            ],
            concept_constraints=[
                ConceptConstraint(
                    constraint_id=f"const_{c3_id}_1",
                    concept_id=c3_id,
                    rule=f"System invariants must hold throughout application of {topic}",
                    constraint_type=ConstraintType.INVARIANT,
                    essential=True,
                )
            ],
        )

        # 4. Constraints & Edge Cases
        c4_id = f"{slug}_edge_cases"
        c4 = ConceptNode(
            id=c4_id,
            name=f"{topic} Constraints & Edge Cases",
            definition=f"Boundary conditions, failure modes, assumptions, and limits of {topic}.",
            prerequisites=[c3_id],
            difficulty_level=4,
            learning_objectives=[
                LearningObjective(
                    objective_id=f"obj_{c4_id}_edge",
                    concept_id=c4_id,
                    description=f"Analyze boundary conditions, failure modes, and limiting constraints of {topic}",
                    cognitive_action=CognitiveAction.ANALYZE,
                    essential=False,
                    expected_evidence=[
                        ExpectedEvidenceRequirement(
                            evidence_id=f"ev_{c4_id}_edge",
                            objective_id=f"obj_{c4_id}_edge",
                            description=f"Identifies assumptions and constraints under which {topic} fails or degrades",
                            evidence_type=EvidenceType.REASONING,
                            essential=True,
                        )
                    ],
                )
            ],
            concept_constraints=[
                ConceptConstraint(
                    constraint_id=f"const_{c4_id}_1",
                    concept_id=c4_id,
                    rule=f"Assumptions must be verified before relying on {topic} guarantees",
                    constraint_type=ConstraintType.BOUNDARY_LIMIT,
                    essential=True,
                )
            ],
            edge_cases=["Empty or zero inputs", "Boundary parameter limits", "Resource exhaustion or degradation"],
        )

        rels = [
            ConceptRelationship(
                source_concept_id=c1_id,
                target_concept_id=c2_id,
                relation_type="PREREQUISITE_OF",
                description=f"{topic} fundamentals are prerequisite to understanding its mechanism.",
            ),
            ConceptRelationship(
                source_concept_id=c2_id,
                target_concept_id=c3_id,
                relation_type="PREREQUISITE_OF",
                description=f"Understanding mechanism enables correct practical application.",
            ),
            ConceptRelationship(
                source_concept_id=c3_id,
                target_concept_id=c4_id,
                relation_type="PREREQUISITE_OF",
                description=f"Application experience leads to constraint and edge case analysis.",
            ),
        ]

        return ConceptModel(
            topic=topic,
            topic_id=f"topic_{slug}",
            topic_title=topic.title(),
            topic_description=f"Topic knowledge model for {topic}.",
            concepts=[c1, c2, c3, c4],
            relationships=rels,
            validation_status=ValidationStatus.VALID,
            metadata={"source": "dynamic_fallback"},
        )
