/**
 * Curio AI — Character Performance Engine Types
 * Pure types for the character performance state machine, animations, props, and overlays.
 */

export type CharacterId = "STUDENT" | "TEACHER" | "PROFESSOR";

export type PerformanceState =
  // ── NEUTRAL ──────────────────────────────────────────────
  | "OFFSTAGE"          // Not visible. Nothing playing.
  | "ENTERING"          // Walking/sliding into position.
  | "IDLE"              // Settled. Breathing. Waiting.
  | "EXITING"           // Walking/sliding off stage.

  // ── LISTENING STATES ──────────────────────────────────────
  | "LISTENING_ACTIVE"  // Mic is recording. Visibly attentive.
  | "LISTENING_IDLE"    // Mic open but silent. Slightly less active.

  // ── PROCESSING STATES ─────────────────────────────────────
  | "THINKING"          // AI request in flight. Head tilt. Pause.
  | "EVALUATING"        // Assessment running. Note-taking / clipboard.

  // ── SPEAKING STATES ───────────────────────────────────────
  | "SPEAKING"          // TTS/audio playing. Speaking gesture active.
  | "ASKING"            // A question is being spoken. Lean forward.

  // ── REACTION STATES ───────────────────────────────────────
  | "REACTING_POSITIVE" // Good answer. Brief celebratory cue.
  | "REACTING_CONFUSED" // Misconception detected. Head tilt + cue.
  | "REACTING_STRICT"   // Wrong answer (Professor). Eyebrow raise.
  | "REACTING_GRUMPY"   // Session-end failure (Professor only).

  // ── ACTIVITY STATES ───────────────────────────────────────
  | "TAKING_NOTES"      // Writing animation + notebook prop.
  | "MARKING"           // Clipboard check (Professor only).
  | "EXPLAINING"        // Teacher explaining. Confident posture.

  // ── TRANSITION ────────────────────────────────────────────
  | "TRANSITIONING_OUT" // Mid-swap. Character leaving stage.
  | "TRANSITIONING_IN"; // Mid-swap. New character arriving.

export const validTransitions: Record<PerformanceState, PerformanceState[]> = {
  OFFSTAGE:          ["ENTERING", "TRANSITIONING_IN"],
  ENTERING:          ["IDLE", "OFFSTAGE"],
  IDLE:              [
    "LISTENING_ACTIVE",
    "LISTENING_IDLE",
    "SPEAKING",
    "ASKING",
    "THINKING",
    "EXITING",
    "TAKING_NOTES",
    "EVALUATING",
    "EXPLAINING",
    "REACTING_POSITIVE",
    "REACTING_CONFUSED",
    "REACTING_STRICT",
    "REACTING_GRUMPY",
    "TRANSITIONING_OUT"
  ],
  LISTENING_ACTIVE:  ["THINKING", "LISTENING_IDLE", "IDLE"],
  LISTENING_IDLE:    ["LISTENING_ACTIVE", "THINKING", "IDLE"],
  THINKING:          [
    "SPEAKING",
    "ASKING",
    "EVALUATING",
    "TAKING_NOTES",
    "REACTING_POSITIVE",
    "REACTING_CONFUSED",
    "REACTING_STRICT",
    "IDLE"
  ],
  EVALUATING:        [
    "MARKING",
    "SPEAKING",
    "REACTING_POSITIVE",
    "REACTING_STRICT",
    "REACTING_GRUMPY",
    "IDLE"
  ],
  SPEAKING:          ["IDLE", "LISTENING_ACTIVE", "ASKING"],
  ASKING:            ["LISTENING_ACTIVE", "IDLE"],
  TAKING_NOTES:      ["THINKING", "IDLE", "SPEAKING", "ASKING"],
  MARKING:           [
    "REACTING_POSITIVE",
    "REACTING_STRICT",
    "REACTING_GRUMPY",
    "SPEAKING",
    "IDLE"
  ],
  EXPLAINING:        ["ASKING", "IDLE", "EXITING", "SPEAKING"],
  REACTING_POSITIVE: ["IDLE", "ASKING", "TAKING_NOTES", "SPEAKING"],
  REACTING_CONFUSED: ["SPEAKING", "ASKING", "IDLE"],
  REACTING_STRICT:   ["SPEAKING", "MARKING", "ASKING", "IDLE"],
  REACTING_GRUMPY:   ["EXITING", "OFFSTAGE"],
  EXITING:           ["OFFSTAGE", "TRANSITIONING_OUT"],
  TRANSITIONING_OUT: ["OFFSTAGE"],
  TRANSITIONING_IN:  ["IDLE", "ENTERING"],
};

export interface TransitionOptions {
  force?: boolean;
  onComplete?: () => void;
}

export interface BodyAnimation {
  translateX?: number | number[];
  translateY?: number | number[];
  rotate?: number | number[];
  scale?: number | number[];
  skewX?: number | number[];
  opacity?: number | number[];
  times?: number[];
  transition?: {
    type?: "tween" | "spring" | "inertia";
    duration?: number;
    ease?: string | number[] | readonly number[];
    stiffness?: number;
    damping?: number;
    repeat?: number;
    repeatType?: "loop" | "reverse" | "mirror";
  };
}

export interface PropAnimation {
  type: "NOTEBOOK" | "BOOK" | "CLIPBOARD";
  enterFrom?: "below" | "left" | "right";
  enterDuration?: number;
  position?: "student-front" | "held-left" | "held-front" | "lowered" | "raised";
  animation?: "open" | "lift" | "mark" | "hold" | "lower" | "slam-close";
  writingLines?: {
    count: number;
    interval: number;
    lineColor: string;
    lineWidth: string;
  };
  triggerAt?: number;
  duration?: number;
  exitTo?: "below";
  exitDuration?: number;
  enterWith?: "character";
  sequence?: Array<{
    action: "lift" | "mark" | "hold" | "lower";
    duration: number;
    markType?: "check-or-cross" | "check" | "cross";
  }>;
}

export interface OverlayAnimation {
  type: "LISTENING_INDICATOR" | "THOUGHT_BUBBLE" | "QUESTION_MARK" | "CHECK_MARK";
  position: "near-ear" | "above-head" | "above-head-right" | "above-left" | "above";
  animation?: "pulse" | "thinking-dots" | "pop-in" | "fade-in" | "draw-in";
  color?: string;
  size?: number;
  delay?: number;
  duration?: number;
  exitOn?: "state-change";
}

export interface AnimationDefinition {
  id: string;
  character: CharacterId | "ALL";
  performanceState: PerformanceState;
  bodyAnimation: BodyAnimation;
  props?: PropAnimation[];
  overlays?: OverlayAnimation[];
  duration: number;
  loop: boolean | number;
  interruptible: boolean;
  onComplete?: PerformanceState;
}

export interface AssessmentResult {
  isPositive?: boolean;
  hasMisconception?: boolean;
  isWeak?: boolean;
  correctness?: number;
}

export interface LearningEngineEvents {
  onRecordStart?: () => void;
  onRecordStop?: () => void;
  onTranscriptStart?: () => void;
  onTranscriptEnd?: () => void;
  onAIRequestStart?: () => void;
  onAIRequestEnd?: () => void;
  onAssessmentResult?: (result: AssessmentResult) => void;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onSpeechError?: () => void;
  onTeacherIntervention?: () => void;
  onTeacherComplete?: () => void;
  onProfessorMode?: () => void;
  onSessionEnd?: (reason: "user" | "completed" | "unanswered_threshold") => void;
}

export interface CharacterPerformanceEngine {
  setCharacter(character: CharacterId): void;
  transition(to: PerformanceState, options?: TransitionOptions): void;
  swapCharacter(to: CharacterId, onSwapReady?: () => void): void;
  interrupt(reason: "error" | "navigation" | "user"): void;
  destroy(): void;
  readonly state: PerformanceState;
  readonly activeCharacter: CharacterId;
  readonly isAnimating: boolean;
}
