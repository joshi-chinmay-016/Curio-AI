"use client";

import React from "react";
import { motion } from "framer-motion";
import { ConceptCell as ConceptCellType } from "@/types/gapReport";

export interface ConceptCellProps {
  concept: ConceptCellType;
  isSelected: boolean;
  isSameLayerAsSelected: boolean;
  isAnySelected: boolean;
  isFocusGaps: boolean;
  onClick: (concept: ConceptCellType) => void;
  // Local coordinates inside the skewed layer
  x: number;
  y: number;
  width?: number;
  height?: number;
  isInteractive?: boolean;
}

export function ConceptCell({
  concept,
  isSelected,
  isSameLayerAsSelected,
  isAnySelected,
  isFocusGaps,
  onClick,
  x,
  y,
  width = 72,
  height = 32,
  isInteractive = true,
}: ConceptCellProps) {
  const { status, name, score } = concept;
  const isGap = status === "GAP" || status === "MISCONCEPTION";
  const isMastered = status === "STRONG";
  const isDeveloping = status === "DEVELOPING";
  const isResolved = status === "RESOLVED";
  const isUntested = status === "UNTESTED";

  // Dimming logic according to spec
  let cellOpacity = 1;
  if (isFocusGaps) {
    cellOpacity = isGap ? 1 : 0.15;
  } else if (isSelected) {
    cellOpacity = 1;
  } else if (isAnySelected) {
    cellOpacity = isSameLayerAsSelected ? 0.4 : 0.25;
  }

  // Color values
  let topFaceFill = "#E8EEF3";
  let topFaceOpacity = 1;
  let sideFaceFill = "#C4CDD6";
  let sideFaceOpacity = 0.5;
  let strokeColor = "#C4CDD6";
  let strokeWidth = 1;
  let strokeDasharray = isUntested ? "3 3" : undefined;
  let labelColor = "#C4CDD6";

  if (isMastered) {
    topFaceFill = "#0F2B4A";
    sideFaceFill = "#091D33";
    sideFaceOpacity = 1;
    strokeColor = "#0F2B4A";
    strokeWidth = 1;
    labelColor = "#FFFFFF";
  } else if (isDeveloping) {
    topFaceFill = "#3A63FF";
    topFaceOpacity = 0.8;
    sideFaceFill = "#2347CC";
    sideFaceOpacity = 0.8;
    strokeColor = "#3A63FF";
    strokeWidth = 1;
    labelColor = "#FFFFFF";
  } else if (isGap) {
    topFaceFill = "url(#gap-hatch-pattern)";
    sideFaceFill = "#FF6B1A";
    sideFaceOpacity = 0.6;
    strokeColor = "#FF6B1A";
    strokeWidth = 2;
    labelColor = "#FF6B1A";
  } else if (isResolved) {
    topFaceFill = "#3A63FF";
    sideFaceFill = "#2347CC";
    sideFaceOpacity = 1;
    strokeColor = "#3A63FF";
    strokeWidth = 1;
    labelColor = "#FFFFFF";
  } else if (isUntested) {
    topFaceFill = "#E8EEF3";
    sideFaceFill = "#C4CDD6";
    sideFaceOpacity = 0.5;
    strokeColor = "#C4CDD6";
    strokeWidth = 1;
    labelColor = "#788796";
  }

  // In Focus Gaps mode: non-gap top faces temporarily become ice (#E8EEF3)
  if (isFocusGaps && !isGap) {
    topFaceFill = "#E8EEF3";
    topFaceOpacity = 0.9;
    labelColor = "#A2B0BD";
  }

  // 8px depth side faces:
  // In the skewed coordinate system (skewX(-30deg) scale(1, 0.866)):
  // Bottom edge runs from (x, y + height) to (x + width, y + height).
  // Front face drops 8px downwards:
  const depth = 8;

  // Truncate concept name if too long and not selected
  const displayLabel = isSelected
    ? name
    : name.length > 12
    ? name.slice(0, 11) + "…"
    : name;

  return (
    <motion.g
      onClick={() => isInteractive && onClick(concept)}
      onKeyDown={(e) => {
        if (isInteractive && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick(concept);
        }
      }}
      tabIndex={isInteractive ? 0 : -1}
      role="button"
      aria-label={`${name}, ${status}, Score: ${score}%`}
      className={`outline-none focus:outline-none ${
        isInteractive ? "cursor-pointer" : "cursor-default"
      }`}
      animate={{
        opacity: cellOpacity,
        y: isSelected ? -4 : 0,
        scale: isSelected ? 1.08 : isFocusGaps && isGap ? 1.05 : 1,
      }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      style={{ transformOrigin: `${x + width / 2}px ${y + height / 2}px` }}
    >
      {/* Glow Ring for Selected Cell or Gap Cells in Focus Mode */}
      {(isSelected || (isFocusGaps && isGap)) && (
        <rect
          x={x - 3}
          y={y - 3}
          width={width + 6}
          height={height + 6 + depth}
          fill="none"
          stroke="#FF6B1A"
          strokeWidth={isSelected ? 3 : 2}
          strokeOpacity={isSelected ? 0.9 : 0.7}
          rx={3}
          filter="url(#gap-glow)"
          className="pointer-events-none"
        />
      )}

      {/* 3D Isometric Side Face (Bottom Edge Depth 8px) */}
      <motion.path
        d={`M ${x} ${y + height} L ${x + width} ${y + height} L ${x + width} ${
          y + height + depth
        } L ${x} ${y + height + depth} Z`}
        fill={sideFaceFill}
        fillOpacity={sideFaceOpacity}
        stroke={strokeColor}
        strokeWidth={Math.min(strokeWidth, 1.5)}
        animate={
          isGap && !isSelected
            ? {
                fillOpacity: isFocusGaps ? [0.6, 1, 0.6] : [0.6, 1, 0.6],
              }
            : isDeveloping && !isSelected
            ? {
                fillOpacity: [0.7, 0.9, 0.7],
              }
            : undefined
        }
        transition={
          isGap && !isSelected
            ? {
                duration: isFocusGaps ? 1.0 : 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }
            : isDeveloping && !isSelected
            ? {
                duration: 2.0,
                repeat: Infinity,
                ease: "easeInOut",
              }
            : undefined
        }
      />

      {/* 3D Isometric Left Depth Face (Optional subtle seam) */}
      <path
        d={`M ${x} ${y} L ${x} ${y + height} L ${x} ${y + height + depth} L ${x} ${
          y + depth
        } Z`}
        fill={sideFaceFill}
        fillOpacity={Math.max(sideFaceOpacity - 0.2, 0.3)}
        className="pointer-events-none"
      />

      {/* Base White Solid Fill for Hatch Pattern Background */}
      {isGap && (
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#FFFFFF"
          rx={2}
        />
      )}

      {/* Top Face Rect / Parallelogram in Skewed Group */}
      <motion.rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={topFaceFill}
        fillOpacity={topFaceOpacity}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeDasharray={strokeDasharray}
        rx={2}
        animate={
          isDeveloping && !isSelected && !isFocusGaps
            ? {
                fillOpacity: [0.7, 0.9, 0.7],
              }
            : undefined
        }
        transition={
          isDeveloping && !isSelected && !isFocusGaps
            ? {
                duration: 2.0,
                repeat: Infinity,
                ease: "easeInOut",
              }
            : undefined
        }
      />

      {/* Status Icons */}
      {/* Gap Warning Triangle Icon ⚠ */}
      {isGap && (
        <g transform={`translate(${x + width - (isFocusGaps ? 17 : 13)}, ${y + 3})`}>
          <polygon
            points={isFocusGaps ? "7,1 13,13 1,13" : "5,1 9,10 1,10"}
            fill="#FF6B1A"
            stroke="#FFFFFF"
            strokeWidth="0.8"
          />
          <circle
            cx={isFocusGaps ? 7 : 5}
            cy={isFocusGaps ? 10.5 : 8}
            r="0.8"
            fill="#FFFFFF"
          />
          <line
            x1={isFocusGaps ? 7 : 5}
            y1={isFocusGaps ? 4.5 : 3.5}
            x2={isFocusGaps ? 7 : 5}
            y2={isFocusGaps ? 8.5 : 6.5}
            stroke="#FFFFFF"
            strokeWidth="1.2"
            strokeLinecap="round"
          />
        </g>
      )}

      {/* Resolved Checkmark Icon ✓ */}
      {isResolved && (
        <g transform={`translate(${x + width - 13}, ${y + 3})`}>
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

      {/* Concept Name Label (IBM Plex Mono 9px) */}
      <text
        x={x + 6}
        y={y + height / 2 + 3.5}
        fill={labelColor}
        fontFamily="var(--font-mono), 'IBM Plex Mono', monospace"
        fontSize="9"
        fontWeight={isSelected || isMastered ? "bold" : "600"}
        letterSpacing="0.02em"
        className="select-none pointer-events-none"
      >
        {displayLabel}
      </text>

      {/* Selected Tooltip Above Cell */}
      {isSelected && (
        <g transform={`translate(${x + width / 2 - 28}, ${y - 15})`} className="pointer-events-none">
          <rect
            x="0"
            y="0"
            width="56"
            height="14"
            fill="#FFFFFF"
            stroke="#FF6B1A"
            strokeWidth="1"
            rx="2"
            filter="url(#gap-glow)"
          />
          <text
            x="28"
            y="10"
            textAnchor="middle"
            fill="#FF6B1A"
            fontFamily="var(--font-mono), 'IBM Plex Mono', monospace"
            fontSize="8"
            fontWeight="bold"
            letterSpacing="0.08em"
          >
            SELECTED
          </text>
        </g>
      )}
    </motion.g>
  );
}

export default ConceptCell;
