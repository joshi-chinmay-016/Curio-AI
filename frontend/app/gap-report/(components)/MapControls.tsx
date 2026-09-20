"use client";

import { KeycapButton } from "@/components/ui/KeycapButton";
import { RotateCcw, AlertTriangle, Eye, Layers } from "lucide-react";

interface MapControlsProps {
  isFocusGaps: boolean;
  showLayerLabels: boolean;
  onResetView: () => void;
  onToggleFocusGaps: () => void;
  onShowAll: () => void;
  onToggleLayerLabels: () => void;
}

export default function MapControls({
  isFocusGaps,
  showLayerLabels,
  onResetView,
  onToggleFocusGaps,
  onShowAll,
  onToggleLayerLabels,
}: MapControlsProps) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2 pt-3">
      <KeycapButton
        size="sm"
        variant="default"
        onClick={onResetView}
        title="Reset layer stack and selections"
      >
        <RotateCcw className="h-3 w-3 mr-1" />
        Reset View
      </KeycapButton>

      <KeycapButton
        size="sm"
        variant={isFocusGaps ? "gap" : "default"}
        onClick={onToggleFocusGaps}
        title="Dim non-gap layers and highlight gaps"
      >
        <AlertTriangle className="h-3 w-3 mr-1 text-gap-orange" />
        Focus Gaps
      </KeycapButton>

      <KeycapButton
        size="sm"
        variant="default"
        onClick={onShowAll}
        title="Restore full visibility across all layers"
      >
        <Eye className="h-3 w-3 mr-1 text-cobalt" />
        Show All
      </KeycapButton>

      <KeycapButton
        size="sm"
        variant="default"
        onClick={onToggleLayerLabels}
        title="Toggle visibility of side layer labels"
      >
        <Layers className="h-3 w-3 mr-1" />
        {showLayerLabels ? "Hide Labels" : "Show Labels"}
      </KeycapButton>
    </div>
  );
}
