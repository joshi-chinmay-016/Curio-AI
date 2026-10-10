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

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      // Clean up sensitive user session items
      sessionStorage.clear();
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
