"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { Gap } from "@/types/gapReport";

export interface EvidenceViewerProps {
  isOpen: boolean;
  gap: Gap | null;
  onClose: () => void;
}

export function EvidenceViewer({ isOpen, gap, onClose }: EvidenceViewerProps) {
  if (!isOpen || !gap) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy/50 backdrop-blur-[1px]">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="w-full max-w-[680px] max-h-[85vh] bg-white border-2 border-navy rounded-none shadow-[8px_8px_0_0_#0F2B4A] flex flex-col overflow-hidden text-navy"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-navy flex items-center justify-between bg-white">
            <div>
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-navy/50 block">
                EVIDENCE TIMELINE
              </span>
              <h3 className="font-mono text-sm md:text-base font-bold uppercase tracking-wider text-navy">
                {gap.title}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-navy/60 hover:text-navy transition-colors"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Timeline Cards Container */}
          <div className="p-6 overflow-y-auto space-y-5 bg-ice/30 flex-1">
            {gap.evidence && gap.evidence.length > 0 ? (
              gap.evidence.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-fog rounded-none shadow-sm overflow-hidden"
                >
                  {/* Card Header */}
                  <div className="px-4 py-2.5 bg-white border-b border-fog flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-navy">
                      Turn {item.turn} · {item.timestamp}
                    </span>
                    <span
                      className={`font-mono text-[10px] font-bold uppercase px-2 py-0.5 rounded-[2px] ${
                        item.detectionType === "misconception"
                          ? "bg-[#A82485] text-white"
                          : "bg-gap-orange text-white"
                      }`}
                    >
                      {item.detectionType}
                    </span>
                  </div>

                  {/* Curio Asked */}
                  {item.curioAsked && (
                    <div className="border-b border-fog">
                      <div className="bg-ice px-3 py-1 font-mono text-[10px] uppercase font-bold text-navy/70">
                        CURIO ASKED
                      </div>
                      <div className="p-3 font-sans text-sm text-navy">
                        "{item.curioAsked}"
                      </div>
                    </div>
                  )}

                  {/* Learner Answered */}
                  {item.learnerAnswered && (
                    <div className="border-b border-fog">
                      <div className="bg-ice px-3 py-1 font-mono text-[10px] uppercase font-bold text-navy/70">
                        YOUR ANSWER
                      </div>
                      <div className="p-3 font-sans text-sm text-navy italic">
                        "{item.learnerAnswered}"
                      </div>
                    </div>
                  )}

                  {/* Curio Detected */}
                  <div>
                    <div className="bg-ice px-3 py-1 font-mono text-[10px] uppercase font-bold text-gap-orange">
                      CURIO DETECTED
                    </div>
                    <div className="p-3 font-sans text-sm text-navy/90">
                      {item.explanation}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="font-sans text-sm text-navy/60 text-center py-8">
                No turn-by-turn evidence recorded for this gap.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 border-t border-navy bg-white flex justify-end">
            <button
              onClick={onClose}
              className="font-mono text-xs font-semibold uppercase px-4 py-2 border border-navy hover:bg-navy hover:text-white transition-colors"
            >
              CLOSE
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
