/**
 * Admin authentication helpers.
 * Stores the session token in localStorage and provides
 * fetch wrappers that attach the X-Admin-Key header.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const TOKEN_KEY = "admin_token";
const USERNAME_KEY = "admin_username";
const EXPIRES_KEY = "admin_expires";

// ── Token management ────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem(TOKEN_KEY);
  const expires = localStorage.getItem(EXPIRES_KEY);
  if (!token || !expires) return null;

  // Check expiry
  if (new Date(expires) < new Date()) {
    clearToken();
    return null;
  }
  return token;
}

export function getUsername(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(USERNAME_KEY);
}

export function setToken(token: string, expiresAt: string, username: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EXPIRES_KEY, expiresAt);
  localStorage.setItem(USERNAME_KEY, username);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXPIRES_KEY);
  localStorage.removeItem(USERNAME_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

// ── Login / Logout ──────────────────────────────────────

export async function login(
  username: string,
  password: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}/admin/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        success: false,
        error: body.detail || "Invalid credentials",
      };
    }

    const data = await res.json();
    setToken(data.token, data.expires_at, data.username);
    return { success: true };
  } catch (err) {
    return { success: false, error: "Network error — is the backend running?" };
  }
}

export async function logout() {
  const token = getToken();
  if (token) {
    try {
      await fetch(`${API_BASE}/admin/logout`, {
        method: "POST",
        headers: { "X-Admin-Key": token },
      });
    } catch {
      // Ignore — we're clearing locally regardless
    }
  }
  clearToken();
}

// ── Authenticated fetch ─────────────────────────────────

export async function adminFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken();
  if (!token) {
    throw new Error("Not authenticated");
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Admin-Key": token,
    ...(options?.headers as Record<string, string> | undefined),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new Error("Session expired");
  }

  if (!res.ok) {
    let errorMessage = "Request failed";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") errorMessage = body.detail;
      else if (body.message) errorMessage = body.message;
    } catch {
      // keep default
    }
    throw new Error(errorMessage);
  }

  return (await res.json()) as T;
}
