"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ConceptCell as ConceptCellType, GapReport, UnderstandingLayer } from "@/types/gapReport";
import { IsometricLayer } from "./IsometricLayer";
import { MapControls } from "./MapControls";
import { ConceptListFallback } from "./ConceptListFallback";

export interface IsometricKnowledgeMapProps {
  report: GapReport;
  selectedConcept: ConceptCellType | null;
  isExploded: boolean;
  focusGaps: boolean;
  onSelectConcept: (concept: ConceptCellType) => void;
  onToggleExplode: () => void;
  onReset: () => void;
  onToggleFocusGaps: () => void;
  onShowAll: () => void;
}

export function IsometricKnowledgeMap({
  report,
  selectedConcept,
  isExploded,
  focusGaps,
  onSelectConcept,
  onToggleExplode,
  onReset,
  onToggleFocusGaps,
  onShowAll,
}: IsometricKnowledgeMapProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Group concepts by layer
  const layer1Concepts = report.concepts.filter((c) => c.layer === "DEFINITION");
  const layer2Concepts = report.concepts.filter((c) => c.layer === "MECHANISM");
  const layer3Concepts = report.concepts.filter((c) => c.layer === "APPLICATION");
  const layer4Concepts = report.concepts.filter((c) => c.layer === "EDGE_CASES");

  const hasGapInLayer = (concepts: ConceptCellType[]) =>
    concepts.some((c) => c.status === "GAP" || c.status === "MISCONCEPTION");

  const effectiveExploded = isExploded || isHovered;

  return (
    <div
      className="relative w-full h-[520px] md:h-[600px] bg-white border border-fog rounded-[6px] shadow-sm overflow-hidden flex flex-col items-center justify-center select-none"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => {
        // Mobile toggle explosion
        if (window.innerWidth < 768) {
          onToggleExplode();
        }
      }}
      aria-label={`Knowledge map for ${report.topicName}`}
    >
      {/* Visual Subtitle / Caption */}
      <div className="absolute top-4 left-4 z-10">
        <span className="font-mono text-[10px] uppercase tracking-wider text-navy/50 font-bold block">
          ISOMETRIC KNOWLEDGE MAP
        </span>
        <span className="font-mono text-[11px] text-navy/70">
          {effectiveExploded ? "EXPLODED VIEW · 4 LAYERS" : "HOVER OR TAP TO EXPLODE"}
        </span>
      </div>

      {/* SVG Container with Isometric Projection */}
      <div className="w-full h-full flex items-center justify-center p-4">
        <motion.svg
          viewBox="-120 -100 540 480"
          className="w-full h-full max-h-[520px] overflow-visible"
          animate={{
            scale: focusGaps ? 1.1 : 1,
          }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
        >
          <defs>
            {/* Gap hatching pattern: orange diagonal stripes */}
            <pattern
              id="gap-hatch"
              patternUnits="userSpaceOnUse"
              width="8"
              height="8"
              patternTransform="rotate(-45)"
            >
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="8"
                stroke="#FF6B1A"
                strokeWidth="2.5"
              />
            </pattern>
          </defs>

          {/* Isometric projection group: skewX(-30deg) scaleY(0.866) */}
          <g
            transform="translate(140, 110) skewX(-30) scale(1, 0.866)"
            className="transition-transform duration-300"
          >
            {/* Layer 1: DEFINITION (bottom) */}
            <IsometricLayer
              layerIndex={1}
              layerName="DEFINITION"
              displayName="DEFINITION"
              concepts={layer1Concepts}
              selectedConceptId={selectedConcept?.id}
              isExploded={effectiveExploded}
              isDimmedByFocus={focusGaps && !hasGapInLayer(layer1Concepts)}
              onSelectConcept={onSelectConcept}
              yBase={90}
            />

            {/* Layer 2: MECHANISM */}
            <IsometricLayer
              layerIndex={2}
              layerName="MECHANISM"
              displayName="MECHANISM"
              concepts={layer2Concepts}
              selectedConceptId={selectedConcept?.id}
              isExploded={effectiveExploded}
              isDimmedByFocus={focusGaps && !hasGapInLayer(layer2Concepts)}
              onSelectConcept={onSelectConcept}
              yBase={45}
            />

            {/* Layer 3: APPLICATION */}
            <IsometricLayer
              layerIndex={3}
              layerName="APPLICATION"
              displayName="APPLICATION"
              concepts={layer3Concepts}
              selectedConceptId={selectedConcept?.id}
              isExploded={effectiveExploded}
              isDimmedByFocus={focusGaps && !hasGapInLayer(layer3Concepts)}
              onSelectConcept={onSelectConcept}
              yBase={0}
            />

            {/* Layer 4: EDGE CASES (top) */}
            <IsometricLayer
              layerIndex={4}
              layerName="EDGE_CASES"
              displayName="EDGE CASES"
              concepts={layer4Concepts}
              selectedConceptId={selectedConcept?.id}
              isExploded={effectiveExploded}
              isDimmedByFocus={focusGaps && !hasGapInLayer(layer4Concepts)}
              onSelectConcept={onSelectConcept}
              yBase={-45}
            />
          </g>
        </motion.svg>
      </div>

      {/* Map Controls (bottom right overlay) */}
      <div className="absolute bottom-4 right-4 z-20">
        <MapControls
          focusGaps={focusGaps}
          onReset={onReset}
          onToggleFocusGaps={onToggleFocusGaps}
          onShowAll={onShowAll}
        />
      </div>

      {/* Screen reader fallback list */}
      <ConceptListFallback concepts={report.concepts} />
    </div>
  );
}
