"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  CharacterId,
  PerformanceState,
  validTransitions,
  TransitionOptions,
  CharacterPerformanceEngine,
} from "@/types/performanceEngine";

interface UsePerformanceEngineProps {
  initialCharacter?: CharacterId;
  initialState?: PerformanceState;
}

export function usePerformanceEngine({
  initialCharacter = "STUDENT",
  initialState = "IDLE",
}: UsePerformanceEngineProps = {}): CharacterPerformanceEngine & {
  prefersReducedMotion: boolean;
} {
  const [activeCharacter, setActiveCharacterState] = useState<CharacterId>(initialCharacter);
  const [state, setState] = useState<PerformanceState>(initialState);
  const [isAnimating, setIsAnimating] = useState<boolean>(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(false);

  const activeCharacterRef = useRef<CharacterId>(initialCharacter);
  const stateRef = useRef<PerformanceState>(initialState);
  const isDestroyedRef = useRef<boolean>(false);
  const activeTimersRef = useRef<NodeJS.Timeout[]>([]);

  // Update refs on change
  useEffect(() => {
    activeCharacterRef.current = activeCharacter;
  }, [activeCharacter]);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Reduced motion media query listener
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;

    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mq.matches);

    const handler = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    if (mq.addEventListener) {
      mq.addEventListener("change", handler);
    } else if ((mq as any).addListener) {
      (mq as any).addListener(handler);
    }

    return () => {
      if (mq.removeEventListener) {
        mq.removeEventListener("change", handler);
      } else if ((mq as any).removeListener) {
        (mq as any).removeListener(handler);
      }
    };
  }, []);

  const clearAllTimers = useCallback(() => {
    activeTimersRef.current.forEach((t) => clearTimeout(t));
    activeTimersRef.current = [];
  }, []);

  const scheduleTimer = useCallback((fn: () => void, ms: number) => {
    if (isDestroyedRef.current) return;
    const timer = setTimeout(() => {
      activeTimersRef.current = activeTimersRef.current.filter((t) => t !== timer);
      if (!isDestroyedRef.current) {
        fn();
      }
    }, ms);
    activeTimersRef.current.push(timer);
    return timer;
  }, []);

  const setCharacter = useCallback((character: CharacterId) => {
    if (isDestroyedRef.current) return;
    activeCharacterRef.current = character;
    setActiveCharacterState(character);
  }, []);

  const transition = useCallback(
    (to: PerformanceState, options?: TransitionOptions) => {
      if (isDestroyedRef.current) return;

      const current = stateRef.current;
      if (current === to) return;

      // Validate transition
      const allowed = validTransitions[current] || [];
      const isValid = allowed.includes(to) || options?.force === true;

      if (!isValid) {
        console.warn(
          `[PerformanceEngine] Invalid state transition rejected: "${current}" → "${to}". Allowed:`,
          allowed
        );
        return;
      }

      clearAllTimers();
      stateRef.current = to;
      setState(to);
      setIsAnimating(true);

      // Handle self-completing states timing (if not reduced motion)
      let autoDuration = 0;
      let nextState: PerformanceState | null = null;

      if (to === "ENTERING") {
        autoDuration = activeCharacterRef.current === "PROFESSOR" ? 1000 : 800;
        nextState = "IDLE";
      } else if (to === "EXITING") {
        autoDuration = activeCharacterRef.current === "PROFESSOR" ? 3200 : 700;
        nextState = "OFFSTAGE";
      } else if (to === "REACTING_POSITIVE") {
        autoDuration = activeCharacterRef.current === "STUDENT" ? 700 : 600;
        nextState = activeCharacterRef.current === "STUDENT" ? "TAKING_NOTES" : "IDLE";
      } else if (to === "REACTING_CONFUSED") {
        autoDuration = 600;
        nextState = "IDLE";
      } else if (to === "REACTING_STRICT") {
        autoDuration = 800;
        nextState = "IDLE";
      }

      if (prefersReducedMotion) {
        // Reduced motion: complete instantly
        setIsAnimating(false);
        if (nextState) {
          stateRef.current = nextState;
          setState(nextState);
        }
        options?.onComplete?.();
        return;
      }

      if (autoDuration > 0 && nextState) {
        const targetNext = nextState;
        scheduleTimer(() => {
          if (isDestroyedRef.current) return;
          stateRef.current = targetNext;
          setState(targetNext);
          setIsAnimating(false);
          options?.onComplete?.();
        }, autoDuration);
      } else {
        setIsAnimating(false);
        options?.onComplete?.();
      }
    },
    [clearAllTimers, prefersReducedMotion, scheduleTimer]
  );

  const swapCharacter = useCallback(
    (to: CharacterId, onSwapReady?: () => void) => {
      if (isDestroyedRef.current) return;

      clearAllTimers();
      const current = stateRef.current;

      const finishSwapToNew = () => {
        if (isDestroyedRef.current) return;
        activeCharacterRef.current = to;
        setActiveCharacterState(to);

        stateRef.current = "ENTERING";
        setState("ENTERING");
        setIsAnimating(true);

        const enterDuration = prefersReducedMotion
          ? 0
          : to === "PROFESSOR"
          ? 1000
          : 700;

        scheduleTimer(() => {
          if (isDestroyedRef.current) return;
          stateRef.current = "IDLE";
          setState("IDLE");
          setIsAnimating(false);
          onSwapReady?.();
        }, enterDuration);
      };

      if (current === "OFFSTAGE") {
        finishSwapToNew();
      } else {
        // Exit first
        stateRef.current = "EXITING";
        setState("EXITING");
        setIsAnimating(true);

        const exitDuration = prefersReducedMotion ? 0 : 600;
        scheduleTimer(() => {
          if (isDestroyedRef.current) return;
          stateRef.current = "OFFSTAGE";
          setState("OFFSTAGE");
          finishSwapToNew();
        }, exitDuration);
      }
    },
    [clearAllTimers, prefersReducedMotion, scheduleTimer]
  );

  const interrupt = useCallback(
    (reason: "error" | "navigation" | "user") => {
      if (isDestroyedRef.current) return;

      clearAllTimers();
      const current = stateRef.current;

      if (current === "OFFSTAGE") return;

      // Snap safely to neutral pose
      const fallbackState: PerformanceState = "IDLE";
      stateRef.current = fallbackState;
      setState(fallbackState);
      setIsAnimating(false);
    },
    [clearAllTimers]
  );

  const destroy = useCallback(() => {
    isDestroyedRef.current = true;
    clearAllTimers();
  }, [clearAllTimers]);

  useEffect(() => {
    isDestroyedRef.current = false;
    return () => {
      destroy();
    };
  }, [destroy]);

  return {
    state,
    activeCharacter,
    isAnimating,
    prefersReducedMotion,
    setCharacter,
    transition,
    swapCharacter,
    interrupt,
    destroy,
  };
}
