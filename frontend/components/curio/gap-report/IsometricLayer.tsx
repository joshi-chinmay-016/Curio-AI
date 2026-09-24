"use client";

import React from "react";
import { motion } from "framer-motion";
import { ConceptCell as ConceptCellType, UnderstandingLayer } from "@/types/gapReport";
import { ConceptCell } from "./ConceptCell";

export interface IsometricLayerProps {
  layerIndex: 1 | 2 | 3 | 4;
  layerName: UnderstandingLayer;
  displayName: string;
  concepts: ConceptCellType[];
  selectedConceptId?: string;
  isExploded: boolean;
  isDimmedByFocus: boolean;
  onSelectConcept: (concept: ConceptCellType) => void;
  yBase: number;
}

export function IsometricLayer({
  layerIndex,
  layerName,
  displayName,
  concepts,
  selectedConceptId,
  isExploded,
  isDimmedByFocus,
  onSelectConcept,
  yBase,
}: IsometricLayerProps) {
  // Layer offsets when exploded
  // Layer 4: translateY(-80px) + translateX(+20px)
  // Layer 3: translateY(-40px) + translateX(+10px)
  // Layer 2: reference (stays)
  // Layer 1: translateY(+40px) + translateX(-10px)
  let explodedX = 0;
  let explodedY = 0;

  if (layerIndex === 4) {
    explodedX = 20;
    explodedY = -80;
  } else if (layerIndex === 3) {
    explodedX = 10;
    explodedY = -40;
  } else if (layerIndex === 2) {
    explodedX = 0;
    explodedY = 0;
  } else if (layerIndex === 1) {
    explodedX = -10;
    explodedY = 40;
  }

  const springTransition = {
    type: "spring" as const,
    stiffness: 300,
    damping: 20,
  };

  // 2x2 grid of cells on each layer
  // Grid layout:
  // Cell 0: (gridX: 0, gridY: 0) -> x: 0, y: 0
  // Cell 1: (gridX: 1, gridY: 0) -> x: 120, y: 0
  // Cell 2: (gridX: 0, gridY: 1) -> x: 0, y: 65
  // Cell 3: (gridX: 1, gridY: 1) -> x: 120, y: 65

  return (
    <motion.g
      initial={false}
      animate={{
        x: isExploded ? explodedX : 0,
        y: (isExploded ? explodedY : 0) + yBase,
        opacity: isDimmedByFocus ? 0.25 : 1,
      }}
      transition={springTransition}
    >
      {/* Side face label background & border */}
      <g transform="translate(-80, 20)">
        <rect
          x="0"
          y="0"
          width="72"
          height="22"
          fill="#0F2B4A"
          rx="2"
        />
        <text
          x="36"
          y="15"
          textAnchor="middle"
          fill="#FFFFFF"
          fontFamily="var(--font-mono), monospace"
          fontSize="9"
          fontWeight="bold"
          letterSpacing="0.05em"
          className="select-none pointer-events-none"
        >
          {displayName}
        </text>
      </g>

      {/* Layer Base Plate */}
      <rect
        x="-5"
        y="-5"
        width="245"
        height="135"
        fill="#FFFFFF"
        stroke="#0F2B4A"
        strokeWidth="1.5"
        rx="4"
        opacity="0.9"
      />

      {/* Cells on this layer */}
      {concepts.map((concept, idx) => {
        const gx = concept.gridX !== undefined ? concept.gridX : idx % 2;
        const gy = concept.gridY !== undefined ? concept.gridY : Math.floor(idx / 2);
        const cellX = gx * 118 + 5;
        const cellY = gy * 62 + 5;

        const isSelected = selectedConceptId === concept.id;
        const isDimmed =
          Boolean(selectedConceptId) && selectedConceptId !== concept.id;

        return (
          <ConceptCell
            key={concept.id}
            concept={concept}
            isSelected={isSelected}
            isDimmed={isDimmed}
            onClick={onSelectConcept}
            x={cellX}
            y={cellY}
            width={112}
            height={56}
          />
        );
      })}
    </motion.g>
  );
}
