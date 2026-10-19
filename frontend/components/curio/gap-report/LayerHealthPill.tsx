"use client";

import React from "react";
import { ConceptCell as ConceptCellType, UnderstandingLayer } from "@/types/gapReport";

export interface LayerHealthPillProps {
  layerName: UnderstandingLayer;
  layerIndex: 1 | 2 | 3 | 4;
  concepts: ConceptCellType[];
  score: number;
}

export function LayerHealthPill({
  layerName,
  layerIndex,
  concepts,
  score,
}: LayerHealthPillProps) {
  const prefixMap: Record<number, string> = {
    1: "01",
    2: "02",
    3: "03",
    4: "04",
  };

  const displayNameMap: Record<UnderstandingLayer, string> = {
    DEFINITION: "DEFINITION",
    MECHANISM: "MECHANISM",
    APPLICATION: "APPLICATION",
    EDGE_CASES: "EDGE CASES",
  };

  // Determine 4 health dots based on concepts in this layer
  // Filled cobalt: >= 20% score / mastered / developing
  // Filled orange: gap / misconception
  // Empty fog: untested
  const dots: { type: "cobalt" | "orange" | "fog" }[] = [];

  concepts.slice(0, 4).forEach((c) => {
    if (c.status === "GAP" || c.status === "MISCONCEPTION") {
      dots.push({ type: "orange" });
    } else if (c.status === "UNTESTED") {
      dots.push({ type: "fog" });
    } else {
      dots.push({ type: "cobalt" });
    }
  });

  // Pad to 4 dots if fewer than 4 concepts
  while (dots.length < 4) {
    if (score < 50 && !dots.some((d) => d.type === "orange")) {
      dots.push({ type: "orange" });
    } else if (score >= 60) {
      dots.push({ type: "cobalt" });
    } else {
      dots.push({ type: "fog" });
    }
  }

  // Score color: cobalt (>70%), white (50-70%), orange (<50%)
  let scoreColor = "#3A63FF";
  if (score < 50) scoreColor = "#FF6B1A";
  else if (score <= 70) scoreColor = "#FFFFFF";

  return (
    <div className="flex items-center gap-2 select-none">
      {/* 4 Health Dots [●●◉○] */}
      <div className="flex items-center gap-1 bg-[#091d33] px-1.5 py-1 rounded-[3px] border border-cobalt/20">
        {dots.map((dot, i) => (
          <span
            key={`dot-${layerName}-${i}`}
            className="w-[5px] h-[5px] rounded-full inline-block"
            style={{
              backgroundColor:
                dot.type === "orange"
                  ? "#FF6B1A"
                  : dot.type === "cobalt"
                  ? "#3A63FF"
                  : "transparent",
              border:
                dot.type === "fog"
                  ? "1px solid #C4CDD6"
                  : dot.type === "orange"
                  ? "1px solid #FF6B1A"
                  : "1px solid #3A63FF",
            }}
          />
        ))}
      </div>

      {/* Layer Label: "01 DEFINITION" */}
      <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-fog/80 font-bold whitespace-nowrap">
        {prefixMap[layerIndex]} {displayNameMap[layerName]}
      </span>
    </div>
  );
}

export default LayerHealthPill;
