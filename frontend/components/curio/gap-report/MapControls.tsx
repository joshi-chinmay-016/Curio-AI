"use client";

import React from "react";
import { KeycapButton } from "@/components/curio/KeycapButton";

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
    <div className="flex items-center gap-2 bg-white/95 p-1.5 rounded-[4px] border border-fog shadow-sm">
      <KeycapButton
        variant="default"
        size="sm"
        onClick={onReset}
        title="Reset map stack and clear selection (Shortcut: R)"
      >
        ↺ RESET
      </KeycapButton>

      <KeycapButton
        variant={focusGaps ? "gap" : "default"}
        size="sm"
        onClick={onToggleFocusGaps}
        title="Highlight knowledge gaps and zoom (Shortcut: F)"
        className={focusGaps ? "border-gap-orange text-gap-orange" : ""}
      >
        ⚠ FOCUS GAPS
      </KeycapButton>

      <KeycapButton
        variant="default"
        size="sm"
        onClick={onShowAll}
        title="Show all concepts without dimming"
      >
        ◈ SHOW ALL
      </KeycapButton>
    </div>
  );
}
