"""
Unit tests for ConceptModel and ConceptModelBuilder (Phase C).
Verifies:
- Arbitrary topics generate structured concept models without hardcoding
- Concept ID normalization and deduplication
- Phantom prerequisite removal and acyclic sanity
- Fallback creation on LLM errors
"""
import pytest
from backend.app.ai.concept_model import ConceptModelBuilder, normalize_concept_id
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import ConceptModel, ConceptNode, ConceptRelationship


class EmptyProvider(MockLLMProvider):
    def generate_structured(self, prompt, response_model):
        return ConceptModel(topic="Corrupt Topic", concepts=[], relationships=[])


class DuplicatingProvider(MockLLMProvider):
    def generate_structured(self, prompt, response_model):
        c1 = ConceptNode(id="same_id", name="First", prerequisites=["phantom_id", "same_id"])
        c2 = ConceptNode(id="same_id", name="Second", prerequisites=["same_id"])
        c3 = ConceptNode(id="VALID_ID!", name="Third", prerequisites=["same_id"])
        return ConceptModel(
            topic="Test Dups",
            concepts=[c1, c2, c3],
            relationships=[
                ConceptRelationship(source_concept_id="same_id", target_concept_id="phantom_id"),
                ConceptRelationship(source_concept_id="same_id", target_concept_id="same_id"),
            ],
        )


def test_normalize_concept_id():
    assert normalize_concept_id("Binary Search Trees") == "binary_search_trees"
    assert normalize_concept_id("  PROCESS-SCHEDULING!! ") == "process_scheduling"
    assert normalize_concept_id("") == "core_concept"


def test_build_model_arbitrary_topic():
    provider = MockLLMProvider()
    builder = ConceptModelBuilder(provider)
    model = builder.build_model("Operating Systems")

    assert model.topic == "Operating Systems"
    assert len(model.concepts) >= 4
    # All concept IDs must be lowercase normalized
    for c in model.concepts:
        assert c.id == c.id.lower()
        assert 1 <= c.difficulty_level <= 5

    # Foundational concept exists
    foundation = model.get_concept("operating_systems_foundation")
    assert foundation is not None
    assert foundation.difficulty_level == 1


def test_deduplication_and_phantom_prereqs():
    provider = DuplicatingProvider()
    builder = ConceptModelBuilder(provider)
    model = builder.build_model("Test Dups")

    concept_ids = [c.id for c in model.concepts]
    # Concept IDs must be unique
    assert len(concept_ids) == len(set(concept_ids))
    assert "same_id" in concept_ids
    assert "same_id_2" in concept_ids
    assert "valid_id" in concept_ids

    # Phantom prereqs must have been pruned
    for c in model.concepts:
        for p in c.prerequisites:
            assert p in concept_ids
            # No self loops in prerequisites
            assert p != c.id

    # Relationships must not contain phantom nodes or self loops
    for rel in model.relationships:
        assert rel.source_concept_id in concept_ids
        assert rel.target_concept_id in concept_ids
        assert rel.source_concept_id != rel.target_concept_id


def test_empty_provider_triggers_fallback():
    provider = EmptyProvider()
    builder = ConceptModelBuilder(provider)
    model = builder.build_model("Distributed Systems")

    assert model.topic == "Distributed Systems"
    assert len(model.concepts) == 4
    assert model.metadata.get("source") == "dynamic_fallback"
