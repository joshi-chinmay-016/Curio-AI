"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { GapReport, ConceptCell as ConceptCellType, UnderstandingLayer } from "@/types/gapReport";
import IsometricLayer from "./IsometricLayer";

interface IsometricKnowledgeMapProps {
  report: GapReport;
  selectedConceptId: string | null;
  selectedLayer: UnderstandingLayer | null;
  isFocusGaps: boolean;
  showLayerLabels: boolean;
  onSelectConcept: (concept: ConceptCellType) => void;
  onSelectLayer: (layer: UnderstandingLayer | null) => void;
}

interface LayerDef {
  layer: UnderstandingLayer;
  label: string;
  defaultY: number;
  explodedYOffset: number;
  explodedXOffset: number;
  zIndex: number;
}

const LAYERS: LayerDef[] = [
  // Layer 4 (top) -> EDGE CASES
  {
    layer: "EDGE_CASES",
    label: "EDGE CASES",
    defaultY: 100,
    explodedYOffset: -80,
    explodedXOffset: 20,
    zIndex: 40,
  },
  // Layer 3 -> APPLICATION
  {
    layer: "APPLICATION",
    label: "APPLICATION",
    defaultY: 175,
    explodedYOffset: -40,
    explodedXOffset: 10,
    zIndex: 30,
  },
  // Layer 2 -> MECHANISM (Reference layer)
  {
    layer: "MECHANISM",
    label: "MECHANISM",
    defaultY: 250,
    explodedYOffset: 0,
    explodedXOffset: 0,
    zIndex: 20,
  },
  // Layer 1 (bottom) -> DEFINITION
  {
    layer: "DEFINITION",
    label: "DEFINITION",
    defaultY: 325,
    explodedYOffset: 40,
    explodedXOffset: -10,
    zIndex: 10,
  },
];

export default function IsometricKnowledgeMap({
  report,
  selectedConceptId,
  selectedLayer,
  isFocusGaps,
  showLayerLabels,
  onSelectConcept,
  onSelectLayer,
}: IsometricKnowledgeMapProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isManualExploded, setIsManualExploded] = useState(false);

  const isExploded = isHovered || isManualExploded;

  // Group concepts by layer
  const conceptsByLayer = React.useMemo(() => {
    const map: Record<UnderstandingLayer, ConceptCellType[]> = {
      DEFINITION: [],
      MECHANISM: [],
      APPLICATION: [],
      EDGE_CASES: [],
    };
    report.concepts.forEach((concept) => {
      if (map[concept.layer]) {
        map[concept.layer].push(concept);
      }
    });
    return map;
  }, [report.concepts]);

  return (
    <div
      className="w-full h-full min-h-[460px] flex items-center justify-center relative bg-ice/40 rounded-xl border border-navy/15 overflow-hidden select-none cursor-default"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => {
        // Toggle mobile explosion
        setIsManualExploded(!isManualExploded);
      }}
      aria-label={`Isometric knowledge map for ${report.topicName}. Hover to explode layer stack.`}
    >
      {/* Background Subtle Isometric Grid Watermark */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#0F2B4A_1px,transparent_1px)] [background-size:16px_16px]" />

      {/* SVG Canvas for Isometric Layers */}
      <svg
        viewBox="-280 -20 560 520"
        className="w-full h-full max-w-[640px] max-h-[520px] overflow-visible"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Hatched Orange Diagonal Lines Pattern for Gaps */}
          <pattern
            id="gap-hatch-pattern"
            patternUnits="userSpaceOnUse"
            width="8"
            height="8"
            patternTransform="rotate(-45)"
          >
            <rect width="8" height="8" fill="#FFFFFF" />
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="8"
              stroke="#FF6B1A"
              strokeWidth="2.4"
            />
          </pattern>
        </defs>

        {/* Render Layers from bottom (DEFINITION) to top (EDGE CASES) */}
        {LAYERS.slice().reverse().map((layerDef) => {
          const isSelected = selectedLayer === layerDef.layer;

          // Layer offsets calculation
          let targetY = layerDef.defaultY;
          let targetX = 0;

          if (isExploded) {
            targetY += layerDef.explodedYOffset;
            targetX += layerDef.explodedXOffset;
          }

          if (isSelected) {
            targetX += 20;
            targetY -= 15;
          }

          return (
            <motion.g
              key={layerDef.layer}
              initial={false}
              animate={{
                x: targetX,
                y: targetY,
              }}
              transition={{
                type: "spring",
                stiffness: 280,
                damping: 22,
              }}
            >
              <IsometricLayer
                layer={layerDef.layer}
                label={layerDef.label}
                concepts={conceptsByLayer[layerDef.layer]}
                selectedConceptId={selectedConceptId}
                isLayerSelected={isSelected}
                isAnyLayerSelected={selectedLayer !== null}
                isFocusGaps={isFocusGaps}
                showLayerLabels={showLayerLabels}
                onSelectConcept={onSelectConcept}
                onSelectLayer={(l) => {
                  onSelectLayer(selectedLayer === l ? null : l);
                }}
              />
            </motion.g>
          );
        })}
      </svg>

      {/* Exploded Hint Tag */}
      <div className="absolute bottom-3 left-4 text-[11px] font-mono text-navy/60 pointer-events-none bg-white/80 backdrop-blur-sm px-2.5 py-1 rounded-[4px] border border-navy/10">
        {isExploded ? "⚡ STACK EXPLODED (HOVERING)" : "HOVER OR TAP TO EXPLODE LAYERS"}
      </div>
    </div>
  );
}
