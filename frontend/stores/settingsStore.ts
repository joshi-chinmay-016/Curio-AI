import { create } from "zustand";
import {
  AppTheme,
  CurioSettingsState,
  UserProfileSettings,
  LearningSettings,
  AudioVoiceSettings,
  PrivacyAndDataSettings,
} from "@/types/settings";
import { getSessionHistory } from "@/services/historyService";
import { getUserProgress } from "@/services/progressService";

const SETTINGS_STORAGE_KEY = "curio_user_settings_v1";

const DEFAULT_SETTINGS: CurioSettingsState = {
  theme: "light",
  profile: {
    displayName: "",
    email: "",
    role: "Learner",
    bio: "",
    learningGoal: "",
    characterAvatar: "PROFESSOR",
    avatarColor: "#3A63FF",
    feynmanLevel: 1,
    levelTitle: "Beginner Explainer",
  },
  learning: {
    rigorLevel: "socratic",
    probingDepth: 3,
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
    conceptsMastered: 0,
    gapsResolved: 0,
    totalSessions: 0,
    voiceMinutes: 0,
    feynmanStreakDays: 0,
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
  syncRealStats: () => Promise<void>;
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
      let parsed = stored ? JSON.parse(stored) : null;

      // Purge any legacy mock user data that might be stuck in localStorage
      if (parsed?.profile?.email === "learner@curio.ai") {
        parsed.profile.email = "";
      }
      if (parsed?.profile?.displayName === "Chinmay Joshi") {
        parsed.profile.displayName = "";
      }

      // Sync user identity from real auth session if available
      const rawUser = localStorage.getItem("curio_auth_user");
      if (rawUser) {
        try {
          const authUser = JSON.parse(rawUser);
          if (!parsed) parsed = {};
          if (!parsed.profile) parsed.profile = {};
          if (authUser.name && !parsed.profile.displayName) {
            parsed.profile.displayName = authUser.name;
          }
          if (authUser.email && !parsed.profile.email) {
            parsed.profile.email = authUser.email;
          }
        } catch {}
      }

      if (parsed) {
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

      // Automatically sync real stats in background
      get().syncRealStats();
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

  syncRealStats: async () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("curio_access_token");
    if (!token) return;

    try {
      const [sessionsRes, progressRes] = await Promise.allSettled([
        getSessionHistory(1, 100),
        getUserProgress(),
      ]);

      let totalSessions = 0;
      let voiceMinutes = 0;
      let conceptsMastered = 0;
      let gapsResolved = 0;
      let feynmanStreakDays = 0;

      if (sessionsRes.status === "fulfilled" && Array.isArray(sessionsRes.value)) {
        const sList = sessionsRes.value;
        totalSessions = sList.length;
        voiceMinutes = sList.reduce((acc, s) => acc + (s.durationMinutes || 0), 0);
        gapsResolved = sList.reduce((acc, s) => acc + (s.resolvedMisconceptions || 0), 0);

        if (sList.length > 0) {
          const uniqueDays = new Set(
            sList
              .filter((s) => s.createdAt)
              .map((s) => new Date(s.createdAt).toISOString().slice(0, 10))
          );
          feynmanStreakDays = uniqueDays.size;
        }
      }

      if (progressRes.status === "fulfilled" && progressRes.value) {
        const p = progressRes.value;
        if (p.concepts && Array.isArray(p.concepts)) {
          conceptsMastered = p.concepts.filter((c) => (c.mastery_score ?? 0) >= 0.8).length;
        }
        if (p.summary?.total_misconceptions) {
          gapsResolved = Math.max(gapsResolved, p.summary.total_misconceptions);
        }
      }

      // Dynamic Feynman Level computation
      let feynmanLevel = 1;
      let levelTitle = "Beginner Explainer";

      if (totalSessions >= 20 || conceptsMastered >= 15) {
        feynmanLevel = 4;
        levelTitle = "Senior Explainer";
      } else if (totalSessions >= 10 || conceptsMastered >= 8) {
        feynmanLevel = 3;
        levelTitle = "Proficient Explainer";
      } else if (totalSessions >= 3 || conceptsMastered >= 3) {
        feynmanLevel = 2;
        levelTitle = "Junior Explainer";
      }

      set((state) => ({
        stats: {
          conceptsMastered,
          gapsResolved,
          totalSessions,
          voiceMinutes,
          feynmanStreakDays,
        },
        profile: {
          ...state.profile,
          feynmanLevel,
          levelTitle,
        },
      }));
    } catch (e) {
      console.warn("Failed to sync real learner stats:", e);
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
