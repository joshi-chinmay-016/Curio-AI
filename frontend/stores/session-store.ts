import { create } from 'zustand';
import { SessionSummary, Session, Message, SessionReport } from '../types';
import { api } from '../lib/api/client';

interface SessionState {
  sessions: SessionSummary[];
  activeSession: Session | null;
  messages: Message[];
  activeReport: SessionReport | null;
  isLoading: boolean;
  error: string | null;

  fetchSessions: () => Promise<void>;
  selectSession: (id: string) => Promise<void>;
  createSession: (topic: string) => Promise<string>;
  sendMessage: (content: string) => Promise<void>;
  endActiveSession: () => Promise<void>;
  clearActiveSession: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  activeSession: null,
  messages: [],
  activeReport: null,
  isLoading: false,
  error: null,

  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const summaries = await api.listSessions();
      set({ sessions: summaries, isLoading: false });
    } catch (e: any) {
      set({ error: e.message || 'Failed to load sessions', isLoading: false });
    }
  },

  selectSession: async (id: string) => {
    set({ isLoading: true, error: null, activeReport: null });
    try {
      const session = await api.getSession(id);
      const messages = await api.getMessages(id);
      
      let report: SessionReport | null = null;
      if (session.status === 'COMPLETED') {
        try {
          // If already ended, get the report
          const savedReport = localStorage.getItem(`curio_report_${id}`);
          if (savedReport) {
            report = JSON.parse(savedReport);
          } else {
            report = await api.endSession(id); // fallback compilation trigger
          }
        } catch (repErr) {
          // ignore report error if not generated yet
        }
      }

      set({
        activeSession: session,
        messages,
        activeReport: report,
        isLoading: false
      });
    } catch (e: any) {
      set({ error: e.message || 'Failed to select session', isLoading: false });
    }
  },

  createSession: async (topic: string) => {
    set({ isLoading: true, error: null });
    try {
      const newSession = await api.createSession({ topic, source_type: 'GENERAL' });
      await get().fetchSessions();
      await get().selectSession(newSession.id);
      set({ isLoading: false });
      return newSession.id;
    } catch (e: any) {
      set({ error: e.message || 'Failed to create session', isLoading: false });
      throw e;
    }
  },

  sendMessage: async (content: string) => {
    const { activeSession, messages } = get();
    if (!activeSession) return;

    set({ isLoading: true, error: null });
    try {
      const turnResponse = await api.sendMessage(activeSession.id, {
        content,
        input_type: 'TEXT'
      });

      // Update local state directly with returned turn evaluations & state parameters
      const updatedSession: Session = {
        ...activeSession,
        status: turnResponse.decision.next_mode === 'EVALUATOR' ? 'COMPLETED' : activeSession.status,
        state: {
          session_id: activeSession.id,
          current_mode: turnResponse.decision.next_mode,
          difficulty: turnResponse.decision.difficulty,
          confidence: turnResponse.decision.confidence,
          active_concept: turnResponse.decision.active_concept,
          current_question_id: turnResponse.ai_message.message_id,
          interrupted_question_id: turnResponse.decision.should_restore_interrupted_question ? null : activeSession.state?.interrupted_question_id || null,
          consecutive_strong_answers: activeSession.state?.consecutive_strong_answers || 0, // updated on server
          consecutive_weak_answers: activeSession.state?.consecutive_weak_answers || 0,
          unresolved_misconceptions: [
            ...(activeSession.state?.unresolved_misconceptions || []),
            ...turnResponse.evaluation.misconceptions
          ],
          mastered_concepts: [
            ...(activeSession.state?.mastered_concepts || []),
            ...turnResponse.evaluation.mastered_concepts
          ]
        }
      };

      set({
        activeSession: updatedSession,
        messages: [...messages, turnResponse.user_message, turnResponse.ai_message],
        isLoading: false
      });

      // Refresh sidebar list
      await get().fetchSessions();
    } catch (e: any) {
      set({ error: e.message || 'Failed to send message', isLoading: false });
    }
  },

  endActiveSession: async () => {
    const { activeSession } = get();
    if (!activeSession) return;

    set({ isLoading: true, error: null });
    try {
      const report = await api.endSession(activeSession.id);
      set({
        activeReport: report,
        activeSession: { ...activeSession, status: 'COMPLETED' },
        isLoading: false
      });
      await get().fetchSessions();
    } catch (e: any) {
      set({ error: e.message || 'Failed to end session', isLoading: false });
    }
  },

  clearActiveSession: () => {
    set({ activeSession: null, messages: [], activeReport: null });
  }
}));
