import {
  SessionRepository,
  StoredSession,
  StoredMessage,
  SessionRepositorySummary,
  ChatTurnResponse,
} from "./types";
import { SessionMode } from "@/types/session";
import { apiClient } from "@/services/apiClient";

export class ApiSessionRepository implements SessionRepository {
  async createSession(topic: string, sourceType: string = "GENERAL"): Promise<StoredSession> {
    const data = await apiClient<any>("/sessions", {
      method: "POST",
      body: JSON.stringify({
        topic: topic.trim(),
        source_type: sourceType,
      }),
    });

    return this.mapBackendSessionToStored(data);
  }

  async getSession(sessionId: string): Promise<StoredSession | null> {
    let data: any;
    try {
      data = await apiClient<any>(`/sessions/${sessionId}`);
    } catch (err: any) {
      if (err.status === 404 || (err.message && err.message.toLowerCase().includes("not found"))) {
        return null;
      }
      throw err;
    }

    const stored = this.mapBackendSessionToStored(data);

    // Fetch messages
    try {
      const msgs = await apiClient<any[]>(`/sessions/${sessionId}/messages`);
      if (Array.isArray(msgs)) {
        stored.messages = msgs.map((m: any) => ({
          id: m.message_id || m.id,
          sessionId: m.session_id || sessionId,
          sender: m.sender === "USER" ? "USER" : m.sender === "AI" ? "AI" : "SYSTEM",
          content: m.content,
          inputType: m.input_type,
          createdAt: m.created_at,
          mode: stored.currentMode,
          type: m.sender === "USER" ? "answer" : "question",
        }));
      }
    } catch (err: any) {
      if (err.status === 401 || err.status === 403) {
        throw err;
      }
      console.warn("Failed to fetch messages for session:", err);
    }

    return stored;
  }

  async listSessions(): Promise<SessionRepositorySummary[]> {
    const data = await apiClient<any>("/sessions");
    const items = Array.isArray(data) ? data : (data?.items || []);
    return items.map((s: any) => {
      const rawConf = typeof s.confidence === "number" ? s.confidence : 0;
      const score = rawConf <= 1 ? Math.round(rawConf * 100) : Math.round(rawConf);
      return {
        sessionId: s.session_id || s.id,
        topicName: s.topic,
        topicId: s.session_id || s.id,
        status: s.status,
        understandingScore: score,
        createdAt: s.created_at,
        lastActiveAt: s.last_active_at || s.created_at,
        currentMode: (s.current_mode as SessionMode) || "STUDENT",
        difficulty: s.difficulty || 1,
        confidence: s.confidence || 0,
      };
    });
  }

  async updateSession(sessionId: string, updates: Partial<StoredSession>): Promise<StoredSession> {
    const data = await apiClient<any>(`/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify({
        topic: updates.topic,
        status: updates.status,
      }),
    });

    return this.mapBackendSessionToStored(data);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await apiClient<void>(`/sessions/${sessionId}`, {
      method: "DELETE",
    });
  }

  async sendMessage(
    sessionId: string,
    content: string,
    inputType: string = "TEXT"
  ): Promise<ChatTurnResponse> {
    return apiClient<ChatTurnResponse>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        content,
        input_type: inputType,
      }),
    });
  }

  async endSession(sessionId: string): Promise<any> {
    return apiClient<any>(`/sessions/${sessionId}/end`, {
      method: "POST",
    });
  }

  private mapBackendSessionToStored(data: any): StoredSession {
    const state = data.state || {};
    const rawConf = state.confidence ?? data.confidence ?? 0.25;
    const confidenceScore = typeof rawConf === "number"
      ? (rawConf <= 1 ? Math.round(rawConf * 100) : Math.round(rawConf))
      : 25;

    return {
      sessionId: data.session_id || data.id,
      userId: data.user_id,
      topic: data.topic,
      title: data.topic,
      sourceType: data.source_type || "GENERAL",
      documentId: data.document_id,
      status: data.status || "ACTIVE",
      createdAt: data.created_at || new Date().toISOString(),
      lastActiveAt: data.last_active_at || data.created_at || new Date().toISOString(),
      endedAt: data.ended_at,
      currentMode: (state.current_mode as SessionMode) || (data.current_mode as SessionMode) || "STUDENT",
      difficulty: state.difficulty ?? data.difficulty ?? 1,
      confidence: confidenceScore,
      activeConcept: state.active_concept || data.topic,
      consecutiveSuccesses: state.consecutive_strong_answers || 0,
      consecutiveFailures: state.consecutive_weak_answers || 0,
      messages: [],
    };
  }
}
