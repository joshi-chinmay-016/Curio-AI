"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import {
  ConceptCell as ConceptCellType,
  GapReport,
  UnderstandingLayer,
} from "@/types/gapReport";
import { CircuitHeader } from "./CircuitHeader";
import { CircuitNode } from "./CircuitNode";
import { BrokenTrace } from "./BrokenTrace";
import { ViaConnections } from "./ViaConnections";
import { LayerHealthPill } from "./LayerHealthPill";
import { MapControls } from "./MapControls";
import { ConceptListFallback } from "./ConceptListFallback";

export interface IsometricKnowledgeMapProps {
  report: GapReport;
  selectedConcept?: ConceptCellType | null;
  selectedConceptId?: string | null;
  selectedLayer?: UnderstandingLayer | null;
  isExploded?: boolean;
  focusGaps?: boolean;
  isFocusGaps?: boolean;
  showLayerLabels?: boolean;
  onSelectConcept: (concept: ConceptCellType) => void;
  onSelectLayer?: (layer: UnderstandingLayer | null) => void;
  onToggleExplode?: () => void;
  onReset?: () => void;
  onResetView?: () => void;
  onToggleFocusGaps?: () => void;
  onShowAll?: () => void;
}

export function IsometricKnowledgeMap({
  report,
  selectedConcept: propSelectedConcept,
  selectedConceptId: propSelectedConceptId,
  selectedLayer: propSelectedLayer,
  isExploded: propIsExploded,
  focusGaps: propFocusGaps,
  isFocusGaps: propIsFocusGaps,
  showLayerLabels = true,
  onSelectConcept,
  onSelectLayer,
  onToggleExplode,
  onReset,
  onResetView,
  onToggleFocusGaps,
  onShowAll,
}: IsometricKnowledgeMapProps) {
  const shouldReduceMotion = useReducedMotion();

  // Unified internal/external state handling
  const [internalFocusGaps, setInternalFocusGaps] = useState(false);
  const [radarKey, setRadarKey] = useState(0);

  // Resolve active concept
  const activeSelectedConceptId =
    propSelectedConceptId !== undefined
      ? propSelectedConceptId
      : propSelectedConcept
      ? propSelectedConcept.id
      : null;

  const activeSelectedConcept = useMemo(() => {
    if (propSelectedConcept) return propSelectedConcept;
    if (activeSelectedConceptId) {
      return report.concepts.find((c) => c.id === activeSelectedConceptId) || null;
    }
    return null;
  }, [propSelectedConcept, activeSelectedConceptId, report.concepts]);

  // Resolve focus gaps state
  const effectiveFocusGaps =
    propFocusGaps !== undefined
      ? propFocusGaps
      : propIsFocusGaps !== undefined
      ? propIsFocusGaps
      : internalFocusGaps;

  // Group concepts by layer
  const conceptsByLayer = useMemo(() => {
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

  // Total gaps count
  const gapCount = useMemo(() => {
    const detected = report.concepts.filter(
      (c) => c.status === "GAP" || c.status === "MISCONCEPTION"
    ).length;
    return detected || report.knowledgeGaps || 0;
  }, [report.concepts, report.knowledgeGaps]);

  // Reset Handler
  const handleReset = () => {
    setInternalFocusGaps(false);
    if (onReset) onReset();
    if (onResetView) onResetView();
  };

  // Focus Gaps Toggle Handler
  const handleToggleFocusGaps = () => {
    const nextState = !effectiveFocusGaps;
    if (nextState) {
      setRadarKey((prev) => prev + 1); // trigger radar sweep once
    }
    if (onToggleFocusGaps) {
      onToggleFocusGaps();
    } else {
      setInternalFocusGaps(nextState);
    }
  };

  // Show All Handler
  const handleShowAll = () => {
    setInternalFocusGaps(false);
    if (onShowAll) onShowAll();
  };

  // 4 Layer Row Definitions
  const layerRows: {
    layer: UnderstandingLayer;
    index: 1 | 2 | 3 | 4;
    y: number;
  }[] = [
    { layer: "DEFINITION", index: 1, y: 65 },
    { layer: "MECHANISM", index: 2, y: 155 },
    { layer: "APPLICATION", index: 3, y: 245 },
    { layer: "EDGE_CASES", index: 4, y: 335 },
  ];

  // Calculate layout geometry for concept nodes and horizontal traces
  // SVG Canvas dimensions: 760px width × 400px height
  const nodePositions = useMemo(() => {
    const pos: Record<string, { x: number; y: number; width: number }> = {};

    const trackStartX = 185;
    const trackEndX = 680;
    const availableWidth = trackEndX - trackStartX;

    layerRows.forEach(({ layer, y }) => {
      const concepts = conceptsByLayer[layer] || [];
      const count = concepts.length;
      if (count === 0) return;

      const spacing = availableWidth / count;

      concepts.forEach((concept, i) => {
        // Node width based on name length: min 95px, max 130px
        const nameLen = Math.min(14, concept.name.length);
        const nodeWidth = Math.max(95, Math.min(130, nameLen * 7.5 + 34));
        const center = trackStartX + spacing * (i + 0.5);
        const nodeX = Math.round(center - nodeWidth / 2);

        pos[concept.id] = {
          x: nodeX,
          y,
          width: nodeWidth,
        };
      });
    });

    return pos;
  }, [conceptsByLayer]);

  // Set of related concept IDs for the selected concept
  const relatedConceptSet = useMemo(() => {
    if (!activeSelectedConcept) return new Set<string>();
    return new Set(activeSelectedConcept.relatedConceptIds || []);
  }, [activeSelectedConcept]);

  return (
    <div
      className="relative w-full h-[520px] md:h-[580px] rounded-[8px] overflow-hidden flex flex-col justify-between p-5 md:p-6 select-none"
      style={{
        backgroundColor: "#0F2B4A",
        backgroundImage: "radial-gradient(circle, #1a3d5c 1px, transparent 1px)",
        backgroundSize: "20px 20px",
        border: "1px solid rgba(58, 99, 255, 0.25)",
      }}
      aria-label={`Knowledge Circuit for ${report.topicName}`}
    >
      {/* Scoped CSS Keyframe Animations for Circuit Effects */}
      <style jsx global>{`
        @keyframes gapPulseRing {
          0%, 100% {
            stroke-opacity: 0.8;
            stroke-width: 1.5px;
          }
          50% {
            stroke-opacity: 0.15;
            stroke-width: 5px;
          }
        }
        .gap-pulse-ring {
          animation: gapPulseRing 2s ease-in-out infinite;
        }

        @keyframes developingPulse {
          0%, 100% {
            stroke-opacity: 0.6;
          }
          50% {
            stroke-opacity: 1;
          }
        }
        .developing-pulse-node {
          animation: developingPulse 2s ease-in-out infinite;
        }

        @keyframes traceFlicker {
          0%, 95%, 100% {
            opacity: 1;
          }
          96% {
            opacity: 0.3;
          }
          98% {
            opacity: 0.7;
          }
        }
        .break-marker-spark {
          animation: traceFlicker 3s infinite;
        }

        @keyframes radarSweepAnim {
          0% {
            top: 0%;
            opacity: 0.8;
          }
          100% {
            top: 100%;
            opacity: 0;
          }
        }
        .radar-sweep-bar {
          position: absolute;
          left: 0;
          right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent, #ff6b1a, transparent);
          box-shadow: 0 0 12px #ff6b1a;
          animation: radarSweepAnim 1s ease-out forwards;
          pointer-events: none;
          z-index: 25;
        }

        @media (prefers-reduced-motion: reduce) {
          .gap-pulse-ring,
          .developing-pulse-node,
          .break-marker-spark,
          .radar-sweep-bar {
            animation: none !important;
          }
        }
      `}</style>

      {/* Focus Gaps Radar Sweep Line (plays once when activated) */}
      {effectiveFocusGaps && !shouldReduceMotion && (
        <div key={`radar-${radarKey}`} className="radar-sweep-bar" />
      )}

      {/* Circuit Header */}
      <CircuitHeader
        topicName={report.topicName}
        overallScore={report.understandingScore}
        gapCount={gapCount}
        isFocusGaps={effectiveFocusGaps}
      />

      {/* SVG Circuit Board Canvas */}
      <div className="w-full flex-1 flex items-center justify-center overflow-hidden">
        <svg
          viewBox="0 0 760 390"
          className="w-full h-full max-h-[460px] overflow-visible"
        >
          {/* Vertical Via Connections between related concepts */}
          <ViaConnections
            concepts={report.concepts}
            nodePositions={nodePositions}
            selectedId={activeSelectedConceptId}
            isFocusGaps={effectiveFocusGaps}
          />

          {/* 4 Layer Horizontal Circuit Tracks */}
          {layerRows.map(({ layer, index, y }, layerIdx) => {
            const concepts = conceptsByLayer[layer] || [];
            const trackStartX = 185;
            const trackEndX = 680;

            // Calculate layer understanding score
            const valid = concepts.filter(
              (c) => typeof c.score === "number" && c.status !== "UNTESTED"
            );
            const layerScore =
              valid.length > 0
                ? Math.round(valid.reduce((acc, c) => acc + c.score, 0) / valid.length)
                : 70;

            // Score badge color: cobalt (>70%), white (50-70%), orange (<50%)
            let scoreColor = "#3A63FF";
            if (layerScore < 50) scoreColor = "#FF6B1A";
            else if (layerScore <= 70) scoreColor = "#FFFFFF";

            return (
              <motion.g
                key={layer}
                initial={shouldReduceMotion ? false : { opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.45,
                  delay: layerIdx * 0.08,
                  ease: "easeOut",
                }}
                className="circuit-layer-row"
              >
                {/* Left Side: Layer Health Pill & Label */}
                <foreignObject x={10} y={y - 14} width={165} height={28}>
                  <LayerHealthPill
                    layerName={layer}
                    layerIndex={index}
                    concepts={concepts}
                    score={layerScore}
                  />
                </foreignObject>

                {/* Right Side: Score Badge ("85%") */}
                <text
                  x={715}
                  y={y + 4}
                  textAnchor="middle"
                  fill={scoreColor}
                  fontFamily="var(--font-mono), 'IBM Plex Mono', monospace"
                  fontSize="11"
                  fontWeight="bold"
                  className="select-none pointer-events-none"
                >
                  {layerScore}%
                </text>

                {/* Horizontal Circuit Traces between nodes */}
                {concepts.length > 0 && (
                  <g className="traces-layer">
                    {/* Track start segment before the first node */}
                    {(() => {
                      const firstNode = nodePositions[concepts[0].id];
                      if (!firstNode) return null;
                      const isFirstGap =
                        concepts[0].status === "GAP" ||
                        concepts[0].status === "MISCONCEPTION";

                      if (isFirstGap) {
                        return (
                          <BrokenTrace
                            startX={trackStartX}
                            endX={firstNode.x}
                            y={y}
                            isSelected={activeSelectedConceptId === concepts[0].id}
                            isFocusGaps={effectiveFocusGaps}
                          />
                        );
                      }

                      return (
                        <line
                          x1={trackStartX}
                          y1={y}
                          x2={firstNode.x}
                          y2={y}
                          stroke="#3A63FF"
                          strokeWidth={2}
                          strokeOpacity={effectiveFocusGaps ? 0.15 : 0.7}
                        />
                      );
                    })()}

                    {/* Traces between adjacent nodes */}
                    {concepts.map((concept, i) => {
                      if (i === concepts.length - 1) return null;
                      const nextConcept = concepts[i + 1];
                      const currentPos = nodePositions[concept.id];
                      const nextPos = nodePositions[nextConcept.id];
                      if (!currentPos || !nextPos) return null;

                      const startX = currentPos.x + currentPos.width;
                      const endX = nextPos.x;

                      const nextIsGap =
                        nextConcept.status === "GAP" ||
                        nextConcept.status === "MISCONCEPTION";

                      // Broken Trace before a gap node
                      if (nextIsGap) {
                        return (
                          <BrokenTrace
                            key={`broken-${concept.id}-${nextConcept.id}`}
                            startX={startX}
                            endX={endX}
                            y={y}
                            isSelected={activeSelectedConceptId === nextConcept.id}
                            isFocusGaps={effectiveFocusGaps}
                          />
                        );
                      }

                      // Normal Trace
                      const isUntested =
                        concept.status === "UNTESTED" ||
                        nextConcept.status === "UNTESTED";

                      return (
                        <line
                          key={`trace-${concept.id}-${nextConcept.id}`}
                          x1={startX}
                          y1={y}
                          x2={endX}
                          y2={y}
                          stroke={isUntested ? "#C4CDD6" : "#3A63FF"}
                          strokeWidth={isUntested ? 1 : 2}
                          strokeDasharray={isUntested ? "4 4" : undefined}
                          strokeOpacity={
                            effectiveFocusGaps ? 0.08 : isUntested ? 0.4 : 0.8
                          }
                        />
                      );
                    })}

                    {/* Track end segment after the last node */}
                    {(() => {
                      const lastConcept = concepts[concepts.length - 1];
                      const lastPos = nodePositions[lastConcept.id];
                      if (!lastPos) return null;
                      const startX = lastPos.x + lastPos.width;

                      return (
                        <line
                          x1={startX}
                          y1={y}
                          x2={trackEndX}
                          y2={y}
                          stroke="#3A63FF"
                          strokeWidth={2}
                          strokeOpacity={effectiveFocusGaps ? 0.15 : 0.7}
                        />
                      );
                    })()}
                  </g>
                )}

                {/* Concept Nodes (The IC Chips on the Board) */}
                {concepts.map((concept) => {
                  const pos = nodePositions[concept.id];
                  if (!pos) return null;

                  const isSelected = activeSelectedConceptId === concept.id;
                  const isRelated = relatedConceptSet.has(concept.id);

                  return (
                    <CircuitNode
                      key={concept.id}
                      concept={concept}
                      isSelected={isSelected}
                      isRelatedToSelected={isRelated}
                      isAnySelected={Boolean(activeSelectedConceptId)}
                      isFocusGaps={effectiveFocusGaps}
                      onClick={onSelectConcept}
                      x={pos.x}
                      y={pos.y}
                      width={pos.width}
                    />
                  );
                })}
              </motion.g>
            );
          })}
        </svg>
      </div>

      {/* Map Controls Keycap Strip (Bottom Right of Circuit Board) */}
      <div className="flex items-center justify-between w-full pt-3 border-t border-cobalt/20 z-10">
        <span className="font-mono text-[9px] uppercase tracking-wider text-fog/50">
          Curio Connected Knowledge Engine
        </span>
        <MapControls
          focusGaps={effectiveFocusGaps}
          onReset={handleReset}
          onToggleFocusGaps={handleToggleFocusGaps}
          onShowAll={handleShowAll}
        />
      </div>

      {/* Screen Reader Accessible Fallback */}
      <ConceptListFallback report={report} onSelectConcept={onSelectConcept} />
    </div>
  );
}

// Named alias for direct KnowledgeCircuit imports
export const KnowledgeCircuit = IsometricKnowledgeMap;

export default IsometricKnowledgeMap;
