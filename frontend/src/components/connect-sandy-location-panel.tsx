"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, MapPin, Satellite, X } from "lucide-react";
import { shareLocationWithSandyCall } from "@/lib/api-client";

type SharedCoords = {
  latitude: number;
  longitude: number;
  accuracyM: number | null;
};

function normalizeCode(value: string) {
  const compact = value.trim().toUpperCase().replace(/\s+/g, "");
  if (compact.startsWith("ROAD-")) return `RC-${compact.slice(5)}`;
  if (compact.startsWith("RC") && !compact.startsWith("RC-")) return `RC-${compact.slice(2)}`;
  return compact;
}

function getBrowserPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("GPS is not available on this device."));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 15000,
    });
  });
}

function geolocationErrorMessage(error: unknown) {
  if (typeof error === "object" && error && "code" in error) {
    const code = Number((error as { code?: number }).code);
    if (code === 1) return "Location permission was denied.";
    if (code === 2) return "Your GPS location is unavailable right now.";
    if (code === 3) return "GPS took too long. Try again.";
  }
  return error instanceof Error ? error.message : "Unable to share location.";
}

export function ConnectSandyLocationPanel({ onShared }: { onShared?: (coords: SharedCoords) => void }) {
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function shareLocation() {
    const code = normalizeCode(token);
    if (code.length < 4) {
      setError("Enter the code Sandy gave you.");
      setSuccess(null);
      return;
    }

    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const position = await getBrowserPosition();
      const coords = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracyM: typeof position.coords.accuracy === "number" ? position.coords.accuracy : null,
      };
      const response = await shareLocationWithSandyCall({
        token: code,
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy: coords.accuracyM,
      });
      setToken(response.token);
      setSuccess(response.city && response.state ? `Location shared near ${response.city}, ${response.state}.` : response.message);
      onShared?.(coords);
    } catch (err) {
      setError(geolocationErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed right-3 top-[calc(env(safe-area-inset-top,0px)+8.75rem)] z-[88] inline-flex h-9 items-center gap-1.5 rounded-full border border-slate-950/10 bg-white/95 px-2.5 text-[10px] font-black uppercase tracking-wide text-slate-950 shadow-2xl shadow-black/20 backdrop-blur-md transition hover:bg-white sm:top-[calc(env(safe-area-inset-top,0px)+9.75rem)] sm:h-10 sm:px-3 sm:text-[11px]"
        aria-label="Connect website location to Sandy call"
      >
        <Satellite className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        Code
      </button>
    );
  }

  return (
    <div className="fixed right-3 top-[calc(env(safe-area-inset-top,0px)+8.75rem)] z-[88] w-[min(18rem,calc(100vw-1.5rem))] rounded-2xl border border-slate-950/10 bg-white/95 p-3 text-slate-950 shadow-2xl shadow-black/25 backdrop-blur-md sm:top-[calc(env(safe-area-inset-top,0px)+9.75rem)]">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.18em] text-cyan-700">Connect to Sandy</p>
          <p className="mt-1 text-xs font-semibold leading-snug text-slate-600">Enter the call code Sandy gives you, then share this device&apos;s GPS.</p>
        </div>
        <button type="button" onClick={() => setOpen(false)} className="rounded-full p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-950" aria-label="Close Sandy code panel">
          <X className="h-4 w-4" />
        </button>
      </div>

      <label className="block text-[11px] font-black uppercase tracking-wide text-slate-600">
        Call code
        <input
          value={token}
          onChange={(event) => setToken(event.target.value.toUpperCase())}
          placeholder="RC-7KQ2M"
          autoCapitalize="characters"
          className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-black uppercase tracking-wider text-slate-950 outline-none focus:border-cyan-500"
        />
      </label>

      <button
        type="button"
        onClick={shareLocation}
        disabled={busy}
        className="mt-2 inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-3 text-xs font-black text-white hover:bg-slate-800 disabled:cursor-wait disabled:opacity-70"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPin className="h-4 w-4" />}
        {busy ? "Sharing..." : "Share current location"}
      </button>

      {success ? (
        <p className="mt-2 flex items-start gap-1.5 rounded-xl bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {success}
        </p>
      ) : null}
      {error ? <p className="mt-2 rounded-xl bg-red-50 px-3 py-2 text-xs font-bold text-red-700">{error}</p> : null}
    </div>
  );
}
