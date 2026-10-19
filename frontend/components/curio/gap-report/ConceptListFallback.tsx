"use client";

import React from "react";
import { ConceptCell, GapReport, UnderstandingLayer } from "@/types/gapReport";

export interface ConceptListFallbackProps {
  concepts?: ConceptCell[];
  report?: GapReport;
  onSelectConcept?: (concept: ConceptCell) => void;
}

export function ConceptListFallback({
  concepts,
  report,
  onSelectConcept,
}: ConceptListFallbackProps) {
  const allConcepts = concepts || report?.concepts || [];
  const topicName = report?.topicName || "Topic";

  const layers: UnderstandingLayer[] = [
    "DEFINITION",
    "MECHANISM",
    "APPLICATION",
    "EDGE_CASES",
  ];

  return (
    <div
      className="sr-only"
      role="list"
      aria-label={`Knowledge map for ${topicName}`}
    >
      {layers.map((layer) => {
        const layerConcepts = allConcepts.filter((c) => c.layer === layer);
        const avgScore =
          layerConcepts.length > 0
            ? Math.round(
                layerConcepts.reduce((acc, c) => acc + (c.score || 0), 0) /
                  layerConcepts.length
              )
            : 0;

        return (
          <div key={layer} role="listitem">
            <h4>
              {layer} layer — {avgScore}% understanding
            </h4>
            <ul>
              {layerConcepts.map((cell) => (
                <li key={cell.id}>
                  <button
                    onClick={() => onSelectConcept && onSelectConcept(cell)}
                    aria-label={`${cell.name}, ${cell.status}, ${cell.score}%`}
                  >
                    {cell.name}: {cell.status} ({cell.score}%)
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

export default ConceptListFallback;
