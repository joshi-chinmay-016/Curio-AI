"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface NotebookProps {
  visible: boolean;
  writingProgress?: number; // 0 to 1
  position?: "student-front";
}

export function Notebook({
  visible,
  writingProgress = 0,
  position = "student-front",
}: NotebookProps) {
  const [internalProgress, setInternalProgress] = useState(0);

  useEffect(() => {
    if (!visible) {
      setInternalProgress(0);
      return;
    }
    // Animate lines sequential drawing
    const t1 = setTimeout(() => setInternalProgress(0.35), 400);
    const t2 = setTimeout(() => setInternalProgress(0.7), 1000);
    const t3 = setTimeout(() => setInternalProgress(1), 1600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [visible]);

  const activeProgress = writingProgress > 0 ? writingProgress : internalProgress;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="student-notebook"
          initial={{ y: 30, opacity: 0, scale: 0.9 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          exit={{ y: 25, opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 pointer-events-none drop-shadow-xl"
          data-testid="student-notebook-prop"
        >
          <svg
            width="90"
            height="65"
            viewBox="0 0 90 65"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Book spine & cover */}
            <rect
              x="2"
              y="2"
              width="86"
              height="61"
              rx="4"
              fill="#0F2B4A"
              stroke="#1E3A5F"
              strokeWidth="2"
            />
            {/* Left page */}
            <rect
              x="6"
              y="6"
              width="38"
              height="53"
              rx="2"
              fill="#FFFFFF"
            />
            {/* Right page */}
            <rect
              x="46"
              y="6"
              width="38"
              height="53"
              rx="2"
              fill="#F8FAFC"
            />
            {/* Center binding crease */}
            <line
              x1="44"
              y1="6"
              x2="44"
              y2="59"
              stroke="#CBD5E1"
              strokeWidth="1.5"
            />

            {/* Left page notes (decorative) */}
            <line x1="10" y1="14" x2="38" y2="14" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="10" y1="22" x2="34" y2="22" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="10" y1="30" x2="36" y2="30" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />

            {/* Right page dynamic writing lines */}
            {/* Line 1 */}
            <motion.line
              x1="50"
              y1="16"
              x2="78"
              y2="16"
              stroke="#0F2B4A"
              strokeWidth="2"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.3 ? 1 : 0 }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
            />
            {/* Line 2 */}
            <motion.line
              x1="50"
              y1="26"
              x2="74"
              y2="26"
              stroke="#3A63FF"
              strokeWidth="2"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.65 ? 1 : 0 }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
            />
            {/* Line 3 */}
            <motion.line
              x1="50"
              y1="36"
              x2="80"
              y2="36"
              stroke="#0F2B4A"
              strokeWidth="2"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.95 ? 1 : 0 }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
            />

            {/* Little pencil accent */}
            <motion.g
              animate={{
                x: activeProgress > 0 && activeProgress < 1 ? [0, 4, 0] : 0,
                y: activeProgress > 0 && activeProgress < 1 ? [0, -2, 0] : 0,
              }}
              transition={{ repeat: Infinity, duration: 0.3 }}
            >
              <rect
                x="76"
                y="42"
                width="8"
                height="3"
                rx="1"
                transform="rotate(-40 76 42)"
                fill="#FF6B1A"
              />
            </motion.g>
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
