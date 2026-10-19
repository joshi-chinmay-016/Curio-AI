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
  const yOffset = position === "raised" ? -10 : position === "lowered" ? 12 : 0;
  const rotation = position === "lowered" ? 6 : 0;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="professor-clipboard"
          initial={{ opacity: 0, scale: 0.85, y: 20 }}
          animate={{
            opacity: 1,
            scale: 1,
            y: yOffset,
            rotate: rotation,
          }}
          exit={{ opacity: 0, scale: 0.85, y: 20 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="absolute bottom-4 right-10 z-20 pointer-events-none drop-shadow-2xl"
          data-testid="professor-clipboard-prop"
        >
          <svg
            width="75"
            height="95"
            viewBox="0 0 75 95"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Wooden board */}
            <rect
              x="2"
              y="6"
              width="71"
              height="85"
              rx="4"
              fill="#785536"
              stroke="#543A23"
              strokeWidth="2"
            />
            {/* White paper */}
            <rect
              x="6"
              y="14"
              width="63"
              height="73"
              rx="2"
              fill="#FFFFFF"
            />
            {/* Form item lines */}
            <line x1="12" y1="24" x2="48" y2="24" stroke="#CBD5E1" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="12" y1="38" x2="44" y2="38" stroke="#CBD5E1" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="12" y1="52" x2="50" y2="52" stroke="#CBD5E1" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="12" y1="66" x2="40" y2="66" stroke="#CBD5E1" strokeWidth="1.5" strokeLinecap="round" />

            {/* In-progress mark scribbles */}
            {markState === "in-progress" && (
              <motion.path
                d="M52 22 L56 26 L52 28"
                stroke="#3A63FF"
                strokeWidth="2"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: [0, 1, 0] }}
                transition={{ repeat: Infinity, duration: 0.6 }}
              />
            )}

            {/* Checkmark (Green approval) */}
            {markState === "check" && (
              <motion.path
                d="M50 36 L54 41 L62 28"
                stroke="#10B981"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
            )}

            {/* Crossmark (Strict orange disapproval) */}
            {markState === "cross" && (
              <g>
                <motion.line
                  x1="52"
                  y1="32"
                  x2="60"
                  y2="40"
                  stroke="#FF6B1A"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                />
                <motion.line
                  x1="60"
                  y1="32"
                  x2="52"
                  y2="40"
                  stroke="#FF6B1A"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.25, delay: 0.15, ease: "easeOut" }}
                />
              </g>
            )}

            {/* Clip mechanism top */}
            <rect
              x="25"
              y="2"
              width="25"
              height="10"
              rx="2"
              fill="#D4AF37"
              stroke="#B8860B"
              strokeWidth="1.5"
            />
            <circle cx="37.5" cy="5" r="1.5" fill="#543A23" />
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
