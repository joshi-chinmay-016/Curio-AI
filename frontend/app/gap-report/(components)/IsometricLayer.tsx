"use client";

import React from "react";
import { ConceptCell as ConceptCellType, UnderstandingLayer } from "@/types/gapReport";
import ConceptCell from "./ConceptCell";

interface IsometricLayerProps {
  layer: UnderstandingLayer;
  label: string;
  concepts: ConceptCellType[];
  selectedConceptId: string | null;
  isLayerSelected: boolean;
  isAnyLayerSelected: boolean;
  isFocusGaps: boolean;
  showLayerLabels: boolean;
  onSelectConcept: (concept: ConceptCellType) => void;
  onSelectLayer: (layer: UnderstandingLayer) => void;
}

export default function IsometricLayer({
  layer,
  label,
  concepts,
  selectedConceptId,
  isLayerSelected,
  isAnyLayerSelected,
  isFocusGaps,
  showLayerLabels,
  onSelectConcept,
  onSelectLayer,
}: IsometricLayerProps) {
  const hasGaps = concepts.some(
    (c) => c.status === "GAP" || c.status === "MISCONCEPTION"
  );

  // Original 45° Isometric Dimensions
  const tileSize = 280;
  const depth = 20;

  // Exact 2:1 isometric diamond vertices:
  const leftX = -198;
  const leftY = 0;
  const rightX = 198;
  const rightY = 0;
  const bottomX = 0;
  const bottomY = 115;

  let layerOpacity = 1;
  if (isFocusGaps && !hasGaps) {
    layerOpacity = 0.28;
  } else if (isAnyLayerSelected && !isLayerSelected) {
    layerOpacity = 0.45;
  }

  return (
    <g
      style={{
        opacity: layerOpacity,
        transition: "opacity 0.3s ease",
      }}
    >
      {/* Bottom Drop Shadow */}
      <polygon
        points={`${leftX + 8},${leftY + depth + 14} ${bottomX},${bottomY + depth + 20} ${rightX - 8},${rightY + depth + 14} ${bottomX},${bottomY + 8}`}
        fill="#0F2B4A"
        fillOpacity={0.18}
      />

      {/* Front-Left Depth Side Face (Side Face with Label) */}
      <polygon
        points={`${leftX},${leftY} ${bottomX},${bottomY} ${bottomX},${bottomY + depth} ${leftX},${leftY + depth}`}
        fill="#0F2B4A"
        stroke="#0F2B4A"
        strokeWidth={1}
        style={{ cursor: "pointer" }}
        onClick={(e) => {
          e.stopPropagation();
          onSelectLayer(layer);
        }}
      />

      {/* Front-Right Depth Side Face (Darker Navy for depth shading) */}
      <polygon
        points={`${bottomX},${bottomY} ${rightX},${rightY} ${rightX},${rightY + depth} ${bottomX},${bottomY + depth}`}
        fill="#091B2F"
        stroke="#091B2F"
        strokeWidth={1}
      />

      {/* Side Face Label Text (Angled along front-left face at 30.2°) */}
      {showLayerLabels && (
        <g
          transform={`translate(${leftX + 18}, ${leftY + 14}) rotate(30.2)`}
          style={{ cursor: "pointer", userSelect: "none" }}
          onClick={(e) => {
            e.stopPropagation();
            onSelectLayer(layer);
          }}
        >
          <rect
            x={-4}
            y={-12}
            width={106}
            height={16}
            fill="#0F2B4A"
            rx={3}
          />
          <text
            x={0}
            y={0}
            fontFamily="var(--font-mono), monospace"
            fontSize={9.5}
            fontWeight={700}
            letterSpacing="0.1em"
            fill="#FFFFFF"
          >
            {label}
          </text>
        </g>
      )}

      {/* Top Isometric Face: exact 45 degrees */}
      <g transform="scale(1, 0.58) rotate(-45)">
        {/* Background Tile Base */}
        <rect
          x={0}
          y={0}
          width={tileSize}
          height={tileSize}
          rx={8}
          fill="#E8EEF3"
          stroke="#0F2B4A"
          strokeWidth={1.8}
        />

        {/* Concept Cells inside this Layer Tile */}
        {concepts.map((concept, index) => {
          const cellWidth = 244;
          const cellHeight = 66;
          const cellX = 18;
          const cellY = 18 + index * 82;

          return (
            <ConceptCell
              key={concept.id}
              concept={concept}
              x={cellX}
              y={cellY}
              width={cellWidth}
              height={cellHeight}
              isSelected={selectedConceptId === concept.id}
              isAnySelected={selectedConceptId !== null}
              isFocusGaps={isFocusGaps}
              onSelect={onSelectConcept}
            />
          );
        })}
      </g>
    </g>
  );
}
