"""
Deterministic Question Selection Engine for Curio AI (Adaptive Learning Core v1).
Decides WHAT concept to test next, WHICH pedagogical objective to pursue,
and WHAT difficulty level to set based on the Concept Model and Learner Model.

Principle:
WHAT should the learner understand next? -> Question Selector (Deterministic).
HOW should it be phrased? -> LLM Generator.
"""
import logging
from typing import List, Optional

from backend.app.ai.schemas import (
    ConceptModel,
    ConceptNode,
    CurrentQuestion,
    LearnerModel,
    LearningObjective,
    ObjectiveType,
    QuestionSpecification,
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
                if latest_evaluation is not None
                else current_difficulty
            )
            obj_type, evidence_exp = self._determine_objective_type(c_node, c_state, target_diff)
            reason = f"Probing understanding of '{c_node.name}' at difficulty {target_diff}."
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
            diff = c_node.difficulty_level if c_node else current_difficulty
            # Bounded difficulty change
            diff = max(1, min(current_difficulty, diff))

            c_state = learner_model.get_or_create_concept(unresolved_target)
            if c_state.active_misconceptions:
                obj_type = ObjectiveType.RESOLVE_MISCONCEPTION
                reason = f"Active misconception detected on concept '{node_name}': {c_state.active_misconceptions[0]}"
                evidence = f"Learner correctly identifies and rejects the misconception on '{node_name}'."
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
            )
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
            )

        # 2. Check for missing prerequisite gaps
        # If learner is trying to learn an advanced concept whose prereqs are weak, steer to prereq
        prereq_target = self._find_unmet_prerequisite(concept_model, learner_model)
        if prereq_target:
            c_node = concept_model.get_concept(prereq_target)
            node_name = c_node.name if c_node else prereq_target
            diff = c_node.difficulty_level if c_node else 1
            diff = max(1, min(diff, current_difficulty))

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
                    "Focus on foundational mechanism and definitions",
                    "Do NOT reveal the answer",
                    "Exactly ONE question",
                ],
            )

        # 3. Determine next concept based on mastery progression
        target_concept_node = self._select_next_concept_node(concept_model, learner_model, recent_concepts)
        c_id = target_concept_node.id
        node_name = target_concept_node.name
        c_state = learner_model.get_or_create_concept(c_id)

        # Determine target difficulty (bounded change: at most +-1)
        if latest_evaluation is not None:
            target_diff = self._calculate_next_difficulty(
                current_difficulty=current_difficulty,
                concept_node=target_concept_node,
                concept_state=c_state,
                latest_evaluation=latest_evaluation,
            )
        else:
            target_diff = current_difficulty

        # Determine pedagogical objective based on difficulty and mastery
        obj_type, evidence_exp = self._determine_objective_type(target_concept_node, c_state, target_diff)
        reason = f"Progressing understanding of '{node_name}' at difficulty {target_diff} based on demonstrated mastery ({c_state.mastery:.2f})."

        obj = LearningObjective(
            objective_type=obj_type,
            target_concept=c_id,
            difficulty=target_diff,
            reason=reason,
            evidence_expected=evidence_exp,
        )

        constraints = [
            f"Target concept: {node_name}",
            f"Objective: {obj_type.value}",
            f"Difficulty level: {target_diff}",
            "Ground the question in the ongoing conversation",
            "Exactly ONE primary question",
            "Do NOT explain or teach the answer in Student mode",
            "Avoid semantic repetition with recent questions",
        ]

        return QuestionSpecification(
            target_concept=c_id,
            learning_objective=obj,
            difficulty=target_diff,
            reason=reason,
            evidence_expected=evidence_exp,
            generation_constraints=constraints,
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

        for node in concept_model.concepts:
            node_state = learner_model.get_or_create_concept(node.id)
            if node_state.attempt_count > 0:
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
        Select the best concept node from the model:
        1. Find unmastered concepts whose prerequisites are all satisfied (mastery >= 0.60).
        2. Prefer concepts not recently tested to avoid repetition.
        3. If all concepts are mastered, pick the highest-difficulty synthesis concept.
        """
        if not concept_model.concepts:
            return ConceptNode(id="core_foundation", name="Core Foundation", difficulty_level=1)

        eligible_nodes: List[ConceptNode] = []
        for node in concept_model.concepts:
            state = learner_model.get_or_create_concept(node.id)
            if state.mastery < 0.85:
                # Check prerequisites
                prereqs_ok = True
                for p_id in node.prerequisites:
                    p_state = learner_model.get_or_create_concept(p_id)
                    if p_state.mastery < 0.50:
                        prereqs_ok = False
                        break
                if prereqs_ok:
                    eligible_nodes.append(node)

        if not eligible_nodes:
            # All available concepts are largely mastered; pick highest difficulty node
            return sorted(concept_model.concepts, key=lambda c: -c.difficulty_level)[0]

        # Order eligible nodes: non-recent first, then lower difficulty first
        def _score(node: ConceptNode):
            recent_penalty = 10 if recent_concepts and recent_concepts[-1] == node.id else 0
            state = learner_model.get_or_create_concept(node.id)
            return (recent_penalty, node.difficulty_level, state.mastery)

        return sorted(eligible_nodes, key=_score)[0]

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
        """
        node_diff = concept_node.difficulty_level

        if latest_evaluation is not None:
            if latest_evaluation.correctness >= 0.80:
                # Strong evidence: can increase difficulty by 1
                proposed = current_difficulty + 1
            elif latest_evaluation.correctness < 0.40 or latest_evaluation.stuck_probability >= 0.5:
                # Weak evidence: decrease difficulty by 1
                proposed = current_difficulty - 1
            else:
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
