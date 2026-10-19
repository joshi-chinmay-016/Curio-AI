"use client";

import React, { memo } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  CharacterId,
  PerformanceState,
  AnimationDefinition,
} from "@/types/performanceEngine";
import { studentAnimations } from "./animations/student.animations";
import { teacherAnimations } from "./animations/teacher.animations";
import { professorAnimations } from "./animations/professor.animations";
import { Notebook } from "./props/Notebook";
import { Book } from "./props/Book";
import { Clipboard } from "./props/Clipboard";
import { ThoughtBubble } from "./props/ThoughtBubble";
import { QuestionMark } from "./props/QuestionMark";
import { CheckMark } from "./props/CheckMark";

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

  // Lookup animation definition
  let animMap: Record<string, AnimationDefinition> = studentAnimations;
  let imageSrc = "/characters/student.png";
  let altText = "Leo - Curious Student";

  if (character === "TEACHER") {
    animMap = teacherAnimations;
    imageSrc = "/characters/teacher.png";
    altText = "Ms. Clara - Pedagogical Guide";
  } else if (character === "PROFESSOR") {
    animMap = professorAnimations;
    imageSrc = "/characters/professor.png";
    altText = "Prof. Sterling - Strict Oral Examiner";
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

  // State checks for props & overlays
  const isTakingNotes = character === "STUDENT" && performanceState === "TAKING_NOTES";
  const isTeacherPresent = character === "TEACHER";
  const isTeacherExplaining =
    isTeacherPresent && (performanceState === "EXPLAINING" || performanceState === "SPEAKING");
  const isProfessorPresent = character === "PROFESSOR";
  const isThinking = performanceState === "THINKING";
  const isAsking = performanceState === "ASKING";
  const isConfused = performanceState === "REACTING_CONFUSED";
  const isPositive = performanceState === "REACTING_POSITIVE";

  return (
    <div className="relative w-full h-full flex items-center justify-center select-none overflow-hidden">
      {/* 1. Behind-Character Prop Layer (Teacher Book if idle) */}
      <Book
        visible={isTeacherPresent && !isTeacherExplaining}
        open={false}
        position="held-left"
      />

      {/* 2. Main Character Render with Performance Transform */}
      <motion.div
        key={`${character}-${performanceState}`}
        animate={animateTarget}
        transition={transitionConfig as any}
        className="relative w-[280px] h-[340px] md:w-[320px] md:h-[380px] flex items-center justify-center"
      >
        <Image
          src={imageSrc}
          alt={altText}
          fill
          priority
          sizes="(max-width: 768px) 280px, 320px"
          className="object-contain drop-shadow-2xl pointer-events-none"
        />

        {/* Listening ear audio pulse indicator for Student */}
        {character === "STUDENT" && performanceState === "LISTENING_ACTIVE" && (
          <motion.div
            className="absolute top-16 right-14 w-6 h-6 rounded-full border-2 border-cobalt/80 pointer-events-none"
            animate={{ scale: [1, 1.8, 1], opacity: [0.9, 0, 0.9] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "easeOut" }}
          />
        )}
      </motion.div>

      {/* 3. Foreground Props Layer */}
      {/* Student Notebook */}
      <Notebook visible={isTakingNotes} position="student-front" />

      {/* Teacher Active Book (open when explaining) */}
      <Book
        visible={isTeacherExplaining}
        open={true}
        position="held-left"
      />

      {/* Professor Clipboard */}
      <Clipboard
        visible={isProfessorPresent && performanceState !== "EXITING"}
        markState={
          performanceState === "MARKING"
            ? "in-progress"
            : clipboardMark
        }
        position={
          performanceState === "ASKING" || performanceState === "MARKING"
            ? "raised"
            : performanceState === "REACTING_GRUMPY"
            ? "lowered"
            : "held-front"
        }
      />

      {/* 4. Overlays Layer */}
      {/* Thought bubble (Appears ONLY in THINKING state) */}
      <ThoughtBubble
        visible={isThinking}
        content="thinking-dots"
        position="above-right"
      />

      {/* Question mark (Cobalt for asking, orange for confused) */}
      <QuestionMark
        visible={isAsking || isConfused}
        color={isConfused ? "#FF6B1A" : "#3A63FF"}
        size={isAsking ? 28 : 24}
        position="above-head"
      />

      {/* Checkmark (Approval on positive reaction) */}
      <CheckMark visible={isPositive} color="#3A63FF" />
    </div>
  );
});
