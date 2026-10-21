"""
Deterministic Question Selection Engine for Curio AI (Adaptive Learning Core v1).
Decides WHAT concept to test next, WHICH pedagogical objective to pursue,
and WHAT difficulty level to set based on the Concept Model and Learner Model.

Principle:
WHAT should the learner understand next? -> Question Selector (Deterministic).
HOW should it be phrased? -> LLM Generator.
"""
import logging
import re
from typing import List, Optional

from backend.app.ai.schemas import (
    ConceptModel,
    ConceptNode,
    CurrentQuestion,
    LearnerModel,
    LearningObjective,
    ObjectiveType,
    QuestionSpecification,
    Strategy,
    TurnEvaluation,
    TurnInterpretation,
)

logger = logging.getLogger("curio.ai.question_selector")


class QuestionSelector:
    """
    Deterministic pedagogical selector.
    Evaluates concept graph dependencies, learner mastery, misconceptions,
    and recent history to formulate a precise QuestionSpecification.
    """

    def select_question_specification(
        self,
        concept_model: ConceptModel,
        learner_model: LearnerModel,
        current_difficulty: int = 1,
        current_objective: Optional[LearningObjective] = None,
        latest_interpretation: Optional[TurnInterpretation] = None,
        latest_evaluation: Optional[TurnEvaluation] = None,
        recent_question_history: Optional[List[str]] = None,
        recent_concept_history: Optional[List[str]] = None,
        interrupted_question: Optional[CurrentQuestion] = None,
        target_concept_override: Optional[str] = None,
        strategy: Optional[Strategy] = None,
        strategy_reason: Optional[str] = None,
        adjust_difficulty: bool = True,
    ) -> QuestionSpecification:
        recent_concepts = recent_concept_history or []
        recent_questions = recent_question_history or []

        # If a specific active concept target is requested (e.g. probing current concept)
        if target_concept_override:
            c_node = concept_model.get_concept(target_concept_override) or ConceptNode(
                id=target_concept_override,
                name=target_concept_override.replace("_", " ").title(),
                difficulty_level=current_difficulty,
            )
            c_state = learner_model.get_or_create_concept(target_concept_override)
            target_diff = (
                self._calculate_next_difficulty(
                    current_difficulty=current_difficulty,
                    concept_node=c_node,
                    concept_state=c_state,
                    latest_evaluation=latest_evaluation,
                )
                if (adjust_difficulty and latest_evaluation is not None)
                else current_difficulty
            )

            # Centralized pedagogical strategy-to-objective resolution
            obj_type, evidence_exp = self._resolve_strategy_objective(
                strategy=strategy,
                concept_node=c_node,
                concept_state=c_state,
                target_difficulty=target_diff,
                latest_evaluation=latest_evaluation,
            )

            reason = (
                strategy_reason.strip()
                if strategy_reason and strategy_reason.strip()
                else f"Probing understanding of '{c_node.name}' at difficulty {target_diff}."
            )
            obj = LearningObjective(
                objective_type=obj_type,
                target_concept=target_concept_override,
                difficulty=target_diff,
                reason=reason,
                evidence_expected=evidence_exp,
            )
            return QuestionSpecification(
                target_concept=target_concept_override,
                learning_objective=obj,
                difficulty=target_diff,
                reason=reason,
                evidence_expected=evidence_exp,
                generation_constraints=[
                    f"Must target concept: {c_node.name}",
                    f"Pedagogical goal: {obj_type.value}",
                    "Do NOT reveal the correct answer",
                    "Ask exactly ONE question in Socratic student voice",
                ],
            )

        # 1. Check for active unresolved misconceptions or gaps
        unresolved_target = self._find_unresolved_gap_or_misconception(concept_model, learner_model)
        if unresolved_target:
            c_node = concept_model.get_concept(unresolved_target)
            node_name = c_node.name if c_node else unresolved_target
            if adjust_difficulty:
                diff = c_node.difficulty_level if c_node else current_difficulty
                # Bounded difficulty change
                diff = max(1, min(current_difficulty, diff))
            else:
                diff = current_difficulty

            c_state = learner_model.get_or_create_concept(unresolved_target)
            target_misc = None
            if c_state.active_misconceptions:
                obj_type = ObjectiveType.RESOLVE_MISCONCEPTION
                target_misc = c_state.active_misconceptions[0]
                reason = f"Active misconception detected on concept '{node_name}': {target_misc}"
                evidence = f"resolves: {target_misc}"
            else:
                obj_type = ObjectiveType.REINFORCE_WEAK_CONCEPT
                reason = f"Knowledge gap detected on concept '{node_name}'."
                evidence = f"Learner demonstrates correct foundational understanding of '{node_name}'."

            obj = LearningObjective(
                objective_type=obj_type,
                target_concept=unresolved_target,
                difficulty=diff,
                reason=reason,
                evidence_expected=evidence,
                success_criteria=target_misc,
            )
            u_node = concept_model.get_concept(unresolved_target)
            u_evidence = None
            u_refs = []
            if u_node:
                from backend.app.ai.document_curriculum import format_concept_evidence
                cm_meta = concept_model.metadata if concept_model and concept_model.metadata else {}
                u_evidence = format_concept_evidence(
                    concept_id=unresolved_target,
                    concept_node=u_node,
                    source_references=getattr(u_node, "source_references", None),
                    expected_doc_id=cm_meta.get("document_id"),
                    expected_doc_version=cm_meta.get("document_version") or cm_meta.get("content_hash"),
                )
                u_refs = list(getattr(u_node, "source_references", []) or [])

            return QuestionSpecification(
                target_concept=unresolved_target,
                learning_objective=obj,
                difficulty=diff,
                reason=reason,
                evidence_expected=evidence,
                generation_constraints=[
                    f"Must target concept: {node_name}",
                    f"Pedagogical goal: {obj_type.value}",
                    "Do NOT reveal the correct answer",
                    "Ask exactly ONE question in Socratic student voice",
                ],
                target_concept_evidence=u_evidence,
                source_references=u_refs,
            )

        # 2. Check for missing prerequisite gaps
        # If learner is trying to learn an advanced concept whose prereqs are weak, steer to prereq
        prereq_target = self._find_unmet_prerequisite(concept_model, learner_model)
        if prereq_target:
            c_node = concept_model.get_concept(prereq_target)
            node_name = c_node.name if c_node else prereq_target
            if adjust_difficulty:
                diff = c_node.difficulty_level if c_node else 1
                diff = max(1, min(diff, current_difficulty))
            else:
                diff = current_difficulty

            p_evidence = None
            p_refs = []
            if c_node:
                from backend.app.ai.document_curriculum import format_concept_evidence
                cm_meta = concept_model.metadata if concept_model and concept_model.metadata else {}
                p_evidence = format_concept_evidence(
                    concept_id=prereq_target,
                    concept_node=c_node,
                    source_references=getattr(c_node, "source_references", None),
                    expected_doc_id=cm_meta.get("document_id"),
                    expected_doc_version=cm_meta.get("document_version") or cm_meta.get("content_hash"),
                )
                p_refs = list(getattr(c_node, "source_references", []) or [])

            obj = LearningObjective(
                objective_type=ObjectiveType.UNDERSTAND_DEFINITION if diff == 1 else ObjectiveType.UNDERSTAND_MECHANISM,
                target_concept=prereq_target,
                difficulty=diff,
                reason=f"Prerequisite concept '{node_name}' has low mastery (<0.60) before advancing.",
                evidence_expected=f"Learner clearly explains the core mechanism and role of '{node_name}'.",
            )
            return QuestionSpecification(
                target_concept=prereq_target,
                learning_objective=obj,
                difficulty=diff,
                reason=obj.reason,
                evidence_expected=obj.evidence_expected,
                generation_constraints=[
                    f"Must target prerequisite concept: {node_name}",
                    f"TABULA RASA: You are a student who does NOT know about '{node_name}' yet! Do NOT name or leak '{node_name}' or any preconditions!",
                    "Curio is an innocent beginner student learning from scratch. Do NOT ask leading pop-quiz questions like 'Does it require X?' or 'Is it arranged in any particular way?'",
                    "Ask the teacher to explain how the mechanism works step-by-step from what they already described",
                    "Do NOT reveal the answer",
                    "Exactly ONE question",
                ],
                target_concept_evidence=p_evidence,
                source_references=p_refs,
            )

        # 3. Determine next concept based on mastery progression
        target_concept_node = self._select_next_concept_node(concept_model, learner_model, recent_concepts)
        c_id = target_concept_node.id
        node_name = target_concept_node.name
        c_state = learner_model.get_or_create_concept(c_id)

        # Determine target difficulty (bounded change: at most +-1)
        if adjust_difficulty and latest_evaluation is not None:
            target_diff = self._calculate_next_difficulty(
                current_difficulty=current_difficulty,
                concept_node=target_concept_node,
                concept_state=c_state,
                latest_evaluation=latest_evaluation,
            )
        else:
            target_diff = current_difficulty

        # Determine pedagogical objective based on strategy (if provided) or curriculum objectives / difficulty
        chosen_lo = None
        if strategy is None and target_concept_node and getattr(target_concept_node, "learning_objectives", None):
            for lo in target_concept_node.learning_objectives:
                if lo.objective_id and lo.objective_id not in c_state.mastered_objectives:
                    chosen_lo = lo
                    break

        if chosen_lo is not None:
            obj_type = chosen_lo.objective_type
            evidence_exp = chosen_lo.evidence_expected or chosen_lo.description
            reason = (
                strategy_reason.strip()
                if strategy_reason and strategy_reason.strip()
                else f"Targeting unmastered learning objective '{chosen_lo.objective_id}' for '{node_name}'."
            )
            obj = chosen_lo.model_copy(update={
                "target_concept": c_id,
                "difficulty": target_diff,
                "reason": reason,
                "evidence_expected": evidence_exp,
            })
        else:
            if strategy is not None:
                obj_type, evidence_exp = self._resolve_strategy_objective(
                    strategy=strategy,
                    concept_node=target_concept_node,
                    concept_state=c_state,
                    target_difficulty=target_diff,
                    latest_evaluation=latest_evaluation,
                )
            else:
                obj_type, evidence_exp = self._determine_objective_type(target_concept_node, c_state, target_diff)

            reason = (
                strategy_reason.strip()
                if strategy_reason and strategy_reason.strip()
                else f"Progressing understanding of '{node_name}' at difficulty {target_diff} based on demonstrated mastery ({c_state.mastery:.2f})."
            )

            obj = LearningObjective(
                objective_type=obj_type,
                target_concept=c_id,
                difficulty=target_diff,
                reason=reason,
                evidence_expected=evidence_exp,
            )

        from backend.app.ai.document_curriculum import format_concept_evidence
        cm_meta = concept_model.metadata if concept_model and concept_model.metadata else {}
        expected_doc_id = cm_meta.get("document_id")
        expected_doc_ver = cm_meta.get("document_version") or cm_meta.get("content_hash")
        targeted_evidence = format_concept_evidence(
            concept_id=c_id,
            concept_node=target_concept_node,
            source_references=getattr(target_concept_node, "source_references", None),
            expected_doc_id=expected_doc_id,
            expected_doc_version=expected_doc_ver,
        )
        node_refs = list(getattr(target_concept_node, "source_references", []) or [])

        constraints = [
            f"Target concept: {node_name}",
            f"Objective: {obj_type.value}",
            f"Difficulty level: {target_diff}",
            "Ground the question in the ongoing conversation",
            "Exactly ONE primary question",
            "Do NOT explain or teach the answer in Student mode",
            "Avoid semantic repetition with recent questions",
        ]
        if targeted_evidence:
            constraints.append("Ground question strictly in verified source evidence for this concept")
        elif expected_doc_id:
            constraints.append("No verified document evidence for this concept; ask from general principles and do NOT claim it came from the document")

        return QuestionSpecification(
            target_concept=c_id,
            learning_objective=obj,
            difficulty=target_diff,
            reason=reason,
            evidence_expected=evidence_exp,
            generation_constraints=constraints,
            target_concept_evidence=targeted_evidence,
            source_references=node_refs,
        )

    def _find_unresolved_gap_or_misconception(
        self, concept_model: ConceptModel, learner_model: LearnerModel
    ) -> Optional[str]:
        # Prioritize gaps explicitly in unresolved_gaps
        for gid in learner_model.unresolved_gaps:
            if gid in [c.id for c in concept_model.concepts] or gid:
                return gid

        # Check concepts with active misconceptions
        for cid, state in learner_model.concepts.items():
            if state.unresolved_gap or state.active_misconceptions:
                return cid

        return None

    def _find_unmet_prerequisite(
        self, concept_model: ConceptModel, learner_model: LearnerModel
    ) -> Optional[str]:
        """
        Identify if any concept that has attempted turns has an unmastered prerequisite (< 0.60 mastery).
        Recursively finds the most foundational unmet prerequisite.
        """
        def _get_deepest_unmet(cid: str, visited: set) -> Optional[str]:
            if cid in visited:
                return None
            visited.add(cid)
            node = concept_model.get_concept(cid)
            if not node:
                return None
            for pid in node.prerequisites:
                deepest = _get_deepest_unmet(pid, visited)
                if deepest:
                    return deepest
                p_state = learner_model.get_or_create_concept(pid)
                if p_state.mastery < 0.60:
                    return pid
            return None

        norm_topic = re.sub(r"[^a-zA-Z0-9]+", "", (concept_model.topic or "").lower())
        for node in concept_model.concepts:
            node_state = learner_model.get_or_create_concept(node.id)
            norm_node_id = re.sub(r"[^a-zA-Z0-9]+", "", node.id.lower())
            norm_node_name = re.sub(r"[^a-zA-Z0-9]+", "", node.name.lower())
            is_main_topic = bool(norm_topic and (norm_topic in norm_node_id or norm_node_id in norm_topic or norm_topic in norm_node_name))

            # The main topic node itself stays focused for at least 2 attempts before redirecting to prerequisites.
            # Sub-concepts (especially advanced ones difficulty >= 3) can redirect immediately if their prereq is unmet.
            min_attempts = 2 if is_main_topic else (1 if node.difficulty_level >= 3 else 2)
            if node_state.attempt_count >= min_attempts:
                unmet = _get_deepest_unmet(node.id, set())
                if unmet:
                    return unmet
        return None

    def _select_next_concept_node(
        self,
        concept_model: ConceptModel,
        learner_model: LearnerModel,
        recent_concepts: List[str],
    ) -> ConceptNode:
        """
        Phase 5 Coverage-Aware Concept Selection:
        1. Construct or derive TopicPlan tracking coverage status (NEEDS_REVIEW, UNASSESSED, IN_PROGRESS, MASTERED).
        2. Ensure prerequisite readiness (mastery >= 0.50).
        3. Prioritize:
           - Tier 0: Concepts needing review (unresolved gaps, active misconceptions).
           - Tier 1: Unassessed core concepts whose prerequisites are satisfied (in topological/importance order).
           - Tier 2: Unassessed non-core concepts whose prerequisites are satisfied.
           - Tier 3: In-progress concepts whose prerequisites are satisfied.
           - Tier 4: Mastered concepts (for synthesis or edge-case trade-offs).
        4. Apply anti-repetition penalty across recent concepts to avoid monopolizing or looping.
        """
        if not concept_model.concepts:
            return ConceptNode(id="core_foundation", name="Core Foundation", difficulty_level=1)

        from backend.app.ai.topic_plan import TopicPlanner, CoverageStatus
        topic_name = getattr(concept_model, "topic", "") or "General Topic"
        topic_plan = TopicPlanner.build_topic_plan(concept_model, learner_model, topic=topic_name)

        # 1. Filter nodes whose prerequisites are satisfied
        def prereqs_satisfied(node: ConceptNode) -> bool:
            for p_id in (node.prerequisites or []):
                p_state = learner_model.get_or_create_concept(p_id)
                if p_state.mastery < 0.50:
                    return False
            return True

        # Identify anchor concept matching the overall topic
        norm_topic = re.sub(r"[^a-zA-Z0-9]+", "", (concept_model.topic or "").lower())
        topic_anchor = None
        if norm_topic:
            for n in concept_model.concepts:
                norm_id = re.sub(r"[^a-zA-Z0-9]+", "", n.id.lower())
                norm_name = re.sub(r"[^a-zA-Z0-9]+", "", n.name.lower())
                if norm_topic in norm_id or norm_id in norm_topic or norm_topic in norm_name:
                    topic_anchor = n
                    break

        eligible_nodes = [node for node in concept_model.concepts if prereqs_satisfied(node)]
        # The primary topic node must ALWAYS remain eligible in early turns (< 3 attempts) so the student learns the selected topic
        if topic_anchor and learner_model.get_or_create_concept(topic_anchor.id).attempt_count < 3:
            if topic_anchor not in eligible_nodes:
                eligible_nodes.append(topic_anchor)

        if not eligible_nodes:
            # Fallback to foundational concepts (nodes with no prerequisites)
            foundation_nodes = [node for node in concept_model.concepts if not node.prerequisites]
            eligible_nodes = foundation_nodes or concept_model.concepts

        # Scoring function incorporating coverage status tier and anti-repetition:
        def _concept_selection_score(node: ConceptNode) -> tuple:
            c_cov = topic_plan.get_concept(node.id)
            status = c_cov.status if c_cov else CoverageStatus.UNASSESSED
            state = learner_model.get_or_create_concept(node.id)

            importance = getattr(node, "importance", "CORE") or "CORE"
            is_core = importance.upper() in ("CORE", "PREREQUISITE")

            # Prioritize the topic anchor in early turns (< 2 attempts) so we establish the foundation of what the user chose
            if topic_anchor and node.id == topic_anchor.id and state.attempt_count < 2:
                tier = -1
            elif status == CoverageStatus.NEEDS_REVIEW:
                tier = 0
            elif status == CoverageStatus.UNASSESSED and is_core:
                tier = 1
            elif status == CoverageStatus.UNASSESSED:
                tier = 2
            elif status == CoverageStatus.IN_PROGRESS:
                tier = 3
            else:
                tier = 4

            # Anti-repetition penalty across recent concepts
            recent_penalty = 0
            if recent_concepts:
                if recent_concepts[-1] == node.id:
                    recent_penalty = 100
                elif node.id in recent_concepts[-3:]:
                    recent_penalty = 25

            # Evidence availability preference: prefer concepts with verified source evidence
            is_scaffold = bool(getattr(node, "metadata", {}).get("is_generic_scaffold", False))
            has_ev = (not is_scaffold) and (
                bool(getattr(node, "source_references", []))
                or (getattr(c_cov, "has_source_evidence", False) if c_cov else False)
            )
            ev_penalty = 0 if has_ev else 10

            # Order by:
            # 1. Tier (NEEDS_REVIEW < UNASSESSED_CORE < UNASSESSED_OTHER < IN_PROGRESS < MASTERED)
            # 2. Anti-repetition penalty (non-recent first)
            # 3. Evidence availability (concepts with source evidence first)
            # 4. Difficulty level (lower/foundational first)
            # 5. Mastery (lower mastery first)
            return (tier, recent_penalty, ev_penalty, node.difficulty_level, state.mastery)

        return sorted(eligible_nodes, key=_concept_selection_score)[0]

    def _calculate_next_difficulty(
        self,
        current_difficulty: int,
        concept_node: ConceptNode,
        concept_state,
        latest_evaluation: Optional[TurnEvaluation],
    ) -> int:
        """
        Difficulty transitions bounded between 1 and 5.
        Maximum delta of +-1 per turn.
        Depends strictly on demonstrated evidence, not conversation length.
        
        Section 4 requirements:
        - A correct but incomplete answer (completeness < 0.70) must not automatically count as a fully correct answer.
        - A vague explanation (depth < 0.60) must not be treated as mastery simply because it contains relevant terminology.
        - A single strong answer must not automatically trigger a jump to advanced synthesis (bounded +-1).
        - Active misconceptions or low correctness block progression and trigger regression/focused clarification.
        - Unresolved gaps or misconceptions on the concept state prevent increase.
        """
        node_diff = concept_node.difficulty_level

        if latest_evaluation is not None:
            has_misc = bool(latest_evaluation.misconceptions and len(latest_evaluation.misconceptions) > 0)
            is_strong = (
                latest_evaluation.correctness >= 0.80
                and latest_evaluation.completeness >= 0.70
                and latest_evaluation.depth >= 0.60
                and latest_evaluation.stuck_probability < 0.30
                and not has_misc
            )
            is_weak = (
                latest_evaluation.correctness < 0.40
                or latest_evaluation.stuck_probability >= 0.50
                or (has_misc and latest_evaluation.correctness < 0.50)
            )

            if is_strong:
                proposed = current_difficulty + 1
            elif is_weak:
                proposed = current_difficulty - 1
            else:
                proposed = current_difficulty

            # Block progression if concept state still has active misconceptions or unresolved gap
            if concept_state and (concept_state.active_misconceptions or concept_state.unresolved_gap):
                if proposed > current_difficulty:
                    proposed = current_difficulty
        else:
            # Initial or default: align towards concept node difficulty
            if current_difficulty < node_diff:
                proposed = current_difficulty + 1
            elif current_difficulty > node_diff:
                proposed = current_difficulty - 1
            else:
                proposed = current_difficulty

        # Bound to [1, 5] and ensure max delta is 1
        proposed = max(1, min(5, proposed))
        if proposed > current_difficulty + 1:
            proposed = current_difficulty + 1
        elif proposed < current_difficulty - 1:
            proposed = current_difficulty - 1

        return max(1, min(5, proposed))

    def _determine_objective_type(
        self, node: ConceptNode, state, target_difficulty: int
    ) -> tuple[ObjectiveType, str]:
        """Determine pedagogical objective and expected evidence from difficulty and node metadata."""
        if target_difficulty == 1:
            return (
                ObjectiveType.UNDERSTAND_DEFINITION,
                f"Learner defines {node.name} accurately and explains its essential purpose.",
            )
        elif target_difficulty == 2:
            return (
                ObjectiveType.UNDERSTAND_MECHANISM,
                f"Learner explains the step-by-step mechanism and internal workflow of {node.name}.",
            )
        elif target_difficulty == 3:
            return (
                ObjectiveType.APPLY_CONCEPT,
                f"Learner applies {node.name} to a practical scenario, correctly predicting its behavior.",
            )
        elif target_difficulty == 4:
            return (
                ObjectiveType.HANDLE_EDGE_CASE,
                f"Learner identifies constraints, boundary conditions, or edge cases of {node.name}.",
            )
        else:
            return (
                ObjectiveType.SYNTHESIZE_CONCEPTS,
                f"Learner synthesizes {node.name} with related system components and analyzes trade-offs.",
            )

    def _resolve_strategy_objective(
        self,
        strategy: Optional[Strategy],
        concept_node: ConceptNode,
        concept_state,
        target_difficulty: int,
        latest_evaluation: Optional[TurnEvaluation] = None,
    ) -> tuple[ObjectiveType, str]:
        """
        Explicitly map pedagogical strategies to their corresponding ObjectiveType and expected evidence.
        Falls back to _determine_objective_type if strategy is absent or not explicitly mapped.
        """
        node_name = concept_node.name

        # 1. Active misconception signal check:
        # If strategy is CHALLENGE_MISCONCEPTION or learner has active misconceptions on this concept
        if strategy == Strategy.CHALLENGE_MISCONCEPTION or (concept_state and concept_state.active_misconceptions):
            misc_text = ""
            if concept_state and concept_state.active_misconceptions:
                misc_text = f" ({concept_state.active_misconceptions[0]})"
            elif latest_evaluation and latest_evaluation.misconceptions:
                misc_text = f" ({latest_evaluation.misconceptions[0]})"
            return (
                ObjectiveType.RESOLVE_MISCONCEPTION,
                f"Learner correctly identifies and resolves the misconception regarding {node_name}{misc_text}.",
            )

        # 2. Term clarification
        if strategy == Strategy.CLARIFY_TERM:
            return (
                ObjectiveType.UNDERSTAND_DEFINITION,
                f"Learner provides a precise definition and clarifying explanation for {node_name}.",
            )

        # 3. Probing causal relationships (Why)
        if strategy == Strategy.PROBE_WHY:
            return (
                ObjectiveType.UNDERSTAND_CAUSAL_RELATION,
                f"Learner explains the underlying rationale, causality, and theoretical justification for {node_name}.",
            )

        # 4. Probing mechanism (How)
        if strategy == Strategy.PROBE_HOW:
            return (
                ObjectiveType.UNDERSTAND_MECHANISM,
                f"Learner details the step-by-step mechanism, process flow, and operations of {node_name}.",
            )

        # 5. Missing concept / gap probing:
        # Distinguish genuinely unassessed concept from a concept with demonstrated weakness
        if strategy == Strategy.PROBE_MISSING_CONCEPT:
            has_weakness = (
                concept_state is not None
                and (
                    concept_state.unresolved_gap
                    or (concept_state.attempt_count > 0 and concept_state.mastery < 0.50)
                )
            ) or (latest_evaluation is not None and latest_evaluation.knowledge_gap)
            if has_weakness:
                return (
                    ObjectiveType.REINFORCE_WEAK_CONCEPT,
                    f"Learner addresses the identified weakness and reinforces foundational understanding of {node_name}.",
                )
            else:
                return (
                    ObjectiveType.VERIFY_GAP,
                    f"Learner supplies the missing conceptual component of {node_name} and explains how it connects.",
                )

        # 6. Verify understanding
        if strategy == Strategy.VERIFY_UNDERSTANDING:
            return (
                ObjectiveType.EXPLAIN_IN_OWN_WORDS,
                f"Learner verifies understanding of {node_name} by explaining key concepts in their own words or with a concrete application.",
            )

        # 7. Request Example (Level 3 - Application)
        if strategy == Strategy.REQUEST_EXAMPLE:
            return (
                ObjectiveType.APPLY_CONCEPT,
                f"Learner illustrates understanding of {node_name} with a concrete, realistic example or scenario.",
            )

        # 8. Test Edge Case (Level 4 - Assumptions and edge cases)
        if strategy == Strategy.TEST_EDGE_CASE:
            return (
                ObjectiveType.HANDLE_EDGE_CASE,
                f"Learner analyzes boundary conditions, failure modes, or edge-case behavior of {node_name}.",
            )

        # 9. Challenge Assumption (Level 4 - Assumptions and edge cases)
        if strategy == Strategy.CHALLENGE_ASSUMPTION:
            return (
                ObjectiveType.HANDLE_EDGE_CASE,
                f"Learner identifies implicit premises or tests assumptions underpinning {node_name}.",
            )

        # 10. Connect Concepts (Level 5 - Synthesis and trade-offs)
        if strategy == Strategy.CONNECT_CONCEPTS:
            return (
                ObjectiveType.SYNTHESIZE_CONCEPTS,
                f"Learner synthesizes {node_name} with related system components and analyzes trade-offs.",
            )

        # 11. Depth Expansion (Deepen incomplete explanation)
        if strategy == Strategy.DEPTH_EXPANSION:
            return (
                ObjectiveType.UNDERSTAND_MECHANISM,
                f"Learner expands the depth, detail, and completeness of the explanation for {node_name}.",
            )

        # 12. Fallback to difficulty-based objective resolution
        return self._determine_objective_type(concept_node, concept_state, target_difficulty)
