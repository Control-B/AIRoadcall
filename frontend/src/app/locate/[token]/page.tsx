"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { MapPin, Shield, CheckCircle2, XCircle, Loader2, AlertTriangle } from "lucide-react";

type State =
  | "idle"
  | "requesting"
  | "submitting"
  | "success"
  | "denied"
  | "unsupported"
  | "timeout"
  | "expired"
  | "error";

export default function LocatePage() {
  const params = useParams();
  const token = params?.token as string;

  const [state, setState] = useState<State>("idle");
  const [errMsg, setErrMsg] = useState("");

  // Sanity check: if no token, show error immediately
  useEffect(() => {
    if (!token) setState("error");
  }, [token]);

  const handleShare = () => {
    if (!navigator.geolocation) {
      setState("unsupported");
      return;
    }

    setState("requesting");

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setState("submitting");
        const { latitude, longitude, accuracy } = pos.coords;
        try {
          const res = await fetch("/api/fleet/location/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              token,
              lat: latitude,
              lng: longitude,
              accuracy_meters: accuracy ?? null,
            }),
          });

          if (res.status === 410) {
            setState("expired");
            return;
          }
          if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            setErrMsg(data?.detail || "Unable to save location.");
            setState("error");
            return;
          }
          setState("success");
        } catch {
          setErrMsg("Network error. Please try again.");
          setState("error");
        }
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) setState("denied");
        else if (err.code === err.TIMEOUT) setState("timeout");
        else setState("error");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-800 via-blue-900 to-slate-900 flex items-center justify-center px-4 py-16">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
        {/* Brand */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <MapPin className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-gray-900 text-lg">Roadcall Fleet</span>
        </div>

        {/* States */}
        {state === "idle" && (
          <>
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <MapPin className="w-8 h-8 text-blue-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">Share your location</h1>
            <p className="text-gray-600 mb-2 leading-relaxed">
              Your dispatcher needs your GPS location to find the nearest roadside mechanic.
            </p>
            <p className="text-gray-500 text-sm mb-8 flex items-center justify-center gap-1">
              <Shield className="w-4 h-4 text-blue-500" />
              One-time share. Your location is not tracked continuously.
            </p>
            <button
              onClick={handleShare}
              className="w-full bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white font-semibold py-4 rounded-xl hover:brightness-110 transition-colors text-lg flex items-center justify-center gap-2"
            >
              <MapPin className="w-5 h-5" /> Share My Location
            </button>
            <p className="text-xs text-gray-400 mt-4">
              Your browser will ask for permission. Tap &quot;Allow&quot; to share.
            </p>
          </>
        )}

        {(state === "requesting" || state === "submitting") && (
          <>
            <Loader2 className="w-14 h-14 text-blue-600 animate-spin mx-auto mb-6" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {state === "requesting" ? "Getting your location…" : "Sending to dispatcher…"}
            </h2>
            <p className="text-gray-500 text-sm">
              {state === "requesting"
                ? "Allow location access in your browser when prompted."
                : "Almost done."}
            </p>
          </>
        )}

        {state === "success" && (
          <>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Location shared!</h2>
            <p className="text-gray-600">
              Your dispatcher has your location and is finding the nearest help. Stay with your vehicle.
            </p>
            <p className="text-sm text-gray-400 mt-6">You can close this page.</p>
          </>
        )}

        {state === "denied" && (
          <>
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-3">Location permission denied</h2>
            <p className="text-gray-600 mb-6">
              Please allow location access in your browser settings and try again, or call your dispatcher directly.
            </p>
            <button
              onClick={() => setState("idle")}
              className="w-full border border-blue-600 text-blue-600 font-semibold py-3 rounded-xl hover:bg-blue-50 transition-colors"
            >
              Try Again
            </button>
          </>
        )}

        {state === "timeout" && (
          <>
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-3">Location timed out</h2>
            <p className="text-gray-600 mb-6">
              We couldn't get a GPS fix in time. Make sure you're not in a tunnel or underground, then try again.
            </p>
            <button
              onClick={() => setState("idle")}
              className="w-full border border-blue-600 text-blue-600 font-semibold py-3 rounded-xl hover:bg-blue-50 transition-colors"
            >
              Try Again
            </button>
          </>
        )}

        {state === "expired" && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-3">Link expired</h2>
            <p className="text-gray-600">
              This location link has expired. Ask your dispatcher to send a new one, or call them directly.
            </p>
          </>
        )}

        {state === "unsupported" && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-3">GPS not supported</h2>
            <p className="text-gray-600">
              Your browser or device doesn't support location sharing. Try opening this link in Chrome or Safari,
              or call your dispatcher to give your location verbally.
            </p>
          </>
        )}

        {state === "error" && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-3">Something went wrong</h2>
            <p className="text-gray-600 mb-4">{errMsg || "Please try again or call your dispatcher."}</p>
            {errMsg && (
              <button
                onClick={() => { setState("idle"); setErrMsg(""); }}
                className="w-full border border-blue-600 text-blue-600 font-semibold py-3 rounded-xl hover:bg-blue-50 transition-colors"
              >
                Try Again
              </button>
            )}
          </>
        )}
      </div>
    </main>
  );
}
