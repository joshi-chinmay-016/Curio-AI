"""
Topic Planning and Comprehensive Concept Coverage for Curio AI (Phase 5).
Represents the topic's knowledge decomposition, coverage states, and mastery progress.
Distinguishes coverage (exploration/assessment status) from mastery (demonstrated understanding).
"""
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from backend.app.ai.schemas import (
    ConceptCoverageItem,
    ConceptModel,
    ConceptNode,
    ConceptState,
    CoverageStatus,
    LearnerModel,
    LearningObjective,
    TopicPlan,
    ValidationStatus,
)

logger = logging.getLogger("curio.ai.topic_plan")

# Re-export for convenience
__all__ = [
    "CoverageStatus",
    "ConceptCoverageItem",
    "TopicPlan",
    "TopicPlanner",
]



class TopicPlanner:
    """
    Deterministic Topic Planner for Curio AI.
    Constructs, validates, and manages topic coverage and concept plans without external network calls.
    Decouples coverage derivation from mastery scoring, ensuring deterministic and testable behavior.
    """

    @staticmethod
    def derive_coverage_status(state: Optional[ConceptState]) -> CoverageStatus:
        """
        Derive the exact CoverageStatus from a ConceptState:
        - NEEDS_REVIEW: If there is an unresolved gap or active misconception.
        - MASTERED: If mastery >= 0.75 and at least one substantive evidence count without active gaps/misconceptions.
        - IN_PROGRESS: If there have been attempts/evidence or partial mastery > 0.0.
        - UNASSESSED: No substantive evidence or attempts.
        """
        if state is None:
            return CoverageStatus.UNASSESSED

        # 1. Unresolved gaps or active misconceptions take precedence
        if state.unresolved_gap or bool(state.active_misconceptions):
            return CoverageStatus.NEEDS_REVIEW

        # 2. Mastered criteria: sufficient demonstrated evidence and high mastery
        if state.mastery >= 0.75 and (state.evidence_count >= 1 or state.attempt_count >= 2):
            return CoverageStatus.MASTERED

        # 3. In progress: learner has attempted or provided some evidence, but not mastered
        if state.attempt_count > 0 or state.evidence_count > 0 or state.mastery > 0.0:
            return CoverageStatus.IN_PROGRESS

        # 4. Unassessed
        return CoverageStatus.UNASSESSED

    @classmethod
    def build_topic_plan(
        cls,
        concept_model: Optional[ConceptModel],
        learner_model: Optional[LearnerModel] = None,
        topic: str = "",
    ) -> TopicPlan:
        """
        Build a deterministic TopicPlan by combining the structural knowledge decomposition
        from ConceptModel with the evidence-based state from LearnerModel.
        Safely handles missing, empty, or duplicate concepts without throwing exceptions.
        """
        clean_topic = (topic or (concept_model.topic if concept_model else "") or "General Topic").strip()
        topic_title = concept_model.topic_title if concept_model and concept_model.topic_title else clean_topic.title()
        topic_desc = concept_model.topic_description if concept_model and concept_model.topic_description else f"Learning plan for {clean_topic}."
        topic_id = concept_model.topic_id if concept_model and concept_model.topic_id else f"topic_{clean_topic.lower().replace(' ', '_')}"

        # If concept model is missing or has zero concepts, construct a clean foundational plan
        raw_concepts = concept_model.concepts if concept_model and concept_model.concepts else []
        if not raw_concepts:
            raw_concepts = cls._construct_fallback_concepts(clean_topic)

        # Deduplicate and sanitize concept nodes
        seen_ids: Set[str] = set()
        coverage_items: List[ConceptCoverageItem] = []

        for node in raw_concepts:
            raw_id = (node.id or "").strip().lower().replace(" ", "_")
            if not raw_id:
                raw_id = "core_concept"

            if raw_id in seen_ids:
                # Disambiguate duplicate concept IDs safely
                suffix = 2
                while f"{raw_id}_{suffix}" in seen_ids:
                    suffix += 1
                raw_id = f"{raw_id}_{suffix}"

            seen_ids.add(raw_id)
            node_name = node.name.strip() if node.name and node.name.strip() else raw_id.replace("_", " ").title()

            # Retrieve state from learner_model
            c_state: Optional[ConceptState] = None
            if learner_model and learner_model.concepts:
                c_state = learner_model.concepts.get(node.id) or learner_model.concepts.get(raw_id)

            status = cls.derive_coverage_status(c_state)
            mastery = round(float(c_state.mastery), 3) if c_state else 0.0
            evidence_cnt = int(c_state.evidence_count) if c_state else 0
            attempt_cnt = int(c_state.attempt_count) if c_state else 0
            gap = bool(c_state.unresolved_gap) if c_state else False
            misc = list(c_state.active_misconceptions) if c_state and c_state.active_misconceptions else []

            # Clean prerequisites (remove self-references)
            prereqs = [p for p in (node.prerequisites or []) if p and p != raw_id and p != node.id]

            diff = max(1, min(5, int(node.difficulty_level or 1)))

            coverage_items.append(
                ConceptCoverageItem(
                    concept_id=raw_id,
                    name=node_name,
                    importance=getattr(node, "importance", "CORE") or "CORE",
                    difficulty_level=diff,
                    prerequisites=prereqs,
                    sub_concepts=list(node.sub_concepts or []),
                    learning_objectives=list(node.learning_objectives or []),
                    status=status,
                    mastery=mastery,
                    evidence_count=evidence_cnt,
                    attempt_count=attempt_cnt,
                    unresolved_gap=gap,
                    active_misconceptions=misc,
                )
            )

        return TopicPlan(
            topic=clean_topic,
            topic_id=topic_id,
            topic_title=topic_title,
            topic_description=topic_desc,
            concepts=coverage_items,
            validation_status=concept_model.validation_status if concept_model else ValidationStatus.VALID,
        )

    @classmethod
    def _construct_fallback_concepts(cls, topic: str) -> List[ConceptNode]:
        """Construct deterministic fallback concepts for any topic without hardcoding."""
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", topic.strip().lower()).strip("_") or "concept"
        return [
            ConceptNode(
                id=f"{slug}_definition",
                name=f"{topic} Core Definition",
                definition=f"Foundational definition and core premise of {topic}.",
                prerequisites=[],
                difficulty_level=1,
            ),
            ConceptNode(
                id=f"{slug}_mechanism",
                name=f"{topic} Mechanism & Operation",
                definition=f"Step-by-step mechanism and operations of {topic}.",
                prerequisites=[f"{slug}_definition"],
                difficulty_level=2,
            ),
            ConceptNode(
                id=f"{slug}_application",
                name=f"{topic} Application & Invariants",
                definition=f"Practical application and key invariants of {topic}.",
                prerequisites=[f"{slug}_mechanism"],
                difficulty_level=3,
            ),
            ConceptNode(
                id=f"{slug}_edge_cases",
                name=f"{topic} Edge Cases & Constraints",
                definition=f"Boundary limits, failure modes, and edge cases of {topic}.",
                prerequisites=[f"{slug}_application"],
                difficulty_level=4,
            ),
        ]
