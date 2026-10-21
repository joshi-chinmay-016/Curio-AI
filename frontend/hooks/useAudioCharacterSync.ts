"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  CharacterType,
  CharacterAnimationState,
  AudioLearningMode,
} from "@/types/audioLearning";
import { CharacterId, PerformanceState } from "@/types/performanceEngine";
import { speechService } from "@/services/speechService";

export interface AudioCharacterSyncConfig {
  initialMode?: AudioLearningMode;
  initialTopic?: string;
  onInterventionStart?: () => void;
  onInterventionEnd?: () => void;
}

export interface AudioCharacterSyncState {
  character: CharacterType; // "student" | "teacher" | "professor"
  characterId: CharacterId; // "STUDENT" | "TEACHER" | "PROFESSOR"
  performanceState: PerformanceState;
  animationState: CharacterAnimationState;
  isPlayingSpeech: boolean;
  isTeacherActive: boolean;
  clipboardMark: "none" | "check" | "cross" | "in-progress";
  currentSpeechText: string;
  spokenCharIndex: number;
}

export function useAudioCharacterSync(config: AudioCharacterSyncConfig = {}) {
  const initialMode = config.initialMode || "STUDENT";

  const [character, setCharacterState] = useState<CharacterType>(
    initialMode === "PROFESSOR" ? "professor" : "student"
  );
  const [animationState, setAnimationState] = useState<CharacterAnimationState>("idle");
  const [isTeacherActive, setIsTeacherActive] = useState<boolean>(false);
  const [isPlayingSpeech, setIsPlayingSpeech] = useState<boolean>(false);
  const [currentSpeechText, setCurrentSpeechText] = useState<string>("");
  const [spokenCharIndex, setSpokenCharIndex] = useState<number>(0);
  const [clipboardMark, setClipboardMark] = useState<"none" | "check" | "cross" | "in-progress">("none");

  // Session & Turn Tracking Refs for Race Condition Protection
  const activeSessionIdRef = useRef<string | null>(null);
  const activeTurnIndexRef = useRef<number>(0);
  const isMountedRef = useRef<boolean>(true);
  const reactionTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Clear pending reaction timers
  const clearReactionTimer = useCallback(() => {
    if (reactionTimerRef.current) {
      clearTimeout(reactionTimerRef.current);
      reactionTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearReactionTimer();
      speechService.stop();
    };
  }, [clearReactionTimer]);

  // Subscribe to central speechService state to guarantee 100% synchronization
  useEffect(() => {
    const unsubscribe = speechService.subscribe((state) => {
      if (!isMountedRef.current) return;
      setIsPlayingSpeech(state.isPlaying);
      if (!state.isPlaying && (animationState === "speaking" || animationState === "explaining")) {
        setAnimationState("idle");
        setSpokenCharIndex(0);
      }
    });
    return () => unsubscribe();
  }, [animationState]);

  // Map to PerformanceState
  const characterId: CharacterId =
    character === "teacher" || isTeacherActive
      ? "TEACHER"
      : character === "professor"
      ? "PROFESSOR"
      : "STUDENT";

  let performanceState: PerformanceState = "IDLE";
  switch (animationState) {
    case "recording":
    case "listening":
      performanceState = "LISTENING_ACTIVE";
      break;
    case "transcribing":
    case "thinking":
      performanceState = "THINKING";
      break;
    case "speaking":
      performanceState = characterId === "TEACHER" ? "EXPLAINING" : "SPEAKING";
      break;
    case "explaining":
      performanceState = "EXPLAINING";
      break;
    case "asking":
    case "curious":
      performanceState = "ASKING";
      break;
    case "taking_notes":
      performanceState = "TAKING_NOTES";
      break;
    case "marking":
      performanceState = "MARKING";
      break;
    case "impressed":
      performanceState = "REACTING_POSITIVE";
      break;
    case "confused":
      performanceState = "REACTING_CONFUSED";
      break;
    case "skeptical":
    case "disappointed":
      performanceState = "REACTING_STRICT";
      break;
    case "grumpy":
      performanceState = "REACTING_GRUMPY";
      break;
    case "leaving":
      performanceState = "EXITING";
      break;
    case "teacher_transition":
      performanceState = "ENTERING";
      break;
    case "idle":
    default:
      performanceState = "IDLE";
      break;
  }

  // Override to SPEAKING/EXPLAINING only when TTS is actually outputting audio
  if (isPlayingSpeech) {
    performanceState = characterId === "TEACHER" ? "EXPLAINING" : "SPEAKING";
  }

  // Set Session ID
  const setSessionId = useCallback((id: string) => {
    activeSessionIdRef.current = id;
    activeTurnIndexRef.current = 1;
  }, []);

  // Set Mode
  const setMode = useCallback((mode: AudioLearningMode) => {
    clearReactionTimer();
    speechService.stop();
    if (mode === "PROFESSOR") {
      setCharacterState("professor");
      setIsTeacherActive(false);
    } else {
      setCharacterState("student");
      setIsTeacherActive(false);
    }
    setAnimationState("idle");
    setClipboardMark("none");
  }, [clearReactionTimer]);

  // Audio Lifecycle: Recording Started
  const handleRecordingStart = useCallback(() => {
    clearReactionTimer();
    speechService.stop();
    setAnimationState("recording");
  }, [clearReactionTimer]);

  // Audio Lifecycle: Recording Stopped
  const handleRecordingStop = useCallback(() => {
    if (animationState === "recording") {
      setAnimationState("thinking");
    }
  }, [animationState]);

  // Audio Lifecycle: Transcription Started
  const handleTranscriptionStart = useCallback(() => {
    setAnimationState("transcribing");
  }, []);

  // Audio Lifecycle: Answer Submitted to AI Backend
  const handleAnswerSubmit = useCallback((mode: AudioLearningMode) => {
    clearReactionTimer();
    speechService.stop();
    if (mode === "PROFESSOR") {
      setAnimationState("marking");
      setClipboardMark("in-progress");
    } else {
      setAnimationState("taking_notes");
    }
  }, [clearReactionTimer]);

  // Audio Lifecycle: AI Evaluation Received
  const handleEvaluationReceived = useCallback(
    (
      mode: AudioLearningMode,
      nextMode: string,
      shouldRestoreInterrupted: boolean,
      correctness: number = 0.7
    ) => {
      clearReactionTimer();

      // Student Mode
      if (mode === "STUDENT") {
        // Teacher Intervention
        if (nextMode === "TEACHER" && !isTeacherActive) {
          setIsTeacherActive(true);
          setCharacterState("teacher");
          setAnimationState("teacher_transition");
          config.onInterventionStart?.();
          return;
        }

        // Return from Teacher to Student
        if (shouldRestoreInterrupted && isTeacherActive) {
          setIsTeacherActive(false);
          setCharacterState("student");
          setAnimationState("impressed");
          config.onInterventionEnd?.();
          return;
        }

        // Regular Student feedback reaction
        if (correctness >= 0.8) {
          setAnimationState("impressed");
        } else if (correctness < 0.5) {
          setAnimationState("confused");
        } else {
          setAnimationState("curious");
        }
      } else {
        // Professor Mode
        if (correctness >= 0.8) {
          setAnimationState("impressed");
          setClipboardMark("check");
        } else if (correctness < 0.4) {
          setAnimationState("skeptical");
          setClipboardMark("cross");
        } else {
          setAnimationState("idle");
          setClipboardMark("none");
        }
      }
    },
    [clearReactionTimer, config, isTeacherActive]
  );

  // Audio Lifecycle: Professor Question Skip (3-strike check)
  const handleProfessorSkip = useCallback(
    (nextUnansweredCount: number, onGrumpyEnd?: () => void) => {
      clearReactionTimer();
      if (nextUnansweredCount >= 3) {
        setAnimationState("grumpy");
        setClipboardMark("cross");
      } else {
        setAnimationState("skeptical");
        setClipboardMark("cross");
      }
    },
    [clearReactionTimer]
  );

  // Speech Lifecycle: Start Speaking
  const handleSpeechStart = useCallback((cleanText: string) => {
    setCurrentSpeechText(cleanText);
    setSpokenCharIndex(0);
    setIsPlayingSpeech(true);
    setAnimationState("speaking");
  }, []);

  // Speech Lifecycle: Spoken Char Boundary
  const handleSpeechBoundary = useCallback((charIndex: number) => {
    setSpokenCharIndex(charIndex);
  }, []);

  // Speech Lifecycle: Speech Finished
  const handleSpeechEnd = useCallback(() => {
    setIsPlayingSpeech(false);
    setAnimationState("idle");
    setSpokenCharIndex(0);
  }, []);

  // Speech Lifecycle: Speech Interrupted or Errored
  const handleSpeechInterrupt = useCallback(() => {
    speechService.stop();
    setIsPlayingSpeech(false);
    setAnimationState("idle");
    setSpokenCharIndex(0);
  }, []);

  // Reset character controller
  const resetController = useCallback(
    (mode: AudioLearningMode = "STUDENT") => {
      clearReactionTimer();
      speechService.stop();
      activeSessionIdRef.current = null;
      activeTurnIndexRef.current = 0;
      setMode(mode);
      setIsPlayingSpeech(false);
      setCurrentSpeechText("");
      setSpokenCharIndex(0);
    },
    [clearReactionTimer, setMode]
  );

  return {
    // State
    character,
    characterId,
    performanceState,
    animationState,
    isPlayingSpeech,
    isTeacherActive,
    clipboardMark,
    currentSpeechText,
    spokenCharIndex,

    // Actions & Event Bindings
    setSessionId,
    setMode,
    setAnimationState,
    handleRecordingStart,
    handleRecordingStop,
    handleTranscriptionStart,
    handleAnswerSubmit,
    handleEvaluationReceived,
    handleProfessorSkip,
    handleSpeechStart,
    handleSpeechBoundary,
    handleSpeechEnd,
    handleSpeechInterrupt,
    resetController,
  };
}
