export type LearningMode = 'STUDENT' | 'TEACHER' | 'EVALUATOR';

export type InputType = 'TEXT' | 'VOICE';

export type SessionStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED';

export type SourceType = 'GENERAL' | 'DOCUMENT';

export type MasteryLevel = 'BEGINNER' | 'DEVELOPING' | 'PROFICIENT' | 'MASTERY';

export type LearningStrategy =
  | 'ASK_FOUNDATION'
  | 'PROBE_WHY'
  | 'PROBE_HOW'
  | 'CLARIFY_TERM'
  | 'PROBE_MISSING_CONCEPT'
  | 'CHALLENGE_MISCONCEPTION'
  | 'INCREASE_DIFFICULTY'
  | 'TEACH_GAP'
  | 'VERIFY_UNDERSTANDING'
  | 'RESTORE_INTERRUPTED_QUESTION'
  | 'OFFER_TERMINATION'
  | 'GENERATE_REPORT';

export interface SessionState {
  session_id: string;
  current_mode: LearningMode;
  difficulty: number;
  confidence: number;
  active_concept: string;
  current_question_id: string | null;
  interrupted_question_id: string | null;
  consecutive_strong_answers: number;
  consecutive_weak_answers: number;
  unresolved_misconceptions: string[];
  mastered_concepts: string[];
}

export interface Session {
  id: string;
  user_id: string;
  topic: string;
  source_type: SourceType;
  document_id: string | null;
  status: SessionStatus;
  created_at: string;
  last_active_at: string;
  ended_at: string | null;
  state?: SessionState;
}

export interface SessionSummary {
  session_id: string;
  topic: string;
  status: SessionStatus;
  current_mode: LearningMode;
  difficulty: number;
  confidence: number;
  created_at: string;
  last_active_at: string;
}

export interface Message {
  message_id: string;
  session_id: string;
  sender: 'USER' | 'AI';
  content: string;
  input_type: InputType;
  created_at: string;
}

export interface TurnEvaluation {
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
  recommended_strategy: LearningStrategy;
  recommended_difficulty: number;
}

export interface LearningDecision {
  next_mode: LearningMode;
  strategy: LearningStrategy;
  difficulty: number;
  confidence: number;
  reason: string;
  active_concept: string;
  should_offer_termination: boolean;
  should_restore_interrupted_question: boolean;
}

export interface ChatTurnResponse {
  user_message: Message;
  ai_message: Message;
  evaluation: TurnEvaluation;
  decision: LearningDecision;
}

export interface SessionReport {
  session_id: string;
  understanding_score: number;
  mastery_level: MasteryLevel;
  strengths: string[];
  high_priority_learning_gaps: string[];
  medium_priority_learning_gaps: string[];
  low_priority_learning_gaps: string[];
  misconceptions_detected: string[];
  concepts_mastered: string[];
  teacher_interventions_required: number;
  difficulty_achieved: number;
  personalized_roadmap: string[];
  recommended_exercises: string[];
  created_at: string;
}

export interface CreateSessionRequest {
  topic: string;
  source_type: SourceType;
  document_id?: string | null;
}

export interface SendMessageRequest {
  content: string;
  input_type: InputType;
}
