import { SessionState, ChatMessage, SessionMode } from "@/types/session";
import { getSessionRepository } from "./sessionRepository";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Session topic registry (in-memory + sessionStorage sync for resilience across refreshes)
const sessionTopicRegistry = new Map<string, string>();

export function registerSessionTopic(sessionId: string, topicName: string) {
  if (!sessionId || !topicName) return;
  sessionTopicRegistry.set(sessionId, topicName);
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.setItem(`curio_topic_${sessionId}`, topicName);
    } catch {
      // Storage quota or SSR safe
    }
  }
}

export function getRegisteredSessionTopic(sessionId: string): string | null {
  if (!sessionId) return null;
  if (sessionTopicRegistry.has(sessionId)) {
    return sessionTopicRegistry.get(sessionId)!;
  }
  if (typeof window !== "undefined") {
    try {
      const saved = window.sessionStorage.getItem(`curio_topic_${sessionId}`);
      if (saved) {
        sessionTopicRegistry.set(sessionId, saved);
        return saved;
      }
    } catch {
      // Storage quota or SSR safe
    }
  }
  return null;
}

export function generateInitialQuestion(topicName: string): ChatMessage {
  const cleanTopic = topicName.trim();
  return {
    id: "m_1",
    role: "curio",
    type: "question",
    content: `Hi! I'm Curio. You're going to teach me about **${cleanTopic}** today!\n\nTo start off, can you explain in simple words: **what is ${cleanTopic}**, and what core problem or mechanism does it address?`,
    timestamp: new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    turnNumber: 1,
    mode: "STUDENT",
  };
}

export async function startSession(topicName: string): Promise<{ sessionId: string; topicName: string }> {
  const cleanTopic = topicName.trim() || "General Concept";
  const repo = getSessionRepository();

  try {
    const session = await repo.createSession(cleanTopic);
    registerSessionTopic(session.sessionId, cleanTopic);
    return { sessionId: session.sessionId, topicName: cleanTopic };
  } catch (err) {
    console.warn("Failed to create session via repository, using fallback:", err);
    const fallbackId = "sess_" + Date.now();
    registerSessionTopic(fallbackId, cleanTopic);
    return { sessionId: fallbackId, topicName: cleanTopic };
  }
}

export async function getSession(sessionId: string, topicHint?: string): Promise<SessionState> {
  const repo = getSessionRepository();
  let session = await repo.getSession(sessionId);

  let topicName = topicHint || (session ? session.topic : getRegisteredSessionTopic(sessionId)) || "";

  if (!session) {
    if (!topicName) topicName = "General Concept";
    session = await repo.createSession(topicName);
  }

  registerSessionTopic(session.sessionId, session.topic);

  // Map stored messages to ChatMessage
  const chatMessages: ChatMessage[] = (session.messages || []).map((m) => ({
    id: m.id,
    role: m.sender === "USER" ? "learner" : m.sender === "SYSTEM" ? "system" : "curio",
    type: m.type || (m.sender === "USER" ? "answer" : "question"),
    content: m.content,
    timestamp: new Date(m.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    turnNumber: m.turnNumber || 1,
    mode: m.mode || "STUDENT",
    isRestored: m.isRestored,
    gapReference: m.gapReference,
  }));

  // If no messages, add initial question
  if (chatMessages.length === 0) {
    chatMessages.push(generateInitialQuestion(session.topic));
  }

  const learnerCount = chatMessages.filter((m) => m.role === "learner").length;

  return {
    sessionId: session.sessionId,
    topicName: session.topic,
    topicId: session.sessionId,
    mode: session.currentMode || "STUDENT",
    messages: chatMessages,
    currentTurnNumber: learnerCount + 1,
    confidence: Math.round(session.confidence || 25),
    isConnected: true,
    isThinking: false,
    interruptedQuestion: session.interruptedQuestion
      ? {
          id: session.interruptedQuestion.id,
          role: "curio",
          type: "question",
          content: session.interruptedQuestion.content,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          turnNumber: 1,
          mode: "STUDENT",
        }
      : undefined,
    activeGap: session.teacherIntervention?.active
      ? {
          conceptId: session.teacherIntervention.gap,
          title: session.teacherIntervention.gap,
          severity: "HIGH",
        }
      : undefined,
  };
}

export async function endSession(sessionId: string): Promise<void> {
  const repo = getSessionRepository();
  try {
    await repo.endSession(sessionId);
  } catch (err) {
    console.warn("Error ending session:", err);
  }
}
