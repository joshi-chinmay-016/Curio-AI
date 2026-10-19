"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface CheckMarkProps {
  visible: boolean;
  color?: string; // cobalt "#3A63FF" or green "#10B981"
  size?: number;
}

export function CheckMark({
  visible,
  color = "#3A63FF",
  size = 36,
}: CheckMarkProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="checkmark-overlay"
          initial={{ scale: 0, opacity: 0, y: 15 }}
          animate={{ scale: [0, 1.25, 1], opacity: 1, y: 0 }}
          exit={{ scale: 0, opacity: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="absolute top-2 left-1/2 -translate-x-1/2 z-30 pointer-events-none drop-shadow-xl"
          data-testid="checkmark-prop"
        >
          <div className="w-12 h-12 rounded-full bg-white/95 border border-slate-200/80 shadow-lg flex items-center justify-center">
            <svg
              width={size}
              height={size}
              viewBox="0 0 36 36"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <motion.path
                d="M9 18.5L15 24.5L27 12.5"
                stroke={color}
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.4, ease: "easeInOut" }}
              />
            </svg>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
