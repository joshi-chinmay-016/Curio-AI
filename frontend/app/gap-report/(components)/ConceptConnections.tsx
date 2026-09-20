"use client";

import { useMemo } from "react";
import { Vector3 } from "three";
import { Line } from "@react-three/drei";
import { ConceptAssessment } from "@/types/gapReport";

interface ConceptConnectionsProps {
  concepts: ConceptAssessment[];
  positions: Map<string, Vector3>;
  selectedConceptId: string | null;
}

export default function ConceptConnections({
  concepts,
  positions,
  selectedConceptId,
}: ConceptConnectionsProps) {
  const connections = useMemo(() => {
    const lines: {
      fromId: string;
      toId: string;
      isRelated: boolean;
      points: [Vector3, Vector3];
    }[] = [];

    // Avoid duplicate lines between concept pairs
    const seen = new Set<string>();

    concepts.forEach((concept) => {
      const fromPos = positions.get(concept.id);
      if (!fromPos) return;

      concept.relatedConceptIds.forEach((relatedId) => {
        const toPos = positions.get(relatedId);
        if (!toPos) return;

        const pairKey = [concept.id, relatedId].sort().join("::");
        if (seen.has(pairKey)) return;
        seen.add(pairKey);

        const isRelated = selectedConceptId
          ? selectedConceptId === concept.id || selectedConceptId === relatedId
          : false;

        lines.push({
          fromId: concept.id,
          toId: relatedId,
          isRelated,
          points: [fromPos, toPos],
        });
      });
    });

    return lines;
  }, [concepts, positions, selectedConceptId]);

  return (
    <group>
      {connections.map((conn, idx) => {
        const color = conn.isRelated ? "#60a5fa" : "#334155";
        const opacity = conn.isRelated ? 0.9 : selectedConceptId ? 0.15 : 0.45;
        const lineWidth = conn.isRelated ? 2.5 : 1;

        return (
          <Line
            key={`connection-${conn.fromId}-${conn.toId}-${idx}`}
            points={conn.points}
            color={color}
            transparent
            opacity={opacity}
            lineWidth={lineWidth}
          />
        );
      })}
    </group>
  );
}
