"use client";

import { useSessionStore } from "@/stores/sessionStore";
import { SessionMode } from "@/types/session";

export function useCurrentMode() {
  const mode = useSessionStore((state) => state.mode);
  const setMode = useSessionStore((state) => state.setMode);
  const activeGap = useSessionStore((state) => state.activeGap);
  const setActiveGap = useSessionStore((state) => state.setActiveGap);

  const isStudent = mode === "STUDENT";
  const isTeacher = mode === "TEACHER";
  const isEvaluating = mode === "EVALUATING";

  const switchToTeacherMode = (gapTitle = "Boundary Conditions", conceptId = "boundary-conditions") => {
    setActiveGap({
      conceptId,
      title: gapTitle,
      severity: "HIGH",
    });
    setMode("TEACHER");
  };

  const switchToStudentMode = () => {
    setActiveGap(undefined);
    setMode("STUDENT");
  };

  const switchToEvaluatingMode = () => {
    setMode("EVALUATING");
  };

  return {
    mode,
    isStudent,
    isTeacher,
    isEvaluating,
    activeGap,
    setMode,
    switchToTeacherMode,
    switchToStudentMode,
    switchToEvaluatingMode,
  };
}
