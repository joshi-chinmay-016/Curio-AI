import { SessionSummary, PracticeQueueItem } from "@/types/history";
import { SessionListResponse } from "@/types/progress";
import { apiClient } from "./apiClient";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const QUEUE_STORAGE_KEY = "curio_practice_queue";

function getStoredPracticeQueue(): PracticeQueueItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(QUEUE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function setStoredPracticeQueue(items: PracticeQueueItem[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(items));
  } catch {}
}

export const DEFAULT_CONFIDENCE = 0.6;

export function formatConfidenceScore(
  confidence?: number | null,
  defaultConfidence: number = DEFAULT_CONFIDENCE
): number {
  const effective = confidence ?? defaultConfidence;
  if (effective > 1) {
    return Math.round(effective);
  }
  return Math.round(effective * 100);
}

export async function getSessionHistory(page: number = 1, pageSize: number = 20): Promise<SessionSummary[]> {
  const token = typeof window !== "undefined" ? localStorage.getItem("curio_access_token") : null;

  if (token) {
    try {
      const res = await apiClient<SessionListResponse>("/sessions", {
        params: { page, page_size: pageSize },
      });

      if (res && Array.isArray(res.items)) {
        return res.items.map((item) => {
          const confidencePct = formatConfidenceScore(item.confidence);
          const rawItem = item as unknown as { turn_count?: number; turnCount?: number };
          const turnCount = rawItem.turn_count ?? rawItem.turnCount ?? 0;

          let durationMinutes = 0;
          if (item.created_at && item.last_active_at) {
            const start = new Date(item.created_at).getTime();
            const end = new Date(item.last_active_at).getTime();
            if (!isNaN(start) && !isNaN(end) && end >= start) {
              durationMinutes = Math.round((end - start) / 60000);
            }
          }

          return {
            sessionId: item.session_id,
            topicName: item.topic,
            topicId: item.session_id,
            status: item.status === "COMPLETED" ? "COMPLETED" : "IN_PROGRESS",
            understandingScore: confidencePct,
            masteryLevel:
              confidencePct >= 80 ? "Mastery" : confidencePct >= 60 ? "Proficient" : "Developing",
            turnCount,
            durationMinutes,
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
      return repoSessions.map((s) => {
        const confidencePct = formatConfidenceScore(s.understandingScore ?? s.confidence, 0.25);
        return {
          sessionId: s.sessionId,
          topicName: s.topicName,
          topicId: s.topicId || s.sessionId,
          status: s.status === "COMPLETED" ? "COMPLETED" : "IN_PROGRESS",
          understandingScore: confidencePct,
          masteryLevel:
            s.masteryLevel ||
            (confidencePct >= 80
              ? "Mastery"
              : confidencePct >= 60
              ? "Proficient"
              : "Developing"),
          turnCount: s.turnCount ?? 0,
          durationMinutes: s.durationMinutes ?? 0,
          unresolvedGaps: s.unresolvedGaps || 0,
          resolvedMisconceptions: s.resolvedMisconceptions || 0,
          createdAt: s.createdAt,
          completedAt: s.completedAt,
        };
      });
    }
  } catch (err) {
    console.warn("[historyService] Local repository fallback error:", err);
  }

  return [];
}

export async function getPracticeQueue(): Promise<PracticeQueueItem[]> {
  await delay(50);
  return getStoredPracticeQueue();
}

export async function saveToPracticeQueue(item: Omit<PracticeQueueItem, "id" | "savedAt">): Promise<void> {
  await delay(50);
  const current = getStoredPracticeQueue();
  const newItem: PracticeQueueItem = {
    ...item,
    id: "pq_" + Date.now(),
    savedAt: new Date().toISOString(),
  };
  setStoredPracticeQueue([newItem, ...current]);
}
