"""
Session Evaluator for Curio AI (Phase 3C).
Synthesizes session-level evidence into a structured SessionEvaluation.
Combines:
- Deterministic scoring and mastery metrics (ScoringEngine)
- Deterministic gap and misconception lifecycle analysis (GapAnalyzer)
- Deterministic concept breakdown (ConceptAssessment)
- Semantic roadmap generation via BaseLLMProvider
"""
import logging
from typing import List, Optional

from backend.app.ai.gap_analyzer import GapAnalyzer
from backend.app.ai.prompts.evaluator_prompts import build_session_evaluation_prompt
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.ai.report_builder import ReportBuilder
from backend.app.ai.schemas import (
    LearningReport,
    RoadmapItem,
    SessionEvaluation,
    SessionEvidence,
)
from backend.app.ai.scoring import ScoringEngine

logger = logging.getLogger("curio.ai.session_evaluator")


class SessionEvaluator:
    """
    SessionEvaluator answers:
    'What does the ENTIRE learning session tell us about the learner?'
    Produces structured SessionEvaluation and LearningReport without hallucinations.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or MockLLMProvider()
        self.scoring_engine = ScoringEngine()
        self.gap_analyzer = GapAnalyzer()
        self.report_builder = ReportBuilder()

    def evaluate_session(self, evidence: SessionEvidence) -> SessionEvaluation:
        """
        Evaluate a complete learning session from structured SessionEvidence.
        """
        logger.info(
            "Evaluating session %s (topic=%s, turns=%d)",
            evidence.session_id,
            evidence.topic,
            evidence.total_learner_turns,
        )

        # 1. Deterministic Scoring
        score = self.scoring_engine.calculate_session_score(evidence)
        confidence = self.scoring_engine.calculate_evidence_confidence(evidence)
        mastery = self.scoring_engine.determine_mastery_level(score, confidence)
        concept_assessments = self.scoring_engine.assess_concepts(evidence)

        # 2. Deterministic Gap and Misconception Lifecycle Analysis
        gap_items, resolved_gaps, unresolved_gaps = self.gap_analyzer.analyze_gaps(evidence)
        misc_items, resolved_misc, unresolved_misc = self.gap_analyzer.analyze_misconceptions(evidence)
        strengths = self.gap_analyzer.extract_strengths(evidence)

        # 3. Teacher Intervention Summary
        teacher_summary = {
            "total_interventions": len(evidence.teacher_interventions),
            "successful_interventions": sum(1 for ti in evidence.teacher_interventions if ti.verification_passed),
            "failed_interventions": sum(1 for ti in evidence.teacher_interventions if not ti.verification_passed),
        }

        # 4. Roadmap Generation
        roadmap_items: List[RoadmapItem] = []
        # First generate deterministic default roadmap grounded in evidence
        proto_eval = SessionEvaluation(
            session_id=evidence.session_id,
            topic=evidence.topic,
            understanding_score=score,
            mastery_level=mastery,
            evidence_confidence=confidence,
            strengths=strengths,
            knowledge_gaps=gap_items,
            misconceptions=misc_items,
            resolved_gaps=resolved_gaps,
            unresolved_gaps=unresolved_gaps,
            resolved_misconceptions=resolved_misc,
            unresolved_misconceptions=unresolved_misc,
            concept_assessments=concept_assessments,
            difficulty_progression=evidence.difficulty_progression,
            teacher_intervention_summary=teacher_summary,
            recommended_next_steps=[],
        )
        roadmap_items = self.report_builder.generate_default_roadmap(proto_eval)

        # 5. Assemble final structured SessionEvaluation
        final_eval = SessionEvaluation(
            session_id=evidence.session_id,
            topic=evidence.topic,
            understanding_score=score,
            mastery_level=mastery,
            evidence_confidence=confidence,
            strengths=strengths,
            knowledge_gaps=gap_items,
            misconceptions=misc_items,
            resolved_gaps=resolved_gaps,
            unresolved_gaps=unresolved_gaps,
            resolved_misconceptions=resolved_misc,
            unresolved_misconceptions=unresolved_misc,
            concept_assessments=concept_assessments,
            difficulty_progression=evidence.difficulty_progression,
            teacher_intervention_summary=teacher_summary,
            recommended_next_steps=roadmap_items,
        )

        return final_eval

    def generate_report(self, evidence: SessionEvidence) -> LearningReport:
        """
        Convenience pipeline:
        SessionEvidence -> SessionEvaluation -> LearningReport.
        """
        evaluation = self.evaluate_session(evidence)
        max_diff = max(evidence.difficulty_progression) if evidence.difficulty_progression else 1
        teacher_count = len(evidence.teacher_interventions)
        return self.report_builder.build_report(
            evaluation=evaluation,
            difficulty_achieved=max_diff,
            teacher_interventions_count=teacher_count,
        )
