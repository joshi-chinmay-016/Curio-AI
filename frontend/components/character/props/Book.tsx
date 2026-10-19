"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface BookProps {
  visible: boolean;
  open?: boolean; // closed (idle) vs open (explaining)
  position?: "held-left";
}

export function Book({
  visible,
  open = false,
  position = "held-left",
}: BookProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="teacher-book"
          initial={{ opacity: 0, scale: 0.85, y: 15 }}
          animate={{
            opacity: 1,
            scale: 1,
            y: open ? -6 : 0,
          }}
          exit={{ opacity: 0, scale: 0.85, y: 15 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="absolute bottom-6 left-8 z-20 pointer-events-none drop-shadow-xl"
          data-testid="teacher-book-prop"
        >
          <svg
            width="65"
            height="85"
            viewBox="0 0 65 85"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Back cover */}
            <rect
              x="4"
              y="4"
              width="56"
              height="76"
              rx="4"
              fill="#0F2B4A"
              stroke="#1E3A5F"
              strokeWidth="2"
            />
            {/* Pages block */}
            <rect
              x="8"
              y="8"
              width="50"
              height="68"
              rx="2"
              fill="#F5F2EB"
            />
            {/* Page lines */}
            <line x1="14" y1="18" x2="50" y2="18" stroke="#D1C7B7" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="26" x2="46" y2="26" stroke="#D1C7B7" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="34" x2="48" y2="34" stroke="#D1C7B7" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="42" x2="42" y2="42" stroke="#D1C7B7" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="14" y1="50" x2="48" y2="50" stroke="#D1C7B7" strokeWidth="1.5" strokeLinecap="round" />

            {/* Bookmark ribbon */}
            <path
              d="M32 4V52L36 48L40 52V4H32Z"
              fill="#FF6B1A"
            />

            {/* Front cover with 3D opening angle */}
            <motion.rect
              x="4"
              y="4"
              width="56"
              height="76"
              rx="4"
              fill="#0F2B4A"
              stroke="#2B4C7E"
              strokeWidth="2"
              animate={{
                rotateY: open ? -35 : 0,
                x: open ? -10 : 0,
                opacity: open ? 0.35 : 1,
              }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
              style={{ transformOrigin: "left center" }}
            />
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
