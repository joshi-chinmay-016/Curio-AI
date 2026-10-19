"use client";

import React from "react";
import { motion } from "framer-motion";

export interface BrokenTraceProps {
  startX: number;
  endX: number;
  y: number;
  isSelected?: boolean;
  isFocusGaps?: boolean;
}

export function BrokenTrace({
  startX,
  endX,
  y,
  isSelected = false,
  isFocusGaps = false,
}: BrokenTraceProps) {
  const midX = Math.round((startX + endX) / 2);
  const breakRadius = 8;
  const markerColor = isSelected ? "#FFFFFF" : "#FF6B1A";
  const markerScale = isFocusGaps ? 1.5 : isSelected ? 1.3 : 1.0;

  return (
    <g className="broken-trace-group select-none pointer-events-none">
      {/* Left Orange Segment */}
      <line
        x1={startX}
        y1={y}
        x2={midX - breakRadius - 4}
        y2={y}
        stroke="#FF6B1A"
        strokeWidth={2}
        strokeLinecap="round"
      />

      {/* Break Marker (✕ spark) with subtle idle flicker */}
      <motion.g
        transform={`translate(${midX}, ${y})`}
        animate={{
          scale: markerScale,
        }}
        transition={{ duration: 0.2 }}
        className="break-marker-spark"
      >
        {/* Glow behind break point */}
        <circle
          cx={0}
          cy={0}
          r={7}
          fill="rgba(255, 107, 26, 0.2)"
        />

        {/* 12×12px ✕ Marker */}
        <line
          x1={-5}
          y1={-5}
          x2={5}
          y2={5}
          stroke={markerColor}
          strokeWidth={2.2}
          strokeLinecap="round"
        />
        <line
          x1={5}
          y1={-5}
          x2={-5}
          y2={5}
          stroke={markerColor}
          strokeWidth={2.2}
          strokeLinecap="round"
        />
      </motion.g>

      {/* Right Orange Dashed Segment leading into the gap node */}
      <line
        x1={midX + breakRadius + 4}
        y1={y}
        x2={endX}
        y2={y}
        stroke="#FF6B1A"
        strokeWidth={2}
        strokeDasharray="4 3"
        strokeLinecap="round"
      />
    </g>
  );
}

export default BrokenTrace;
