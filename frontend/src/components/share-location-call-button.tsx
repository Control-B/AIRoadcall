"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Phone, PhoneOff } from "lucide-react";
import { RetellWebClient } from "retell-client-js-sdk";

import { createRoadsideRetellWebCall } from "@/lib/api-client";

type CallState = "idle" | "locating" | "connecting" | "connected" | "error";

function getErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === "string" && err.trim()) return err;
  if (err && typeof err === "object") {
    const maybeMessage = (err as { message?: unknown; error?: unknown; detail?: unknown }).message
      ?? (err as { message?: unknown; error?: unknown; detail?: unknown }).error
      ?? (err as { message?: unknown; error?: unknown; detail?: unknown }).detail;
    if (typeof maybeMessage === "string" && maybeMessage.trim()) return maybeMessage;
    try {
      return JSON.stringify(err);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

function statusLabel(state: CallState, error: string | null): string {
  if (state === "locating") return "Getting GPS";
  if (state === "connecting") return "Calling Sandy";
  if (state === "connected") return "Live with Sandy";
  if (state === "error") return error || "Call failed";
  return "Call Sandy";
}

export function ShareLocationCallButton({
  className = "",
  latitude,
  longitude,
  accuracyM,
  requireSharedLocation = false,
}: {
  className?: string;
  latitude?: number | null;
  longitude?: number | null;
  accuracyM?: number | null;
  requireSharedLocation?: boolean;
}) {
  const [state, setState] = useState<CallState>("idle");
  const [error, setError] = useState<string | null>(null);
  const clientRef = useRef<RetellWebClient | null>(null);

  useEffect(() => {
    return () => {
      try {
        clientRef.current?.stopCall();
      } catch {
        /* ignore */
      }
      clientRef.current = null;
    };
  }, []);

  async function endCall() {
    try {
      clientRef.current?.stopCall();
    } catch {
      /* ignore */
    }
    clientRef.current = null;
    setState("idle");
    setError(null);
  }

  async function startCall() {
    if (state === "connected") {
      await endCall();
      return;
    }
    if (state === "locating" || state === "connecting") return;

    if (!navigator.geolocation) {
      setError("GPS unavailable");
      setState("error");
      return;
    }

    try {
      setError(null);
      let coords: { latitude: number; longitude: number; accuracy_meters: number | null };

      if (typeof latitude === "number" && typeof longitude === "number" && Number.isFinite(latitude) && Number.isFinite(longitude)) {
        coords = {
          latitude,
          longitude,
          accuracy_meters: typeof accuracyM === "number" && Number.isFinite(accuracyM) ? accuracyM : null,
        };
      } else {
        if (requireSharedLocation) {
          setError("Map GPS not ready yet");
          setState("error");
          return;
        }
        if (!navigator.geolocation) {
          setError("GPS unavailable");
          setState("error");
          return;
        }
        setState("locating");
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 12000,
            maximumAge: 30000,
          });
        });
        coords = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_meters: position.coords.accuracy,
        };
      }

      setState("connecting");
      console.info("[Sandy] creating Retell web call", coords);
      const session = await createRoadsideRetellWebCall(coords);
      console.info("[Sandy] Retell web call created", { callId: session.call_id, agentId: session.agent_id });

      const client = new RetellWebClient();
      client.on("call_started", () => {
        setState("connected");
      });
      client.on("call_ended", () => {
        clientRef.current = null;
        setState("idle");
      });
      client.on("error", (err: unknown) => {
        console.warn("[Sandy] Retell client error", err);
        try {
          client.stopCall();
        } catch {
          /* ignore */
        }
        clientRef.current = null;
        setError(getErrorMessage(err, "Call error"));
        setState("error");
      });

      clientRef.current = client;
      console.info("[Sandy] starting Retell client call");
      await client.startCall({ accessToken: session.access_token });
      setState((prev) => (prev === "connecting" ? "connected" : prev));
    } catch (err) {
      console.error("[Sandy] call failed", err);
      try {
        clientRef.current?.stopCall();
      } catch {
        /* ignore */
      }
      clientRef.current = null;
      setError(getErrorMessage(err, "Unable to call Sandy"));
      setState("error");
    }
  }

  const isBusy = state === "locating" || state === "connecting";
  const isConnected = state === "connected";

  const label = statusLabel(state, error);
  const shortLabel =
    state === "locating" ? "GPS…" :
    state === "connecting" ? "Calling…" :
    state === "connected" ? "Live" :
    state === "error" ? "Retry" :
    "Sandy";

  return (
    <>
      <button
        type="button"
        onClick={startCall}
        disabled={isBusy}
        aria-label={isConnected ? "End Sandy call" : label}
        style={{ top: "calc(env(safe-area-inset-top, 0px) + 4.75rem)" }}
        className={`fixed right-3 z-[90] inline-flex h-11 items-center gap-1.5 rounded-full border px-3 text-[11px] font-black uppercase tracking-wide shadow-2xl shadow-black/50 backdrop-blur-md transition active:scale-95 disabled:cursor-wait disabled:opacity-70 ${
          isConnected
            ? "border-red-500/40 bg-[#06101f]/95 text-red-400 hover:bg-red-950/80"
            : state === "error"
            ? "border-yellow-500/40 bg-[#06101f]/95 text-yellow-400 hover:bg-yellow-950/80"
            : "border-emerald-500/30 bg-[#06101f]/95 text-emerald-400 hover:bg-emerald-950/60"
        } ${className}`}
      >
        {isConnected ? (
          <PhoneOff className="h-4 w-4 shrink-0" fill="currentColor" />
        ) : isBusy ? (
          <Mic className="h-4 w-4 shrink-0 animate-pulse" />
        ) : (
          <Phone className="h-4 w-4 shrink-0" fill="currentColor" />
        )}
        <span>{shortLabel}</span>
      </button>
      {state === "error" && error && (
        <div
          style={{ top: "calc(env(safe-area-inset-top, 0px) + 8.25rem)" }}
          className="fixed right-3 z-[90] max-w-[16rem] rounded-md border border-yellow-500/40 bg-[#06101f]/95 px-3 py-2 text-[11px] font-medium text-yellow-200 shadow-2xl shadow-black/50 backdrop-blur-md"
        >
          {error}
        </div>
      )}
    </>
  );
}
