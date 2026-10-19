"use client";

import React from "react";

export function IsometricStageDefs() {
  return (
    <defs>
      {/* 24px Isometric Grid Floor Dots */}
      <pattern
        id="iso-dot-grid"
        patternUnits="userSpaceOnUse"
        width="24"
        height="24"
      >
        <circle cx="12" cy="12" r="1.2" fill="#C4CDD6" fillOpacity="0.45" />
      </pattern>

      {/* High-Contrast Diagonal Orange Hatching for Gap Cells */}
      <pattern
        id="gap-hatch-pattern"
        patternUnits="userSpaceOnUse"
        width="9"
        height="9"
        patternTransform="rotate(-45)"
      >
        <rect width="9" height="9" fill="#FFFFFF" />
        <line
          x1="0"
          y1="0"
          x2="0"
          y2="9"
          stroke="#FF6B1A"
          strokeWidth="2.5"
        />
      </pattern>

      {/* Focus Gaps Mode Hatch Pattern (same contrast) */}
      <pattern
        id="gap-hatch"
        patternUnits="userSpaceOnUse"
        width="9"
        height="9"
        patternTransform="rotate(-45)"
      >
        <rect width="9" height="9" fill="#FFFFFF" />
        <line
          x1="0"
          y1="0"
          x2="0"
          y2="9"
          stroke="#FF6B1A"
          strokeWidth="2.5"
        />
      </pattern>

      {/* Subtle Radial Vignette to focus attention on center stack */}
      <radialGradient id="iso-vignette" cx="50%" cy="50%" r="65%">
        <stop offset="35%" stopColor="#FFFFFF" stopOpacity="0" />
        <stop offset="75%" stopColor="#E8EEF3" stopOpacity="0.4" />
        <stop offset="100%" stopColor="#E8EEF3" stopOpacity="0.85" />
      </radialGradient>

      {/* Orange Glow Filter for Selected Cell */}
      <filter id="gap-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#FF6B1A" floodOpacity="0.9" />
        <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor="#FF6B1A" floodOpacity="0.4" />
      </filter>

      {/* Subtle Drop Shadow for Layer Slabs */}
      <filter id="layer-slab-shadow" x="-10%" y="-10%" width="120%" height="130%">
        <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#0F2B4A" floodOpacity="0.12" />
      </filter>
    </defs>
  );
}

export function IsometricStageBackground() {
  return (
    <g className="iso-stage-bg pointer-events-none select-none">
      {/* Background Dot Grid */}
      <rect
        x="-300"
        y="-300"
        width="1200"
        height="1200"
        fill="url(#iso-dot-grid)"
        className="opacity-90"
      />
      {/* Soft Vignette Overlay */}
      <rect
        x="-300"
        y="-300"
        width="1200"
        height="1200"
        fill="url(#iso-vignette)"
      />
    </g>
  );
}
