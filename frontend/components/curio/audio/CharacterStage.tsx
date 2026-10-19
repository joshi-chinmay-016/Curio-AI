"use client";

import React, { memo } from "react";
import {
  CharacterType,
  CharacterAnimationState,
} from "@/types/audioLearning";
import {
  CharacterId,
  PerformanceState,
} from "@/types/performanceEngine";
import { CharacterStage as NewCharacterStage } from "@/components/character/CharacterStage";

interface CharacterStageProps {
  character: CharacterType;
  animationState: CharacterAnimationState | PerformanceState;
  activeConcept?: string;
  isTeacherIntervention?: boolean;
  isPlayingSpeech?: boolean;
  onStopSpeech?: () => void;
  onReplaySpeech?: () => void;
  statusLabel?: string;
}

export const CharacterStage = memo(function CharacterStage({
  character,
  animationState,
  activeConcept,
  isTeacherIntervention = false,
  isPlayingSpeech = false,
  onStopSpeech,
  onReplaySpeech,
  statusLabel,
}: CharacterStageProps) {
  // Map CharacterType to CharacterId
  const characterId: CharacterId =
    character === "teacher" || isTeacherIntervention
      ? "TEACHER"
      : character === "professor"
      ? "PROFESSOR"
      : "STUDENT";

  // Map AnimationState to PerformanceState
  let performanceState: PerformanceState = "IDLE";

  const stateStr = String(animationState).toLowerCase();

  switch (stateStr) {
    case "listening":
    case "recording":
    case "listening_active":
      performanceState = "LISTENING_ACTIVE";
      break;
    case "listening_idle":
      performanceState = "LISTENING_IDLE";
      break;
    case "transcribing":
    case "thinking":
      performanceState = "THINKING";
      break;
    case "evaluating":
      performanceState = "EVALUATING";
      break;
    case "speaking":
      performanceState = "SPEAKING";
      break;
    case "asking":
    case "curious":
      performanceState = "ASKING";
      break;
    case "taking_notes":
      performanceState = "TAKING_NOTES";
      break;
    case "confused":
    case "reacting_confused":
      performanceState = "REACTING_CONFUSED";
      break;
    case "impressed":
    case "reacting_positive":
      performanceState = "REACTING_POSITIVE";
      break;
    case "skeptical":
    case "disappointed":
    case "reacting_strict":
      performanceState = "REACTING_STRICT";
      break;
    case "marking":
      performanceState = "MARKING";
      break;
    case "grumpy":
    case "reacting_grumpy":
      performanceState = "REACTING_GRUMPY";
      break;
    case "leaving":
    case "exiting":
      performanceState = "EXITING";
      break;
    case "offstage":
      performanceState = "OFFSTAGE";
      break;
    case "teacher_transition":
    case "entering":
      performanceState = "ENTERING";
      break;
    case "explaining":
      performanceState = "EXPLAINING";
      break;
    case "idle":
    default:
      performanceState = "IDLE";
      break;
  }

  // Determine clipboard marking for Professor
  let clipboardMark: "none" | "check" | "cross" | "in-progress" = "none";
  if (stateStr === "marking") {
    clipboardMark = "in-progress";
  } else if (stateStr === "impressed" || stateStr === "reacting_positive") {
    clipboardMark = "check";
  } else if (
    stateStr === "skeptical" ||
    stateStr === "disappointed" ||
    stateStr === "reacting_strict"
  ) {
    clipboardMark = "cross";
  }

  return (
    <NewCharacterStage
      character={characterId}
      performanceState={performanceState}
      isPlayingSpeech={isPlayingSpeech}
      statusLabel={statusLabel}
      clipboardMark={clipboardMark}
      onStopSpeech={onStopSpeech}
      onReplaySpeech={onReplaySpeech}
    />
  );
});
