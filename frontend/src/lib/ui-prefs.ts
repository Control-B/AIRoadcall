/**
 * UI preferences live in localStorage (not cookies) — they don't need to
 * round-trip to the backend, and the backend never reads them.
 *
 * Allowed: theme, sidebar collapsed state, last dashboard view.
 * NOT ALLOWED: any business/customer/job data.
 */

const STORAGE_KEYS = {
  THEME: "roadcall.ui.theme",
  SIDEBAR_COLLAPSED: "roadcall.ui.sidebar_collapsed",
  LAST_DASHBOARD_VIEW: "roadcall.ui.last_view",
  NOTIFICATION_PREF: "roadcall.ui.notifications",
} as const;

export type Theme = "light" | "dark" | "default";

function safeGet(key: string): string | null {
  try {
    return typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    if (typeof window !== "undefined") window.localStorage.setItem(key, value);
  } catch {
    /* private mode / storage disabled — silently no-op */
  }
}

export function getTheme(): Theme {
  const v = safeGet(STORAGE_KEYS.THEME) as Theme | null;
  return v && ["light", "dark", "default"].includes(v) ? v : "default";
}
export function setTheme(value: Theme): void {
  safeSet(STORAGE_KEYS.THEME, value);
}

export function getSidebarCollapsed(): boolean {
  return safeGet(STORAGE_KEYS.SIDEBAR_COLLAPSED) === "1";
}
export function setSidebarCollapsed(value: boolean): void {
  safeSet(STORAGE_KEYS.SIDEBAR_COLLAPSED, value ? "1" : "0");
}

export function getLastDashboardView(): string | null {
  return safeGet(STORAGE_KEYS.LAST_DASHBOARD_VIEW);
}
export function setLastDashboardView(value: string): void {
  safeSet(STORAGE_KEYS.LAST_DASHBOARD_VIEW, value);
}

export function getNotificationPref(): boolean {
  const v = safeGet(STORAGE_KEYS.NOTIFICATION_PREF);
  return v === null ? true : v === "1";
}
export function setNotificationPref(value: boolean): void {
  safeSet(STORAGE_KEYS.NOTIFICATION_PREF, value ? "1" : "0");
}
