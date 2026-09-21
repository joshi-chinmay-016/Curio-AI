import {
  SessionRepository,
  StoredSession,
  StoredMessage,
  SessionRepositorySummary,
  ChatTurnResponse,
} from "./types";
import { SessionMode } from "@/types/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiSessionRepository implements SessionRepository {
  async createSession(topic: string, sourceType: string = "GENERAL"): Promise<StoredSession> {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: topic.trim(),
        source_type: sourceType,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to create session on backend: ${res.statusText}`);
    }

    const data = await res.json();
    return this.mapBackendSessionToStored(data);
  }

  async getSession(sessionId: string): Promise<StoredSession | null> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (res.status === 404) return null;
    if (!res.ok) {
      throw new Error(`Failed to fetch session ${sessionId}: ${res.statusText}`);
    }

    const data = await res.json();
    const stored = this.mapBackendSessionToStored(data);

    // Fetch messages
    try {
      const msgRes = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      });
      if (msgRes.ok) {
        const msgs = await msgRes.json();
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
    } catch (err) {
      console.warn("Failed to fetch messages for session:", err);
    }

    return stored;
  }

  async listSessions(): Promise<SessionRepositorySummary[]> {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to list sessions: ${res.statusText}`);
    }

    const data = await res.json();
    return (data || []).map((s: any) => ({
      sessionId: s.session_id || s.id,
      topicName: s.topic,
      topicId: s.session_id || s.id,
      status: s.status,
      understandingScore: s.confidence ? Math.round(s.confidence * 100) : 0,
      createdAt: s.created_at,
      lastActiveAt: s.last_active_at || s.created_at,
      currentMode: (s.current_mode as SessionMode) || "STUDENT",
      difficulty: s.difficulty || 1,
      confidence: s.confidence || 0,
    }));
  }

  async updateSession(sessionId: string, updates: Partial<StoredSession>): Promise<StoredSession> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: updates.topic,
        status: updates.status,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to update session: ${res.statusText}`);
    }

    const data = await res.json();
    return this.mapBackendSessionToStored(data);
  }

  async deleteSession(sessionId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "DELETE",
    });

    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete session: ${res.statusText}`);
    }
  }

  async sendMessage(
    sessionId: string,
    content: string,
    inputType: string = "TEXT"
  ): Promise<ChatTurnResponse> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        input_type: inputType,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to send message: ${res.statusText}`);
    }

    return await res.json();
  }

  async endSession(sessionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/end`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      throw new Error(`Failed to end session: ${res.statusText}`);
    }

    return await res.json();
  }

  private mapBackendSessionToStored(data: any): StoredSession {
    const state = data.state || {};
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
      confidence: (state.confidence ?? data.confidence ?? 0.25) * 100,
      activeConcept: state.active_concept || data.topic,
      consecutiveSuccesses: state.consecutive_strong_answers || 0,
      consecutiveFailures: state.consecutive_weak_answers || 0,
      messages: [],
    };
  }
}
