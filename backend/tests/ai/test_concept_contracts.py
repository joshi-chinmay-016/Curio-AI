"""
Unit tests for Milestone D Concept Model, Learning Objective, and Evidence Contracts.
Verifies:
- TopicModel / ConceptModel initialization and validation
- LearningObjective and ExpectedEvidenceRequirement schemas
- ConceptConstraint and MisconceptionDefinition schemas
- CognitiveAction, RelationshipType, and EvidenceType enums
- Backward compatibility with Milestone A-C baseline models
- Model helper queries (objectives, evidence, prerequisite edges, essential objectives)
"""
import pytest
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


def test_topic_model_alias_identity():
    """Verify TopicModel is identical to ConceptModel for complete interoperability."""
    assert TopicModel is ConceptModel
    model = TopicModel(topic="Binary Search")
    assert isinstance(model, ConceptModel)
    assert model.topic == "Binary Search"


def test_backward_compatibility_minimal_instantiation():
    """Verify existing code creating ConceptModel with only baseline fields remains 100% valid."""
    c1 = ConceptNode(
        id="binary_search_core",
        name="Binary Search Algorithm",
        definition="Divide and conquer algorithm searching sorted collections in O(log n).",
        prerequisites=[],
        difficulty_level=2,
    )
    rel = ConceptRelationship(
        source_concept_id="sorted_array",
        target_concept_id="binary_search_core",
        relation_type="PREREQUISITE_OF",
    )
    model = ConceptModel(
        topic="Binary Search",
        concepts=[c1],
        relationships=[rel],
        metadata={"source": "manual"},
    )

    assert model.topic == "Binary Search"
    assert len(model.concepts) == 1
    assert model.concepts[0].id == "binary_search_core"
    assert model.relationships[0].relation_type == "PREREQUISITE_OF"
    assert model.validation_status == ValidationStatus.VALID


def test_rich_milestone_d_concept_model():
    """Verify rich Milestone D model with LearningObjectives, Evidence, and Constraints."""
    ev1 = ExpectedEvidenceRequirement(
        evidence_id="ev_bs_split",
        concept_id="binary_search",
        objective_id="obj_bs_mech",
        description="Explains comparing search key against midpoint and halving the search interval.",
        evidence_type=EvidenceType.MECHANISM,
        essential=True,
        acceptance_criteria="Identifies midpoint comparison and interval reduction.",
    )

    obj1 = LearningObjective(
        objective_id="obj_bs_mech",
        concept_id="binary_search",
        description="Explain how binary search halves the search space at each step.",
        cognitive_action=CognitiveAction.EXPLAIN,
        difficulty=2,
        essential=True,
        expected_evidence=[ev1],
    )

    constraint1 = ConceptConstraint(
        constraint_id="con_sorted_order",
        concept_id="binary_search",
        description="Collection must be sorted according to a total order before search begins.",
        constraint_type=ConstraintType.PREREQUISITE_CONDITION,
    )

    misc1 = MisconceptionDefinition(
        misconception_id="misc_unsorted",
        concept_id="binary_search",
        description="Believing binary search works on unsorted lists by sorting implicitly.",
        why_it_is_incorrect="Binary search does not sort input; unsorted input causes invalid branch decisions.",
        corrective_evidence="Binary search requires pre-sorted data or O(n) search must be used.",
        related_objective_ids=["obj_bs_mech"],
    )

    node = ConceptNode(
        id="binary_search",
        name="Binary Search",
        definition="Logarithmic search algorithm over monotonic sequences.",
        prerequisites=["sorted_sequences"],
        learning_objectives=[obj1],
        expected_evidence=[ev1],
        concept_constraints=[constraint1],
        misconception_definitions=[misc1],
        difficulty_level=2,
    )

    model = TopicModel(
        topic="Binary Search",
        topic_id="top_binary_search",
        topic_title="Binary Search & Monotonic Optimization",
        topic_description="Algorithmic principles of bisection and binary search over collections and functions.",
        subject_area="Algorithms & Data Structures",
        concepts=[node],
        relationships=[
            ConceptRelationship(
                source_concept_id="sorted_sequences",
                target_concept_id="binary_search",
                relation_type=RelationshipType.PREREQUISITE_OF,
                description="Sorting is required for binary search decisions.",
            )
        ],
        learning_objectives=[obj1],
        validation_status=ValidationStatus.VALID,
    )

    # Verification of queries
    assert model.has_concept("binary_search")
    assert model.get_concept("BINARY_SEARCH") is not None
    assert model.get_prerequisites("binary_search") == ["sorted_sequences"]

    objs = model.get_objectives_for_concept("binary_search")
    assert len(objs) == 1
    assert objs[0].objective_id == "obj_bs_mech"
    assert objs[0].cognitive_action == CognitiveAction.EXPLAIN

    ev_reqs = model.get_expected_evidence_for_concept("binary_search")
    assert len(ev_reqs) == 1
    assert ev_reqs[0].evidence_id == "ev_bs_split"
    assert ev_reqs[0].evidence_type == EvidenceType.MECHANISM

    essential_objs = model.get_essential_objectives()
    assert len(essential_objs) == 1
    assert essential_objs[0].essential is True

    edges = model.get_all_prerequisite_edges()
    assert ("sorted_sequences", "binary_search") in edges


def test_serialization_round_trip():
    """Verify full JSON/dict serialization round trip with Pydantic."""
    ev = ExpectedEvidenceRequirement(
        evidence_id="ev_acid_atom",
        concept_id="atomicity",
        description="All operations commit or all roll back.",
        evidence_type=EvidenceType.DEFINITION,
    )
    obj = LearningObjective(
        objective_id="obj_acid_atom",
        concept_id="atomicity",
        description="Define transaction atomicity.",
        cognitive_action=CognitiveAction.DEFINE,
        expected_evidence=[ev],
    )
    c = ConceptNode(
        id="atomicity",
        name="Atomicity",
        definition="All-or-nothing guarantee.",
        learning_objectives=[obj],
    )
    model = ConceptModel(
        topic="DBMS Transactions",
        concepts=[c],
        learning_objectives=[obj],
    )

    raw_dict = model.model_dump()
    assert raw_dict["topic"] == "DBMS Transactions"
    assert raw_dict["concepts"][0]["learning_objectives"][0]["cognitive_action"] == "DEFINE"

    # Reconstitute from dict
    reconstituted = ConceptModel.model_validate(raw_dict)
    assert reconstituted.topic == "DBMS Transactions"
    assert reconstituted.concepts[0].learning_objectives[0].cognitive_action == CognitiveAction.DEFINE
    assert reconstituted.concepts[0].learning_objectives[0].expected_evidence[0].evidence_id == "ev_acid_atom"
