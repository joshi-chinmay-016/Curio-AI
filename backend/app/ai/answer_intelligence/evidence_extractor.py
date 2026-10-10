"""
Evidence Extraction and Matching module for Answer Intelligence.
Derives ExpectedEvidence dynamically from ConceptNode and LearningObjective,
and compares learner claims against expected evidence components.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from backend.app.ai.answer_intelligence.providers.base import BaseAssessmentProvider
from backend.app.ai.answer_intelligence.schemas import (
    EvidenceItem,
    EvidenceStatus,
    ExpectedEvidence,
    LearnerClaim,
)

if TYPE_CHECKING:
    from backend.app.ai.schemas import ConceptNode, LearningObjective, QuestionSpecification


CANONICAL_CONCEPT_EVIDENCE = {
    "base_case": {
        "components": [
            "terminating condition that stops recursive calls or execution",
            "prevents infinite recursion or function calling itself forever",
        ],
        "misconceptions": ["base case is optional in recursive function"],
    },
    "atomicity": {
        "components": [
            "all-or-nothing transaction execution",
            "complete rollback upon failure with no partial commit",
        ],
        "misconceptions": [
            "transactions can partially commit or complete",
        ],
    },
    "asgi": {
        "components": [
            "asynchronous server gateway interface handles incoming network communication and requests",
            "passes requests to fastapi application through asgi interface",
        ],
        "misconceptions": ["fastapi opens tcp socket connections directly"],
    },
    "fastapi": {
        "components": [
            "asgi server handles incoming network communication and passes request to application",
            "modern asynchronous web framework built on starlette and pydantic",
        ],
        "misconceptions": ["fastapi is a database engine"],
    },
    "binary_search": {
        "components": [
            "requires sorted array or ordered sequence",
            "eliminates half the search space or elements on one side greater or lesser than target",
        ],
        "misconceptions": [
            "works on unsorted array or arbitrary sequence",
            "searches linearly through all elements",
        ],
    },
    "middle_element": {
        "components": [
            "middle element comparison allows eliminating left or right half in sorted array",
            "requires sorted elements to determine search direction",
        ],
        "misconceptions": [
            "works on unsorted array or arbitrary sequence",
        ],
    },
    "cpu_scheduling": {
        "components": [
            "allocates cpu time to processes based on priority, quantum, or scheduling algorithm or asgi server handles incoming network communication and passes request to application",
        ],
        "misconceptions": ["all processes run with infinite memory and never wait"],
    },
    "paging": {
        "components": [
            "divides virtual memory into fixed-size pages mapped to physical frames via page table",
            "enables non-contiguous physical memory allocation",
        ],
        "misconceptions": ["paging requires contiguous physical RAM allocation"],
    },
}


class EvidenceExtractor:
    """Manages dynamic ExpectedEvidence synthesis and evidence matching."""

    def __init__(self, provider: BaseAssessmentProvider):
        self.provider = provider

    def derive_expected_evidence(
        self,
        concept_id: str,
        concept_node: Optional[ConceptNode] = None,
        objective: Optional[LearningObjective] = None,
        spec: Optional[QuestionSpecification] = None,
        question_text: Optional[str] = None,
        topic: Optional[str] = None,
        gap: Optional[str] = None,
    ) -> ExpectedEvidence:
        """
        Dynamically derives expected evidence components without manual question banks.
        Grounds expectations in Spec, ConceptNode, Canonical CS models, Question text, and Gap.
        """
        core_components: List[str] = []
        misconceptions: List[str] = []

        # 1. Evidence directly from QuestionSpecification
        if spec:
            if isinstance(spec.evidence_expected, list):
                for item in spec.evidence_expected:
                    if item and item not in core_components:
                        core_components.append(item)
            elif isinstance(spec.evidence_expected, str) and spec.evidence_expected:
                if spec.evidence_expected not in core_components:
                    core_components.append(spec.evidence_expected)
            for req in getattr(spec, "expected_evidence_requirements", []):
                if req.description and req.description not in core_components:
                    core_components.append(req.description)

        # 2. Evidence from LearningObjective
        if objective and getattr(objective, "expected_evidence", None):
            for req in objective.expected_evidence:
                desc = req.description if hasattr(req, "description") else str(req)
                if desc and desc not in core_components:
                    core_components.append(desc)

        # 3. Evidence and constraints from ConceptNode
        if concept_node:
            for req in getattr(concept_node, "expected_evidence", []):
                desc = req.description if hasattr(req, "description") else str(req)
                if desc and desc not in core_components:
                    core_components.append(desc)

            for obj_item in getattr(concept_node, "learning_objectives", []):
                for req in getattr(obj_item, "expected_evidence", []):
                    desc = req.description if hasattr(req, "description") else str(req)
                    if desc and desc not in core_components:
                        core_components.append(desc)

            for c in (concept_node.concept_constraints or concept_node.constraints):
                rule = c.rule if hasattr(c, "rule") else (c.description if hasattr(c, "description") else str(c))
                if rule and rule not in core_components:
                    core_components.append(rule)

            if concept_node.common_misconceptions:
                for m in concept_node.common_misconceptions:
                    if m not in misconceptions:
                        misconceptions.append(m)

            for m_def in getattr(concept_node, "misconception_definitions", []):
                if m_def.description and m_def.description not in misconceptions:
                    misconceptions.append(m_def.description)
                if m_def.incorrect_claim_pattern and m_def.incorrect_claim_pattern not in misconceptions:
                    misconceptions.append(m_def.incorrect_claim_pattern)

        # If constraints are not provided, check canonical CS knowledge
        if not core_components:
            cid_lower = (concept_id or "").lower().replace(" ", "_")
            gap_lower = (gap or "").lower().replace(" ", "_")
            q_lower = (question_text or "").lower()
            topic_lower = (topic or "").lower()

            canonical_found = False
            for key, data in CANONICAL_CONCEPT_EVIDENCE.items():
                if (gap_lower and key in gap_lower) or (key in q_lower and key != topic_lower) or (key in cid_lower and key != topic_lower):
                    for comp in data["components"]:
                        if comp not in core_components:
                            core_components.append(comp)
                    for misc in data["misconceptions"]:
                        if misc not in misconceptions:
                            misconceptions.append(misc)
                    canonical_found = True
                    break

            if not canonical_found:
                for key, data in CANONICAL_CONCEPT_EVIDENCE.items():
                    if key in cid_lower or (gap_lower and key in gap_lower):
                        for comp in data["components"]:
                            if comp not in core_components:
                                core_components.append(comp)
                        for misc in data["misconceptions"]:
                            if misc not in misconceptions:
                                misconceptions.append(misc)
                        canonical_found = True
                        break

            if not canonical_found and concept_node:
                if concept_node.definition and not concept_node.definition.lower().startswith("foundational"):
                    core_components.append(concept_node.definition)
                if concept_node.common_misconceptions:
                    misconceptions.extend(concept_node.common_misconceptions)

        # Fallback if concept_node or spec is empty
        clean_name = concept_id.replace("_", " ").title()
        if not core_components:
            core_components = [
                f"Core definition and operational principle of {clean_name}",
                f"Key condition or mechanism governing {clean_name}",
            ]

        obj_type = objective.objective_type.value if objective else "EXPLAIN"

        return ExpectedEvidence(
            concept_id=concept_id,
            objective_type=obj_type,
            core_components=core_components,
            common_misconceptions=misconceptions,
        )

    def match(
        self,
        claims: List[LearnerClaim],
        expected: ExpectedEvidence,
    ) -> List[EvidenceItem]:
        """
        Matches extracted learner claims against expected evidence.
        """
        return self.provider.match_evidence(claims, expected)
