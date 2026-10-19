"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ConceptCell as ConceptCellType } from "@/types/gapReport";

export interface ViaConnectionsProps {
  concepts: ConceptCellType[];
  nodePositions: Record<string, { x: number; y: number; width: number }>;
  selectedId: string | null;
  isFocusGaps?: boolean;
}

export function ViaConnections({
  concepts,
  nodePositions,
  selectedId,
  isFocusGaps = false,
}: ViaConnectionsProps) {
  // Collect all unique cross-layer connection pairs
  const connections = React.useMemo(() => {
    const list: {
      key: string;
      source: ConceptCellType;
      target: ConceptCellType;
      start: { x: number; y: number };
      end: { x: number; y: number };
      isHighlighted: boolean;
    }[] = [];

    const seen = new Set<string>();

    concepts.forEach((concept) => {
      const startPos = nodePositions[concept.id];
      if (!startPos) return;

      (concept.relatedConceptIds || []).forEach((relId) => {
        const target = concepts.find((c) => c.id === relId);
        const endPos = nodePositions[relId];
        if (!target || !endPos) return;

        // Only draw via connections across different layers or distant nodes
        const pairKey = [concept.id, relId].sort().join("-");
        if (seen.has(pairKey)) return;
        seen.add(pairKey);

        const isHighlighted =
          selectedId === concept.id || selectedId === target.id;

        // Anchor points at top or bottom edge of nodes
        const isTargetBelow = endPos.y > startPos.y;
        const startX = startPos.x + startPos.width / 2;
        const startY = isTargetBelow ? startPos.y + 18 : startPos.y - 18;

        const endX = endPos.x + endPos.width / 2;
        const endY = isTargetBelow ? endPos.y - 18 : endPos.y + 18;

        list.push({
          key: pairKey,
          source: concept,
          target,
          start: { x: startX, y: startY },
          end: { x: endX, y: endY },
          isHighlighted,
        });
      });
    });

    return list;
  }, [concepts, nodePositions, selectedId]);

  if (connections.length === 0) return null;

  return (
    <g className="via-connections-layer pointer-events-none select-none">
      {connections.map(({ key, start, end, isHighlighted }) => {
        // If Focus Gaps mode is active and this connection is not highlighted, hide it
        if (isFocusGaps && !isHighlighted) return null;

        // S-curve PCB trace connecting the two vias
        const midY = (start.y + end.y) / 2;
        const pathData = `M ${start.x} ${start.y} C ${start.x} ${midY}, ${end.x} ${midY}, ${end.x} ${end.y}`;

        const strokeColor = isHighlighted ? "#3A63FF" : "#C4CDD6";
        const strokeOpacity = isHighlighted ? 0.95 : 0.35;
        const strokeWidth = isHighlighted ? 2.0 : 1.0;
        const strokeDasharray = isHighlighted ? "none" : "3 3";

        return (
          <g key={key}>
            {/* PCB Trace Path */}
            <motion.path
              d={pathData}
              fill="none"
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeOpacity={strokeOpacity}
              strokeDasharray={strokeDasharray}
              initial={false}
              animate={{
                stroke: strokeColor,
                strokeOpacity,
                strokeWidth,
              }}
              transition={{ duration: 0.3 }}
            />

            {/* Start Via Ring */}
            <circle
              cx={start.x}
              cy={start.y}
              r={isHighlighted ? 3.5 : 2.5}
              fill={isHighlighted ? "#3A63FF" : "#0F2B4A"}
              stroke={strokeColor}
              strokeWidth={1.2}
            />

            {/* End Via Ring */}
            <circle
              cx={end.x}
              cy={end.y}
              r={isHighlighted ? 3.5 : 2.5}
              fill={isHighlighted ? "#3A63FF" : "#0F2B4A"}
              stroke={strokeColor}
              strokeWidth={1.2}
            />
          </g>
        );
      })}
    </g>
  );
}

export default ViaConnections;
