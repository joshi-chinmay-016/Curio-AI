"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface QuestionMarkProps {
  visible: boolean;
  color?: string; // e.g. "#3A63FF" or "#FF6B1A"
  size?: number;
  position?: "above-head";
}

export function QuestionMark({
  visible,
  color = "#3A63FF",
  size = 28,
  position = "above-head",
}: QuestionMarkProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="question-mark-overlay"
          initial={{ scale: 0, opacity: 0, y: 15 }}
          animate={{ scale: [0, 1.3, 1], opacity: 1, y: 0 }}
          exit={{ scale: 0, opacity: 0, y: -10 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="absolute top-2 left-1/2 -translate-x-1/2 z-30 pointer-events-none drop-shadow-lg"
          data-testid="question-mark-prop"
        >
          <div
            className="w-10 h-10 rounded-full bg-white/95 border border-slate-200/80 shadow-md flex items-center justify-center font-mono font-black"
            style={{ color, fontSize: `${size}px` }}
          >
            ?
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
