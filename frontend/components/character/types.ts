/**
 * Curio AI — Character Types
 * Shared types for animated SVG characters, state machine, and performance engine.
 */

export type CharacterType = "STUDENT" | "TEACHER" | "PROFESSOR";
export type CharacterId = CharacterType;

export type PerformanceState =
  | "OFFSTAGE"
  | "ENTERING"
  | "IDLE"
  | "LISTENING"
  | "LISTENING_ACTIVE"
  | "LISTENING_IDLE"
  | "THINKING"
  | "SPEAKING"
  | "ASKING"
  | "TAKING_NOTES"
  | "EXPLAINING"
  | "EVALUATING"
  | "MARKING"
  | "REACTING_POSITIVE"
  | "REACTING_CONFUSED"
  | "REACTING_STRICT"
  | "REACTING_GRUMPY"
  | "EXITING"
  | "TRANSITIONING_OUT"
  | "TRANSITIONING_IN";

export interface CharacterEngineState {
  character: CharacterType;
  performance: PerformanceState;
  previousPerformance: PerformanceState | null;
}

export interface CharacterEngineActions {
  setCharacter: (c: CharacterType) => void;
  transition: (to: PerformanceState) => void;
  swapTo: (c: CharacterType, onReady?: () => void) => void;
  interrupt: () => void;
}

export type CharacterEngine = CharacterEngineState & CharacterEngineActions;

export interface CharacterComponentProps {
  performance: PerformanceState;
  prefersReducedMotion?: boolean;
  clipboardMark?: "none" | "check" | "cross" | "in-progress";
  onExitComplete?: () => void;
}
