"use client";

import React from "react";
import { motion } from "framer-motion";
import { ConceptCell as ConceptCellType } from "@/types/gapReport";

export interface CircuitNodeProps {
  concept: ConceptCellType;
  isSelected: boolean;
  isRelatedToSelected: boolean;
  isAnySelected: boolean;
  isFocusGaps: boolean;
  onClick: (concept: ConceptCellType) => void;
  x: number;
  y: number;
  width?: number;
}

export function CircuitNode({
  concept,
  isSelected,
  isRelatedToSelected,
  isAnySelected,
  isFocusGaps,
  onClick,
  x,
  y,
  width = 110,
}: CircuitNodeProps) {
  const { status, name, score } = concept;
  const isGap = status === "GAP" || status === "MISCONCEPTION";
  const isMastered = status === "STRONG";
  const isDeveloping = status === "DEVELOPING";
  const isResolved = status === "RESOLVED";
  const isUntested = status === "UNTESTED";

  // Dimming logic
  let opacity = 1.0;
  if (isFocusGaps) {
    if (isGap) opacity = 1.0;
    else if (isUntested) opacity = 0.0;
    else opacity = 0.08;
  } else if (isSelected) {
    opacity = 1.0;
  } else if (isAnySelected) {
    if (isRelatedToSelected) opacity = 0.85;
    else opacity = 0.3;
  }

  // Node background, border, text color
  let bg = "#0F2B4A";
  let border = "#3A63FF";
  let borderWidth = 1.5;
  let textColor = "#FFFFFF";
  let borderStyle = "solid";

  if (isMastered) {
    bg = "#0F2B4A";
    border = "#3A63FF";
    borderWidth = 1.5;
    textColor = "#FFFFFF";
  } else if (isDeveloping) {
    bg = "rgba(58, 99, 255, 0.12)";
    border = "#3A63FF";
    borderWidth = 1.5;
    textColor = "#3A63FF";
  } else if (isGap) {
    bg = "rgba(255, 107, 26, 0.08)";
    border = "#FF6B1A";
    borderWidth = 2;
    textColor = "#FF6B1A";
  } else if (isResolved) {
    bg = "rgba(58, 99, 255, 0.15)";
    border = "#3A63FF";
    borderWidth = 1.5;
    textColor = "#FFFFFF";
  } else if (isUntested) {
    bg = "transparent";
    border = "#C4CDD6";
    borderWidth = 1.5;
    borderStyle = "dashed";
    textColor = "#C4CDD6";
  }

  // Selected overrides
  if (isSelected) {
    border = "#FFFFFF";
    borderWidth = 2.5;
    borderStyle = "solid";
    if (isGap) {
      bg = "#FF6B1A";
      textColor = "#FFFFFF";
    } else if (isDeveloping || isResolved) {
      bg = "#3A63FF";
      textColor = "#FFFFFF";
    } else if (isMastered) {
      bg = "#0F2B4A";
      textColor = "#FFFFFF";
    }
  }

  // Truncate concept name if longer than 14 characters
  const displayName =
    name.length > 14 ? name.slice(0, 13) + "…" : name;

  const nodeHeight = 36;
  const halfHeight = nodeHeight / 2;

  return (
    <motion.g
      onClick={() => onClick(concept)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick(concept);
        }
      }}
      tabIndex={0}
      role="button"
      aria-label={`${name}, ${status}, Score: ${score}%`}
      className="cursor-pointer outline-none focus:outline-none select-none"
      animate={{
        opacity,
        scale: isSelected ? 1.05 : 1.0,
      }}
      transition={{ duration: 0.2 }}
      style={{ transformOrigin: `${x + width / 2}px ${y}px` }}
    >
      {/* Related Concept Highlight Ring */}
      {isRelatedToSelected && !isSelected && (
        <rect
          x={x - 3}
          y={y - halfHeight - 3}
          width={width + 6}
          height={nodeHeight + 6}
          rx={6}
          fill="none"
          stroke="#3A63FF"
          strokeWidth="1.5"
          strokeDasharray="3 3"
          className="pointer-events-none"
        />
      )}

      {/* Pulsing Outer Ring for Gap Node when not selected */}
      {isGap && !isSelected && (
        <rect
          x={x - 2}
          y={y - halfHeight - 2}
          width={width + 4}
          height={nodeHeight + 4}
          rx={5}
          fill="none"
          stroke="#FF6B1A"
          strokeWidth="1.5"
          className="gap-pulse-ring pointer-events-none"
        />
      )}

      {/* Main Node Chip Rectangle */}
      <rect
        x={x}
        y={y - halfHeight}
        width={width}
        height={nodeHeight}
        rx={4}
        fill={bg}
        stroke={border}
        strokeWidth={borderWidth}
        strokeDasharray={borderStyle === "dashed" ? "4 3" : undefined}
        filter={
          isSelected
            ? "drop-shadow(0 4px 12px rgba(0, 0, 0, 0.5))"
            : undefined
        }
        className={isDeveloping && !isSelected ? "developing-pulse-node" : undefined}
      />

      {/* MASTERED Indicator: Small 6px filled cobalt circle in top-right */}
      {isMastered && !isSelected && (
        <circle
          cx={x + width - 8}
          cy={y - halfHeight + 8}
          r="3"
          fill="#3A63FF"
        />
      )}

      {/* GAP Icon: ⚠ Triangle left of text */}
      {isGap && (
        <g transform={`translate(${x + 8}, ${y - 6})`}>
          <polygon
            points="5,0 10,11 0,11"
            fill={isSelected ? "#FFFFFF" : "#FF6B1A"}
          />
          <line
            x1="5"
            y1="3"
            x2="5"
            y2="7"
            stroke={isSelected ? "#FF6B1A" : "#FFFFFF"}
            strokeWidth="1.2"
            strokeLinecap="round"
          />
          <circle
            cx="5"
            cy="9.2"
            r="0.7"
            fill={isSelected ? "#FF6B1A" : "#FFFFFF"}
          />
        </g>
      )}

      {/* RESOLVED Icon: ✓ in circle */}
      {isResolved && (
        <g transform={`translate(${x + 8}, ${y - 6})`}>
          <circle cx="5" cy="5" r="4.5" fill="#3A63FF" />
          <path
            d="M 3 5 L 4.5 6.5 L 7.5 3.5"
            fill="none"
            stroke="#FFFFFF"
            strokeWidth="1.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      )}

      {/* Concept Name — Front-facing, Horizontal, 100% Legible */}
      <text
        x={x + (isGap || isResolved ? 24 : 12)}
        y={y + 3.5}
        fill={textColor}
        fontFamily="var(--font-mono), 'IBM Plex Mono', monospace"
        fontSize="10"
        fontWeight={isGap || isSelected ? "600" : "400"}
        letterSpacing="0.05em"
        className="pointer-events-none select-none uppercase"
      >
        {displayName}
      </text>

      {/* Native tooltip showing full concept name */}
      <title>{`${name} (${status} · ${score}%)`}</title>
    </motion.g>
  );
}

export default CircuitNode;
