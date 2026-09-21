import { SessionSummary, PracticeQueueItem } from "@/types/history";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockHistory: SessionSummary[] = [
  {
    sessionId: "sess_bs_01",
    topicName: "Binary Search",
    topicId: "bs_1",
    status: "COMPLETED",
    understandingScore: 78,
    masteryLevel: "Proficient",
    turnCount: 14,
    durationMinutes: 42,
    unresolvedGaps: 2,
    resolvedMisconceptions: 1,
    createdAt: "2024-01-15T14:30:00Z",
    completedAt: "2024-01-15T15:12:00Z",
  },
  {
    sessionId: "sess_sort_02",
    topicName: "QuickSort & Partitioning",
    topicId: "qs_1",
    status: "COMPLETED",
    understandingScore: 92,
    masteryLevel: "Mastery",
    turnCount: 18,
    durationMinutes: 55,
    unresolvedGaps: 0,
    resolvedMisconceptions: 2,
    createdAt: "2024-01-12T10:15:00Z",
    completedAt: "2024-01-12T11:10:00Z",
  },
  {
    sessionId: "sess_tree_03",
    topicName: "Binary Search Trees",
    topicId: "bst_1",
    status: "IN_PROGRESS",
    understandingScore: 64,
    masteryLevel: "Developing",
    turnCount: 7,
    durationMinutes: 20,
    unresolvedGaps: 3,
    resolvedMisconceptions: 0,
    createdAt: "2024-01-16T09:00:00Z",
  },
  {
    sessionId: "sess_graph_04",
    topicName: "Dijkstra's Algorithm",
    topicId: "dijk_1",
    status: "COMPLETED",
    understandingScore: 84,
    masteryLevel: "Proficient",
    turnCount: 16,
    durationMinutes: 48,
    unresolvedGaps: 1,
    resolvedMisconceptions: 1,
    createdAt: "2024-01-08T16:20:00Z",
    completedAt: "2024-01-08T17:08:00Z",
  },
];

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

export async function getSessionHistory(): Promise<SessionSummary[]> {
  try {
    const { getSessionRepository } = await import("./sessionRepository");
    const repo = getSessionRepository();
    const repoSessions = await repo.listSessions();

    if (repoSessions && repoSessions.length > 0) {
      // Map stored sessions to SessionSummary
      const dynamicList: SessionSummary[] = repoSessions.map((s) => ({
        sessionId: s.sessionId,
        topicName: s.topicName,
        topicId: s.topicId || s.sessionId,
        status: s.status === "COMPLETED" ? "COMPLETED" : "IN_PROGRESS",
        understandingScore: s.understandingScore ?? Math.round((s.confidence || 0.25) * 100),
        masteryLevel: s.masteryLevel || (s.confidence && s.confidence >= 80 ? "Mastery" : s.confidence && s.confidence >= 60 ? "Proficient" : "Developing"),
        turnCount: s.turnCount || 1,
        durationMinutes: s.durationMinutes || 5,
        unresolvedGaps: s.unresolvedGaps || 0,
        resolvedMisconceptions: s.resolvedMisconceptions || 0,
        createdAt: s.createdAt,
        completedAt: s.completedAt,
      }));

      // Combine with mock history if there are few sessions, avoiding duplicates
      const seen = new Set(dynamicList.map((s) => s.sessionId));
      const merged = [...dynamicList];
      for (const m of mockHistory) {
        if (!seen.has(m.sessionId)) {
          merged.push(m);
        }
      }
      return merged;
    }
  } catch (err) {
    console.warn("Failed to retrieve sessions from repository, using fallback:", err);
  }

  return mockHistory;
}

export async function getPracticeQueue(): Promise<PracticeQueueItem[]> {
  await delay(250);
  return [...mockPracticeQueue];
}

export async function saveToPracticeQueue(item: Omit<PracticeQueueItem, "id" | "savedAt">): Promise<void> {
  await delay(300);
  const newItem: PracticeQueueItem = {
    ...item,
    id: "pq_" + Date.now(),
    savedAt: new Date().toISOString(),
  };
  mockPracticeQueue = [newItem, ...mockPracticeQueue];
}
