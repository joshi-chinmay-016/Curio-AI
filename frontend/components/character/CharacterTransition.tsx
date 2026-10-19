"use client";

import React, { memo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CharacterId, PerformanceState } from "@/types/performanceEngine";
import { CharacterRenderer } from "./CharacterRenderer";

interface CharacterTransitionProps {
  activeCharacter: CharacterId;
  performanceState: PerformanceState;
  prefersReducedMotion?: boolean;
  clipboardMark?: "none" | "check" | "cross" | "in-progress";
}

export const CharacterTransition = memo(function CharacterTransition({
  activeCharacter,
  performanceState,
  prefersReducedMotion = false,
  clipboardMark = "none",
}: CharacterTransitionProps) {
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.div
          key={activeCharacter}
          initial={
            prefersReducedMotion
              ? { opacity: 1 }
              : {
                  opacity: 0,
                  scale: 0.96,
                  x: activeCharacter === "STUDENT" ? -40 : 40,
                }
          }
          animate={{ opacity: 1, scale: 1, x: 0 }}
          exit={
            prefersReducedMotion
              ? { opacity: 0 }
              : {
                  opacity: 0,
                  scale: 0.94,
                  x: activeCharacter === "STUDENT" ? -60 : 60,
                }
          }
          transition={{
            duration: prefersReducedMotion ? 0 : 0.45,
            ease: "easeInOut",
          }}
          className="relative w-full h-full flex items-center justify-center"
        >
          <CharacterRenderer
            character={activeCharacter}
            performanceState={performanceState}
            prefersReducedMotion={prefersReducedMotion}
            clipboardMark={clipboardMark}
          />
        </motion.div>
      </AnimatePresence>
    </div>
  );
});
