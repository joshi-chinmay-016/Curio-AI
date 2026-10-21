"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ClipboardProps {
  visible: boolean;
  markState?: "none" | "check" | "cross" | "in-progress";
  position?: "held-front" | "lowered" | "raised";
}

export function Clipboard({
  visible,
  markState = "none",
  position = "held-front",
}: ClipboardProps) {
  const yOffset = position === "raised" ? -16 : position === "lowered" ? 18 : 0;
  const rotation = position === "lowered" ? 8 : position === "raised" ? -2 : 0;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="professor-clipboard"
          initial={{ opacity: 0, scale: 0.85, y: 30 }}
          animate={{
            opacity: 1,
            scale: 1,
            y: yOffset,
            rotate: rotation,
          }}
          exit={{ opacity: 0, scale: 0.85, y: 30 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="absolute bottom-6 right-6 z-30 pointer-events-none drop-shadow-[0_16px_32px_rgba(0,0,0,0.55)]"
          data-testid="professor-clipboard-prop"
        >
          {/* Subtle marking illumination glow */}
          <div className="absolute inset-0 bg-amber-500/10 blur-xl rounded-full pointer-events-none" />

          <svg
            width="105"
            height="135"
            viewBox="0 0 105 135"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="relative"
          >
            {/* Wooden board */}
            <rect
              x="2"
              y="6"
              width="101"
              height="124"
              rx="6"
              fill="#5A3A1E"
              stroke="#3D2612"
              strokeWidth="2.5"
            />
            {/* Beveled wood grain edge */}
            <rect
              x="5"
              y="9"
              width="95"
              height="118"
              rx="4"
              fill="#6D4624"
            />

            {/* White rubric examination paper */}
            <rect
              x="9"
              y="18"
              width="87"
              height="105"
              rx="3"
              fill="#FFFFFF"
              stroke="#E2E8F0"
              strokeWidth="1"
            />

            {/* Rubric Title Header Bar */}
            <rect x="15" y="24" width="50" height="4" rx="2" fill="#0F2B4A" />
            <rect x="15" y="31" width="30" height="2" rx="1" fill="#94A3B8" />

            {/* Rubric Criteria 1: Checkbox + Line */}
            <rect x="15" y="40" width="7" height="7" rx="1.5" stroke="#64748B" strokeWidth="1.2" fill="#F8FAFC" />
            <line x1="26" y1="44" x2="68" y2="44" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />

            {/* Rubric Criteria 2: Checkbox + Line */}
            <rect x="15" y="54" width="7" height="7" rx="1.5" stroke="#64748B" strokeWidth="1.2" fill="#F8FAFC" />
            <line x1="26" y1="58" x2="64" y2="58" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />

            {/* Rubric Criteria 3: Checkbox + Line */}
            <rect x="15" y="68" width="7" height="7" rx="1.5" stroke="#64748B" strokeWidth="1.2" fill="#F8FAFC" />
            <line x1="26" y1="72" x2="70" y2="72" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />

            {/* Rubric Criteria 4: Checkbox + Line */}
            <rect x="15" y="82" width="7" height="7" rx="1.5" stroke="#64748B" strokeWidth="1.2" fill="#F8FAFC" />
            <line x1="26" y1="86" x2="58" y2="86" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />

            {/* Examiner Signature Line at Bottom */}
            <line x1="15" y1="108" x2="55" y2="108" stroke="#94A3B8" strokeWidth="1.5" strokeDasharray="3 2" />

            {/* Checkmark (Green approval mark on criteria 2) */}
            {markState === "check" && (
              <motion.path
                d="M16 57 L19 60 L26 50"
                stroke="#10B981"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
              />
            )}

            {/* Crossmark (Strict orange disapproval on criteria 2) */}
            {markState === "cross" && (
              <g>
                <motion.line
                  x1="16"
                  y1="54"
                  x2="22"
                  y2="61"
                  stroke="#FF6B1A"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                />
                <motion.line
                  x1="22"
                  y1="54"
                  x2="16"
                  y2="61"
                  stroke="#FF6B1A"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.2, delay: 0.1, ease: "easeOut" }}
                />
              </g>
            )}

            {/* Active Pen Marking Animation when markState === "in-progress" */}
            {(markState === "in-progress" || position === "raised") && (
              <motion.g
                animate={{
                  x: [0, -6, 4, -4, 0],
                  y: [0, 4, -2, 3, 0],
                  rotate: [-3, 5, -2, 4, -3],
                }}
                transition={{
                  repeat: Infinity,
                  duration: 0.5,
                  ease: "easeInOut",
                }}
                style={{ originX: "50px", originY: "65px" }}
              >
                {/* Pen Scribble mark trail */}
                <path
                  d="M17 56 L20 60 L24 52"
                  stroke="#3A63FF"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Silver Fountain Pen body */}
                <rect
                  x="48"
                  y="45"
                  width="6"
                  height="45"
                  rx="2"
                  transform="rotate(35 48 45)"
                  fill="#1E293B"
                  stroke="#0F172A"
                  strokeWidth="1"
                />
                {/* Gold Trim band */}
                <rect
                  x="45"
                  y="62"
                  width="7"
                  height="3"
                  transform="rotate(35 45 62)"
                  fill="#D4AF37"
                />
                {/* Gold Nib touching paper */}
                <polygon
                  points="25,72 29,66 22,62"
                  fill="#D4AF37"
                />
                <polygon
                  points="24,73 26,72 23,68"
                  fill="#0F172A"
                />
                {/* Writing Sparkle */}
                <circle cx="24" cy="73" r="1.5" fill="#3A63FF" className="animate-ping" />
              </motion.g>
            )}

            {/* Brass Top Clip Mechanism */}
            <rect
              x="36"
              y="2"
              width="33"
              height="15"
              rx="3"
              fill="#D4AF37"
              stroke="#A17C18"
              strokeWidth="2"
            />
            {/* Clip rivet hole */}
            <circle cx="52.5" cy="8" r="2.5" fill="#3D2612" />
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
