"""
Deterministic Report Builder and Roadmap Generator for Curio AI (Phase 3F).
Transforms structured SessionEvaluation into a clean, UI-agnostic LearningReport.
"""
from datetime import datetime, timezone
from typing import List, Optional
from backend.app.ai.schemas import (
     LearningReport,
     RoadmapItem,
     SessionEvaluation,
)


class ReportBuilder:
    """
    Transforms a SessionEvaluation into a user-facing, UI-agnostic LearningReport.
    Ensures that roadmap recommendations are grounded in session evidence.
    """

    def build_report(
        self,
        evaluation: SessionEvaluation,
        difficulty_achieved: int = 1,
        teacher_interventions_count: int = 0,
    ) -> LearningReport:
        """
        Constructs a LearningReport from a SessionEvaluation.
        """
        # Ensure roadmap is populated and prioritized
        roadmap = list(evaluation.recommended_next_steps)
        if not roadmap:
            roadmap = self.generate_default_roadmap(evaluation)

        # High-level knowledge gaps list: unresolved gaps
        unresolved_gaps = list(evaluation.unresolved_gaps)
        resolved_gaps = list(evaluation.resolved_gaps)

        # Misconceptions: unresolved
        unresolved_misc = list(evaluation.unresolved_misconceptions)
        resolved_misc = list(evaluation.resolved_misconceptions)

        created_at_str = datetime.now(timezone.utc).isoformat()

        return LearningReport(
            session_id=evaluation.session_id,
            topic=evaluation.topic,
            understanding_score=evaluation.understanding_score,
            mastery_level=evaluation.mastery_level,
            evidence_confidence=evaluation.evidence_confidence,
            strengths=list(evaluation.strengths),
            knowledge_gaps=unresolved_gaps,
            resolved_gaps=resolved_gaps,
            unresolved_gaps=unresolved_gaps,
            misconceptions=unresolved_misc,
            resolved_misconceptions=resolved_misc,
            unresolved_misconceptions=unresolved_misc,
            concept_assessments=list(evaluation.concept_assessments),
            difficulty_achieved=max(1, difficulty_achieved),
            teacher_interventions_required=teacher_interventions_count,
            recommended_next_steps=roadmap,
            created_at=created_at_str,
        )

    def generate_default_roadmap(self, evaluation: SessionEvaluation) -> List[RoadmapItem]:
        """
        Generates deterministic roadmap items derived directly from evidence:
        Priority 1: Unresolved critical misconceptions
        Priority 2: Major unresolved knowledge gaps
        Priority 3: Concepts with low scores (< 70)
        Priority 4: Consolidation / advanced practice
        """
        items: List[RoadmapItem] = []
        p = 1

        # 1. Unresolved misconceptions
        for m in evaluation.unresolved_misconceptions:
            items.append(
                RoadmapItem(
                    priority=p,
                    title=f"Clarify Misconception: {m}",
                    description=f"Review and challenge the premise of '{m}'. Contrast with valid counterexamples.",
                    target_concept=evaluation.topic,
                    action_type="RESOLVE_MISCONCEPTION",
                )
            )
            p += 1

        # 2. Unresolved gaps
        for g in evaluation.unresolved_gaps:
            items.append(
                RoadmapItem(
                    priority=p,
                    title=f"Bridge Gap: {g}",
                    description=f"Study core mechanics addressing '{g}'. Focus on boundary conditions and edge cases.",
                    target_concept=evaluation.topic,
                    action_type="FILL_GAP",
                )
            )
            p += 1

        # 3. Concepts needing reinforcement
        for ca in evaluation.concept_assessments:
            if ca.understanding_score < 70.0:
                items.append(
                    RoadmapItem(
                        priority=p,
                        title=f"Practice {ca.concept}",
                        description=f"Current score is {ca.understanding_score}%. Work through guided exercises on {ca.concept}.",
                        target_concept=ca.concept,
                        action_type="PRACTICE",
                    )
                )
                p += 1

        # 4. Fallback or advanced step if everything is solid
        if not items:
            if evaluation.understanding_score >= 85.0:
                items.append(
                    RoadmapItem(
                        priority=1,
                        title=f"Advanced Synthesis on {evaluation.topic}",
                        description=f"Demonstrated mastery of {evaluation.topic}. Practice complex synthesis and real-world system design questions.",
                        target_concept=evaluation.topic,
                        action_type="ADVANCED",
                    )
                )
            else:
                items.append(
                    RoadmapItem(
                        priority=1,
                        title=f"Comprehensive Practice on {evaluation.topic}",
                        description=f"Reinforce understanding by explaining {evaluation.topic} in your own words using real-world analogies.",
                        target_concept=evaluation.topic,
                        action_type="PRACTICE",
                    )
                )

        return items
