"use client";

import { useCallback, useState } from "react";
import { Loader2, MapPin, Phone, CheckCircle2, AlertCircle } from "lucide-react";

import { getApiBase } from "@/lib/api-client";
import { HELP_PHONE, telHref } from "@/lib/phone";

type Step = "idle" | "phone" | "locating" | "submitting" | "ready" | "error";

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
  const [step, setStep] = useState<Step>("idle");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirmedAddress, setConfirmedAddress] = useState<string | null>(null);

  const reset = useCallback(() => {
    setStep("idle");
    setError(null);
    setConfirmedAddress(null);
  }, []);

  const submit = useCallback(async () => {
    const digits = digitsOnly(phone);
    if (digits.length < 10) {
      setError("Enter a 10-digit phone number so Sandy knows who's calling.");
      return;
    }
    setError(null);

    if (!navigator.geolocation) {
      setError("Your browser blocked location access. Try a different browser.");
      return;
    }

    setStep("locating");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setStep("submitting");
        try {
          const res = await fetch(`${getApiBase()}/caller/share-location`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              phone: digits,
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
              accuracy: pos.coords.accuracy ?? null,
            }),
          });
          if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body?.detail || `Could not share location (${res.status})`);
          }
          const data = await res.json();
          const where = data?.address || [data?.city, data?.state].filter(Boolean).join(", ");
          setConfirmedAddress(where || null);
          setStep("ready");
        } catch (err: any) {
          setError(err?.message || "Could not send your location to Sandy.");
          setStep("error");
        }
      },
      (geoErr) => {
        setError(
          geoErr.code === geoErr.PERMISSION_DENIED
            ? "Location permission was denied. Please allow location and try again."
            : "Could not read your GPS. Try moving to an area with better signal."
        );
        setStep("error");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  }, [phone]);

  if (step === "idle") {
    return (
      <button
        type="button"
        onClick={() => setStep("phone")}
        className={`inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-roadcall-orange to-amber-400 px-4 py-3 text-sm font-bold text-slate-950 shadow-lg hover:brightness-110 ${className}`}
      >
        <MapPin className="h-4 w-4" />
        Share location & call Sandy
      </button>
    );
  }

  return (
    <div
      className={`rounded-xl border border-roadcall-cyan/25 bg-roadcall-panel/80 p-4 shadow-2xl backdrop-blur-md ${className}`}
    >
      {step === "phone" || step === "error" ? (
        <>
          <p className="mb-2 text-sm font-semibold text-white">
            Sandy will pick up with your location already loaded.
          </p>
          <p className="mb-3 text-xs text-roadcall-muted">
            Enter the phone number you'll call from so Sandy can match the GPS to your call.
          </p>
          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-roadcall-muted">
            Your phone
            <input
              type="tel"
              autoComplete="tel"
              inputMode="numeric"
              placeholder="(555) 123-4567"
              value={formatPhone(phone)}
              onChange={(e) => setPhone(e.target.value)}
              className="rounded-lg border border-roadcall-cyan/20 bg-[#06101f]/90 px-3 py-2 text-sm font-normal text-white placeholder:text-roadcall-muted/60 focus:border-roadcall-cyan/60 focus:outline-none"
            />
          </label>
          {error ? (
            <p className="mt-2 flex items-start gap-1.5 text-xs text-red-400">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {error}
            </p>
          ) : null}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={submit}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-roadcall-orange to-amber-400 px-3 py-2 text-sm font-bold text-slate-950 hover:brightness-110"
            >
              <MapPin className="h-4 w-4" />
              Share GPS
            </button>
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-roadcall-cyan/15 px-3 py-2 text-xs font-semibold text-roadcall-silver hover:text-white"
            >
              Cancel
            </button>
          </div>
        </>
      ) : null}

      {step === "locating" || step === "submitting" ? (
        <p className="flex items-center gap-2 text-sm text-roadcall-silver">
          <Loader2 className="h-4 w-4 animate-spin text-roadcall-cyan" />
          {step === "locating" ? "Reading GPS…" : "Sending to Sandy…"}
        </p>
      ) : null}

      {step === "ready" ? (
        <>
          <p className="mb-2 flex items-start gap-2 text-sm font-semibold text-emerald-300">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            Location ready for Sandy.
          </p>
          {confirmedAddress ? (
            <p className="mb-3 text-xs text-roadcall-muted">{confirmedAddress}</p>
          ) : null}
          <p className="mb-3 text-xs text-roadcall-muted">
            Tap below to call from <span className="font-semibold text-white">{formatPhone(phone)}</span>. Sandy will already have your GPS.
          </p>
          <a
            href={telHref(HELP_PHONE)}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-400 to-cyan-400 px-3 py-2.5 text-sm font-bold text-slate-950 hover:brightness-110"
          >
            <Phone className="h-4 w-4" />
            Call {HELP_PHONE}
          </a>
          <button
            type="button"
            onClick={reset}
            className="mt-2 w-full text-xs text-roadcall-muted hover:text-white"
          >
            Use a different number
          </button>
        </>
      ) : null}
    </div>
  );
}
