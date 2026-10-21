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
    const t1 = setTimeout(() => setInternalProgress(0.35), 300);
    const t2 = setTimeout(() => setInternalProgress(0.7), 800);
    const t3 = setTimeout(() => setInternalProgress(1), 1400);

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
          initial={{ y: 50, opacity: 0, scale: 0.85, rotate: -4 }}
          animate={{
            y: 0,
            opacity: 1,
            scale: 1,
            rotate: 0,
            transition: { type: "spring", stiffness: 220, damping: 18 },
          }}
          exit={{ y: 40, opacity: 0, scale: 0.85, rotate: 2 }}
          className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 pointer-events-none drop-shadow-[0_12px_28px_rgba(0,0,0,0.5)]"
          data-testid="student-notebook-prop"
        >
          {/* Subtle note illumination glow */}
          <div className="absolute inset-0 bg-cobalt/20 blur-xl rounded-full pointer-events-none" />

          <svg
            width="130"
            height="95"
            viewBox="0 0 130 95"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="relative"
          >
            {/* Hardcover Outer Frame */}
            <rect
              x="2"
              y="2"
              width="126"
              height="91"
              rx="6"
              fill="#0F2B4A"
              stroke="#2A4D7A"
              strokeWidth="2.5"
            />

            {/* Left Page (Grid / ruled) */}
            <rect
              x="8"
              y="7"
              width="54"
              height="80"
              rx="3"
              fill="#FFFFFF"
            />
            {/* Right Page (Ruled note paper) */}
            <rect
              x="68"
              y="7"
              width="54"
              height="80"
              rx="3"
              fill="#F8FAFC"
            />

            {/* Center Spiral / Binding */}
            <rect
              x="62"
              y="5"
              width="6"
              height="84"
              rx="3"
              fill="#1E293B"
            />
            {/* Spiral loops */}
            {[14, 26, 38, 50, 62, 74].map((y) => (
              <ellipse
                key={y}
                cx="65"
                cy={y}
                rx="3.5"
                ry="2.5"
                fill="#94A3B8"
                stroke="#0F172A"
                strokeWidth="1"
              />
            ))}

            {/* Left page notes (printed diagram/text) */}
            <line x1="14" y1="18" x2="52" y2="18" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />
            <line x1="14" y1="28" x2="48" y2="28" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="38" x2="54" y2="38" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="48" x2="44" y2="48" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />
            <line x1="14" y1="58" x2="50" y2="58" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="68" x2="40" y2="68" stroke="#E2E8F0" strokeWidth="1.5" strokeLinecap="round" />

            {/* Small lightbulb / formula icon on left */}
            <circle cx="48" cy="74" r="5" fill="#FEF08A" stroke="#EAB308" strokeWidth="1" />

            {/* Right Page Dynamic Note Writing Lines */}
            {/* Line 1 */}
            <motion.line
              x1="74"
              y1="20"
              x2="114"
              y2="20"
              stroke="#0F2B4A"
              strokeWidth="2.5"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.25 ? 1 : 0 }}
              transition={{ duration: 0.35, ease: "easeInOut" }}
            />
            {/* Line 2 */}
            <motion.line
              x1="74"
              y1="32"
              x2="110"
              y2="32"
              stroke="#3A63FF"
              strokeWidth="2.5"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.55 ? 1 : 0 }}
              transition={{ duration: 0.35, ease: "easeInOut" }}
            />
            {/* Line 3 */}
            <motion.line
              x1="74"
              y1="44"
              x2="116"
              y2="44"
              stroke="#0F2B4A"
              strokeWidth="2.5"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.8 ? 1 : 0 }}
              transition={{ duration: 0.35, ease: "easeInOut" }}
            />
            {/* Line 4 */}
            <motion.line
              x1="74"
              y1="56"
              x2="105"
              y2="56"
              stroke="#FF6B1A"
              strokeWidth="2"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: activeProgress >= 0.95 ? 1 : 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            />

            {/* Dynamic Animated Pencil with Hand */}
            <motion.g
              animate={{
                x: [0, 8, -4, 6, 0],
                y: [0, -3, 2, -1, 0],
                rotate: [-2, 3, -4, 2, -2],
              }}
              transition={{
                repeat: Infinity,
                duration: 0.55,
                ease: "easeInOut",
              }}
              style={{ originX: "105px", originY: "45px" }}
            >
              {/* Pencil body */}
              <rect
                x="102"
                y="30"
                width="8"
                height="32"
                rx="2"
                transform="rotate(38 102 30)"
                fill="#FF6B1A"
                stroke="#C2410C"
                strokeWidth="1"
              />
              {/* Eraser */}
              <rect
                x="117"
                y="20"
                width="7"
                height="8"
                rx="1"
                transform="rotate(38 117 20)"
                fill="#FDA4AF"
              />
              {/* Metal Ferrule */}
              <rect
                x="113"
                y="25"
                width="7.5"
                height="4"
                transform="rotate(38 113 25)"
                fill="#94A3B8"
              />
              {/* Sharpened Wood Tip */}
              <polygon
                points="95,57 99,52 92,49"
                fill="#FED7AA"
              />
              {/* Graphite Tip touching paper */}
              <polygon
                points="93,56 95,57 92,53"
                fill="#0F172A"
              />

              {/* Sparkle at pen tip */}
              <circle
                cx="94"
                cy="56"
                r="1.8"
                fill="#3A63FF"
                className="animate-ping"
              />
            </motion.g>
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
