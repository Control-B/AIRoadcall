"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Phone, X, AlertCircle, CheckCircle2 } from "lucide-react";

import { getApiBase } from "@/lib/api-client";
import { HELP_PHONE, telHref } from "@/lib/phone";

const PHONE_STORAGE_KEY = "roadcall.caller_phone";

type Status = "idle" | "needPhone" | "working" | "ready";

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
  const callLinkRef = useRef<HTMLAnchorElement | null>(null);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(PHONE_STORAGE_KEY);
      if (saved) setPhone(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const shareAndCall = useCallback(async (rawPhone: string) => {
    const digits = digitsOnly(rawPhone);
    if (digits.length < 10) {
      setStatus("needPhone");
      setMessage("Enter the number you'll call from.");
      return;
    }
    try {
      window.localStorage.setItem(PHONE_STORAGE_KEY, digits);
    } catch {
      /* ignore */
    }

    const dial = () => {
      setStatus("ready");
      setTimeout(() => callLinkRef.current?.click(), 50);
    };

    if (!navigator.geolocation) {
      setMessage("Calling now — Sandy will ask for your location.");
      dial();
      return;
    }

    setStatus("working");
    setMessage("Reading your GPS…");

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setMessage("Sending your location to Sandy…");
        try {
          await fetch(`${getApiBase()}/caller/share-location`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              phone: digits,
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
              accuracy: pos.coords.accuracy ?? null,
            }),
          });
        } catch {
          /* even if the share fails, still place the call */
        }
        setMessage("Calling Sandy now…");
        dial();
      },
      () => {
        setMessage("Couldn't read GPS — calling now, Sandy will ask for your location.");
        dial();
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  }, []);

  const handleClick = useCallback(() => {
    if (digitsOnly(phone).length < 10) {
      setStatus("needPhone");
      setMessage(null);
      return;
    }
    void shareAndCall(phone);
  }, [phone, shareAndCall]);

  const close = useCallback(() => {
    setStatus("idle");
    setMessage(null);
  }, []);

  return (
    <>
      <a ref={callLinkRef} href={telHref(HELP_PHONE)} className="hidden" aria-hidden="true">
        call
      </a>

      <button
        type="button"
        onClick={handleClick}
        aria-label={`Share location and call ${HELP_PHONE}`}
        className={`fixed bottom-6 right-6 z-40 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-slate-950 shadow-2xl ring-4 ring-emerald-400/30 transition hover:scale-105 active:scale-95 sm:h-20 sm:w-20 ${className}`}
      >
        {status === "working" ? (
          <Loader2 className="h-7 w-7 animate-spin" />
        ) : (
          <Phone className="h-7 w-7 sm:h-8 sm:w-8" fill="currentColor" />
        )}
      </button>

      {status !== "idle" ? (
        <div className="fixed bottom-28 right-6 z-40 w-[18rem] max-w-[calc(100vw-3rem)] rounded-2xl border border-roadcall-cyan/25 bg-roadcall-panel/95 p-4 shadow-2xl backdrop-blur-md">
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
            <p className="flex items-start gap-2 text-sm text-emerald-300">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              {message || "Calling Sandy now…"}
            </p>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
