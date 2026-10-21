"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  CharacterType,
  PerformanceState,
  CharacterEngineState,
  CharacterEngineActions,
} from "./types";

export const VALID_TRANSITIONS: Record<PerformanceState, PerformanceState[]> = {
  OFFSTAGE:          ["ENTERING"],
  ENTERING:          ["IDLE", "OFFSTAGE"],
  IDLE:              [
    "LISTENING",
    "LISTENING_ACTIVE",
    "LISTENING_IDLE",
    "SPEAKING",
    "ASKING",
    "THINKING",
    "TAKING_NOTES",
    "EXPLAINING",
    "EVALUATING",
    "REACTING_POSITIVE",
    "REACTING_CONFUSED",
    "REACTING_STRICT",
    "REACTING_GRUMPY",
    "EXITING"
  ],
  LISTENING:         ["THINKING", "IDLE"],
  LISTENING_ACTIVE:  ["THINKING", "LISTENING_IDLE", "IDLE"],
  LISTENING_IDLE:    ["THINKING", "LISTENING_ACTIVE", "IDLE"],
  THINKING:          [
    "SPEAKING",
    "ASKING",
    "TAKING_NOTES",
    "EVALUATING",
    "REACTING_POSITIVE",
    "REACTING_CONFUSED",
    "REACTING_STRICT",
    "IDLE"
  ],
  SPEAKING:          ["IDLE", "LISTENING", "LISTENING_ACTIVE", "ASKING"],
  ASKING:            ["LISTENING", "LISTENING_ACTIVE", "IDLE"],
  TAKING_NOTES:      ["IDLE", "SPEAKING", "THINKING", "ASKING"],
  EXPLAINING:        ["ASKING", "IDLE", "EXITING", "SPEAKING"],
  EVALUATING:        [
    "REACTING_POSITIVE",
    "REACTING_STRICT",
    "REACTING_GRUMPY",
    "SPEAKING",
    "MARKING",
    "IDLE"
  ],
  MARKING:           [
    "REACTING_POSITIVE",
    "REACTING_STRICT",
    "REACTING_GRUMPY",
    "SPEAKING",
    "IDLE"
  ],
  REACTING_POSITIVE: ["IDLE", "TAKING_NOTES", "ASKING"],
  REACTING_CONFUSED: ["SPEAKING", "ASKING", "IDLE"],
  REACTING_STRICT:   ["SPEAKING", "EVALUATING", "IDLE"],
  REACTING_GRUMPY:   ["EXITING", "OFFSTAGE"],
  EXITING:           ["OFFSTAGE", "TRANSITIONING_OUT"],
  TRANSITIONING_OUT: ["OFFSTAGE"],
  TRANSITIONING_IN:  ["IDLE", "ENTERING"],
};

interface UseCharacterEngineProps {
  initialCharacter?: CharacterType;
  initialPerformance?: PerformanceState;
}

export function useCharacterEngine({
  initialCharacter = "STUDENT",
  initialPerformance = "IDLE",
}: UseCharacterEngineProps = {}): CharacterEngineState & CharacterEngineActions {
  const [character, setCharacterState] = useState<CharacterType>(initialCharacter);
  const [performance, setPerformanceState] = useState<PerformanceState>(initialPerformance);
  const [previousPerformance, setPreviousPerformance] = useState<PerformanceState | null>(null);

  const characterRef = useRef<CharacterType>(initialCharacter);
  const performanceRef = useRef<PerformanceState>(initialPerformance);
  const timersRef = useRef<NodeJS.Timeout[]>([]);
  const isDestroyedRef = useRef<boolean>(false);

  useEffect(() => {
    characterRef.current = character;
  }, [character]);

  useEffect(() => {
    performanceRef.current = performance;
  }, [performance]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((t) => clearTimeout(t));
    timersRef.current = [];
  }, []);

  useEffect(() => {
    return () => {
      isDestroyedRef.current = true;
      clearTimers();
    };
  }, [clearTimers]);

  const setCharacter = useCallback((c: CharacterType) => {
    if (isDestroyedRef.current) return;
    characterRef.current = c;
    setCharacterState(c);
  }, []);

  const transition = useCallback((to: PerformanceState) => {
    if (isDestroyedRef.current) return;
    const current = performanceRef.current;
    if (current === to) return;

    const allowed = VALID_TRANSITIONS[current] || [];
    if (!allowed.includes(to)) {
      console.warn(
        `[useCharacterEngine] Invalid transition attempted from "${current}" to "${to}". Staying in "${current}".`
      );
      return;
    }

    setPreviousPerformance(current);
    performanceRef.current = to;
    setPerformanceState(to);
  }, []);

  const swapTo = useCallback(
    (c: CharacterType, onReady?: () => void) => {
      if (isDestroyedRef.current) return;
      clearTimers();

      const finishSwap = () => {
        if (isDestroyedRef.current) return;
        characterRef.current = c;
        setCharacterState(c);
        performanceRef.current = "ENTERING";
        setPerformanceState("ENTERING");

        const tEnter = setTimeout(() => {
          if (isDestroyedRef.current) return;
          performanceRef.current = "IDLE";
          setPerformanceState("IDLE");
          onReady?.();
        }, 500);
        timersRef.current.push(tEnter);
      };

      if (performanceRef.current === "OFFSTAGE") {
        finishSwap();
      } else {
        performanceRef.current = "EXITING";
        setPerformanceState("EXITING");

        const tExit = setTimeout(() => {
          if (isDestroyedRef.current) return;
          performanceRef.current = "OFFSTAGE";
          setPerformanceState("OFFSTAGE");
          finishSwap();
        }, 400);
        timersRef.current.push(tExit);
      }
    },
    [clearTimers]
  );

  const interrupt = useCallback(() => {
    if (isDestroyedRef.current) return;
    clearTimers();
    if (performanceRef.current === "OFFSTAGE") return;
    setPreviousPerformance(performanceRef.current);
    performanceRef.current = "IDLE";
    setPerformanceState("IDLE");
  }, [clearTimers]);

  return {
    character,
    performance,
    previousPerformance,
    setCharacter,
    transition,
    swapTo,
    interrupt,
  };
}
