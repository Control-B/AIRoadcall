/**
 * Roadcall.ai operational session helpers.
 *
 * - `roadside_session_id`   — keeps the roadside flow stitched together as the
 *                             user navigates from issue → location → vehicle →
 *                             payment → mechanic → tracking. The actual job
 *                             data lives in the backend; the cookie is just a
 *                             reference. 6h max.
 * - `location_session_id`   — short-lived (≤60 min) reference for SMS GPS
 *                             links. Falls back to a URL token when cookies
 *                             are blocked (e.g. Safari private mode).
 * - `ai_conversation_id`    — keeps AI chat continuous across refresh, 24h
 *                             for anonymous users.
 *
 * Nothing sensitive is ever written to the browser. All real data stays in
 * the backend database keyed by these opaque references.
 */
import { COOKIE, deleteCookie, getOrCreate, readCookie, writeCookie } from "./cookies";

// ── Roadside flow ────────────────────────────────────────────────────────────
export function getOrCreateRoadsideSessionId(): string {
  return getOrCreate(COOKIE.ROADSIDE_SESSION, 24);
}

export function clearRoadsideSession(): void {
  deleteCookie(COOKIE.ROADSIDE_SESSION);
}

// ── Location capture (SMS link) ──────────────────────────────────────────────
/**
 * Resolve the location session, in priority order:
 *   1. URL token from SMS link (?t=…)
 *   2. Existing cookie
 *   3. Newly minted opaque ID (cookie + return)
 *
 * The SMS-token path is critical for users on Safari private mode or any
 * browser that blocks third-party cookies — the backend can validate the
 * token and reattach the GPS submission to the right job.
 */
export function resolveLocationSessionId(urlToken?: string | null): string {
  if (urlToken && urlToken.length >= 8) {
    writeCookie(COOKIE.LOCATION_SESSION, urlToken, { path: "/locate" });
    return urlToken;
  }
  return getOrCreate(COOKIE.LOCATION_SESSION, 24);
}

export function clearLocationSession(): void {
  deleteCookie(COOKIE.LOCATION_SESSION, "/locate");
}

// ── AI conversation ──────────────────────────────────────────────────────────
export function getOrCreateAiConversationId(): string {
  return getOrCreate(COOKIE.AI_CONVERSATION, 24);
}

export function clearAiConversation(): void {
  deleteCookie(COOKIE.AI_CONVERSATION);
}

export function getCurrentAiConversationId(): string | null {
  return readCookie(COOKIE.AI_CONVERSATION);
}
