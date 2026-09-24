"use client";

import React from "react";
import { motion } from "framer-motion";

export function HeroIsometricWidget() {
  return (
    <div className="relative w-full max-w-[420px] h-[340px] flex flex-col items-center justify-center select-none">
      <svg
        viewBox="-60 -40 380 300"
        className="w-full h-full overflow-visible"
      >
        <defs>
          <pattern
            id="hero-gap-hatch"
            patternUnits="userSpaceOnUse"
            width="8"
            height="8"
            patternTransform="rotate(-45)"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="8"
              stroke="#FF6B1A"
              strokeWidth="2.5"
            />
          </pattern>
        </defs>

        <g transform="translate(100, 70) skewX(-30) scale(1, 0.866)">
          {/* Layer 1 (Bottom) */}
          <motion.g
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: 50 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <rect
              x="0"
              y="0"
              width="160"
              height="90"
              fill="#FFFFFF"
              stroke="#0F2B4A"
              strokeWidth="1.5"
              rx="3"
            />
            {/* 2 solid cells (navy) */}
            <rect x="10" y="10" width="65" height="32" fill="#0F2B4A" rx="2" />
            <rect x="85" y="10" width="65" height="32" fill="#0F2B4A" rx="2" />
            <rect x="10" y="48" width="65" height="32" fill="#3A63FF" opacity="0.8" rx="2" />
            <rect x="85" y="48" width="65" height="32" fill="#E8EEF3" stroke="#C4CDD6" rx="2" />
          </motion.g>

          {/* Layer 2 (Middle) */}
          <motion.g
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: 10 }}
            transition={{ duration: 0.6, delay: 0.45 }}
          >
            <rect
              x="0"
              y="0"
              width="160"
              height="90"
              fill="#FFFFFF"
              stroke="#0F2B4A"
              strokeWidth="1.5"
              rx="3"
            />
            <rect x="10" y="10" width="65" height="32" fill="#0F2B4A" rx="2" />
            {/* 1 hatched orange cell (gap) */}
            <rect x="85" y="10" width="65" height="32" fill="#FFFFFF" rx="2" />
            <rect
              x="85"
              y="10"
              width="65"
              height="32"
              fill="url(#hero-gap-hatch)"
              stroke="#FF6B1A"
              strokeWidth="1.5"
              rx="2"
            />
            <rect x="10" y="48" width="65" height="32" fill="#3A63FF" opacity="0.8" rx="2" />
            <rect x="85" y="48" width="65" height="32" fill="#E8EEF3" stroke="#C4CDD6" rx="2" />
          </motion.g>

          {/* Layer 3 (Top) */}
          <motion.g
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: -30 }}
            transition={{ duration: 0.6, delay: 0.6 }}
          >
            <rect
              x="0"
              y="0"
              width="160"
              height="90"
              fill="#FFFFFF"
              stroke="#0F2B4A"
              strokeWidth="1.5"
              rx="3"
            />
            {/* 1 empty, 1 hatched, 2 solid */}
            <rect x="10" y="10" width="65" height="32" fill="#0F2B4A" rx="2" />
            <rect x="85" y="10" width="65" height="32" fill="#E8EEF3" stroke="#C4CDD6" rx="2" />
            <rect x="10" y="48" width="65" height="32" fill="#FFFFFF" rx="2" />
            <rect
              x="10"
              y="48"
              width="65"
              height="32"
              fill="url(#hero-gap-hatch)"
              stroke="#FF6B1A"
              strokeWidth="1.5"
              rx="2"
            />
            <rect x="85" y="48" width="65" height="32" fill="#0F2B4A" rx="2" />
          </motion.g>
        </g>
      </svg>

      <div className="font-mono text-[11px] font-bold tracking-widest text-navy/60 uppercase mt-2">
        YOUR KNOWLEDGE, MAPPED.
      </div>
    </div>
  );
}
