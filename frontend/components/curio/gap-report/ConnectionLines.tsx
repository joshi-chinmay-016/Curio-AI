"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ConceptCell as ConceptCellType } from "@/types/gapReport";

export interface CellCoordinate {
  id: string;
  x: number;
  y: number;
}

export interface ConnectionLinesProps {
  selectedConcept: ConceptCellType | null;
  cellPositions: Record<string, { x: number; y: number }>;
}

export function ConnectionLines({
  selectedConcept,
  cellPositions,
}: ConnectionLinesProps) {
  if (!selectedConcept || !selectedConcept.relatedConceptIds || selectedConcept.relatedConceptIds.length === 0) {
    return null;
  }

  const startPos = cellPositions[selectedConcept.id];
  if (!startPos) return null;

  const validTargets = selectedConcept.relatedConceptIds
    .map((targetId) => ({ id: targetId, pos: cellPositions[targetId] }))
    .filter((item): item is { id: string; pos: { x: number; y: number } } => Boolean(item.pos));

  if (validTargets.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="connection-lines-group pointer-events-none"
      >
        {validTargets.map(({ id, pos }) => {
          // Calculate subtle curved path or direct dashed path
          const midX = (startPos.x + pos.x) / 2 + (pos.y > startPos.y ? -15 : 15);
          const midY = (startPos.y + pos.y) / 2;
          const pathData = `M ${startPos.x} ${startPos.y} Q ${midX} ${midY} ${pos.x} ${pos.y}`;

          return (
            <g key={`conn-${selectedConcept.id}-${id}`}>
              {/* Dashed Connecting Line with Marching Ants Flow */}
              <path
                d={pathData}
                fill="none"
                stroke="#3A63FF"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                strokeOpacity="0.75"
              >
                <animate
                  attributeName="stroke-dashoffset"
                  from="8"
                  to="0"
                  dur="1s"
                  repeatCount="indefinite"
                />
              </path>

              {/* Start Node Dot */}
              <circle
                cx={startPos.x}
                cy={startPos.y}
                r="3"
                fill="#3A63FF"
                stroke="#FFFFFF"
                strokeWidth="0.8"
              />

              {/* End Node Dot */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r="3"
                fill="#3A63FF"
                stroke="#FFFFFF"
                strokeWidth="0.8"
              />
            </g>
          );
        })}
      </motion.g>
    </AnimatePresence>
  );
}

export default ConnectionLines;
