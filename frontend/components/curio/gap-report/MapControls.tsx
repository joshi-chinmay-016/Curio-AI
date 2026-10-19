"use client";

import React from "react";

export interface MapControlsProps {
  focusGaps: boolean;
  onReset: () => void;
  onToggleFocusGaps: () => void;
  onShowAll: () => void;
}

export function MapControls({
  focusGaps,
  onReset,
  onToggleFocusGaps,
  onShowAll,
}: MapControlsProps) {
  return (
    <div className="flex items-center gap-2 bg-[#091D33]/90 p-1 rounded-[4px] border border-cobalt/30 shadow-md backdrop-blur-sm select-none">
      {/* RESET Button (Navy Keycap) */}
      <button
        onClick={onReset}
        title="Reset circuit view and clear selection"
        className="h-[32px] px-3 inline-flex items-center justify-center font-mono text-[10px] uppercase font-bold tracking-wider rounded-[3px] border border-fog/40 bg-[#0F2B4A] text-fog/90 hover:text-white hover:border-fog shadow-[0_2px_0_0_#051321] active:translate-y-[2px] active:shadow-none transition-all duration-75 cursor-pointer"
      >
        ↺ RESET
      </button>

      {/* FOCUS GAPS Button (Orange Keycap, Collapses Shadow when Active) */}
      <button
        onClick={onToggleFocusGaps}
        title="Focus and highlight broken traces and knowledge gaps"
        className={`h-[32px] px-3 inline-flex items-center justify-center font-mono text-[10px] uppercase font-bold tracking-wider rounded-[3px] border transition-all duration-75 cursor-pointer ${
          focusGaps
            ? "bg-gap-orange text-white border-gap-orange translate-y-[2px] shadow-none"
            : "bg-[#0F2B4A] text-gap-orange border-gap-orange shadow-[0_2px_0_0_#CC4A00] hover:bg-gap-orange/15 active:translate-y-[2px] active:shadow-none"
        }`}
      >
        ⚠ FOCUS GAPS
      </button>

      {/* SHOW ALL Button (Cobalt Keycap) */}
      <button
        onClick={onShowAll}
        title="Show all circuit nodes with neutral illumination"
        className="h-[32px] px-3 inline-flex items-center justify-center font-mono text-[10px] uppercase font-bold tracking-wider rounded-[3px] border border-cobalt bg-[#0F2B4A] text-cobalt shadow-[0_2px_0_0_#2347CC] hover:bg-cobalt/20 active:translate-y-[2px] active:shadow-none transition-all duration-75 cursor-pointer"
      >
        ◆ SHOW ALL
      </button>
    </div>
  );
}

export default MapControls;
