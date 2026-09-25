"""
Dynamic Concept Model Builder and Graph Utilities for Curio AI.
Generates structured concept graphs, normalizes IDs, validates relationships,
and ensures learning decisions are grounded in concepts rather than hardcoded topics.
"""
import logging
import re
from typing import Dict, List, Optional, Set

from backend.app.ai.prompts.concept_prompts import build_concept_model_prompt
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.schemas import (
    ConceptModel,
    ConceptNode,
    ConceptRelationship,
)

logger = logging.getLogger("curio.ai.concept_model")


def normalize_concept_id(raw_id: str) -> str:
    """Normalize a concept ID into a clean snake_case identifier."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw_id or "").strip().lower()).strip("_")
    return cleaned or "core_concept"


class ConceptModelBuilder:
    """
    Dynamically builds structured ConceptModels from arbitrary topic strings.
    No hardcoded question banks or topic branches.
    """

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider

    def build_model(self, topic: str, context_notes: str = "") -> ConceptModel:
        """
        Build and validate a ConceptModel for any topic.
        Guaranteed to return a well-formed model.
        """
        clean_topic = (topic or "").strip() or "General Knowledge"
        prompt = build_concept_model_prompt(clean_topic, context_notes)

        try:
            raw_model: ConceptModel = self.provider.generate_structured(prompt, ConceptModel)
            return self._validate_and_sanitize(raw_model, clean_topic)
        except Exception as e:
            logger.warning(
                "ConceptModel structured generation failed for topic '%s' (%s: %s); constructing dynamic fallback model.",
                clean_topic,
                type(e).__name__,
                str(e),
            )
            return self._construct_fallback_model(clean_topic)

    def _validate_and_sanitize(self, model: ConceptModel, topic: str) -> ConceptModel:
        """
        Sanitize and normalize concept IDs, eliminate duplicate IDs,
        remove invalid prerequisites and self-loops, and ensure valid difficulties.
        """
        seen_ids: Set[str] = set()
        sanitized_concepts: List[ConceptNode] = []

        for node in model.concepts:
            norm_id = normalize_concept_id(node.id)
            if not norm_id or norm_id in seen_ids:
                # Handle duplicate or empty ID by appending suffix
                suffix = 2
                base_id = norm_id or "concept"
                while f"{base_id}_{suffix}" in seen_ids:
                    suffix += 1
                norm_id = f"{base_id}_{suffix}"

            seen_ids.add(norm_id)
            diff = max(1, min(5, int(node.difficulty_level or 1)))

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
                    edge_cases=list(node.edge_cases or []),
                    difficulty_level=diff,
                )
            )

        # Filter out prerequisites that do not exist in the concept set
        valid_id_set = {c.id for c in sanitized_concepts}
        for c in sanitized_concepts:
            c.prerequisites = [p for p in c.prerequisites if p in valid_id_set]

        # If LLM returned zero concepts, build fallback
        if not sanitized_concepts:
            return self._construct_fallback_model(topic)

        # Sanitize relationships
        sanitized_rels: List[ConceptRelationship] = []
        for rel in model.relationships:
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
            concepts=sanitized_concepts,
            relationships=sanitized_rels,
            metadata=dict(model.metadata or {}),
        )

    def _construct_fallback_model(self, topic: str) -> ConceptModel:
        """
        Dynamically construct a baseline 4-tier concept model for any arbitrary topic.
        Never relies on hardcoded topic branches like Binary Search or FastAPI.
        """
        slug = normalize_concept_id(topic)
        c1 = ConceptNode(
            id=f"{slug}_foundation",
            name=f"{topic} Fundamentals",
            definition=f"Foundational concepts, terms, and core properties of {topic}.",
            prerequisites=[],
            difficulty_level=1,
            common_misconceptions=[f"Confusing foundational principles of {topic} with superficial rules."],
        )
        c2 = ConceptNode(
            id=f"{slug}_mechanism",
            name=f"{topic} Mechanism",
            definition=f"The step-by-step mechanism and underlying process governing {topic}.",
            prerequisites=[f"{slug}_foundation"],
            difficulty_level=2,
            common_misconceptions=[f"Assuming {topic} operates without state or order."],
        )
        c3 = ConceptNode(
            id=f"{slug}_application",
            name=f"{topic} Applications & Invariants",
            definition=f"Applying {topic} to concrete problems while preserving essential invariants.",
            prerequisites=[f"{slug}_mechanism"],
            difficulty_level=3,
        )
        c4 = ConceptNode(
            id=f"{slug}_edge_cases",
            name=f"{topic} Constraints & Edge Cases",
            definition=f"Boundary conditions, failure modes, and performance limits of {topic}.",
            prerequisites=[f"{slug}_application"],
            difficulty_level=4,
            edge_cases=["Empty inputs", "Malformed parameters", "Concurrency or resource limits"],
        )

        rels = [
            ConceptRelationship(
                source_concept_id=f"{slug}_foundation",
                target_concept_id=f"{slug}_mechanism",
                relation_type="PREREQUISITE_OF",
                description=f"{topic} fundamentals are required to understand its mechanism.",
            ),
            ConceptRelationship(
                source_concept_id=f"{slug}_mechanism",
                target_concept_id=f"{slug}_application",
                relation_type="PREREQUISITE_OF",
                description=f"Understanding the mechanism enables proper application.",
            ),
            ConceptRelationship(
                source_concept_id=f"{slug}_application",
                target_concept_id=f"{slug}_edge_cases",
                relation_type="PREREQUISITE_OF",
                description=f"Practical application leads to edge-case and constraint handling.",
            ),
        ]

        return ConceptModel(
            topic=topic,
            concepts=[c1, c2, c3, c4],
            relationships=rels,
            metadata={"source": "dynamic_fallback"},
        )
