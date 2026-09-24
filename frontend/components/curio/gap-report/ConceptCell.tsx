"use client";

import React from "react";
import { ConceptCell as ConceptCellType } from "@/types/gapReport";

export interface ConceptCellProps {
  concept: ConceptCellType;
  isSelected: boolean;
  isDimmed: boolean;
  onClick: (concept: ConceptCellType) => void;
  // Position in layer coordinate space
  x: number;
  y: number;
  width?: number;
  height?: number;
}

export function ConceptCell({
  concept,
  isSelected,
  isDimmed,
  onClick,
  x,
  y,
  width = 110,
  height = 55,
}: ConceptCellProps) {
  const { status, name, score } = concept;

  let fill = "#E8EEF3";
  let stroke = "#C4CDD6";
  let strokeWidth = 1;
  let opacity = 1;

  if (status === "STRONG") {
    fill = "#0F2B4A";
    stroke = "#0F2B4A";
  } else if (status === "DEVELOPING") {
    fill = "#3A63FF";
    opacity = 0.75;
    stroke = "#3A63FF";
  } else if (status === "GAP" || status === "MISCONCEPTION") {
    fill = "url(#gap-hatch)";
    stroke = "#FF6B1A";
    strokeWidth = 1.5;
  } else if (status === "RESOLVED") {
    fill = "#3A63FF";
    stroke = "#3A63FF";
  } else if (status === "UNTESTED") {
    fill = "#E8EEF3";
    stroke = "#C4CDD6";
  }

  if (isSelected) {
    stroke = "#3A63FF";
    strokeWidth = 2.5;
  }

  const effectiveOpacity = isDimmed ? opacity * 0.45 : opacity;

  // Parallelogram path for isometric projection
  // (x, y) is top-left in the skewed layer
  const pathData = `M ${x} ${y} L ${x + width} ${y} L ${x + width} ${y + height} L ${x} ${y + height} Z`;

  return (
    <g
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
      className="cursor-pointer transition-all duration-200 outline-none focus:outline-none"
      style={{ opacity: effectiveOpacity }}
    >
      {/* Background base rect for gap hatch cells to ensure white background behind orange lines */}
      {(status === "GAP" || status === "MISCONCEPTION") && (
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#FFFFFF"
          rx={2}
        />
      )}

      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeWidth}
        rx={2}
        className="transition-colors duration-150 hover:brightness-110"
      />

      {/* Checkmark icon for RESOLVED status */}
      {status === "RESOLVED" && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 5}
          textAnchor="middle"
          fill="#FFFFFF"
          fontSize="14"
          fontWeight="bold"
          pointerEvents="none"
        >
          ✓
        </text>
      )}

      {/* Cell label truncated in SVG */}
      <text
        x={x + width / 2}
        y={y + height / 2 + (status === "RESOLVED" ? 16 : 4)}
        textAnchor="middle"
        fill={
          status === "STRONG" || status === "RESOLVED"
            ? "#FFFFFF"
            : status === "GAP" || status === "MISCONCEPTION"
            ? "#0F2B4A"
            : "#0F2B4A"
        }
        fontSize="10"
        fontFamily="var(--font-mono), monospace"
        fontWeight="600"
        pointerEvents="none"
        className="select-none"
      >
        {name.length > 14 ? name.substring(0, 12) + ".." : name}
      </text>
    </g>
  );
}
