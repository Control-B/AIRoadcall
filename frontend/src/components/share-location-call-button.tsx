"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Phone, PhoneOff } from "lucide-react";
import { Room, RoomEvent, createLocalAudioTrack } from "livekit-client";

import { createRoadsideLiveKitSession } from "@/lib/api-client";

type CallState = "idle" | "locating" | "connecting" | "connected" | "error";

function statusLabel(state: CallState, error: string | null): string {
  if (state === "locating") return "Getting GPS";
  if (state === "connecting") return "Calling Sandy";
  if (state === "connected") return "Live with Sandy";
  if (state === "error") return error || "Call failed";
  return "Call Sandy";
}

export function ShareLocationCallButton({ className = "" }: { className?: string }) {
  const [state, setState] = useState<CallState>("idle");
  const [error, setError] = useState<string | null>(null);
  const roomRef = useRef<Room | null>(null);

  useEffect(() => {
    return () => {
      roomRef.current?.disconnect();
    };
  }, []);

  async function endCall() {
    roomRef.current?.disconnect();
    roomRef.current = null;
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
      setState("locating");
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 12000,
          maximumAge: 30000,
        });
      });

      setState("connecting");
      const session = await createRoadsideLiveKitSession({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy_meters: position.coords.accuracy,
      });

      const room = new Room({ adaptiveStream: true, dynacast: true });
      room.on(RoomEvent.Disconnected, () => {
        roomRef.current = null;
        setState("idle");
      });
      await room.connect(session.livekit_url, session.participant_token);
      const audioTrack = await createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true });
      await room.localParticipant.publishTrack(audioTrack);
      roomRef.current = room;
      setState("connected");
    } catch (err) {
      roomRef.current?.disconnect();
      roomRef.current = null;
      setError(err instanceof Error ? err.message : "Unable to call Sandy");
      setState("error");
    }
  }

  const isBusy = state === "locating" || state === "connecting";
  const isConnected = state === "connected";

  return (
    <button
      type="button"
      onClick={startCall}
      disabled={isBusy}
      aria-label={isConnected ? "End Sandy call" : "Share GPS and call Sandy"}
      className={`fixed bottom-6 left-1/2 z-[90] flex h-12 min-w-12 -translate-x-1/2 items-center justify-center gap-2 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 px-4 text-sm font-semibold text-slate-950 shadow-2xl ring-2 ring-emerald-400/30 transition hover:scale-105 active:scale-95 disabled:cursor-wait disabled:opacity-80 sm:h-14 sm:min-w-14 ${className}`}
    >
      {isConnected ? (
        <PhoneOff className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" />
      ) : isBusy ? (
        <Mic className="h-5 w-5 animate-pulse sm:h-6 sm:w-6" />
      ) : (
        <Phone className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" />
      )}
      <span className="max-w-[10rem] truncate sm:max-w-none">{statusLabel(state, error)}</span>
    </button>
  );
}
