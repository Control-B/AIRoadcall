"use client";

import { useEffect, useRef, useState } from "react";
import { BadgeCheck, Mic2, Play, Square, Upload } from "lucide-react";

type VoiceSampleSource = "recorded" | "uploaded" | null;

export type VoiceCloneSample = {
  enabled: boolean;
  cloneName: string;
  sampleName: string;
  sampleSource: Exclude<VoiceSampleSource, null>;
};

type VoiceCloneControlsProps = {
  title?: string;
  description?: string;
  initialName?: string;
  enabled?: boolean;
  className?: string;
  onEnabledChange?: (enabled: boolean) => void;
  onSave?: (sample: VoiceCloneSample) => void;
  onError?: (message: string) => void;
  onMessage?: (message: string) => void;
};

export function VoiceCloneControls({
  title = "Voice cloning",
  description = "Record through this computer or upload an existing voice sample.",
  initialName = "Owner voice",
  enabled: controlledEnabled,
  className = "",
  onEnabledChange,
  onSave,
  onError,
  onMessage,
}: VoiceCloneControlsProps) {
  const [internalEnabled, setInternalEnabled] = useState(Boolean(controlledEnabled));
  const [cloneName, setCloneName] = useState(initialName);
  const [sampleName, setSampleName] = useState("");
  const [sampleSource, setSampleSource] = useState<VoiceSampleSource>(null);
  const [sampleUrl, setSampleUrl] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<BlobPart[]>([]);
  const sampleUrlRef = useRef<string | null>(null);

  const enabled = controlledEnabled ?? internalEnabled;

  useEffect(() => {
    setCloneName(initialName);
  }, [initialName]);

  useEffect(() => {
    return () => {
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());
      if (sampleUrlRef.current) URL.revokeObjectURL(sampleUrlRef.current);
    };
  }, []);

  function setEnabled(next: boolean) {
    if (controlledEnabled === undefined) setInternalEnabled(next);
    onEnabledChange?.(next);
  }

  function setVoiceSample(next: { name: string; source: Exclude<VoiceSampleSource, null>; url: string }) {
    if (sampleUrlRef.current) URL.revokeObjectURL(sampleUrlRef.current);
    sampleUrlRef.current = next.url;
    setSampleUrl(next.url);
    setSampleName(next.name);
    setSampleSource(next.source);
    setEnabled(true);
  }

  async function startVoiceRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      onError?.("This browser cannot record audio here. Upload an audio sample instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(recordedChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (!blob.size) {
          onError?.("No audio was captured. Try recording again or upload a sample.");
          return;
        }
        const url = URL.createObjectURL(blob);
        const extension = recorder.mimeType.includes("mp4") ? "m4a" : "webm";
        setVoiceSample({ name: `Recorded voice sample.${extension}`, source: "recorded", url });
        onMessage?.("Voice sample recorded. Listen back, then save the clone when it sounds right.");
      };
      recorder.start();
      setRecording(true);
      onMessage?.("Recording voice sample. Speak naturally, then stop recording.");
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Microphone access was blocked. Upload an audio sample instead.");
    }
  }

  function stopVoiceRecording() {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    setRecording(false);
  }

  function handleVoiceUpload(file?: File) {
    if (!file) return;
    if (!file.type.startsWith("audio/")) {
      onError?.("Upload an audio file such as MP3, WAV, M4A, or WEBM.");
      return;
    }
    const url = URL.createObjectURL(file);
    setVoiceSample({ name: file.name, source: "uploaded", url });
    onMessage?.("Voice sample uploaded. Listen back, then save the clone when it sounds right.");
  }

  function saveVoiceClone() {
    if (!sampleName || !sampleSource) {
      onError?.("Record or upload a voice sample before saving the clone.");
      return;
    }
    setEnabled(true);
    onSave?.({ enabled: true, cloneName: cloneName || "Cloned voice", sampleName, sampleSource });
    onMessage?.(`${cloneName || "Cloned voice"} saved from ${sampleSource === "recorded" ? "a recorded" : "an uploaded"} voice sample.`);
  }

  return (
    <div className={`rounded-2xl border border-violet-300/20 bg-violet-500/10 p-5 ${className}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/15 text-violet-200">
            <Mic2 className="h-5 w-5" />
          </span>
          <div>
            <p className="font-bold text-white">{title}</p>
            <p className="mt-1 text-sm leading-5 text-slate-400">{description}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setEnabled(!enabled)}
          className={`rounded-full px-4 py-2 text-xs font-bold transition ${enabled ? "bg-violet-400 text-white" : "bg-white/10 text-slate-200 ring-1 ring-white/15"}`}
        >
          {enabled ? "Enabled" : "Enable"}
        </button>
      </div>

      {enabled ? (
        <div className="mt-5 space-y-4">
          <label className="block text-sm font-semibold text-slate-200">
            Clone name
            <input
              value={cloneName}
              onChange={(event) => setCloneName(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-violet-300 focus:ring-2 focus:ring-violet-300/20"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-dashed border-violet-300/35 bg-slate-950/70 p-4">
              <div className="flex items-center gap-2 text-sm font-bold text-violet-100">
                <Mic2 className="h-4 w-4" /> Speak to computer
              </div>
              <button
                type="button"
                onClick={recording ? stopVoiceRecording : startVoiceRecording}
                className={`mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold transition ${recording ? "bg-red-400 text-slate-950 hover:bg-red-300" : "bg-slate-950 text-white ring-1 ring-white/10 hover:bg-white/10"}`}
              >
                {recording ? <Square className="h-4 w-4" /> : <Mic2 className="h-4 w-4" />}
                {recording ? "Stop recording" : "Record sample"}
              </button>
            </div>

            <label className="flex cursor-pointer flex-col rounded-xl border border-dashed border-violet-300/35 bg-slate-950/70 p-4 transition hover:bg-white/[0.04]">
              <span className="flex items-center gap-2 text-sm font-bold text-violet-100">
                <Upload className="h-4 w-4" /> Upload voice
              </span>
              <span className="mt-4 inline-flex w-full items-center justify-center rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white ring-1 ring-white/10">
                Choose audio file
              </span>
              <input type="file" accept="audio/*" className="sr-only" onChange={(event) => handleVoiceUpload(event.target.files?.[0])} />
            </label>
          </div>

          {sampleName ? (
            <div className="rounded-xl border border-white/10 bg-slate-950/80 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-bold text-white">{sampleName}</p>
                  <p className="mt-1 text-xs capitalize text-slate-500">{sampleSource} voice sample ready.</p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200">
                  <BadgeCheck className="h-4 w-4" /> Ready
                </span>
              </div>
              {sampleUrl ? <audio controls src={sampleUrl} className="mt-4 w-full" aria-label="Voice sample playback" /> : null}
            </div>
          ) : null}

          <button
            type="button"
            disabled={!sampleName || recording}
            onClick={saveVoiceClone}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-400 px-4 py-3 text-sm font-bold text-white transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            <Play className="h-4 w-4" /> Save voice clone
          </button>
        </div>
      ) : null}
    </div>
  );
}
