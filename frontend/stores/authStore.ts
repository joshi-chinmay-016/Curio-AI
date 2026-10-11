import { create } from "zustand";
import { User, LoginCredentials, RegisterCredentials } from "@/types/auth";
import { loginApi, registerApi, getMeApi } from "@/services/authService";

const TOKEN_KEY = "curio_access_token";

interface AuthStoreState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  loginDemoUser: (email?: string) => void;
  logout: () => void;
  initAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthStoreState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
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
      const user = await getMeApi(token);
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
      // Automatically log in following registration
      await get().login(credentials);
    } catch (err: any) {
      set({
        isLoading: false,
        error: err.message || "Registration failed. Please try again.",
      });
      throw err;
    }
  },

  loginDemoUser: (email?: string) => {
    const demoEmail = email || "learner@curio.ai";
    const demoUser: User = {
      id: "demo-" + Math.random().toString(36).substring(2, 9),
      email: demoEmail,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    const demoToken = "demo-session-token";
    if (typeof window !== "undefined") {
      localStorage.setItem(TOKEN_KEY, demoToken);
      localStorage.setItem("curio_demo_user", JSON.stringify(demoUser));
    }
    set({
      token: demoToken,
      user: demoUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("curio_demo_user");
      // Clean up sensitive user session items
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
    set({ isLoading: true, error: null });
    if (typeof window === "undefined") {
      set({ isLoading: false });
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

    if (savedToken === "demo-session-token") {
      let storedUser: User = {
        id: "demo-user",
        email: "learner@curio.ai",
        is_active: true,
        created_at: new Date().toISOString(),
      };
      try {
        const raw = localStorage.getItem("curio_demo_user");
        if (raw) storedUser = JSON.parse(raw);
      } catch {}
      set({
        token: savedToken,
        user: storedUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return;
    }

    try {
      const user = await getMeApi(savedToken);
      set({
        token: savedToken,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      // Invalid or expired token
      localStorage.removeItem(TOKEN_KEY);
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
