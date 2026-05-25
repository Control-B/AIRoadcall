"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Phone, PhoneOff } from "lucide-react";
import { Room, RoomEvent, Track, createLocalAudioTrack } from "livekit-client";

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

  function detachSandyAudio() {
    document.querySelectorAll<HTMLAudioElement>("audio[data-lk-sandy]").forEach((el) => {
      el.pause();
      el.srcObject = null;
      el.remove();
    });
  }

  useEffect(() => {
    return () => {
      roomRef.current?.disconnect();
      detachSandyAudio();
    };
  }, []);

  async function endCall() {
    roomRef.current?.disconnect();
    roomRef.current = null;
    detachSandyAudio();
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

      // Play Sandy's audio when she joins and starts speaking
      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach() as HTMLAudioElement;
          el.dataset.lkSandy = "true";
          el.autoplay = true;
          document.body.appendChild(el);
        }
      });
      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach();
      });
      room.on(RoomEvent.Disconnected, () => {
        detachSandyAudio();
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
      detachSandyAudio();
      setError(err instanceof Error ? err.message : "Unable to call Sandy");
      setState("error");
    }
  }

  const isBusy = state === "locating" || state === "connecting";
  const isConnected = state === "connected";

  const label = statusLabel(state, error);
  // Compact label: shorten long states for the small button
  const shortLabel =
    state === "locating" ? "GPS…" :
    state === "connecting" ? "Calling…" :
    state === "connected" ? "Live" :
    state === "error" ? "Retry" :
    "Sandy";

  return (
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
  );
}
