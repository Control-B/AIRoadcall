/**
 * Roadcall.ai cookie utilities (browser).
 *
 * Centralizes every NON-HttpOnly cookie used by the public site and dashboards:
 *   - cookie consent state
 *   - preferred language
 *   - AI conversation reference
 *   - UI preferences (delegated to localStorage where appropriate)
 *
 * Auth cookies (`roadcall_auth_session`, `roadcall_refresh_session`) are
 * HttpOnly and ONLY managed by the backend — never read or written here.
 *
 * Rules:
 *   - Always include the `roadcall_` prefix.
 *   - Always set `Secure` outside of localhost.
 *   - Always set `SameSite=Lax` unless explicitly cross-site.
 *   - Never store PII, GPS, payment data, or transcripts.
 */

export type SameSite = "Lax" | "Strict" | "None";

export interface CookieOptions {
  maxAgeSeconds: number;
  path?: string;
  sameSite?: SameSite;
  secure?: boolean; // overridden to true on https
}

const HOUR = 3600;
const DAY = 24 * HOUR;

// ── Cookie names (must match backend/app/core/cookies.py) ────────────────────
export const COOKIE = {
  CLIENT_SESSION: "roadcall_client_session_id",
  ROADSIDE_SESSION: "roadcall_roadside_session_id",
  LOCATION_SESSION: "roadcall_location_session_id",
  AI_CONVERSATION: "roadcall_ai_conversation_id",
  PREFERRED_LANGUAGE: "roadcall_preferred_language",
  COOKIE_CONSENT: "roadcall_cookie_consent",
  ANALYTICS_CONSENT: "roadcall_analytics_consent",
} as const;

export const COOKIE_LIFETIME: Record<string, number> = {
  [COOKIE.CLIENT_SESSION]: 30 * DAY,
  [COOKIE.ROADSIDE_SESSION]: 6 * HOUR,
  [COOKIE.LOCATION_SESSION]: 60 * 60,
  [COOKIE.AI_CONVERSATION]: 24 * HOUR,
  [COOKIE.PREFERRED_LANGUAGE]: 180 * DAY,
  [COOKIE.COOKIE_CONSENT]: 365 * DAY,
  [COOKIE.ANALYTICS_CONSENT]: 365 * DAY,
};

function isProduction(): boolean {
  if (typeof window === "undefined") return false;
  return window.location.protocol === "https:";
}

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const target = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(target)) {
      return decodeURIComponent(trimmed.substring(target.length));
    }
  }
  return null;
}

export function writeCookie(name: string, value: string, opts?: Partial<CookieOptions>): void {
  if (typeof document === "undefined") return;
  const maxAge = opts?.maxAgeSeconds ?? COOKIE_LIFETIME[name] ?? DAY;
  const path = opts?.path ?? "/";
  const sameSite: SameSite = opts?.sameSite ?? "Lax";
  const secure = opts?.secure ?? isProduction();
  const parts = [
    `${name}=${encodeURIComponent(value)}`,
    `Max-Age=${maxAge}`,
    `Path=${path}`,
    `SameSite=${sameSite}`,
  ];
  if (secure) parts.push("Secure");
  document.cookie = parts.join("; ");
}

export function deleteCookie(name: string, path = "/"): void {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; Path=${path}; SameSite=Lax`;
}

/** Crypto-strong opaque ID (URL-safe base64-ish). */
export function newOpaqueId(byteCount = 18): string {
  if (typeof crypto !== "undefined" && "getRandomValues" in crypto) {
    const buf = new Uint8Array(byteCount);
    crypto.getRandomValues(buf);
    return Array.from(buf)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/**
 * Get-or-create helper for any reference-ID cookie.
 * Returns the same value across the lifetime of the cookie.
 */
export function getOrCreate(name: string, byteCount = 18): string {
  const existing = readCookie(name);
  if (existing) return existing;
  const id = newOpaqueId(byteCount);
  writeCookie(name, id);
  return id;
}
