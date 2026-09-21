export type SessionMode = "STUDENT" | "TEACHER" | "EVALUATING";

export type MessageRole = "curio" | "learner" | "system";

export type MessageType =
  | "question"
  | "answer"
  | "evaluation"
  | "gap_detected"
  | "teacher_content"
  | "verification"
  | "separator";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  type: MessageType;
  content: string;
  timestamp: string;
  turnNumber?: number;
  mode: SessionMode;
  gapReference?: string; // conceptId if gap-related
  isRestored?: boolean;
  isVerified?: boolean;
}

export interface SessionState {
  sessionId: string;
  topicName: string;
  topicId: string;
  mode: SessionMode;
  messages: ChatMessage[];
  currentTurnNumber: number;
  confidence: number;
  activeGap?: {
    conceptId: string;
    title: string;
    severity: "LOW" | "MEDIUM" | "HIGH";
  };
  interruptedQuestion?: ChatMessage;
  isConnected: boolean;
  isThinking: boolean;
}

export interface SessionWebSocketMessage {
  type:
    | "question"
    | "evaluation"
    | "mode_change"
    | "gap_detected"
    | "teacher_start"
    | "teacher_end"
    | "session_complete";
  content: string;
  mode: "STUDENT" | "TEACHER" | "EVALUATOR";
  gap?: {
    conceptId: string;
    title: string;
    severity: "LOW" | "MEDIUM" | "HIGH";
  };
  confidence?: number;
  turnNumber?: number;
}
