"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

export interface CircuitHeaderProps {
  topicName: string;
  overallScore: number;
  gapCount: number;
  isFocusGaps: boolean;
}

export function CircuitHeader({
  topicName,
  overallScore,
  gapCount,
  isFocusGaps,
}: CircuitHeaderProps) {
  return (
    <div className="flex items-center justify-between w-full pb-4 mb-2 border-b border-cobalt/20 select-none z-10">
      {/* Left side: KNOWLEDGE CIRCUIT · TOPIC NAME · SCORE */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-fog/70 font-semibold">
          KNOWLEDGE CIRCUIT
        </span>
        <span className="font-mono text-fog/40 text-[10px]">·</span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-white font-bold">
          {topicName}
        </span>
        <span className="font-mono text-fog/40 text-[10px]">·</span>
        <span className="font-mono text-[11px] text-white font-bold">
          {overallScore}%
        </span>
      </div>

      {/* Right side: Overall Health Bar + Score OR "N GAPS FOUND" Badge */}
      <div className="flex items-center gap-3">
        <AnimatePresence mode="wait">
          {isFocusGaps ? (
            <motion.div
              key="gap-counter-badge"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="bg-gap-orange text-white font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-[3px] shadow-sm flex items-center gap-1.5"
            >
              <span>⚠</span>
              <span>{gapCount} {gapCount === 1 ? "GAP" : "GAPS"} FOUND</span>
            </motion.div>
          ) : (
            <div key="health-bar" className="flex items-center gap-2">
              {/* Thin Health Bar (120px x 3px) */}
              <div className="w-[120px] h-[3px] bg-[#1a3d5c] rounded-full overflow-hidden flex">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100, Math.max(5, overallScore))}%`,
                    background:
                      overallScore >= 70
                        ? "#3A63FF"
                        : overallScore >= 50
                        ? "linear-gradient(to right, #3A63FF, #FF6B1A)"
                        : "#FF6B1A",
                  }}
                />
              </div>
              <span className="font-mono text-[10px] text-white/80 font-bold">
                {overallScore}%
              </span>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default CircuitHeader;
