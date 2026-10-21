import { create } from "zustand";
import { User, LoginCredentials, RegisterCredentials } from "@/types/auth";
import { loginApi, registerApi, getMeApi } from "@/services/authService";
import { useSettingsStore } from "@/stores/settingsStore";

const TOKEN_KEY = "curio_access_token";
const USER_KEY = "curio_auth_user";

interface AuthStoreState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  loginDemoUser: (email?: string, name?: string) => void;
  logout: () => void;
  initAuth: () => Promise<void>;
  clearError: () => void;
}

function getInitialAuthState(): {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
} {
  if (typeof window === "undefined") {
    return { user: null, token: null, isAuthenticated: false, isLoading: false };
  }
  try {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (!savedToken) {
      return { user: null, token: null, isAuthenticated: false, isLoading: false };
    }

    // Clean up any stale demo session tokens
    if (savedToken === "demo-session-token") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem("curio_demo_user");
      return { user: null, token: null, isAuthenticated: false, isLoading: false };
    }

    const rawUser = localStorage.getItem(USER_KEY);
    if (rawUser) {
      try {
        const user = JSON.parse(rawUser);
        // Clean up legacy mock learner
        if (user.email === "learner@curio.ai" && user.id === "demo-learner") {
          localStorage.removeItem(USER_KEY);
        } else {
          return { user, token: savedToken, isAuthenticated: true, isLoading: false };
        }
      } catch {}
    }

    // Token exists without cached user - preserve session and let initAuth fetch real user in background
    return {
      user: null,
      token: savedToken,
      isAuthenticated: true,
      isLoading: false,
    };
  } catch {
    return { user: null, token: null, isAuthenticated: false, isLoading: false };
  }
}

const initialState = getInitialAuthState();

export const useAuthStore = create<AuthStoreState>((set, get) => ({
  user: initialState.user,
  token: initialState.token,
  isAuthenticated: initialState.isAuthenticated,
  isLoading: initialState.isLoading,
  error: null,

  clearError: () => set({ error: null }),

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const tokenRes = await loginApi(credentials);
      const token = tokenRes.access_token;
      if (typeof window !== "undefined") {
        localStorage.setItem(TOKEN_KEY, token);
      }

      // Fetch user profile immediately
      let user: User;
      try {
        user = await getMeApi(token);
      } catch {
        user = {
          id: "user-" + Math.random().toString(36).substring(2, 9),
          email: credentials.email,
          is_active: true,
          created_at: new Date().toISOString(),
        };
      }

      if (typeof window !== "undefined") {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      }

      // Sync with settings store
      try {
        const displayName = user.name || credentials.email.split("@")[0];
        useSettingsStore.getState().updateProfile({
          displayName,
          email: user.email,
        });
        useSettingsStore.getState().syncRealStats();
      } catch {}

      set({
        token,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      if (typeof window !== "undefined") {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }
      set({
        token: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: err.message || "Failed to sign in. Please verify your credentials.",
      });
      throw err;
    }
  },

  register: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      await registerApi(credentials);

      // Save name to settings immediately
      if (credentials.name) {
        try {
          useSettingsStore.getState().updateProfile({
            displayName: credentials.name,
            email: credentials.email,
          });
        } catch {}
      }

      // Automatically log in following registration
      await get().login({
        email: credentials.email,
        password: credentials.password,
      });

      // Update name on user object if returned without it
      const currentUser = get().user;
      if (currentUser && credentials.name) {
        const updatedUser = { ...currentUser, name: credentials.name };
        set({ user: updatedUser });
        if (typeof window !== "undefined") {
          localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
        }
      }
    } catch (err: any) {
      set({
        isLoading: false,
        error: err.message || "Registration failed. Please try again.",
      });
      throw err;
    }
  },

  loginDemoUser: () => {
    console.warn("[CurioAuth] Demo access is disabled. Real authentication is required.");
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem("curio_demo_user");
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.clear();
      }
    }
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  },

  initAuth: async () => {
    if (typeof window === "undefined") return;

    // Idempotency: If already authenticated and user object exists, do NOT wipe state or enter loading!
    if (get().isAuthenticated && get().user && get().token) {
      return;
    }

    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (!savedToken) {
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return;
    }

    // Clean up any stale demo tokens
    if (savedToken === "demo-session-token") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem("curio_demo_user");
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return;
    }

    // Try reading cached user first to preserve instant render
    const cachedUserRaw = localStorage.getItem(USER_KEY);
    if (cachedUserRaw) {
      try {
        const cachedUser = JSON.parse(cachedUserRaw);
        set({
          token: savedToken,
          user: cachedUser,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch {}
    }

    // Background validation
    try {
      const user = await getMeApi(savedToken);
      if (typeof window !== "undefined") {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      }

      // Sync user profile & stats to settings store
      try {
        const displayName = user.name || (user.email ? user.email.split("@")[0] : "Learner");
        useSettingsStore.getState().updateProfile({
          displayName,
          email: user.email,
        });
        useSettingsStore.getState().syncRealStats();
      } catch {}

      set({
        token: savedToken,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      // ONLY clear token if the server explicitly returned 401 Unauthorized
      // On network errors / timeouts, keep user logged in so their session never drops
      if (err?.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      } else {
        // Keep authenticated state active from cache
        set({
          isAuthenticated: true,
          isLoading: false,
        });
      }
    }
  },
}));
