"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CharacterType, PerformanceState } from "./types";
import { StudentCharacter } from "./characters/StudentCharacter";
import { TeacherCharacter } from "./characters/TeacherCharacter";
import { ProfessorCharacter } from "./characters/ProfessorCharacter";

interface CharacterStageProps {
  activeCharacter: CharacterType;
  performance: PerformanceState;
  prefersReducedMotion?: boolean;
}

export const CharacterStage = ({
  activeCharacter,
  performance,
  prefersReducedMotion = false,
}: CharacterStageProps) => {
  return (
    <div
      style={{
        width: 280,
        height: 380,
        position: "relative",
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
      }}
    >
      {/* Stage background — subtle, not distracting */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          width: "100%",
          height: 6,
          borderRadius: 3,
          background: "#C4CDD6",
          opacity: 0.4,
        }}
      />

      {/* Characters — AnimatePresence handles enter/exit */}
      <AnimatePresence mode="wait">
        {activeCharacter === "STUDENT" && (
          <motion.div
            key="student"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full flex items-center justify-center"
          >
            <StudentCharacter
              performance={performance}
              prefersReducedMotion={prefersReducedMotion}
            />
          </motion.div>
        )}
        {activeCharacter === "TEACHER" && (
          <motion.div
            key="teacher"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full flex items-center justify-center"
          >
            <TeacherCharacter
              performance={performance}
              prefersReducedMotion={prefersReducedMotion}
            />
          </motion.div>
        )}
        {activeCharacter === "PROFESSOR" && (
          <motion.div
            key="professor"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full flex items-center justify-center"
          >
            <ProfessorCharacter
              performance={performance}
              prefersReducedMotion={prefersReducedMotion}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CharacterStage;
