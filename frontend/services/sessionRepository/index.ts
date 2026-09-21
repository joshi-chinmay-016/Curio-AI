import { SessionRepository } from "./types";
import { LocalSessionRepository } from "./LocalSessionRepository";
import { ApiSessionRepository } from "./ApiSessionRepository";

export * from "./types";
export { LocalSessionRepository } from "./LocalSessionRepository";
export { ApiSessionRepository } from "./ApiSessionRepository";

class ResilientSessionRepository implements SessionRepository {
  private localRepo = new LocalSessionRepository();
  private apiRepo = new ApiSessionRepository();

  private shouldUseApi(): boolean {
    return process.env.NEXT_PUBLIC_USE_API === "true";
  }

  async createSession(topic: string, sourceType?: string) {
    if (this.shouldUseApi()) {
      try {
        const session = await this.apiRepo.createSession(topic, sourceType);
        // Sync locally as well for offline safety
        await this.localRepo.updateSession(session.sessionId, session).catch(() => {});
        return session;
      } catch (err) {
        console.warn("[SessionRepository] API createSession failed, falling back to local:", err);
      }
    }
    return this.localRepo.createSession(topic, sourceType);
  }

  async getSession(sessionId: string) {
    if (this.shouldUseApi()) {
      try {
        const session = await this.apiRepo.getSession(sessionId);
        if (session) return session;
      } catch (err) {
        console.warn("[SessionRepository] API getSession failed, falling back to local:", err);
      }
    }
    return this.localRepo.getSession(sessionId);
  }

  async listSessions() {
    if (this.shouldUseApi()) {
      try {
        const apiSessions = await this.apiRepo.listSessions();
        if (apiSessions && apiSessions.length > 0) return apiSessions;
      } catch (err) {
        console.warn("[SessionRepository] API listSessions failed, falling back to local:", err);
      }
    }
    return this.localRepo.listSessions();
  }

  async updateSession(sessionId: string, updates: any) {
    if (this.shouldUseApi()) {
      try {
        return await this.apiRepo.updateSession(sessionId, updates);
      } catch (err) {
        console.warn("[SessionRepository] API updateSession failed, falling back to local:", err);
      }
    }
    return this.localRepo.updateSession(sessionId, updates);
  }

  async deleteSession(sessionId: string) {
    if (this.shouldUseApi()) {
      try {
        await this.apiRepo.deleteSession(sessionId);
      } catch (err) {
        console.warn("[SessionRepository] API deleteSession failed, falling back to local:", err);
      }
    }
    return this.localRepo.deleteSession(sessionId);
  }

  async sendMessage(sessionId: string, content: string, inputType?: string) {
    if (this.shouldUseApi()) {
      try {
        const res = await this.apiRepo.sendMessage(sessionId, content, inputType);
        return res;
      } catch (err) {
        console.warn("[SessionRepository] API sendMessage failed, falling back to local:", err);
      }
    }
    return this.localRepo.sendMessage(sessionId, content, inputType);
  }

  async endSession(sessionId: string) {
    if (this.shouldUseApi()) {
      try {
        return await this.apiRepo.endSession(sessionId);
      } catch (err) {
        console.warn("[SessionRepository] API endSession failed, falling back to local:", err);
      }
    }
    return this.localRepo.endSession(sessionId);
  }
}

const defaultRepository: SessionRepository = new ResilientSessionRepository();

export function getSessionRepository(): SessionRepository {
  return defaultRepository;
}
