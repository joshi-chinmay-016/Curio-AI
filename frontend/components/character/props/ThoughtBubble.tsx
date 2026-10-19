"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ThoughtBubbleProps {
  visible: boolean;
  content?: "thinking-dots" | "question" | "confused";
  position?: "above-right" | "above-left" | "above";
}

export function ThoughtBubble({
  visible,
  content = "thinking-dots",
  position = "above-right",
}: ThoughtBubbleProps) {
  const posClasses =
    position === "above-right"
      ? "top-4 right-10"
      : position === "above-left"
      ? "top-4 left-10"
      : "top-2 left-1/2 -translate-x-1/2";

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="thought-bubble"
          initial={{ scale: 0, opacity: 0, y: 10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0, opacity: 0, y: 8 }}
          transition={{ type: "spring", stiffness: 320, damping: 20 }}
          style={{ transformOrigin: "bottom left" }}
          className={`absolute ${posClasses} z-30 pointer-events-none drop-shadow-md`}
          data-testid="thought-bubble-prop"
        >
          {/* Main Bubble */}
          <div className="relative bg-white/95 backdrop-blur-sm border border-slate-200/90 rounded-2xl px-3.5 py-2 flex items-center justify-center shadow-lg min-w-[54px] min-h-[36px]">
            {content === "thinking-dots" && (
              <div className="flex items-center space-x-1.5">
                <motion.span
                  className="w-2 h-2 rounded-full bg-slate-400"
                  animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.15, 0.8] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                />
                <motion.span
                  className="w-2 h-2 rounded-full bg-slate-400"
                  animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.15, 0.8] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                />
                <motion.span
                  className="w-2 h-2 rounded-full bg-slate-400"
                  animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.15, 0.8] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                />
              </div>
            )}

            {content === "question" && (
              <span className="font-mono font-bold text-lg text-cobalt">?</span>
            )}

            {content === "confused" && (
              <span className="font-mono font-bold text-lg text-gap-orange">?</span>
            )}

            {/* Ascending trailing circles below bubble */}
            <div className="absolute -bottom-2 -left-1 w-2.5 h-2.5 rounded-full bg-white/95 border border-slate-200 shadow-sm" />
            <div className="absolute -bottom-4 -left-3 w-1.5 h-1.5 rounded-full bg-white/95 border border-slate-200 shadow-sm" />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
