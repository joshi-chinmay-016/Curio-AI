import { ChatMessage, SourceCitation } from "@/types/session";

export type AudioLearningMode = "STUDENT" | "PROFESSOR";

export type CharacterType = "student" | "teacher" | "professor";

export type CharacterAnimationState =
  | "idle"
  | "listening"
  | "recording"
  | "transcribing"
  | "thinking"
  | "taking_notes"
  | "marking"
  | "speaking"
  | "explaining"
  | "asking"
  | "curious"
  | "confused"
  | "impressed"
  | "skeptical"
  | "disappointed"
  | "teacher_transition"
  | "moving_on"
  | "grumpy"
  | "leaving"
  | "session_complete"
  | "error";

export type DifficultyOrdering = "EASY_TO_HARD" | "HARD_TO_EASY" | "MIXED";

export interface AudioSessionConfig {
  mode: AudioLearningMode;
  topic: string;
  sourceType: "GENERAL" | "DOCUMENT";
  documentId?: string;
  documentName?: string;
  difficultyOrder?: DifficultyOrdering;
  maxConsecutiveUnanswered?: number; // default: 3
}

export interface AudioTurnState {
  currentQuestion?: string;
  currentQuestionId?: string;
  currentObjective?: string;
  activeConcept?: string;
  transcript: string;
  isRecording: boolean;
  isTranscribing: boolean;
  isPlayingSpeech: boolean;
  speakingText?: string;
  consecutiveUnanswered: number;
  totalQuestionsAsked: number;
  totalAnswered: number;
  totalSkipped: number;
  hasEndedByProfessor: boolean;
  latestCitations?: SourceCitation[];
}
