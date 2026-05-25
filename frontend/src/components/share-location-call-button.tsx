"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Phone, X, AlertCircle, CheckCircle2 } from "lucide-react";

import { getApiBase } from "@/lib/api-client";
import { HELP_PHONE, telHref } from "@/lib/phone";

const PHONE_STORAGE_KEY = "roadcall.caller_phone";
const SESSION_STORAGE_KEY = "roadcall.dispatch_session_id";

type Status = "idle" | "needPhone" | "working" | "ready";

type SharedLocation = {
  dispatchSessionId: string;
  readableAddress: string | null;
  city: string | null;
  state: string | null;
  accuracy: number | null;
};

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  const ten = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits.slice(0, 10);
  if (ten.length <= 3) return ten;
  if (ten.length <= 6) return `(${ten.slice(0, 3)}) ${ten.slice(3)}`;
  return `(${ten.slice(0, 3)}) ${ten.slice(3, 6)}-${ten.slice(6)}`;
}

function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

export function ShareLocationCallButton({ className = "" }: { className?: string }) {
  const [status, setStatus] = useState<Status>("idle");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [sharedLocation, setSharedLocation] = useState<SharedLocation | null>(null);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(PHONE_STORAGE_KEY);
      if (saved) setPhone(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const shareLocation = useCallback(async (rawPhone: string): Promise<boolean> => {
    const digits = digitsOnly(rawPhone);
    if (digits.length < 10) return false;

    try {
      window.localStorage.setItem(PHONE_STORAGE_KEY, digits);
    } catch {
      /* ignore */
    }

    if (!navigator.geolocation) {
      setStatus("ready");
      setMessage("Sandy will ask for your location on the call.");
      return false;
    }

    setStatus("working");
    setMessage("Sharing your GPS with Sandy…");

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          try {
            const response = await fetch(`${getApiBase()}/caller/share-location`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                phone: digits,
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy: pos.coords.accuracy ?? null,
                captured_at: new Date().toISOString(),
              }),
            });
            if (!response.ok) throw new Error("Location share failed");
            const stored = await response.json();
            const nextLocation: SharedLocation = {
              dispatchSessionId: stored.dispatch_session_id,
              readableAddress: stored.readable_address || stored.address || null,
              city: stored.city || null,
              state: stored.state || null,
              accuracy: typeof stored.accuracy === "number" ? stored.accuracy : null,
            };
            setSharedLocation(nextLocation);
            try {
              window.localStorage.setItem(SESSION_STORAGE_KEY, nextLocation.dispatchSessionId);
            } catch {
              /* ignore */
            }
            setStatus("ready");
            setMessage("Location Shared Successfully");
            resolve(true);
          } catch {
            setStatus("ready");
            setSharedLocation(null);
            setMessage("Couldn't share GPS. Tap the phone button to call Sandy now.");
            resolve(false);
          }
        },
        () => {
          setStatus("ready");
          setSharedLocation(null);
          setMessage("Couldn't read GPS. Tap the phone button to call Sandy now.");
          resolve(false);
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
      );
    });
  }, []);

  const shareAndCall = useCallback(async (rawPhone: string) => {
    const digits = digitsOnly(rawPhone);
    if (digits.length < 10) {
      setStatus("needPhone");
      setMessage("Enter the number you'll call from.");
      return;
    }

    setPhone(digits);
    await shareLocation(digits);
  }, [shareLocation]);

  const hasPhone = digitsOnly(phone).length >= 10;

  const handleFabClick = useCallback((event?: { preventDefault: () => void }) => {
    if (!hasPhone) {
      event?.preventDefault();
      setStatus("needPhone");
      setMessage(null);
      return;
    }
    if (status === "ready" && sharedLocation) return;
    event?.preventDefault();
    void shareAndCall(phone);
  }, [hasPhone, phone, shareAndCall, sharedLocation, status]);

  const close = useCallback(() => {
    setStatus("idle");
    setMessage(null);
  }, []);

  const locationLabel = sharedLocation?.readableAddress || [sharedLocation?.city, sharedLocation?.state].filter(Boolean).join(", ");
  const canCall = status === "ready" && Boolean(sharedLocation);

  return (
    <>
      {hasPhone && canCall ? (
        <a
          href={telHref(HELP_PHONE)}
          aria-label={`Share location and call ${HELP_PHONE}`}
          className={`fixed bottom-6 left-1/2 z-[90] flex h-12 w-12 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-slate-950 shadow-2xl ring-2 ring-emerald-400/30 transition hover:scale-105 active:scale-95 sm:h-14 sm:w-14 ${className}`}
        >
          <Phone className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" />
        </a>
      ) : (
        <button
          type="button"
          onClick={handleFabClick}
          disabled={status === "working"}
          aria-label={`Share location and call ${HELP_PHONE}`}
          className={`fixed bottom-6 left-1/2 z-[90] flex h-12 w-12 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-slate-950 shadow-2xl ring-2 ring-emerald-400/30 transition hover:scale-105 active:scale-95 disabled:cursor-wait disabled:opacity-70 sm:h-14 sm:w-14 ${className}`}
        >
          {status === "working" ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Phone className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" />
          )}
        </button>
      )}

      {status !== "idle" ? (
        <div className="fixed bottom-28 left-1/2 z-[90] w-[18rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 rounded-2xl border border-roadcall-cyan/25 bg-roadcall-panel/95 p-4 shadow-2xl backdrop-blur-md">
          <div className="mb-2 flex items-start justify-between gap-2">
            <p className="text-sm font-semibold text-white">Share location & call Sandy</p>
            <button
              type="button"
              onClick={close}
              aria-label="Close"
              className="text-roadcall-muted hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {status === "needPhone" ? (
            <>
              <p className="mb-2 text-xs text-roadcall-muted">
                One time only — so Sandy can match your GPS to your incoming call.
              </p>
              <input
                type="tel"
                autoFocus
                inputMode="numeric"
                autoComplete="tel"
                placeholder="(555) 123-4567"
                value={formatPhone(phone)}
                onChange={(e) => setPhone(e.target.value)}
                className="mb-2 w-full rounded-lg border border-roadcall-cyan/20 bg-[#06101f]/90 px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/60 focus:border-roadcall-cyan/60 focus:outline-none"
              />
              {message ? (
                <p className="mb-2 flex items-start gap-1.5 text-xs text-amber-300">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  {message}
                </p>
              ) : null}
              <button
                type="button"
                onClick={() => void shareAndCall(phone)}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-400 to-cyan-400 px-3 py-2.5 text-sm font-bold text-slate-950 hover:brightness-110"
              >
                <Phone className="h-4 w-4" />
                Share & Call {HELP_PHONE}
              </button>
            </>
          ) : null}

          {status === "working" ? (
            <p className="flex items-center gap-2 text-sm text-roadcall-silver">
              <Loader2 className="h-4 w-4 animate-spin text-roadcall-cyan" />
              {message || "Working…"}
            </p>
          ) : null}

          {status === "ready" ? (
            <div className="space-y-3">
              <p className="flex items-start gap-2 text-sm text-emerald-300">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                {message || "Ready to call Sandy."}
              </p>
              {locationLabel ? (
                <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-50">
                  <p className="font-semibold text-emerald-200">Shared location</p>
                  <p>{locationLabel}</p>
                  {sharedLocation?.accuracy ? <p className="mt-1 text-emerald-100/70">Accuracy about {Math.round(sharedLocation.accuracy)} m</p> : null}
                </div>
              ) : null}
              {canCall ? (
                <a
                  href={telHref(HELP_PHONE)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-400 to-cyan-400 px-3 py-2.5 text-sm font-bold text-slate-950 hover:brightness-110"
                >
                  <Phone className="h-4 w-4" />
                  Call Sandy {HELP_PHONE}
                </a>
              ) : (
                <button
                  type="button"
                  onClick={() => void shareAndCall(phone)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-400 to-cyan-400 px-3 py-2.5 text-sm font-bold text-slate-950 hover:brightness-110"
                >
                  <Phone className="h-4 w-4" />
                  Try sharing location again
                </button>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
