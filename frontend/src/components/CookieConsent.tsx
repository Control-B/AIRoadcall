"use client";

import { useEffect, useState } from "react";
import { getCookieConsent, hasAnsweredConsent, setConsent, type ConsentChoice } from "@/lib/consent";

/**
 * Cookie consent banner + preferences modal.
 *
 * - Renders nothing until mount (avoids hydration mismatch).
 * - Renders nothing if the user has already answered.
 * - Essential cookies run regardless of choice.
 * - Analytics/marketing scripts must check `isAnalyticsAllowed()` before
 *   loading.
 */
export default function CookieConsent() {
  const [mounted, setMounted] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
    setOpen(!hasAnsweredConsent());
  }, []);

  if (!mounted || !open) return null;

  function pick(choice: ConsentChoice) {
    setConsent(choice);
    setOpen(false);
    setShowPrefs(false);
  }

  return (
    <>
      {/* Bottom banner */}
      {!showPrefs && (
        <div
          role="dialog"
          aria-live="polite"
          aria-label="Cookie preferences"
          className="fixed inset-x-0 bottom-0 z-[60] px-4 pb-4 sm:px-6"
        >
          <div className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white/95 backdrop-blur shadow-2xl ring-1 ring-black/5">
            <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm leading-snug text-slate-700">
                <strong className="text-slate-900">Roadcall.ai</strong> uses essential cookies to
                keep roadside sessions, dashboard access, and dispatch workflows secure and
                reliable. Optional analytics cookies help us improve the service.
              </p>
              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <button
                  onClick={() => setShowPrefs(true)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Preferences
                </button>
                <button
                  onClick={() => pick("denied")}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Reject optional
                </button>
                <button
                  onClick={() => pick("granted")}
                  className="rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
                >
                  Accept all
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preferences modal */}
      {showPrefs && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <h2 className="text-lg font-semibold text-slate-900">Cookie preferences</h2>
            <p className="mt-1 text-sm text-roadcall-muted/70">
              Essential cookies keep roadside dispatch, GPS capture, and dashboard sessions
              working. Optional cookies are off until you turn them on.
            </p>

            <div className="mt-5 space-y-4">
              <Row
                title="Essential"
                detail="Auth, roadside session, GPS capture, language, security."
                tag="Always on"
                disabled
              />
              <Row
                title="Analytics"
                detail="Aggregated usage to fix bugs and improve the service."
                tag="Optional"
              />
              <Row
                title="Marketing"
                detail="Roadcall.ai does not run retargeting pixels by default."
                tag="Off"
                disabled
              />
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <button
                onClick={() => setShowPrefs(false)}
                className="rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Back
              </button>
              <button
                onClick={() => pick("denied")}
                className="rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Save — essential only
              </button>
              <button
                onClick={() => pick("granted")}
                className="rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
              >
                Save — allow analytics
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Row({
  title,
  detail,
  tag,
  disabled,
}: {
  title: string;
  detail: string;
  tag: string;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50/50 px-4 py-3">
      <div>
        <p className="text-sm font-semibold text-slate-800">{title}</p>
        <p className="text-xs text-roadcall-muted/70">{detail}</p>
      </div>
      <span
        className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
          disabled ? "bg-slate-200 text-roadcall-muted/55" : "bg-emerald-100 text-emerald-700"
        }`}
      >
        {tag}
      </span>
    </div>
  );
}

/** Tiny re-open hook for footer/account links: `window.dispatchEvent(new CustomEvent("roadcall:open-consent"))` */
export function useReopenConsent() {
  useEffect(() => {
    function handler() {
      // Force re-show by clearing the "answered" cookie.
      document.cookie = "roadcall_cookie_consent=; Max-Age=0; Path=/; SameSite=Lax";
      window.location.reload();
    }
    window.addEventListener("roadcall:open-consent", handler);
    return () => window.removeEventListener("roadcall:open-consent", handler);
  }, []);
}

// Suppress unused import warning when consumer code doesn't pull this
void getCookieConsent;
