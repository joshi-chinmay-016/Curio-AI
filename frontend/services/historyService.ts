import { SessionSummary, PracticeQueueItem } from "@/types/history";
import { SessionListResponse } from "@/types/progress";
import { apiClient } from "./apiClient";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let mockPracticeQueue: PracticeQueueItem[] = [
  {
    id: "pq_1",
    gapId: "gap_bc_1",
    conceptName: "Boundary Conditions (low <= high vs low < high)",
    topicName: "Binary Search",
    severity: "HIGH",
    savedAt: "2024-01-15T15:14:00Z",
  },
  {
    id: "pq_2",
    gapId: "gap_mid_2",
    conceptName: "Integer Overflow in Midpoint Calculation",
    topicName: "Binary Search",
    severity: "MEDIUM",
    savedAt: "2024-01-15T15:15:00Z",
  },
  {
    id: "pq_3",
    gapId: "gap_dijk_3",
    conceptName: "Negative Edge Weights in Dijkstra",
    topicName: "Dijkstra's Algorithm",
    severity: "HIGH",
    savedAt: "2024-01-08T17:10:00Z",
  },
];

export async function getSessionHistory(page: number = 1, pageSize: number = 20): Promise<SessionSummary[]> {
  const token = typeof window !== "undefined" ? localStorage.getItem("curio_access_token") : null;

  if (token) {
    try {
      const res = await apiClient<SessionListResponse>("/sessions", {
        params: { page, page_size: pageSize },
      });

      if (res && Array.isArray(res.items)) {
        return res.items.map((item) => {
          const confidencePct = Math.round(item.confidence || 60);
          return {
            sessionId: item.session_id,
            topicName: item.topic,
            topicId: item.session_id,
            status: item.status === "COMPLETED" ? "COMPLETED" : "IN_PROGRESS",
            understandingScore: confidencePct,
            masteryLevel:
              confidencePct >= 80 ? "Mastery" : confidencePct >= 60 ? "Proficient" : "Developing",
            turnCount: item.difficulty * 3 || 3,
            durationMinutes: Math.max(5, Math.round(item.difficulty * 7)),
            unresolvedGaps: 0,
            resolvedMisconceptions: 0,
            createdAt: item.created_at,
            completedAt: item.status === "COMPLETED" ? item.last_active_at : undefined,
          };
        });
      }
    } catch (err) {
      console.warn("[historyService] Failed to load sessions from API, trying local repository:", err);
    }
  }

  // Fallback to local session repository for offline learners
  try {
    const { getSessionRepository } = await import("./sessionRepository");
    const repo = getSessionRepository();
    const repoSessions = await repo.listSessions();

    if (repoSessions && repoSessions.length > 0) {
      return repoSessions.map((s) => ({
        sessionId: s.sessionId,
        topicName: s.topicName,
        topicId: s.topicId || s.sessionId,
        status: s.status === "COMPLETED" ? "COMPLETED" : "IN_PROGRESS",
        understandingScore: s.understandingScore ?? Math.round((s.confidence || 0.25) * 100),
        masteryLevel:
          s.masteryLevel ||
          (s.confidence && s.confidence >= 80
            ? "Mastery"
            : s.confidence && s.confidence >= 60
            ? "Proficient"
            : "Developing"),
        turnCount: s.turnCount || 1,
        durationMinutes: s.durationMinutes || 5,
        unresolvedGaps: s.unresolvedGaps || 0,
        resolvedMisconceptions: s.resolvedMisconceptions || 0,
        createdAt: s.createdAt,
        completedAt: s.completedAt,
      }));
    }
  } catch (err) {
    console.warn("[historyService] Local repository fallback error:", err);
  }

  return [];
}

export async function getPracticeQueue(): Promise<PracticeQueueItem[]> {
  await delay(150);
  return [...mockPracticeQueue];
}

export async function saveToPracticeQueue(item: Omit<PracticeQueueItem, "id" | "savedAt">): Promise<void> {
  await delay(200);
  const newItem: PracticeQueueItem = {
    ...item,
    id: "pq_" + Date.now(),
    savedAt: new Date().toISOString(),
  };
  mockPracticeQueue = [newItem, ...mockPracticeQueue];
}
