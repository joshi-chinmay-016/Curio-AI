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
  selectedConceptId?: string | null;
  isLayerSelected: boolean;
  isExploded: boolean;
  isFocusGaps: boolean;
  onSelectConcept: (concept: ConceptCellType) => void;
  yBase: number;
  triggerResetBounce?: boolean;
}

export function IsometricLayer({
  layerIndex,
  layerName,
  displayName,
  concepts,
  selectedConceptId,
  isLayerSelected,
  isExploded,
  isFocusGaps,
  onSelectConcept,
  yBase,
  triggerResetBounce = false,
}: IsometricLayerProps) {
  // Layer numbering prefixes
  const prefixMap: Record<number, string> = {
    1: "01",
    2: "02",
    3: "03",
    4: "04",
  };
  const fullLabel = `${prefixMap[layerIndex]} ${displayName}`;

  // Dimensions of the layer slab
  const layerWidth = 328;
  const layerHeight = 78;
  const slabDepth = 16; // 16px screen height depth for physical slab weight

  // Compute average understanding score for this layer
  const validScores = concepts.filter((c) => typeof c.score === "number" && c.status !== "UNTESTED");
  const layerScore =
    validScores.length > 0
      ? Math.round(validScores.reduce((acc, c) => acc + c.score, 0) / validScores.length)
      : concepts.length > 0
      ? Math.round(concepts.reduce((acc, c) => acc + (c.score || 0), 0) / concepts.length)
      : 70;

  // Badge & progress bar colors
  let badgeColor = "#3A63FF"; // Cobalt (>=80%)
  if (layerScore < 50) {
    badgeColor = "#FF6B1A"; // Orange (<50%)
  } else if (layerScore < 80) {
    badgeColor = "#0F2B4A"; // Navy (50-79%)
  }

  // Layer offsets
  // Standard exploded offsets from spec:
  // Layer 4 (EDGE CASES):  translateY(-120px) translateX(+28px)
  // Layer 3 (APPLICATION): translateY(-60px)  translateX(+14px)
  // Layer 2 (MECHANISM):   translateY(0)      translateX(0)
  // Layer 1 (DEFINITION):  translateY(+60px)  translateX(-14px)
  // Collapsed: tightly stacked (8px separation)
  let explodedX = 0;
  let explodedY = 0;
  let collapsedY = 0;

  if (layerIndex === 4) {
    explodedX = 28;
    explodedY = -120;
    collapsedY = -16;
  } else if (layerIndex === 3) {
    explodedX = 14;
    explodedY = -60;
    collapsedY = -8;
  } else if (layerIndex === 2) {
    explodedX = 0;
    explodedY = 0;
    collapsedY = 0;
  } else if (layerIndex === 1) {
    explodedX = -14;
    explodedY = 60;
    collapsedY = 8;
  }

  // In Focus Gaps mode: separation increases by 20% extra
  if (isFocusGaps) {
    explodedX = Math.round(explodedX * 1.2);
    explodedY = Math.round(explodedY * 1.2);
  }

  // Selected layer moves 20px further from neighbors for extra visual emphasis
  if (isLayerSelected) {
    if (layerIndex === 4) explodedY -= 20;
    else if (layerIndex === 3) explodedY -= 15;
    else if (layerIndex === 1) explodedY += 20;
  }

  const targetX = isExploded ? explodedX : 0;
  const targetY = isExploded ? explodedY + yBase : collapsedY + yBase;

  // Spring physics from spec: { stiffness: 280, damping: 22, mass: 0.8 }
  const springTransition = {
    type: "spring" as const,
    stiffness: 280,
    damping: 22,
    mass: 0.8,
  };

  // Populate 4 columns × 2 rows = 8 concept cells
  // If fewer than 8 exist in data, fill with UNTESTED cells
  const gridCells: ConceptCellType[] = [];
  const assigned = new Set<string>();

  // Place concepts with explicit gridX/gridY first
  const matrix: (ConceptCellType | null)[][] = [
    [null, null, null, null],
    [null, null, null, null],
  ];

  concepts.forEach((c) => {
    if (
      c.gridX !== undefined &&
      c.gridY !== undefined &&
      c.gridX >= 0 &&
      c.gridX < 4 &&
      c.gridY >= 0 &&
      c.gridY < 2 &&
      !matrix[c.gridY][c.gridX]
    ) {
      matrix[c.gridY][c.gridX] = c;
      assigned.add(c.id);
    }
  });

  // Place remaining concepts in next available empty slots
  concepts.forEach((c) => {
    if (!assigned.has(c.id)) {
      outer: for (let r = 0; r < 2; r++) {
        for (let col = 0; col < 4; col++) {
          if (!matrix[r][col]) {
            matrix[r][col] = c;
            assigned.add(c.id);
            break outer;
          }
        }
      }
    }
  });

  // Fill empty slots with UNTESTED placeholder cells
  for (let r = 0; r < 2; r++) {
    for (let col = 0; col < 4; col++) {
      if (matrix[r][col]) {
        gridCells.push(matrix[r][col]!);
      } else {
        gridCells.push({
          id: `untested-${layerName}-${r}-${col}`,
          name: "UNTESTED",
          layer: layerName,
          status: "UNTESTED",
          score: 0,
          confidence: 0,
          relatedConceptIds: [],
          gridX: col,
          gridY: r,
        });
      }
    }
  }

  // Check if any concept is selected
  const isAnyConceptSelected = Boolean(selectedConceptId);

  // Geometry calculations for skewed top face:
  // Top face is rendered inside a skewed group with transform="skewX(-30) scale(1, 0.866)"
  // In that skewed coordinate space:
  // Top edge: (0, 0) to (layerWidth, 0)
  // Left edge: (0, 0) to (0, layerHeight)
  // Right edge: (layerWidth, 0) to (layerWidth, layerHeight)
  // Bottom edge: (0, layerHeight) to (layerWidth, layerHeight)
  //
  // Side faces (16px depth):
  // Drawn directly inside the skewed group along bottom edge and left edge!
  // Bottom edge front face: rect from y = layerHeight down to y = layerHeight + slabDepth
  // Left edge side face: navy parallelogram from x = -28 to 0

  return (
    <motion.g
      initial={false}
      animate={{
        x: targetX,
        y: targetY,
      }}
      transition={springTransition}
      className="layer-group select-none"
    >
      {/* Revealed Thin Strata Separator Rule (fog #C4CDD6) when exploded */}
      {isExploded && layerIndex > 1 && (
        <motion.line
          x1="-40"
          y1={layerHeight + 28}
          x2={layerWidth + 20}
          y2={layerHeight + 28}
          stroke="#C4CDD6"
          strokeWidth="1"
          strokeDasharray="4 4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.8 }}
          transition={{ duration: 0.3 }}
          className="pointer-events-none"
        />
      )}

      {/* 3D FRONT SLAB FACE (Visible Bottom Edge Depth: 16px) */}
      <path
        d={`M 0 ${layerHeight} L ${layerWidth} ${layerHeight} L ${layerWidth} ${
          layerHeight + slabDepth
        } L 0 ${layerHeight + slabDepth} Z`}
        fill="#091D33"
        stroke="#0F2B4A"
        strokeWidth="1.2"
      />

      {/* BOTTOM FACE GROUND CONTACT (Only on Layer 1 DEFINITION) */}
      {layerIndex === 1 && (
        <path
          d={`M 0 ${layerHeight + slabDepth} L ${layerWidth} ${
            layerHeight + slabDepth
          } L ${layerWidth + 20} ${layerHeight + slabDepth + 12} L -20 ${
            layerHeight + slabDepth + 12
          } Z`}
          fill="#C4CDD6"
          fillOpacity={0.4}
          stroke="#C4CDD6"
          strokeWidth="0.8"
          strokeDasharray="3 3"
          className="pointer-events-none"
        />
      )}

      {/* 3D RIGHT FACE (Subtle Depth + Progress Bar + Score Badge) */}
      <g transform={`translate(${layerWidth}, 0)`}>
        {/* Right edge depth face */}
        <path
          d={`M 0 0 L 8 4 L 8 ${layerHeight + slabDepth + 4} L 0 ${layerHeight + slabDepth} Z`}
          fill="#0F2B4A"
          fillOpacity={0.3}
          stroke="#0F2B4A"
          strokeWidth="0.8"
        />

        {/* Right Edge Vertical Progress Bar (Width 4px, fills bottom-to-top) */}
        {(() => {
          const barHeight = Math.max(8, Math.round((layerHeight * layerScore) / 100));
          const barY = layerHeight - barHeight;
          return (
            <rect
              x="2"
              y={barY}
              width="4"
              height={barHeight}
              fill={badgeColor}
              rx="1"
              className="pointer-events-none"
            />
          );
        })()}

        {/* Right Edge Layer Score Badge ("XX%") */}
        <motion.g
          transform={`translate(16, ${layerHeight / 2 - 10})`}
          animate={
            triggerResetBounce
              ? { scale: [1, 1.15, 1] }
              : isLayerSelected
              ? { scale: 1.05 }
              : { scale: 1 }
          }
          transition={{ duration: 0.25 }}
        >
          <rect
            x="0"
            y="0"
            width="34"
            height="18"
            fill="#FFFFFF"
            stroke={isLayerSelected ? "#3A63FF" : badgeColor}
            strokeWidth={isLayerSelected ? 2 : 1.2}
            rx="2"
            filter="drop-shadow(0 1px 2px rgba(15, 43, 74, 0.12))"
          />
          <text
            x="17"
            y="12.5"
            textAnchor="middle"
            fill={badgeColor}
            fontFamily="var(--font-mono), 'IBM Plex Mono', monospace"
            fontSize="9"
            fontWeight="bold"
            letterSpacing="0.04em"
          >
            {layerScore}%
          </text>
        </motion.g>
      </g>

      {/* 3D LEFT ISOMETRIC FACE (The Key Depth Element with Navy Slab & Label) */}
      {/* Left Face Parallelogram (Solid Navy #0F2B4A, Height 16px) */}
      <g transform="translate(-32, 0)">
        {/* Navy Left Slab Face */}
        <path
          d={`M 0 0 L 32 0 L 32 ${layerHeight + slabDepth} L 0 ${layerHeight + slabDepth} Z`}
          fill="#0F2B4A"
          stroke="#091D33"
          strokeWidth="1.2"
        />

        {/* Highlight border line on left edge */}
        <line
          x1="0"
          y1="0"
          x2="0"
          y2={layerHeight + slabDepth}
          stroke="#3A63FF"
          strokeWidth={isLayerSelected ? 2.5 : 1}
          strokeOpacity={isLayerSelected ? 0.9 : 0.4}
        />

        {/* Layer Label Inside Left Face */}
        <text
          x={16}
          y={(layerHeight + slabDepth) / 2}
          textAnchor="middle"
          fill="#FFFFFF"
          fontFamily="var(--font-mono), 'IBM Plex Mono', monospace"
          fontSize={isLayerSelected ? "10" : "9"}
          fontWeight="bold"
          letterSpacing="0.12em"
          transform={`rotate(-90, 16, ${(layerHeight + slabDepth) / 2})`}
          className="select-none pointer-events-none"
        >
          {fullLabel}
        </text>
      </g>

      {/* TOP FACE PLATE (White Base Surface with Navy Border) */}
      <rect
        x="0"
        y="0"
        width={layerWidth}
        height={layerHeight}
        fill="#FFFFFF"
        stroke="#0F2B4A"
        strokeWidth="1.5"
        rx="3"
        filter="url(#layer-slab-shadow)"
      />

      {/* 4 COLUMNS × 2 ROWS CONCEPT CELL GRID (8 Cells per Layer) */}
      {gridCells.map((concept, idx) => {
        const col = idx % 4;
        const row = Math.floor(idx / 4);

        // Cell dimensions: width 72px, height 30px, gap 4px
        // Left margin = 10px, top margin = 6px
        const cellX = 10 + col * (72 + 5);
        const cellY = 6 + row * (30 + 4);

        const isSelected = selectedConceptId === concept.id;
        const isInteractive = !concept.id.startsWith("untested-");

        return (
          <ConceptCell
            key={concept.id}
            concept={concept}
            isSelected={isSelected}
            isSameLayerAsSelected={isLayerSelected}
            isAnySelected={isAnyConceptSelected}
            isFocusGaps={isFocusGaps}
            onClick={onSelectConcept}
            x={cellX}
            y={cellY}
            width={72}
            height={30}
            isInteractive={isInteractive}
          />
        );
      })}
    </motion.g>
  );
}

export default IsometricLayer;
