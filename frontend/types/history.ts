export interface SessionSummary {
  sessionId: string;
  topicName: string;
  topicId: string;
  status: "IN_PROGRESS" | "COMPLETED" | "ABANDONED";
  understandingScore: number;
  masteryLevel: string;
  turnCount: number;
  durationMinutes: number;
  unresolvedGaps: number;
  resolvedMisconceptions: number;
  createdAt: string;
  completedAt?: string;
}

export interface PracticeQueueItem {
  id: string;
  gapId: string;
  conceptName: string;
  topicName: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  savedAt: string;
}
