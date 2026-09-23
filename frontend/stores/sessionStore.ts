import { create } from "zustand";
import { ChatMessage, SessionMode, SessionState } from "@/types/session";
import { getSession, registerSessionTopic } from "@/services/sessionService";

interface SessionStoreState extends SessionState {
  setSessionId: (id: string) => void;
  setTopic: (name: string, id?: string) => void;
  setMode: (mode: SessionMode) => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setThinking: (thinking: boolean) => void;
  setConfidence: (confidence: number) => void;
  setTurnNumber: (turn: number) => void;
  setActiveGap: (gap?: SessionState["activeGap"]) => void;
  setInterruptedQuestion: (question?: ChatMessage) => void;
  initSession: (sessionId: string, topicHint?: string) => Promise<void>;
  reset: () => void;
}

const initialState: SessionState = {
  sessionId: "",
  topicName: "",
  topicId: "",
  mode: "STUDENT",
  messages: [],
  currentTurnNumber: 1,
  confidence: 65,
  isConnected: true,
  isThinking: false,
};

export const useSessionStore = create<SessionStoreState>((set, get) => ({
  ...initialState,

  setSessionId: (sessionId) => set({ sessionId }),
  setTopic: (topicName, id) => {
    const currentId = id || get().sessionId;
    if (currentId) {
      registerSessionTopic(currentId, topicName);
    }
    set({ topicName, topicId: currentId || topicName });
  },
  setMode: (mode) => set({ mode }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setMessages: (messages) => set({ messages }),
  setThinking: (isThinking) => set({ isThinking }),
  setConfidence: (confidence) => set({ confidence }),
  setTurnNumber: (currentTurnNumber) => set({ currentTurnNumber }),
  setActiveGap: (activeGap) => set({ activeGap }),
  setInterruptedQuestion: (interruptedQuestion) => set({ interruptedQuestion }),

  initSession: async (sessionId: string, topicHint?: string) => {
    const currentTopic = get().topicName;
    const resolvedHint = topicHint || currentTopic || undefined;
    const data = await getSession(sessionId, resolvedHint);
    set({
      sessionId: data.sessionId,
      topicName: data.topicName,
      topicId: data.topicId,
      mode: data.mode,
      messages: data.messages,
      currentTurnNumber: data.currentTurnNumber,
      confidence: data.confidence,
      interruptedQuestion: data.interruptedQuestion,
      activeGap: data.activeGap,
      isConnected: true,
      isThinking: false,
    });
  },

  reset: () => set({ ...initialState }),
}));
