import { SessionMode } from "@/types/session";

export interface StoredQuestion {
  id: string;
  content: string;
  concept?: string;
  difficulty?: number;
}

export interface StoredTeacherIntervention {
  active: boolean;
  gap: string;
  attemptCount: number;
  verificationRequired: boolean;
  verificationQuestionAsked?: boolean;
}

export interface StoredMessage {
  id: string;
  sessionId: string;
  sender: "USER" | "AI" | "SYSTEM";
  content: string;
  inputType?: "TEXT" | "VOICE" | "DOCUMENT";
  createdAt: string;
  turnNumber?: number;
  mode?: SessionMode;
  type?: "question" | "answer" | "separator" | "teacher_content";
  gapReference?: string;
  isRestored?: boolean;
  evaluation?: TurnEvaluationData;
  decision?: LearningDecisionData;
}

export interface InjectedMistakeState {
  active: boolean;
  turn: number;
  misconception: string;
  concept: string;
  counterReason: string;
}

export interface StoredSession {
  sessionId: string;
  userId?: string;
  topic: string;
  title?: string;
  sourceType?: string;
  documentId?: string | null;
  status: "ACTIVE" | "PAUSED" | "COMPLETED";
  createdAt: string;
  lastActiveAt: string;
  endedAt?: string | null;
  currentMode: SessionMode;
  difficulty: number;
  confidence: number;
  activeConcept?: string;
  currentQuestion?: StoredQuestion;
  interruptedQuestion?: StoredQuestion;
  teacherIntervention?: StoredTeacherIntervention;
  injectedMistake?: InjectedMistakeState;
  lastMistakeInjectedTurn?: number;
  consecutiveSuccesses: number;
  consecutiveFailures: number;
  messages: StoredMessage[];
  topicPlan?: StoredTopicPlan;
}

export interface StoredTopicObjective {
  id: string;
  category: "definition" | "prerequisite" | "mechanism" | "complexity" | "edge_cases" | "application" | "trade_offs";
  title: string;
  difficultyLevel: number;
  status: "UNEXPLORED" | "IN_PROGRESS" | "MASTERED";
}

export interface StoredTopicPlan {
  topic: string;
  objectives: StoredTopicObjective[];
  currentObjectiveId: string;
}

export interface TurnEvaluationData {
  correctness: number;
  clarity: number;
  completeness: number;
  depth: number;
  relevance: number;
  stuck_probability: number;
  misconceptions: string[];
  missing_concepts: string[];
  undefined_terms: string[];
  mastered_concepts: string[];
  knowledge_gap: string | null;
  recommended_strategy: string;
  recommended_difficulty: number;
}

export interface LearningDecisionData {
  next_mode: SessionMode;
  strategy: string;
  difficulty: number;
  confidence: number;
  reason: string;
  active_concept: string;
  should_offer_termination: boolean;
  should_restore_interrupted_question: boolean;
}

export interface ChatTurnResponse {
  user_message: {
    message_id: string;
    session_id: string;
    sender: "USER";
    content: string;
    input_type: string;
    created_at: string;
  };
  ai_message: {
    message_id: string;
    session_id: string;
    sender: "AI";
    content: string;
    input_type: string;
    created_at: string;
  };
  evaluation: TurnEvaluationData;
  decision: LearningDecisionData;
}

export interface SessionRepositorySummary {
  sessionId: string;
  topicName: string;
  topicId?: string;
  status: "ACTIVE" | "PAUSED" | "COMPLETED" | "IN_PROGRESS";
  understandingScore?: number;
  masteryLevel?: string;
  turnCount?: number;
  durationMinutes?: number;
  unresolvedGaps?: number;
  resolvedMisconceptions?: number;
  createdAt: string;
  completedAt?: string;
  lastActiveAt?: string;
  currentMode?: SessionMode;
  difficulty?: number;
  confidence?: number;
}

export interface SessionRepository {
  createSession(topic: string, sourceType?: string, documentId?: string): Promise<StoredSession>;
  getSession(sessionId: string): Promise<StoredSession | null>;
  listSessions(): Promise<SessionRepositorySummary[]>;
  updateSession(sessionId: string, updates: Partial<StoredSession>): Promise<StoredSession>;
  deleteSession(sessionId: string): Promise<void>;
  sendMessage(sessionId: string, content: string, inputType?: string): Promise<ChatTurnResponse>;
  endSession(sessionId: string): Promise<any>;
}
