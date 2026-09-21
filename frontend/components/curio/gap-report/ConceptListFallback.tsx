"use client";

import React from "react";
import { ConceptCell } from "@/types/gapReport";

export interface ConceptListFallbackProps {
  concepts: ConceptCell[];
}

export function ConceptListFallback({ concepts }: ConceptListFallbackProps) {
  return (
    <ul className="sr-only" aria-label="Accessible list of concepts in the knowledge map">
      {concepts.map((concept) => (
        <li
          key={concept.id}
          aria-label={`${concept.name} — ${concept.status} — Score: ${concept.score}%`}
        >
          <span>{concept.name}</span>
          <span>Layer: {concept.layer}</span>
          <span>Status: {concept.status}</span>
          <span>Understanding: {concept.score}%</span>
          <span>Confidence: {concept.confidence}%</span>
          {concept.description && <span>Description: {concept.description}</span>}
        </li>
      ))}
    </ul>
  );
}
