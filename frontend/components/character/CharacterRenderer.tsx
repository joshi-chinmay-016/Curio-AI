"use client";

import React, { memo } from "react";
import { motion } from "framer-motion";
import {
  CharacterId,
  PerformanceState,
  AnimationDefinition,
} from "@/types/performanceEngine";
import { studentAnimations } from "./animations/student.animations";
import { teacherAnimations } from "./animations/teacher.animations";
import { professorAnimations } from "./animations/professor.animations";
import { StudentCharacter } from "./characters/StudentCharacter";
import { TeacherCharacter } from "./characters/TeacherCharacter";
import { ProfessorCharacter } from "./characters/ProfessorCharacter";

interface CharacterRendererProps {
  character: CharacterId;
  performanceState: PerformanceState;
  prefersReducedMotion?: boolean;
  clipboardMark?: "none" | "check" | "cross" | "in-progress";
}

export const CharacterRenderer = memo(function CharacterRenderer({
  character,
  performanceState,
  prefersReducedMotion = false,
  clipboardMark = "none",
}: CharacterRendererProps) {
  if (performanceState === "OFFSTAGE") {
    return null;
  }

  // Lookup animation definition for stage-level transforms
  let animMap: Record<string, AnimationDefinition> = studentAnimations;
  if (character === "TEACHER") {
    animMap = teacherAnimations;
  } else if (character === "PROFESSOR") {
    animMap = professorAnimations;
  }

  const animDef = animMap[performanceState] || animMap["IDLE"];
  const bodyAnim = animDef?.bodyAnimation || {};

  // In reduced motion, cancel all transforms and keep opacity 1
  const animateTarget = prefersReducedMotion
    ? { x: 0, y: 0, rotate: 0, scale: 1, opacity: 1 }
    : {
        x: bodyAnim.translateX ?? 0,
        y: bodyAnim.translateY ?? 0,
        rotate: bodyAnim.rotate ?? 0,
        scale: bodyAnim.scale ?? 1,
        opacity: bodyAnim.opacity ?? 1,
      };

  const transitionConfig = prefersReducedMotion
    ? { duration: 0 }
    : {
        ...(bodyAnim.transition || {
          type: "tween",
          ease: "easeInOut",
          duration: 0.4,
        }),
        ...(bodyAnim.times ? { times: bodyAnim.times } : {}),
      };

  const isTakingNotes = character === "STUDENT" && performanceState === "TAKING_NOTES";

  return (
    <div className="relative w-full h-full flex items-center justify-center select-none overflow-hidden">
      {/* Main Layered SVG Character with Performance Animation */}
      <motion.div
        key={`${character}-${performanceState}`}
        animate={animateTarget}
        transition={transitionConfig as any}
        className="relative w-[280px] h-[340px] md:w-[320px] md:h-[380px] flex items-center justify-center"
      >
        {character === "STUDENT" && (
          <StudentCharacter
            performance={performanceState}
            prefersReducedMotion={prefersReducedMotion}
          />
        )}
        {character === "TEACHER" && (
          <TeacherCharacter
            performance={performanceState}
            prefersReducedMotion={prefersReducedMotion}
          />
        )}
        {character === "PROFESSOR" && (
          <ProfessorCharacter
            performance={performanceState}
            prefersReducedMotion={prefersReducedMotion}
            clipboardMark={clipboardMark}
          />
        )}

        {/* Dynamic Listening Soundwave Pulse Rings */}
        {(performanceState === "LISTENING_ACTIVE" || (performanceState as string) === "LISTENING") && (
          <div className="absolute top-14 right-10 pointer-events-none z-10">
            <motion.div
              className={`w-8 h-8 rounded-full border-2 ${
                character === "PROFESSOR"
                  ? "border-amber-400/80"
                  : character === "TEACHER"
                  ? "border-gap-orange/80"
                  : "border-cobalt/80"
              }`}
              animate={{ scale: [1, 2.2, 1], opacity: [0.9, 0, 0.9] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
            />
            <motion.div
              className={`absolute inset-0 rounded-full border-2 ${
                character === "PROFESSOR"
                  ? "border-amber-300/60"
                  : character === "TEACHER"
                  ? "border-gap-orange/60"
                  : "border-cobalt/60"
              }`}
              animate={{ scale: [1, 2.8, 1], opacity: [0.7, 0, 0.7] }}
              transition={{ duration: 1.6, repeat: Infinity, delay: 0.4, ease: "easeOut" }}
            />
          </div>
        )}

        {/* Ambient Character Focus Glow */}
        {isTakingNotes && (
          <div className="absolute -bottom-6 w-48 h-24 bg-cobalt/25 blur-2xl rounded-full pointer-events-none" />
        )}
        {(performanceState === "MARKING" || performanceState === "EVALUATING") && (
          <div className="absolute -bottom-6 right-0 w-48 h-24 bg-amber-500/20 blur-2xl rounded-full pointer-events-none" />
        )}
      </motion.div>
    </div>
  );
});
