/**
 * Cookie / analytics consent state.
 *
 * Three states for analytics:
 *   - "unset"    : user has not answered yet → only essential cookies run
 *   - "granted"  : analytics & marketing scripts may load
 *   - "denied"   : analytics & marketing scripts MUST stay disabled
 *
 * Essential cookies always run (auth, roadside session, language, etc.).
 */
import { COOKIE, readCookie, writeCookie } from "./cookies";

export type ConsentChoice = "granted" | "denied";
export type ConsentState = "unset" | ConsentChoice;

export function getCookieConsent(): ConsentState {
  const seen = readCookie(COOKIE.COOKIE_CONSENT);
  if (seen !== "1") return "unset";
  const analytics = readCookie(COOKIE.ANALYTICS_CONSENT);
  return analytics === "granted" ? "granted" : "denied";
}

export function hasAnsweredConsent(): boolean {
  return readCookie(COOKIE.COOKIE_CONSENT) === "1";
}

export function setConsent(choice: ConsentChoice): void {
  writeCookie(COOKIE.COOKIE_CONSENT, "1");
  writeCookie(COOKIE.ANALYTICS_CONSENT, choice);
  // Notify any listeners (e.g. analytics loader) without a full reload.
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("roadcall:consent", { detail: { choice } }));
  }
}

export function isAnalyticsAllowed(): boolean {
  return getCookieConsent() === "granted";
}
