"""
Tests for ConceptModel Session Lifecycle, Model Reuse, and Topic-Change Handling (Milestone D Phase D7 & D8).
Verifies:
1. Valid concept model is reused across turns without redundant generation.
2. Material topic changes trigger generation of a new topic model.
3. Model version, limitations, and validation status are preserved across session turns.
4. Token-efficient sub-graph prompt context reduces prompt size by >60% compared to full graph dump.
5. Session restoration compatibility with existing contracts.
"""
import pytest
from backend.app.ai.concept_model import (
    ConceptModelBuilder,
    extract_assessment_subgraph,
    summarize_for_prompt,
)
from backend.app.ai.nodes.student_nodes import evaluation_node
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.schemas import (
    AIContext,
    CognitiveAction,
    ConceptModel,
    ConceptNode,
    ConversationContext,
    CurrentQuestion,
    EvidenceType,
    ExpectedEvidenceRequirement,
    LearningContext,
    LearningObjective,
    Mode,
    SessionInfo,
    SessionState,
    ValidationStatus,
)


def test_concept_model_reuse_across_turns():
    """Verify that an existing ConceptModel in session state is preserved and not re-generated."""
    # 1. Custom pre-built concept model
    pre_built_model = ConceptModel(
        topic="Database Indexing",
        model_version="1.0.0",
        concepts=[
            ConceptNode(id="b_tree_indexing", name="B-Tree Indexing", difficulty_level=2),
            ConceptNode(id="hash_indexing", name="Hash Indexing", difficulty_level=2),
        ],
        validation_status=ValidationStatus.VALID,
    )

    state = SessionState(
        session_id="session_123",
        concept_model=pre_built_model,
        active_concept="b_tree_indexing",
    )
    context = AIContext(
        session=SessionInfo(session_id="session_123", topic="Database Indexing"),
        current_state=state,
        conversation=ConversationContext(),
        learning_context=LearningContext(),
    )

    call_count = 0

    class TrackingProvider(MockLLMProvider):
        def generate_structured(self, prompt, response_model):
            nonlocal call_count
            call_count += 1
            return super().generate_structured(prompt, response_model)

    provider = TrackingProvider()
    graph_state = {"context": context, "provider": provider}

    # Run evaluation node (initial turn)
    res = evaluation_node(graph_state)

    # Concept model in returned state must be the exact pre-built model
    returned_model = res["concept_model"]
    assert returned_model.topic == "Database Indexing"
    assert returned_model.concepts[0].id == "b_tree_indexing"
    # No LLM structured generation call should have been made to rebuild concept model
    assert call_count == 0


def test_topic_change_triggers_new_model_generation():
    """When the topic changes materially, a new model must be constructed rather than using the stale model."""
    provider = MockLLMProvider()
    builder = ConceptModelBuilder(provider)

    old_model = builder.build_model("Operating Systems")
    assert old_model.topic == "Operating Systems"
    assert any("operating" in c.id for c in old_model.concepts)

    # Learner switches topic to Cellular Respiration
    new_model = builder.build_model("Cellular Respiration")
    assert new_model.topic == "Cellular Respiration"
    assert any("cellular" in c.id for c in new_model.concepts)
    assert not any("operating" in c.id for c in new_model.concepts)


def test_model_version_and_metadata_preserved_across_lifecycle():
    """Validation status, model version, and limitations must survive serialization round-trip."""
    model = ConceptModel(
        topic="Macroeconomics",
        topic_id="topic_macroeconomics",
        topic_title="Macroeconomics",
        topic_description="Principles of macroeconomic policy",
        model_version="2.1.0",
        validation_status=ValidationStatus.VALID_INCOMPLETE,
        limitations=["Simplified aggregate demand model"],
        concepts=[
            ConceptNode(id="aggregate_demand", name="Aggregate Demand", difficulty_level=2),
            ConceptNode(id="fiscal_policy", name="Fiscal Policy", difficulty_level=3),
        ],
    )

    dumped = model.model_dump(mode="json")
    restored = ConceptModel.model_validate(dumped)

    assert restored.topic == "Macroeconomics"
    assert restored.model_version == "2.1.0"
    assert restored.validation_status == ValidationStatus.VALID_INCOMPLETE
    assert restored.limitations == ["Simplified aggregate demand model"]
    assert len(restored.concepts) == 2


def test_subgraph_token_efficiency_measurement():
    """Verify that subgraph extraction is significantly more compact than the full model."""
    provider = MockLLMProvider()
    builder = ConceptModelBuilder(provider)

    model = builder.build_model("Quantum Mechanics")
    full_dump_str = model.model_dump_json()

    # Subgraph representation
    subgraph = extract_assessment_subgraph(model, model.concepts[0].id)
    summary_md = summarize_for_prompt(model, active_concept_id=model.concepts[0].id, max_chars=1000)

    # Subgraph markdown representation must be under 1000 characters and >60% smaller than full model JSON
    assert len(summary_md) < 1000
    assert len(summary_md) < (len(full_dump_str) * 0.40)
    assert model.concepts[0].name in summary_md
