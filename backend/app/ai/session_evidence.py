"""
Session Evidence Builder for Curio AI (Phase 3B).
Extracts and normalizes structured evidence from raw session interaction history,
turn evaluations, teacher interventions, and state progression.

Boundary rule:
This module does NOT make final judgments or calculate mastery scores.
It normalizes and organizes raw and derived evidence for the SessionEvaluator.
"""
from typing import Any, Dict, List, Optional, Union

from backend.app.ai.schemas import (
    ChatMessage,
    ConceptEvidenceItem,
    Role,
    SessionEvidence,
    Strategy,
    TeacherInterventionEvidence,
    TurnEvaluation,
    TurnEvidence,
)


class SessionEvidenceBuilder:
    """
    Constructs structured SessionEvidence from session history, evaluations,
    and state transitions.
    """

    def build_from_history(
        self,
        session_id: str,
        topic: str,
        messages: List[Any],
        evaluations: Optional[List[TurnEvaluation]] = None,
        difficulty_history: Optional[List[int]] = None,
        confidence_history: Optional[List[float]] = None,
        active_concept: str = "",
    ) -> SessionEvidence:
        """
        Build a SessionEvidence object from chronological messages and evaluations.

        Args:
            session_id: Session identifier.
            topic: Primary topic of the session.
            messages: Chronological message models, dicts, or ChatMessage instances.
            evaluations: Optional list of TurnEvaluation instances matching user turns.
            difficulty_history: Optional list of difficulty levels across turns.
            confidence_history: Optional list of confidence levels across turns.
            active_concept: Default concept if not specified in messages/evaluations.

        Returns:
            Structured SessionEvidence.
        """
        turns: List[TurnEvidence] = []
        teacher_interventions: List[TeacherInterventionEvidence] = []
        concept_map: Dict[str, ConceptEvidenceItem] = {}
        concepts_encountered: List[str] = []

        # 1. Normalize messages into ChatMessage format with metadata
        normalized_messages: List[Dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, dict):
                sender = str(msg.get("sender", msg.get("role", "USER"))).upper()
                content = str(msg.get("content", ""))
                metadata = msg.get("metadata", {})
            elif hasattr(msg, "sender") and hasattr(msg, "content"):
                sender = str(msg.sender).upper()
                content = str(msg.content)
                meta_attr = getattr(msg, "metadata", {})
                metadata = meta_attr if isinstance(meta_attr, dict) else {}
            elif isinstance(msg, ChatMessage):
                sender = "AI" if msg.role == Role.ASSISTANT else "USER"
                content = msg.content
                metadata = {}
            else:
                continue

            role = Role.ASSISTANT if sender in ["AI", "ASSISTANT"] else Role.USER
            normalized_messages.append({
                "sender": sender,
                "role": role,
                "content": content,
                "metadata": metadata,
            })

        # 2. Extract TurnEvidence by matching AI questions with User answers
        user_msg_indices = [
            i for i, m in enumerate(normalized_messages) if m["role"] == Role.USER
        ]

        eval_idx = 0
        diff_prog = list(difficulty_history) if difficulty_history else []
        conf_prog = list(confidence_history) if confidence_history else []

        for turn_idx, u_idx in enumerate(user_msg_indices):
            user_msg = normalized_messages[u_idx]["content"]

            # Find the most recent preceding AI message
            prev_ai_msg = "Initial Turn / Topic Introduction"
            for prev_idx in range(u_idx - 1, -1, -1):
                if normalized_messages[prev_idx]["role"] == Role.ASSISTANT:
                    prev_ai_msg = normalized_messages[prev_idx]["content"]
                    break

            # Fetch or fabricate fallback evaluation if evaluations list is shorter
            turn_eval: TurnEvaluation
            if evaluations and eval_idx < len(evaluations):
                turn_eval = evaluations[eval_idx]
                eval_idx += 1
            else:
                # Default neutral evaluation
                turn_eval = TurnEvaluation(
                    correctness=0.5,
                    clarity=0.5,
                    completeness=0.5,
                    depth=0.5,
                    relevance=1.0,
                    stuck_probability=0.0,
                    recommended_strategy=Strategy.PROBE_WHY,
                    recommended_difficulty=1,
                )

            # Determine concept for this turn
            turn_concept = active_concept or topic
            if turn_eval.mastered_concepts:
                turn_concept = turn_eval.mastered_concepts[0]
            elif turn_eval.missing_concepts:
                turn_concept = turn_eval.missing_concepts[0]

            turn_diff = (
                diff_prog[turn_idx]
                if turn_idx < len(diff_prog)
                else turn_eval.recommended_difficulty
            )

            turn_evidence = TurnEvidence(
                turn_index=turn_idx,
                question=prev_ai_msg,
                learner_answer=user_msg,
                concept=turn_concept,
                difficulty=turn_diff,
                evaluation=turn_eval,
            )
            turns.append(turn_evidence)

            # Update concept evidence map
            if turn_concept not in concepts_encountered:
                concepts_encountered.append(turn_concept)

            if turn_concept not in concept_map:
                concept_map[turn_concept] = ConceptEvidenceItem(
                    concept=turn_concept,
                    turns_evaluated=[],
                    correctness_scores=[],
                    misconceptions=[],
                    gaps=[],
                    teacher_assisted=False,
                    highest_difficulty_passed=0,
                )

            c_item = concept_map[turn_concept]
            c_item.turns_evaluated.append(turn_idx)
            c_item.correctness_scores.append(turn_eval.correctness)
            for m in turn_eval.misconceptions:
                if m not in c_item.misconceptions:
                    c_item.misconceptions.append(m)
            if turn_eval.knowledge_gap and turn_eval.knowledge_gap not in c_item.gaps:
                c_item.gaps.append(turn_eval.knowledge_gap)
            if turn_eval.correctness >= 0.7 and turn_diff > c_item.highest_difficulty_passed:
                c_item.highest_difficulty_passed = turn_diff

        # 3. Detect Teacher Interventions from message transcript & evaluations
        # A teacher intervention occurs when an AI message is generated in Teacher Mode
        # followed by a user verification response.
        intervention_counter = 0
        for i, m in enumerate(normalized_messages):
            if m["role"] == Role.ASSISTANT:
                content = m["content"]
                # Detect teacher mode markers or structure (e.g. 2 paragraphs with a verification question)
                # or metadata indicating TEACHER mode
                is_teacher = (
                    m["metadata"].get("mode") == "TEACHER"
                    or "Teacher" in m["metadata"].get("sender", "")
                    or (
                        "?" in content
                        and any(
                            phrase in content.lower()
                            for phrase in [
                                "suppose the middle",
                                "why can we ignore",
                                "why does this alphabetical",
                                "consider [",
                                "can you explain what would happen",
                                "why does knowing",
                            ]
                        )
                    )
                )

                if is_teacher:
                    # Next user message is verification answer
                    verif_ans = None
                    verif_passed = False
                    related_c = active_concept or topic
                    gap_text = m["metadata"].get("gap", "Knowledge gap addressed by teacher")

                    if i + 1 < len(normalized_messages) and normalized_messages[i + 1]["role"] == Role.USER:
                        verif_ans = normalized_messages[i + 1]["content"]
                        # Check subsequent turn evaluation
                        # If the turn evaluation for this answer has Strategy.RESTORE_INTERRUPTED_QUESTION
                        # or high correctness, verification passed
                        matching_turns = [t for t in turns if t.learner_answer == verif_ans]
                        if matching_turns:
                            matching_eval = matching_turns[0].evaluation
                            if (
                                matching_eval.recommended_strategy == Strategy.RESTORE_INTERRUPTED_QUESTION
                                or matching_eval.correctness >= 0.7
                            ):
                                verif_passed = True
                            if matching_turns[0].concept:
                                related_c = matching_turns[0].concept

                    teacher_interventions.append(
                        TeacherInterventionEvidence(
                            intervention_index=intervention_counter,
                            gap=gap_text,
                            attempt_count=m["metadata"].get("attempt_count", 1),
                            teacher_explanation=content,
                            verification_question=content.split("\n\n")[-1] if "\n\n" in content else content,
                            verification_answer=verif_ans,
                            verification_passed=verif_passed,
                            related_concept=related_c,
                        )
                    )
                    intervention_counter += 1

                    # Mark concept as teacher assisted
                    if related_c in concept_map:
                        concept_map[related_c].teacher_assisted = True

        # 4. Compute high-level turn counts
        total_turns = len(turns)
        successful = sum(
            1 for t in turns
            if t.evaluation.correctness >= 0.7 and t.evaluation.stuck_probability < 0.5
        )
        failed = sum(
            1 for t in turns
            if t.evaluation.correctness < 0.5 or t.evaluation.stuck_probability >= 0.7
        )

        return SessionEvidence(
            session_id=session_id,
            topic=topic,
            turns=turns,
            teacher_interventions=teacher_interventions,
            concepts_encountered=concepts_encountered,
            concept_evidence_map=concept_map,
            difficulty_progression=diff_prog if diff_prog else [t.difficulty for t in turns],
            confidence_progression=conf_prog,
            total_learner_turns=total_turns,
            successful_turns=successful,
            failed_turns=failed,
        )
