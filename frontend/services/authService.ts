import { User, TokenResponse, LoginCredentials, RegisterCredentials } from "@/types/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS = 15000;

export class AuthError extends Error {
  status?: number;
  code?: string;
  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = "AuthError";
    this.status = status;
    this.code = code;
  }
}

async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs = TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res;
  } catch (err: any) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new AuthError(
        "Request timed out (server took >15s to respond). Database connection may be offline or slow.",
        408,
        "TIMEOUT"
      );
    }
    throw new AuthError(
      "Unable to reach the backend service. Please ensure the server is running on port 8000.",
      503,
      "NETWORK_ERROR"
    );
  }
}

export async function loginApi(credentials: LoginCredentials): Promise<TokenResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : errorData.message || "Invalid email or password";
    throw new AuthError(message, response.status, errorData.code);
  }

  return response.json();
}

export async function registerApi(credentials: RegisterCredentials): Promise<User> {
  const response = await fetchWithTimeout(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : errorData.message ||
          (Array.isArray(errorData.detail)
            ? errorData.detail.map((e: any) => e.msg || e.message).join(", ")
            : "Failed to create account");
    throw new AuthError(message, response.status, errorData.code);
  }

  return response.json();
}

export async function getMeApi(token: string): Promise<User> {
  const response = await fetchWithTimeout(`${API_BASE}/auth/me`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new AuthError("Session expired or invalid", response.status);
  }

  return response.json();
}
