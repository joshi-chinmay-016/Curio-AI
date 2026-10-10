"""
Dynamic Prompt Augmentation Module for Curio AI (Milestone B).
Transforms structured LearningAssessment evidence into clean, structured context
for the question and response generation layer without exposing hidden chain-of-thought.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from pydantic import BaseModel, Field

from backend.app.ai.answer_intelligence.schemas import (
    AssessmentIntent,
    CorrectnessLevel,
    EvidenceStatus,
    LearningAssessment,
    RelevanceLevel,
)

if TYPE_CHECKING:
    from backend.app.ai.schemas import AIContext, LearningDecision


class DynamicPromptContext(BaseModel):
    """
    Structured context passed to prompt and generation templates.
    Strictly structured evidence only; no hidden chain-of-thought.
    """
    active_concept: str
    learner_intent: str
    relevance_level: str
    relevance_score: float
    correctness_level: str
    completeness_level: str
    supported_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    unresolved_gap: Optional[str] = None
    confidence: float = 0.90
    recommended_strategy: str = "PROBE_UNDERSTANDING"
    difficulty: int = 1
    teacher_intervention_gap: Optional[str] = None
    prompt_instruction: str = ""
    active_objective_description: Optional[str] = None
    concept_subgraph_summary: Optional[str] = None

    def to_prompt_section(self) -> str:
        """Renders cleanly formatted structured context for LLM prompt templates."""
        supp_str = "; ".join(self.supported_evidence) if self.supported_evidence else "None yet demonstrated"
        miss_str = "; ".join(self.missing_evidence) if self.missing_evidence else "None identified"
        misc_str = "; ".join(self.misconceptions) if self.misconceptions else "None detected"

        lines = [
            "STRUCTURED LEARNER ASSESSMENT CONTEXT (Use to guide question phrasing):",
            f"- Target Concept: {self.active_concept}",
            f"- Learner Intent: {self.learner_intent}",
            f"- Semantic Relevance: {self.relevance_level} (score: {self.relevance_score:.2f})",
            f"- Demonstrated Understanding: {supp_str}",
            f"- Missing / Unproven Concepts: {miss_str}",
            f"- Active Misconceptions: {misc_str}",
            f"- Assessment Confidence: {self.confidence:.2f}",
        ]
        if self.active_objective_description:
            lines.append(f"- Active Learning Objective: {self.active_objective_description}")
        if self.concept_subgraph_summary:
            lines.append(f"- Concept Context: {self.concept_subgraph_summary}")
        if self.teacher_intervention_gap:
            lines.append(f"- Active Teacher Gap: {self.teacher_intervention_gap}")
        if self.prompt_instruction:
            lines.append(f"- Phrasing Guidance: {self.prompt_instruction}")

        return "\n".join(lines)


def build_dynamic_prompt_context(
    assessment: Optional[LearningAssessment],
    context: Optional[AIContext] = None,
    decision: Optional[LearningDecision] = None,
    difficulty: int = 1,
) -> DynamicPromptContext:
    """
    Synthesizes a structured DynamicPromptContext from authoritative assessment evidence.
    """
    if assessment is None:
        target = (decision.active_concept if decision else None) or (context.active_concept if context else "general_concept")
        return DynamicPromptContext(
            active_concept=target,
            learner_intent="UNKNOWN",
            relevance_level="UNKNOWN",
            relevance_score=0.0,
            correctness_level="UNKNOWN",
            completeness_level="UNKNOWN",
            difficulty=difficulty,
            prompt_instruction="Ask a foundational question to probe understanding.",
        )

    # Extract supported and missing evidence
    supp_ev = [
        it.expected_description for it in assessment.evidence
        if it.status in (EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIALLY_SUPPORTED)
    ]
    miss_ev = [
        it.expected_description for it in assessment.evidence
        if it.status == EvidenceStatus.MISSING
    ]
    if not miss_ev and assessment.missing_concepts:
        miss_ev = list(assessment.missing_concepts)

    misc_descriptions = [m.description for m in assessment.misconceptions]

    target_concept = (
        (decision.active_concept if decision else None)
        or (context.active_concept if context else None)
        or "target_concept"
    )

    intervention_gap = None
    if context and hasattr(context, "teacher_intervention") and context.teacher_intervention:
        if getattr(context.teacher_intervention, "active", False):
            intervention_gap = getattr(context.teacher_intervention, "gap", None)

    # Derive clean pedagogical prompt guidance without chain-of-thought
    instruction = ""
    if assessment.misconception_status or misc_descriptions:
        first_misc = misc_descriptions[0] if misc_descriptions else "the flawed assumption"
        probe = f"why {miss_ev[0]} matters" if miss_ev else f"how {target_concept} actually operates"
        instruction = (
            f"Challenge the misconception that '{first_misc}'. "
            f"Do not introduce unrelated concepts. "
            f"Ask one question that probes {probe}."
        )
    elif assessment.correctness == CorrectnessLevel.CONTRADICTORY or assessment.contradictory_claims:
        contra = assessment.contradictory_claims[0] if assessment.contradictory_claims else "the contradiction"
        instruction = (
            f"Address the contradiction in the learner's explanation: '{contra}'. "
            f"Ask one targeted question clarifying how {target_concept} resolves this."
        )
    elif assessment.intent == AssessmentIntent.HELP_REQUEST:
        instruction = (
            f"The learner asked for help with '{target_concept}'. "
            f"Provide a subtle intuitive hint and ask one simple question to help them re-engage."
        )
    elif assessment.intent == AssessmentIntent.CLARIFICATION_REQUEST:
        instruction = (
            f"The learner requested clarification on '{target_concept}'. "
            f"Clarify the specific term concisely in one sentence, then ask them to apply it."
        )
    elif assessment.relevance_level == RelevanceLevel.IRRELEVANT:
        instruction = (
            f"The learner's response was off-topic. "
            f"Gently redirect back to '{target_concept}' with an inviting question."
        )
    elif assessment.correctness in (CorrectnessLevel.PARTIALLY_CORRECT, CorrectnessLevel.INCOMPLETE):
        first_miss = miss_ev[0] if miss_ev else f"the core mechanism of {target_concept}"
        instruction = (
            f"The learner gave a partial explanation. "
            f"Acknowledge what was correct, then ask one question probing the missing concept: '{first_miss}'."
        )
    elif assessment.correctness == CorrectnessLevel.CORRECT:
        instruction = (
            f"The learner demonstrated sound understanding of '{target_concept}'. "
            f"Ask one question exploring a deeper nuance, edge case, or trade-off."
        )
    else:
        instruction = f"Ask one focused question to probe understanding of '{target_concept}'."

    strat = decision.strategy.value if decision and hasattr(decision.strategy, "value") else assessment.recommended_learning_action

    active_obj_desc = None
    subgraph_summary = None
    if context and hasattr(context, "current_state"):
        curr_obj = getattr(context.current_state, "current_objective", None)
        if curr_obj and getattr(curr_obj, "description", None):
            active_obj_desc = curr_obj.description
        c_model = getattr(context.current_state, "concept_model", None)
        if c_model:
            from backend.app.ai.concept_model import summarize_for_prompt
            subgraph_summary = summarize_for_prompt(c_model, active_concept_id=target_concept, max_chars=350)

    return DynamicPromptContext(
        active_concept=target_concept,
        learner_intent=assessment.intent.value,
        relevance_level=assessment.relevance_level.value,
        relevance_score=assessment.relevance_score,
        correctness_level=assessment.correctness.value,
        completeness_level=assessment.completeness.value,
        supported_evidence=supp_ev,
        missing_evidence=miss_ev,
        misconceptions=misc_descriptions,
        unresolved_gap=intervention_gap,
        confidence=assessment.confidence,
        recommended_strategy=strat,
        difficulty=difficulty,
        teacher_intervention_gap=intervention_gap,
        prompt_instruction=instruction,
        active_objective_description=active_obj_desc,
        concept_subgraph_summary=subgraph_summary,
    )
