"use client";

import React from "react";
import { ConceptCell as ConceptCellType } from "@/types/gapReport";

interface ConceptCellProps {
  concept: ConceptCellType;
  x: number;
  y: number;
  width: number;
  height: number;
  isSelected: boolean;
  isAnySelected: boolean;
  isFocusGaps: boolean;
  onSelect: (concept: ConceptCellType) => void;
}

export default function ConceptCell({
  concept,
  x,
  y,
  width,
  height,
  isSelected,
  isAnySelected,
  isFocusGaps,
  onSelect,
}: ConceptCellProps) {
  const isGap = concept.status === "GAP" || concept.status === "MISCONCEPTION";
  const isResolved = concept.status === "RESOLVED";
  const isDeveloping = concept.status === "DEVELOPING";
  const isMastered = concept.status === "STRONG";
  const isUntested = concept.status === "UNTESTED";

  // Dimming logic
  let opacity = 1;
  if (isFocusGaps && !isGap) {
    opacity = 0.25;
  } else if (isAnySelected && !isSelected) {
    opacity = 0.7;
  }

  // Visual treatments per state
  let fill = "#0F2B4A";
  let stroke = isSelected ? "#3A63FF" : "#0F2B4A";
  let strokeWidth = isSelected ? 3.5 : 1.5;
  let textColor = "#FFFFFF";

  if (isGap) {
    fill = "url(#gap-hatch-pattern)";
    stroke = isSelected ? "#3A63FF" : "#FF6B1A";
    strokeWidth = isSelected ? 3.5 : 2;
    textColor = "#0F2B4A";
  } else if (isDeveloping) {
    fill = "#3A63FF";
    textColor = "#FFFFFF";
  } else if (isResolved) {
    fill = "#3A63FF";
    textColor = "#FFFFFF";
  } else if (isUntested) {
    fill = "#E8EEF3";
    stroke = isSelected ? "#3A63FF" : "#0F2B4A";
    strokeWidth = 1.2;
    textColor = "#0F2B4A";
  } else if (isMastered) {
    fill = "#0F2B4A";
    textColor = "#FFFFFF";
  }

  return (
    <g
      transform={`translate(${x}, ${y}) scale(${isSelected ? 1.05 : 1})`}
      style={{
        cursor: "pointer",
        transition: "transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease",
        opacity,
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(concept);
      }}
    >
      {/* Background White base for hatched cells */}
      {isGap && (
        <rect
          x={0}
          y={0}
          width={width}
          height={height}
          rx={5}
          fill="#FFFFFF"
        />
      )}

      {/* Main Cell Body */}
      <rect
        x={0}
        y={0}
        width={width}
        height={height}
        rx={5}
        fill={fill}
        fillOpacity={isDeveloping ? 0.72 : 1}
        stroke={stroke}
        strokeWidth={strokeWidth}
        className={isGap && isFocusGaps ? "animate-pulse" : ""}
      />

      {/* Selected Indicator Outline */}
      {isSelected && (
        <rect
          x={-3}
          y={-3}
          width={width + 6}
          height={height + 6}
          rx={8}
          fill="none"
          stroke="#3A63FF"
          strokeWidth={2}
          strokeDasharray="4 2"
        />
      )}

      {/* Concept Name */}
      <text
        x={12}
        y={24}
        fontFamily="var(--font-sora), sans-serif"
        fontSize={13}
        fontWeight={700}
        fill={textColor}
        style={{ pointerEvents: "none", userSelect: "none" }}
      >
        {concept.name}
      </text>

      {/* Status or Score Subtext */}
      <text
        x={12}
        y={43}
        fontFamily="var(--font-mono), monospace"
        fontSize={10}
        fontWeight={600}
        letterSpacing="0.05em"
        fill={isGap ? "#FF6B1A" : textColor}
        fillOpacity={isGap ? 1 : 0.8}
        style={{ pointerEvents: "none", userSelect: "none" }}
      >
        {isGap
          ? "⚠ GAP DETECTED"
          : isResolved
          ? "✓ RESOLVED"
          : isUntested
          ? "UNTESTED"
          : `${concept.score}% UNDERSTANDING`}
      </text>

      {/* Checkmark icon on RESOLVED cell */}
      {isResolved && (
        <g transform={`translate(${width - 24}, 14)`}>
          <circle cx={6} cy={6} r={7} fill="#FFFFFF" />
          <path
            d="M3 6.2 L5.2 8.5 L9.5 4"
            fill="none"
            stroke="#3A63FF"
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      )}

      {/* Warning tag on GAP cell */}
      {isGap && (
        <g transform={`translate(${width - 26}, 12)`}>
          <rect
            x={0}
            y={0}
            width={18}
            height={18}
            rx={3}
            fill="#FF6B1A"
          />
          <text
            x={9}
            y={13}
            textAnchor="middle"
            fontFamily="var(--font-mono), monospace"
            fontSize={12}
            fontWeight={800}
            fill="#FFFFFF"
          >
            !
          </text>
        </g>
      )}
    </g>
  );
}
