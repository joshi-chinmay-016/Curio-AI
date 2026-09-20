"use client";

import { GapReport } from "@/types/gapReport";

interface ConceptListFallbackProps {
  report: GapReport;
  selectedConceptId: string | null;
  onSelectConcept: (conceptId: string) => void;
}

export default function ConceptListFallback({
  report,
  selectedConceptId,
  onSelectConcept,
}: ConceptListFallbackProps) {
  return (
    <div className="sr-only" aria-label="Accessible Concept List">
      <h3>All Concepts for {report.topicName}</h3>
      <ul>
        {report.concepts.map((concept) => (
          <li key={concept.id}>
            <button
              onClick={() => onSelectConcept(concept.id)}
              aria-selected={selectedConceptId === concept.id}
            >
              {concept.name} — Layer: {concept.layer} — Status: {concept.status} —
              Score: {concept.score}% — Confidence: {concept.confidence}%
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
