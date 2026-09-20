"""
Gap and Misconception Lifecycle Analyzer for Curio AI (Phase 3E).
Tracks:
- Gap lifecycle: DETECTED -> CHALLENGED -> RESOLVED vs. UNRESOLVED
- Misconception lifecycle: DETECTED -> CHALLENGED -> RESOLVED vs. UNRESOLVED
- Gap severity: LOW, MEDIUM, HIGH
- Evidence-backed strengths
"""
from typing import Dict, List, Set, Tuple
from backend.app.ai.schemas import (
    GapAnalysisItem,
    GapSeverity,
    GapStatus,
    MisconceptionAnalysisItem,
    MisconceptionStatus,
    SessionEvidence,
    Strategy,
    TurnEvidence,
)


class GapAnalyzer:
    """
    Analyzes the lifecycle of knowledge gaps and misconceptions across session evidence.
    """

    def analyze_gaps(self, evidence: SessionEvidence) -> Tuple[List[GapAnalysisItem], List[str], List[str]]:
        """
        Extracts all gaps, determines their lifecycle status and severity,
        and returns:
        (gap_items, resolved_gaps_list, unresolved_gaps_list)
        """
        gap_map: Dict[str, GapAnalysisItem] = {}
        resolved_gaps: List[str] = []
        unresolved_gaps: List[str] = []

        # 1. Collect from turn evaluations
        for turn in evidence.turns:
            ev = turn.evaluation
            if ev.knowledge_gap:
                g_text = ev.knowledge_gap.strip()
                ref = f"turn_{turn.turn_index}"
                if g_text not in gap_map:
                    gap_map[g_text] = GapAnalysisItem(
                        gap=g_text,
                        concept=turn.concept,
                        severity=GapSeverity.MEDIUM,
                        status=GapStatus.DETECTED,
                        evidence_references=[ref],
                    )
                else:
                    if ref not in gap_map[g_text].evidence_references:
                        gap_map[g_text].evidence_references.append(ref)
                    # Recurring gap increases severity
                    gap_map[g_text].severity = GapSeverity.HIGH

            # Missing concepts as low/medium gaps
            for mc in ev.missing_concepts:
                g_text = f"Omission of {mc}"
                ref = f"turn_{turn.turn_index}"
                if g_text not in gap_map:
                    gap_map[g_text] = GapAnalysisItem(
                        gap=g_text,
                        concept=turn.concept,
                        severity=GapSeverity.LOW,
                        status=GapStatus.DETECTED,
                        evidence_references=[ref],
                    )
                else:
                    if ref not in gap_map[g_text].evidence_references:
                        gap_map[g_text].evidence_references.append(ref)

        # 2. Correlate with teacher interventions
        for ti in evidence.teacher_interventions:
            ref = f"intervention_{ti.intervention_index}"
            g_text = ti.gap.strip()

            # Find matching or closely matching gap
            matched_key = None
            for key in gap_map:
                if key.lower() in g_text.lower() or g_text.lower() in key.lower():
                    matched_key = key
                    break

            if not matched_key:
                matched_key = g_text
                gap_map[matched_key] = GapAnalysisItem(
                    gap=matched_key,
                    concept=ti.related_concept,
                    severity=GapSeverity.HIGH,
                    status=GapStatus.CHALLENGED,
                    evidence_references=[ref],
                )
            else:
                if ref not in gap_map[matched_key].evidence_references:
                    gap_map[matched_key].evidence_references.append(ref)
                gap_map[matched_key].severity = GapSeverity.HIGH
                gap_map[matched_key].status = GapStatus.CHALLENGED

            # Check if resolved
            if ti.verification_passed:
                gap_map[matched_key].status = GapStatus.RESOLVED
            else:
                gap_map[matched_key].status = GapStatus.UNRESOLVED

        # 3. Check subsequent turn evidence for gaps without teacher intervention
        for g_text, item in gap_map.items():
            if item.status == GapStatus.DETECTED:
                # Check if later turns had high correctness without this gap
                later_turns = [
                    t for t in evidence.turns
                    if t.turn_index > int(item.evidence_references[0].split("_")[-1])
                ]
                if later_turns and all(t.evaluation.correctness >= 0.75 for t in later_turns):
                    item.status = GapStatus.RESOLVED
                else:
                    item.status = GapStatus.UNRESOLVED

            if item.status == GapStatus.RESOLVED:
                if g_text not in resolved_gaps:
                    resolved_gaps.append(g_text)
            else:
                if g_text not in unresolved_gaps:
                    unresolved_gaps.append(g_text)

        return list(gap_map.values()), resolved_gaps, unresolved_gaps

    def analyze_misconceptions(
        self, evidence: SessionEvidence
    ) -> Tuple[List[MisconceptionAnalysisItem], List[str], List[str]]:
        """
        Extracts misconceptions, tracks lifecycle status, and returns:
        (misconception_items, resolved_misconceptions_list, unresolved_misconceptions_list)
        """
        misc_map: Dict[str, MisconceptionAnalysisItem] = {}
        resolved_misc: List[str] = []
        unresolved_misc: List[str] = []

        # 1. Collect from turns
        for turn in evidence.turns:
            ref = f"turn_{turn.turn_index}"
            for m in turn.evaluation.misconceptions:
                m_clean = m.strip()
                if m_clean not in misc_map:
                    misc_map[m_clean] = MisconceptionAnalysisItem(
                        misconception=m_clean,
                        concept=turn.concept,
                        status=MisconceptionStatus.DETECTED,
                        evidence_references=[ref],
                    )
                else:
                    if ref not in misc_map[m_clean].evidence_references:
                        misc_map[m_clean].evidence_references.append(ref)

        # 2. Correlate with challenges & teacher interventions
        for m_clean, item in misc_map.items():
            first_seen_turn = int(item.evidence_references[0].split("_")[-1])

            # Check if challenged
            challenged = any(
                t.evaluation.recommended_strategy == Strategy.CHALLENGE_MISCONCEPTION
                for t in evidence.turns
                if t.turn_index >= first_seen_turn
            )
            if challenged:
                item.status = MisconceptionStatus.CHALLENGED

            # Check if teacher intervened and passed verification
            teacher_resolved = any(
                ti.verification_passed and (m_clean.lower() in ti.gap.lower() or item.concept.lower() in ti.related_concept.lower())
                for ti in evidence.teacher_interventions
            )

            # Check if later turns in session showed no misconceptions and high correctness
            later_turns = [
                t for t in evidence.turns
                if t.turn_index > first_seen_turn
            ]
            later_cleared = (
                bool(later_turns)
                and all(m_clean not in t.evaluation.misconceptions for t in later_turns)
                and any(t.evaluation.correctness >= 0.75 for t in later_turns)
            )

            if teacher_resolved or later_cleared:
                item.status = MisconceptionStatus.RESOLVED
                if m_clean not in resolved_misc:
                    resolved_misc.append(m_clean)
            else:
                item.status = MisconceptionStatus.UNRESOLVED
                if m_clean not in unresolved_misc:
                    unresolved_misc.append(m_clean)

        return list(misc_map.values()), resolved_misc, unresolved_misc

    def extract_strengths(self, evidence: SessionEvidence) -> List[str]:
        """
        Extracts evidence-backed strengths.
        Does NOT award strength based on a single isolated answer.
        Requires consistency, higher difficulty success, or verified gap resolution.
        """
        strengths: List[str] = []

        # 1. Look at concept evidence: >= 2 turns with high correctness or difficulty >= 3 passed
        for c_name, c_item in evidence.concept_evidence_map.items():
            high_scores = [s for s in c_item.correctness_scores if s >= 0.8]
            if len(high_scores) >= 2:
                strengths.append(f"Consistent and deep understanding of {c_name}")
            elif c_item.highest_difficulty_passed >= 3:
                strengths.append(f"Strong problem solving on {c_name} at advanced difficulty")

        # 2. Add mastered concepts confirmed across turns
        for turn in evidence.turns:
            if turn.evaluation.correctness >= 0.85 and turn.evaluation.depth >= 0.75:
                for mc in turn.evaluation.mastered_concepts:
                    desc = f"Clear mastery of {mc}"
                    if desc not in strengths:
                        strengths.append(desc)

        # 3. Add successfully resolved teacher interventions as growth strengths
        for ti in evidence.teacher_interventions:
            if ti.verification_passed and ti.related_concept:
                res_desc = f"Successfully overcame initial gap in {ti.related_concept}"
                if res_desc not in strengths:
                    strengths.append(res_desc)

        if not strengths and evidence.successful_turns > 0:
            strengths.append(f"Grasped foundational principles of {evidence.topic}")

        return strengths
