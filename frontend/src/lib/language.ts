/**
 * Language preference utilities.
 * Order: explicit user choice → cookie → browser language → "en".
 */
import { COOKIE, readCookie, writeCookie } from "./cookies";

export const SUPPORTED_LANGUAGES = ["en", "es", "fr", "pt"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const DEFAULT: SupportedLanguage = "en";

function normalize(raw: string | null | undefined): SupportedLanguage {
  if (!raw) return DEFAULT;
  const base = raw.toLowerCase().split(/[-_]/)[0] as SupportedLanguage;
  return SUPPORTED_LANGUAGES.includes(base) ? base : DEFAULT;
}

export function detectBrowserLanguage(): SupportedLanguage {
  if (typeof navigator === "undefined") return DEFAULT;
  const candidates = [navigator.language, ...(navigator.languages ?? [])];
  for (const c of candidates) {
    const n = normalize(c);
    if (n !== DEFAULT || c.toLowerCase().startsWith("en")) return n;
  }
  return DEFAULT;
}

export function getPreferredLanguage(): SupportedLanguage {
  const stored = readCookie(COOKIE.PREFERRED_LANGUAGE);
  if (stored) return normalize(stored);
  return detectBrowserLanguage();
}

export function setPreferredLanguage(lang: SupportedLanguage): void {
  writeCookie(COOKIE.PREFERRED_LANGUAGE, lang);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("roadcall:language", { detail: { lang } }));
  }
}
