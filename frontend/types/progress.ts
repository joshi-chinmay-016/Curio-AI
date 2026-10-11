export interface ConceptProgress {
  concept: string;
  mastery_score: number;
  total_attempts: number;
  successful_attempts: number;
  last_practiced_at?: string | null;
  last_difficulty: number;
  misconception_count: number;
}

export interface LearningProgressSummary {
  total_concepts_tracked: number;
  concepts_with_progress: number;
  total_attempts: number;
  total_successful_attempts: number;
  total_misconceptions: number;
  most_recently_practiced_concept?: string | null;
  last_practiced_at?: string | null;
}

export interface LearningProgressData {
  user_id: string;
  concepts: ConceptProgress[];
  summary: LearningProgressSummary;
}

export interface SessionSummaryItem {
  session_id: string;
  topic: string;
  status: "ACTIVE" | "PAUSED" | "COMPLETED";
  current_mode: "STUDENT" | "TEACHER" | "EVALUATING";
  difficulty: number;
  confidence: number;
  created_at: string;
  last_active_at: string;
}

export interface SessionListResponse {
  items: SessionSummaryItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
