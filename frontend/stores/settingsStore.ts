import { create } from "zustand";
import {
  AppTheme,
  CurioSettingsState,
  UserProfileSettings,
  LearningSettings,
  AudioVoiceSettings,
  PrivacyAndDataSettings,
} from "@/types/settings";

const SETTINGS_STORAGE_KEY = "curio_user_settings_v1";

const DEFAULT_SETTINGS: CurioSettingsState = {
  theme: "light",
  profile: {
    displayName: "Chinmay Joshi",
    email: "learner@curio.ai",
    role: "AI & Systems Researcher",
    bio: "Passionate about testing mental models from first principles using the Feynman technique.",
    learningGoal: "Master Quantum Mechanics, Topology & Distributed Consensus",
    characterAvatar: "PROFESSOR",
    avatarColor: "#3A63FF",
    feynmanLevel: 4,
    levelTitle: "Senior Explainer",
  },
  learning: {
    rigorLevel: "socratic",
    probingDepth: 4,
    defaultCharacter: "STUDENT",
    evaluationStrictness: "standard",
    showReasoningSteps: true,
    autoGenerateReport: true,
    allowAnalogyTesting: true,
  },
  audio: {
    voicePersona: "Curio Feynman (Enthusiastic & Deep)",
    speechRate: 1.0,
    pitch: 1.0,
    autoPlayAudio: true,
    soundEffects: true,
    micSensitivity: 80,
    noiseCancellation: true,
  },
  privacy: {
    analyticsEnabled: true,
    autoSaveCloud: true,
    customGeminiApiKey: "",
    customElevenLabsApiKey: "",
  },
  stats: {
    conceptsMastered: 48,
    gapsResolved: 17,
    totalSessions: 23,
    voiceMinutes: 64,
    feynmanStreakDays: 6,
  },
};

interface SettingsStoreActions {
  setTheme: (theme: AppTheme) => void;
  updateProfile: (profile: Partial<UserProfileSettings>) => void;
  updateLearning: (learning: Partial<LearningSettings>) => void;
  updateAudio: (audio: Partial<AudioVoiceSettings>) => void;
  updatePrivacy: (privacy: Partial<PrivacyAndDataSettings>) => void;
  incrementGapsResolved: () => void;
  incrementSessionCount: () => void;
  resetToDefaults: () => void;
  exportDataAsJson: () => string;
  initSettings: () => void;
}

export type SettingsStore = CurioSettingsState & SettingsStoreActions;

function applyThemeToDOM(theme: AppTheme) {
  if (typeof window === "undefined") return;

  const root = document.documentElement;
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  if (isDark) {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  ...DEFAULT_SETTINGS,

  initSettings: () => {
    if (typeof window === "undefined") return;

    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        set((state) => ({
          ...state,
          ...parsed,
          profile: { ...state.profile, ...parsed.profile },
          learning: { ...state.learning, ...parsed.learning },
          audio: { ...state.audio, ...parsed.audio },
          privacy: { ...state.privacy, ...parsed.privacy },
          stats: { ...state.stats, ...parsed.stats },
        }));
        applyThemeToDOM(parsed.theme || "light");
      } else {
        applyThemeToDOM(get().theme);
      }
    } catch (e) {
      console.warn("Failed to load settings from storage:", e);
      applyThemeToDOM("light");
    }

    // Listen for system theme changes if theme is set to 'system'
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleThemeChange = () => {
        if (get().theme === "system") {
          applyThemeToDOM("system");
        }
      };
      try {
        mediaQuery.addEventListener("change", handleThemeChange);
      } catch {
        mediaQuery.addListener(handleThemeChange);
      }
    }
  },

  setTheme: (theme: AppTheme) => {
    set({ theme });
    applyThemeToDOM(theme);
    if (typeof window !== "undefined") {
      try {
        const current = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}");
        localStorage.setItem(
          SETTINGS_STORAGE_KEY,
          JSON.stringify({ ...current, theme })
        );
      } catch (e) {
        console.error("Failed to persist theme", e);
      }
    }
  },

  updateProfile: (profileUpdate) => {
    set((state) => {
      const nextProfile = { ...state.profile, ...profileUpdate };
      if (typeof window !== "undefined") {
        try {
          const current = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}");
          localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify({ ...current, profile: nextProfile })
          );
        } catch (e) {
          console.error("Failed to persist profile", e);
        }
      }
      return { profile: nextProfile };
    });
  },

  updateLearning: (learningUpdate) => {
    set((state) => {
      const nextLearning = { ...state.learning, ...learningUpdate };
      if (typeof window !== "undefined") {
        try {
          const current = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}");
          localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify({ ...current, learning: nextLearning })
          );
        } catch (e) {
          console.error("Failed to persist learning settings", e);
        }
      }
      return { learning: nextLearning };
    });
  },

  updateAudio: (audioUpdate) => {
    set((state) => {
      const nextAudio = { ...state.audio, ...audioUpdate };
      if (typeof window !== "undefined") {
        try {
          const current = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}");
          localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify({ ...current, audio: nextAudio })
          );
        } catch (e) {
          console.error("Failed to persist audio settings", e);
        }
      }
      return { audio: nextAudio };
    });
  },

  updatePrivacy: (privacyUpdate) => {
    set((state) => {
      const nextPrivacy = { ...state.privacy, ...privacyUpdate };
      if (typeof window !== "undefined") {
        try {
          const current = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}");
          localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify({ ...current, privacy: nextPrivacy })
          );
        } catch (e) {
          console.error("Failed to persist privacy settings", e);
        }
      }
      return { privacy: nextPrivacy };
    });
  },

  incrementGapsResolved: () => {
    set((state) => ({
      stats: { ...state.stats, gapsResolved: state.stats.gapsResolved + 1 },
    }));
  },

  incrementSessionCount: () => {
    set((state) => ({
      stats: { ...state.stats, totalSessions: state.stats.totalSessions + 1 },
    }));
  },

  resetToDefaults: () => {
    set(DEFAULT_SETTINGS);
    applyThemeToDOM(DEFAULT_SETTINGS.theme);
    if (typeof window !== "undefined") {
      localStorage.removeItem(SETTINGS_STORAGE_KEY);
    }
  },

  exportDataAsJson: () => {
    const data = {
      curioVersion: "2.5.0",
      exportDate: new Date().toISOString(),
      settings: {
        profile: get().profile,
        learning: get().learning,
        audio: get().audio,
        stats: get().stats,
      },
    };
    return JSON.stringify(data, null, 2);
  },
}));
