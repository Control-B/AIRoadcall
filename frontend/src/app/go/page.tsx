"use client";

/**
 * roadcall.ai/go — website-first dispatch flow.
 *
 * Replaces SMS magic-link while carrier registration is pending.
 * Driver enters phone number or Roadcall case code, taps Submit, browser captures GPS,
 * backend reverse-geocodes via Mapbox and returns top 3 mechanics.
 */

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  MapPin,
  Phone,
  RefreshCcw,
  Wrench,
  AlertTriangle,
} from "lucide-react";
import { getApiBase } from "@/lib/api-client";
import { GoResultsMap } from "@/components/maps/go-results-map";

const API_URL = getApiBase();

// ───────── helpers ─────────
function formatPhonePretty(raw: string): string {
  const d = raw.replace(/\D/g, "").slice(0, 10);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}
function digitsOnly(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 10);
}
function normalizeCaseCode(raw: string): string {
  const cleaned = raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (!cleaned) return "";
  const withoutPrefix = cleaned.startsWith("RC") ? cleaned.slice(2) : cleaned;
  return withoutPrefix ? `RC-${withoutPrefix}` : "RC-";
}
function telHrefFor(raw?: string | null): string {
  if (!raw) return "#";
  const d = raw.replace(/[^\d+]/g, "");
  if (d.startsWith("+")) return `tel:${d}`;
  if (d.length === 10) return `tel:+1${d}`;
  if (d.length === 11 && d.startsWith("1")) return `tel:+${d}`;
  return `tel:${d}`;
}

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY",
];

// ───────── types ─────────
type Mechanic = {
  mechanicId: string;
  businessName: string;
  phone: string;
  city?: string;
  state?: string;
  address?: string;
  latitude?: number | null;
  longitude?: number | null;
  distanceMiles?: number | null;
  reason?: string;
  mobileService?: boolean;
  emergencyService?: boolean;
};

type MajorVendor = {
  vendorId: string;
  brandName: string;
  locationName?: string;
  phone?: string;
  city?: string;
  state?: string;
  interstate?: string;
  exitNumber?: string;
  distanceMiles?: number | null;
};

type DispatchResponse = {
  work_order_id: string;
  status: string;
  location: {
    latitude?: number;
    longitude?: number;
    city?: string;
    state?: string;
    address?: string;
    place_name?: string;
    accuracy_m?: number;
    source: string;
  };
  match: {
    status: string;
    matches: Mechanic[];
    majorVendor?: MajorVendor | null;
    message?: string;
    needsMoreInfo?: boolean;
    missingFields?: string[];
  };
};

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

// ───────── component ─────────
export default function GoPage() {
  const [step, setStep] = useState<Step>("intake");
  const [phone, setPhone] = useState("");
  const [problem, setProblem] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [name, setName] = useState("");
  const [manualCity, setManualCity] = useState("");
  const [manualState, setManualState] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DispatchResponse | null>(null);
  const [sessionResult, setSessionResult] = useState<DispatchSessionStatus | null>(null);
  const [dispatchToken, setDispatchToken] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [progressMsg, setProgressMsg] = useState<string>("");
  const pollRef = useRef<number | null>(null);

  const phoneDigits = useMemo(() => digitsOnly(phone), [phone]);
  const caseCode = useMemo(() => normalizeCaseCode(phone), [phone]);
  const phoneValid = phoneDigits.length === 10;
  const caseCodeValid = /^RC-[A-Z0-9]{4,12}$/.test(caseCode);
  const tokenMode = Boolean(dispatchToken);
  const caseCodeMode = !tokenMode && caseCodeValid;
  const canSubmitIntake = tokenMode || phoneValid || caseCodeValid;

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("t");
    if (token) {
      setDispatchToken(token);
      setProgressMsg("This secure Roadcall link will attach your GPS to the live call.");
    }
  }, []);

  const submitTokenLocation = useCallback(
    async (opts: { latitude: number; longitude: number; accuracy_m?: number }, tokenOverride?: string) => {
      const token = tokenOverride || dispatchToken;
      if (!token) return;
      setSubmitting(true);
      setError(null);
      setStep("matching");
      setProgressMsg("Sending your exact GPS location to Roadcall…");
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
        setResult(null);
        setStep("results");
      } catch (err: any) {
        setError(err?.message || "We could not attach your GPS to this Roadcall session.");
        setStep("manual_fallback");
      } finally {
        setSubmitting(false);
      }
    },
    [dispatchToken, problem, vehicleType],
  );

  const linkCaseCode = useCallback(async () => {
    const res = await fetch(`${API_URL}/dispatch/link-case-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ public_code: caseCode }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body?.detail || "We could not find that Roadcall case code.");
    }
    setDispatchToken(body.location_token);
    setProgressMsg(`Case ${body.public_code} found. Share your GPS to attach it to the live call.`);
    return body.location_token as string;
  }, [caseCode]);

  const submitDispatch = useCallback(
    async (opts: {
      latitude?: number;
      longitude?: number;
      accuracy_m?: number;
      city?: string;
      state?: string;
    }) => {
      setSubmitting(true);
      setError(null);
      setStep("matching");
      setProgressMsg("Finding the closest mechanic to you…");
      try {
        const res = await fetch(`${API_URL}/go/dispatch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            phone: phoneDigits,
            latitude: opts.latitude ?? null,
            longitude: opts.longitude ?? null,
            accuracy_m: opts.accuracy_m ?? null,
            city: opts.city ?? null,
            state: opts.state ?? null,
            problem: problem || null,
            vehicle_type: vehicleType || null,
            name: name || null,
          }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail || `Dispatch failed (${res.status})`);
        }
        const data: DispatchResponse = await res.json();
        setResult(data);
        if (data.match.needsMoreInfo) {
          setStep("manual_fallback");
        } else {
          setStep("results");
        }
      } catch (err: any) {
        setError(err?.message || "Something went wrong. Please try again.");
        setStep("intake");
      } finally {
        setSubmitting(false);
      }
    },
    [phoneDigits, problem, vehicleType, name],
  );

  const requestGpsThenDispatch = useCallback(async () => {
    if (!canSubmitIntake) {
      setError("Enter the phone number from your call or the Roadcall code the agent gave you.");
      return;
    }
    let linkedToken: string | undefined;
    if (caseCodeMode) {
      try {
        setSubmitting(true);
        linkedToken = await linkCaseCode();
      } catch (err: any) {
        setError(err?.message || "We could not find that Roadcall case code.");
        setSubmitting(false);
        return;
      } finally {
        setSubmitting(false);
      }
    }
    if (!("geolocation" in navigator)) {
      setStep("manual_fallback");
      setError("Your browser can’t share GPS here. Enter your city and state and we’ll still find help.");
      return;
    }
    setError(null);
    setStep("locating");
    setProgressMsg("Getting your location… please tap “Allow” if your phone asks.");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
        };
        if (tokenMode || linkedToken) {
          submitTokenLocation(coords, linkedToken);
        } else {
          submitDispatch(coords);
        }
      },
      (geoErr) => {
        // Permission denied / timeout → fallback
        let msg = "GPS didn’t come through. Enter your city and state and we’ll still find help.";
        if (geoErr.code === geoErr.PERMISSION_DENIED) {
          msg = "Location permission was blocked. You can enter city/state below, or allow Location in your browser and tap Try GPS again.";
        } else if (geoErr.code === geoErr.TIMEOUT) {
          msg = "GPS timed out. Enter city/state below, or tap Try GPS again if you’re outside or have better signal.";
        }
        setError(msg);
        setStep("manual_fallback");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    );
  }, [canSubmitIntake, caseCodeMode, linkCaseCode, submitDispatch, submitTokenLocation, tokenMode]);

  const handleSubmitForm = (e: FormEvent) => {
    e.preventDefault();
    requestGpsThenDispatch();
  };

  const handleManualSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (tokenMode || caseCodeMode) {
      setError("This secure call link needs GPS. If GPS will not work, tell the Roadcall dispatcher your city, state, highway, exit, or nearest landmark while staying on the call.");
      return;
    }
    if (!manualCity.trim() || !manualState) {
      setError("City and state are required.");
      return;
    }
    submitDispatch({ city: manualCity.trim(), state: manualState });
  };

  // Light polling while results are visible — picks up dispatch state changes
  useEffect(() => {
    if (step !== "results" || !result?.work_order_id) return;
    const id = window.setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/go/status/${result.work_order_id}`);
        if (res.ok) {
          const data: DispatchResponse = await res.json();
          setResult(data);
        }
      } catch {
        /* swallow polling errors */
      }
    }, 15000);
    pollRef.current = id;
    return () => {
      window.clearInterval(id);
      pollRef.current = null;
    };
  }, [step, result?.work_order_id]);

  const reset = () => {
    setStep("intake");
    setResult(null);
    setSessionResult(null);
    setError(null);
    setProgressMsg("");
  };

  // ───────── render ─────────
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <header className="border-b border-slate-800/70 bg-slate-900/70 px-4 py-3">
        <div className="mx-auto flex max-w-md items-center justify-between">
          <Link href="/" className="text-sm font-semibold text-slate-200 hover:text-white">
            ← Roadcall
          </Link>
          <span className="text-xs uppercase tracking-widest text-emerald-400">
            Live Dispatch
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-lg px-4 pb-20 pt-6">
        {/* Hero */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-orange-500/20 ring-1 ring-orange-400/40">
            <MapPin className="h-7 w-7 text-orange-400" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">I need help now</h1>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {tokenMode
              ? "Tap submit and share your GPS. This links your exact location to the live Roadcall dispatch session."
              : "Enter your phone number and tap submit. We'll find the closest mechanic to your exact GPS location and call them for you."}
          </p>
        </div>

        {/* INTAKE */}
        {step === "intake" && (
          <form
            onSubmit={handleSubmitForm}
            className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl"
          >
            {tokenMode ? (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-100">
                Secure Roadcall session link detected. You do not need to enter your phone number here.
              </div>
            ) : (
            <div>
              <label htmlFor="phone" className="mb-1 block text-sm font-medium text-slate-200">
                Phone number or Roadcall code <span className="text-orange-400">*</span>
              </label>
              <input
                id="phone"
                type="text"
                inputMode="text"
                autoComplete="one-time-code"
                value={caseCodeValid || phone.toUpperCase().startsWith("RC") ? phone.toUpperCase() : formatPhonePretty(phone)}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="(555) 123-4567 or RC-12345"
                className="h-14 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 text-center text-xl font-semibold tracking-wider text-white placeholder:text-slate-600 focus:border-orange-400 focus:outline-none"
              />
              <p className="mt-1 text-xs text-slate-400">
                If you are on the phone with Roadcall AI, enter the code the agent gave you. Otherwise enter the phone number from your call.
              </p>
              {caseCodeValid && (
                <div className="mt-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-center text-xs text-emerald-100">
                  We&apos;ll attach your GPS to case <span className="font-mono font-semibold">{caseCode}</span>.
                </div>
              )}
            </div>
            )}

            <details className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-sm">
              <summary className="cursor-pointer text-slate-300">Optional — helps us match faster</summary>
              <div className="mt-3 space-y-3">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  className="h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 placeholder:text-slate-500 focus:border-orange-400 focus:outline-none"
                />
                <input
                  type="text"
                  value={problem}
                  onChange={(e) => setProblem(e.target.value)}
                  placeholder="What's wrong? (tire, battery, fuel, towing…)"
                  className="h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 placeholder:text-slate-500 focus:border-orange-400 focus:outline-none"
                />
                <select
                  value={vehicleType}
                  onChange={(e) => setVehicleType(e.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 focus:border-orange-400 focus:outline-none"
                >
                  <option value="">Vehicle type…</option>
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
              className="flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-orange-500 text-lg font-bold text-slate-950 shadow-lg transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {submitting ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  Submit & share my location
                  <ArrowRight className="h-5 w-5" />
                </>
              )}
            </button>

            <p className="text-center text-xs text-slate-500">
              Tapping submit asks your browser for your GPS location.
            </p>
          </form>
        )}

        {/* LOCATING / MATCHING */}
        {(step === "locating" || step === "matching") && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8 text-center shadow-xl">
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-orange-400" />
            <h2 className="mt-4 text-xl font-semibold">{progressMsg}</h2>
            <p className="mt-2 text-sm text-slate-400">
              {step === "locating"
                ? "Some phones take a few seconds to fix GPS — hang tight."
                : "Searching 35,000+ mechanics across the US."}
            </p>
          </div>
        )}

        {/* MANUAL FALLBACK */}
        {step === "manual_fallback" && (
          <form
            onSubmit={handleManualSubmit}
            className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl"
          >
            <div className="flex items-start gap-2 rounded-lg border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error || "GPS didn’t come through — enter city/state and we’ll still find help."}</span>
            </div>
            <p className="text-xs leading-5 text-slate-400">
              This keeps your work order moving even if your browser blocks location. If you prefer GPS, allow Location for roadcall.ai and tap Try GPS again.
            </p>
            <input
              type="text"
              value={manualCity}
              onChange={(e) => setManualCity(e.target.value)}
              placeholder="City"
              className="h-12 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 placeholder:text-slate-500 focus:border-orange-400 focus:outline-none"
            />
            <select
              value={manualState}
              onChange={(e) => setManualState(e.target.value)}
              className="h-12 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 focus:border-orange-400 focus:outline-none"
            >
              <option value="">State…</option>
              {US_STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={submitting}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-orange-500 text-base font-bold text-slate-950 hover:bg-orange-400 disabled:bg-slate-700 disabled:text-slate-400"
            >
              {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : "Find mechanics"}
            </button>
            <button
              type="button"
              onClick={requestGpsThenDispatch}
              className="flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-slate-700 text-sm text-slate-300 hover:border-orange-400 hover:text-orange-300"
            >
              <RefreshCcw className="h-4 w-4" /> Try GPS again
            </button>
          </form>
        )}

        {/* RESULTS */}
        {step === "results" && sessionResult && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
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
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow">
                <div className="text-xs uppercase tracking-wider text-orange-400">Best current match</div>
                <div className="mt-1 text-base font-semibold text-white">
                  {sessionResult.best_match.company_name}
                </div>
                <div className="mt-0.5 text-xs text-slate-400">
                  {[sessionResult.best_match.city, sessionResult.best_match.state].filter(Boolean).join(", ")}
                  {typeof sessionResult.best_match.distance_miles === "number"
                    ? ` · ${sessionResult.best_match.distance_miles.toFixed(1)} mi away`
                    : ""}
                </div>
                <p className="mt-3 text-sm text-slate-300">{sessionResult.say}</p>
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-300">
                <Wrench className="mb-2 h-6 w-6 text-slate-500" />
                {sessionResult.say || "Roadcall has your location and is checking nearby providers."}
              </div>
            )}

            <p className="text-center text-xs text-slate-500">
              Stay on the phone with Roadcall while dispatch confirms availability.
            </p>
          </div>
        )}

        {step === "results" && result && !sessionResult && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
                <div>
                  <div className="font-semibold">Got your location.</div>
                  <div className="text-emerald-200/90">
                    {result.location.place_name ||
                      [result.location.city, result.location.state].filter(Boolean).join(", ") ||
                      "Location received"}
                  </div>
                  <div className="mt-1 text-xs text-emerald-300/80">
                    Work order: <span className="font-mono">{result.work_order_id}</span>
                    {result.location.accuracy_m
                      ? ` · GPS ±${Math.round(result.location.accuracy_m)} m`
                      : ""}
                  </div>
                </div>
              </div>
            </div>

            <GoResultsMap
              caller={{
                latitude: result.location.latitude,
                longitude: result.location.longitude,
                label:
                  result.location.place_name ||
                  [result.location.city, result.location.state].filter(Boolean).join(", ") ||
                  "Your GPS location",
              }}
              mechanics={result.match.matches}
            />

            {result.match.matches.length > 0 ? (
              <div className="space-y-3">
                <h2 className="text-lg font-semibold text-slate-100">
                  Closest mechanics
                </h2>
                {result.match.matches.map((m, i) => (
                  <div
                    key={m.mechanicId}
                    className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="text-xs uppercase tracking-wider text-orange-400">
                          Option {i + 1}
                        </div>
                        <div className="mt-1 text-base font-semibold text-white">
                          {m.businessName}
                        </div>
                        <div className="mt-0.5 text-xs text-slate-400">
                          {[m.city, m.state].filter(Boolean).join(", ")}
                          {typeof m.distanceMiles === "number"
                            ? ` · ${m.distanceMiles.toFixed(1)} mi away`
                            : ""}
                        </div>
                        {m.reason && (
                          <div className="mt-1 text-xs text-slate-500">{m.reason}</div>
                        )}
                      </div>
                      <a
                        href={telHrefFor(m.phone)}
                        className="flex h-12 shrink-0 items-center gap-2 rounded-xl bg-emerald-500 px-4 text-sm font-bold text-slate-950 hover:bg-emerald-400"
                      >
                        <Phone className="h-4 w-4" /> Call
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-center text-sm text-slate-300">
                <Wrench className="mx-auto mb-2 h-6 w-6 text-slate-500" />
                No local mechanics matched in our directory yet — but we have a major-vendor option below.
              </div>
            )}

            {result.match.majorVendor && (
              <div className="rounded-2xl border border-blue-500/40 bg-blue-500/10 p-4">
                <div className="text-xs uppercase tracking-wider text-blue-300">
                  National vendor
                </div>
                <div className="mt-1 text-base font-semibold text-white">
                  {result.match.majorVendor.brandName}
                  {result.match.majorVendor.locationName ? ` · ${result.match.majorVendor.locationName}` : ""}
                </div>
                <div className="mt-0.5 text-xs text-blue-200/90">
                  {[result.match.majorVendor.city, result.match.majorVendor.state]
                    .filter(Boolean)
                    .join(", ")}
                  {result.match.majorVendor.interstate
                    ? ` · ${result.match.majorVendor.interstate}${
                        result.match.majorVendor.exitNumber
                          ? ` exit ${result.match.majorVendor.exitNumber}`
                          : ""
                      }`
                    : ""}
                </div>
                {result.match.majorVendor.phone && (
                  <a
                    href={telHrefFor(result.match.majorVendor.phone)}
                    className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-blue-500 text-sm font-bold text-slate-950 hover:bg-blue-400"
                  >
                    <Phone className="h-4 w-4" /> Call {result.match.majorVendor.brandName}
                  </a>
                )}
              </div>
            )}

            <button
              onClick={reset}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-slate-700 text-sm text-slate-300 hover:border-orange-400 hover:text-orange-300"
            >
              <RefreshCcw className="h-4 w-4" /> Start over
            </button>

            <p className="text-center text-xs text-slate-500">
              If no one answers, call our dispatcher: {" "}
              <a href="tel:+18889999999" className="text-orange-400 hover:underline">
                Roadcall AI dispatch
              </a>
            </p>
          </div>
        )}

        {/* Existing case-code lookup link */}
        <div className="mt-10 text-center text-xs text-slate-500">
          Have a case code from the dispatcher?{" "}
          <Link href="/go/lookup" className="text-orange-400 hover:underline">
            Look it up
          </Link>
        </div>
      </main>
    </div>
  );
}
