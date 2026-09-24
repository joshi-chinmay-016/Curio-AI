"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { SessionMode } from "@/types/session";

export interface StatusBarProps {
  mode: SessionMode;
  turnNumber: number;
  confidence?: number;
  activeGapTitle?: string;
  className?: string;
  onStuckClick?: () => void;
}

export function StatusBar({
  mode,
  turnNumber,
  confidence = 70,
  activeGapTitle,
  className,
  onStuckClick,
}: StatusBarProps) {
  const getConfidenceWord = (val: number) => {
    if (val >= 85) return "High";
    if (val >= 65) return "Rising";
    if (val >= 40) return "Moderate";
    return "Developing";
  };

  const isTeacher = mode === "TEACHER";
  const isEvaluating = mode === "EVALUATING";

  return (
    <div
      className={cn(
        "w-full px-4 py-2 border-y border-fog flex items-center justify-between text-xs font-mono transition-colors duration-500 select-none",
        isTeacher
          ? "bg-[#FFF8F5] text-navy border-gap-orange/40"
          : isEvaluating
          ? "bg-ice text-navy"
          : "bg-white/80 text-navy",
        className
      )}
    >
      <div className="flex items-center gap-3">
        {mode === "STUDENT" && (
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cobalt inline-block animate-pulse" />
            <span className="font-bold tracking-wider text-navy">STUDENT MODE</span>
          </div>
        )}

        {mode === "TEACHER" && (
          <div className="flex items-center gap-2">
            <span className="text-gap-orange text-sm leading-none font-bold">◆</span>
            <span className="font-bold tracking-wider text-gap-orange">TEACHER MODE</span>
            {activeGapTitle && (
              <>
                <span className="text-fog">|</span>
                <span className="text-navy font-medium">
                  ADDRESSING GAP: <span className="font-semibold text-gap-orange">{activeGapTitle}</span>
                </span>
              </>
            )}
          </div>
        )}

        {mode === "EVALUATING" && (
          <div className="flex items-center gap-2">
            <span className="text-cobalt animate-spin inline-block text-sm">◈</span>
            <span className="font-bold tracking-wider text-cobalt">EVALUATING...</span>
          </div>
        )}

        <span className="text-fog hidden sm:inline">|</span>
        <span className="text-navy/70 hidden sm:inline">Turn {turnNumber}</span>

        <span className="text-fog hidden md:inline">|</span>
        <span className="text-navy/70 hidden md:inline">
          Confidence: <span className="font-semibold text-navy">{getConfidenceWord(confidence)}</span>
        </span>
      </div>

      {/* Mobile mode tap for stuck if student mode */}
      {mode === "STUDENT" && onStuckClick && (
        <button
          onClick={onStuckClick}
          className="sm:hidden font-mono text-[11px] uppercase text-navy/70 underline underline-offset-2"
        >
          [STUCK?]
        </button>
      )}
    </div>
  );
}
