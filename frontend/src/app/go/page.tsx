"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Loader2,
  MapPin,
  RefreshCcw,
  Wrench,
} from "lucide-react";

import { GoResultsMap } from "@/components/maps/go-results-map";
import { getApiBase } from "@/lib/api-client";

const API_URL = getApiBase();

function normalizeCaseCode(raw: string): string {
  const value = raw.trim().toUpperCase();
  if (/[A-Z]/.test(value) && !value.startsWith("RC")) {
    return value.replace(/[^A-Z0-9]+/g, " ").replace(/\s+/g, " ").trim();
  }
  const cleaned = value.replace(/[^A-Z0-9]/g, "");
  if (!cleaned) return "";
  const withoutPrefix = cleaned.startsWith("RC") ? cleaned.slice(2) : cleaned;
  return withoutPrefix ? `RC-${withoutPrefix}` : "RC-";
}

function looksLikeCaseCode(raw: string): boolean {
  const normalized = normalizeCaseCode(raw);
  return /^RC-[A-Z0-9]{4,12}$/.test(normalized) || /^[A-Z]{3,12}(\s+[A-Z0-9]{3,12}){0,2}$/.test(normalized);
}

type DispatchSessionStatus = {
  dispatch_session_id: string;
  public_code: string;
  status: string;
  location_captured: boolean;
  city?: string | null;
  state?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  problem_type?: string | null;
  vehicle_type?: string | null;
  payment_status: string;
  match_status?: string | null;
  best_match?: {
    company_name?: string;
    city?: string;
    state?: string;
    distance_miles?: number | null;
    phone_available?: boolean;
    reason?: string;
  } | null;
  missing_fields: string[];
  say: string;
};

type Step = "intake" | "locating" | "matching" | "results" | "manual_fallback";

export default function GoPage() {
  const [step, setStep] = useState<Step>("intake");
  const [codeInput, setCodeInput] = useState("");
  const [problem, setProblem] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sessionResult, setSessionResult] = useState<DispatchSessionStatus | null>(null);
  const [dispatchToken, setDispatchToken] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [progressMsg, setProgressMsg] = useState("");

  const caseCode = useMemo(() => normalizeCaseCode(codeInput), [codeInput]);
  const caseCodeValid = looksLikeCaseCode(codeInput);
  const tokenMode = Boolean(dispatchToken);
  const canSubmitIntake = tokenMode || caseCodeValid;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("t");
    const code = params.get("code");
    if (token) {
      setDispatchToken(token);
      setProgressMsg("This secure Roadcall link will attach your GPS to the live dispatch session.");
    }
    if (code) {
      setCodeInput(code.trim().toUpperCase());
      setProgressMsg("This Roadcall code will attach your GPS to the live dispatch session.");
    }
  }, []);

  const linkCaseCode = useCallback(async () => {
    const res = await fetch(`${API_URL}/dispatch/link-case-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ public_code: caseCode }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body?.detail || "We could not find that Roadcall code. Ask Sandy to repeat the two words.");
    }
    setDispatchToken(body.location_token);
    setProgressMsg(`Case ${body.public_code} found. Share your GPS to attach it to the live call.`);
    return body.location_token as string;
  }, [caseCode]);

  const submitTokenLocation = useCallback(
    async (opts: { latitude: number; longitude: number; accuracy_m?: number }, tokenOverride?: string) => {
      const token = tokenOverride || dispatchToken;
      if (!token) return;
      setSubmitting(true);
      setError(null);
      setStep("matching");
      setProgressMsg("Sending your exact GPS location to Roadcall...");
      try {
        const res = await fetch(`${API_URL}/dispatch/update-location`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token,
            latitude: opts.latitude,
            longitude: opts.longitude,
            accuracy_m: opts.accuracy_m ?? null,
            source: "browser_gps",
            caller_name: name || null,
            problem_description: problem || null,
            vehicle_type: vehicleType || null,
          }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail || `Location update failed (${res.status})`);
        }
        const data: { session: DispatchSessionStatus } = await res.json();
        setSessionResult(data.session);
        setStep("results");
      } catch (err: any) {
        setError(err?.message || "We could not attach your GPS to this Roadcall session.");
        setStep("manual_fallback");
      } finally {
        setSubmitting(false);
      }
    },
    [dispatchToken, name, problem, vehicleType],
  );

  const requestGpsThenDispatch = useCallback(async () => {
    if (!canSubmitIntake) {
      setError("Enter the Roadcall word code Sandy gave you, or use the secure link from the dispatcher.");
      return;
    }

    let linkedToken: string | undefined;
    if (!tokenMode) {
      try {
        setSubmitting(true);
        linkedToken = await linkCaseCode();
      } catch (err: any) {
        setError(err?.message || "We could not find that Roadcall code. Ask Sandy to repeat the two words.");
        setSubmitting(false);
        return;
      } finally {
        setSubmitting(false);
      }
    }

    if (!("geolocation" in navigator)) {
      setError("This browser cannot share GPS. Stay on the line and tell Sandy your city, state, highway, exit, mile marker, or nearest landmark.");
      setStep("manual_fallback");
      return;
    }

    setError(null);
    setStep("locating");
    setProgressMsg("Getting your location... please tap Allow if your phone asks.");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        submitTokenLocation(
          {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy,
          },
          linkedToken,
        );
      },
      (geoErr) => {
        let msg = "GPS did not come through. Stay on the line and tell Sandy your city, state, highway, exit, mile marker, or nearest landmark.";
        if (geoErr.code === geoErr.PERMISSION_DENIED) {
          msg = "Location permission was blocked. Allow Location for roadcall.ai and tap Try GPS again, or tell Sandy your manual location.";
        } else if (geoErr.code === geoErr.TIMEOUT) {
          msg = "GPS timed out. Tap Try GPS again, or tell Sandy your city, highway, exit, mile marker, or nearest landmark.";
        }
        setError(msg);
        setStep("manual_fallback");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    );
  }, [canSubmitIntake, linkCaseCode, submitTokenLocation, tokenMode]);

  const handleSubmitForm = (event: FormEvent) => {
    event.preventDefault();
    requestGpsThenDispatch();
  };

  const reset = () => {
    setStep("intake");
    setSessionResult(null);
    setError(null);
    setProgressMsg("");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <header className="border-b border-slate-800/70 bg-slate-900/70 px-4 py-3">
        <div className="mx-auto flex max-w-md items-center justify-between">
          <Link href="/" className="text-sm font-semibold text-slate-200 hover:text-white">
            Roadcall
          </Link>
          <span className="text-xs uppercase tracking-widest text-emerald-400">Live Dispatch</span>
        </div>
      </header>

      <main className="mx-auto max-w-lg px-4 pb-20 pt-6">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-orange-500/20 ring-1 ring-orange-400/40">
            <MapPin className="h-7 w-7 text-orange-400" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Share your Roadcall location</h1>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Stay on the line with Sandy. This page only attaches your GPS to the live Roadcall dispatch session.
          </p>
        </div>

        {step === "intake" && (
          <form onSubmit={handleSubmitForm} className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-5 shadow-xl">
            {tokenMode ? (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-100">
                Secure Roadcall session link detected. You do not need to enter contact details.
              </div>
            ) : (
              <div>
                <label htmlFor="case-code" className="mb-1 block text-sm font-medium text-slate-200">
                  Roadcall word code <span className="text-orange-400">*</span>
                </label>
                <input
                  id="case-code"
                  type="text"
                  inputMode="text"
                  autoComplete="one-time-code"
                  value={codeInput.toUpperCase()}
                  onChange={(event) => setCodeInput(event.target.value)}
                  placeholder="BLUE ROAD"
                  className="h-14 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 text-center text-xl font-semibold tracking-wider text-white placeholder:text-slate-600 focus:border-orange-400 focus:outline-none"
                />
                <p className="mt-1 text-xs text-slate-400">
                  Enter the two words Sandy gave you. No phone number is needed here.
                </p>
                {caseCodeValid && (
                  <div className="mt-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-center text-xs text-emerald-100">
                    We will attach your GPS to case <span className="font-mono font-semibold">{caseCode}</span>.
                  </div>
                )}
              </div>
            )}

            <details className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-sm">
              <summary className="cursor-pointer text-slate-300">Optional details Sandy may already have</summary>
              <div className="mt-3 space-y-3">
                <input
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Your name"
                  className="h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 placeholder:text-slate-500 focus:border-orange-400 focus:outline-none"
                />
                <input
                  type="text"
                  value={problem}
                  onChange={(event) => setProblem(event.target.value)}
                  placeholder="Problem, if Sandy has not captured it"
                  className="h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 placeholder:text-slate-500 focus:border-orange-400 focus:outline-none"
                />
                <select
                  value={vehicleType}
                  onChange={(event) => setVehicleType(event.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 focus:border-orange-400 focus:outline-none"
                >
                  <option value="">Vehicle type, if needed</option>
                  <option value="car">Car / SUV / pickup</option>
                  <option value="box truck">Box truck / straight truck</option>
                  <option value="semi">Semi / tractor</option>
                  <option value="trailer">Trailer / reefer</option>
                  <option value="rv">RV / motorhome</option>
                </select>
              </div>
            </details>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!canSubmitIntake || submitting}
              className="flex h-14 w-full items-center justify-center gap-2 rounded-lg bg-orange-500 text-lg font-bold text-slate-950 shadow-lg transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <>Submit and share GPS <ArrowRight className="h-5 w-5" /></>}
            </button>

            <p className="text-center text-xs text-slate-500">
              Tapping submit asks your browser for GPS and sends it to the live Roadcall case only.
            </p>
          </form>
        )}

        {(step === "locating" || step === "matching") && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-8 text-center shadow-xl">
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-orange-400" />
            <h2 className="mt-4 text-xl font-semibold">{progressMsg}</h2>
            <p className="mt-2 text-sm text-slate-400">
              {step === "locating" ? "Some phones take a few seconds to fix GPS." : "Attaching your location to the Roadcall dispatch session."}
            </p>
          </div>
        )}

        {step === "manual_fallback" && (
          <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-5 shadow-xl">
            <div className="flex items-start gap-2 rounded-lg border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error || "GPS did not come through."}</span>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-sm leading-6 text-slate-300">
              Tell Sandy your city, state, highway, exit, mile marker, truck stop, or nearest landmark while you stay on the call.
            </div>
            <button
              type="button"
              onClick={requestGpsThenDispatch}
              disabled={submitting}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-lg border border-slate-700 text-sm text-slate-300 hover:border-orange-400 hover:text-orange-300 disabled:opacity-60"
            >
              <RefreshCcw className="h-4 w-4" /> Try GPS again
            </button>
            <button
              type="button"
              onClick={reset}
              className="h-10 w-full rounded-lg text-sm text-slate-500 hover:text-slate-300"
            >
              Enter code again
            </button>
          </div>
        )}

        {step === "results" && sessionResult && (
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
                <div>
                  <div className="font-semibold">Location attached to your live Roadcall case.</div>
                  <div className="text-emerald-200/90">
                    {[sessionResult.city, sessionResult.state].filter(Boolean).join(", ") || "GPS location received"}
                  </div>
                  <div className="mt-1 text-xs text-emerald-300/80">
                    Case: <span className="font-mono">{sessionResult.public_code}</span>
                  </div>
                </div>
              </div>
            </div>

            <GoResultsMap
              caller={{
                latitude: sessionResult.latitude,
                longitude: sessionResult.longitude,
                label: [sessionResult.city, sessionResult.state].filter(Boolean).join(", ") || "Roadcall GPS location",
              }}
            />

            {sessionResult.best_match ? (
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 shadow">
                <div className="text-xs uppercase tracking-wider text-orange-400">Best current match</div>
                <div className="mt-1 text-base font-semibold text-white">
                  {sessionResult.best_match.company_name}
                </div>
                <div className="mt-0.5 text-xs text-slate-400">
                  {[sessionResult.best_match.city, sessionResult.best_match.state].filter(Boolean).join(", ")}
                  {typeof sessionResult.best_match.distance_miles === "number"
                    ? ` - ${sessionResult.best_match.distance_miles.toFixed(1)} mi away`
                    : ""}
                </div>
                <p className="mt-3 text-sm text-slate-300">{sessionResult.say}</p>
              </div>
            ) : (
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-300">
                <Wrench className="mb-2 h-6 w-6 text-slate-500" />
                {sessionResult.say || "Roadcall has your location and is checking nearby providers."}
              </div>
            )}

            <p className="text-center text-xs text-slate-500">
              Stay on the phone with Sandy while dispatch confirms availability.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}