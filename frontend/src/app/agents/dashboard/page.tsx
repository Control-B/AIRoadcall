"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  Brain,
  Building2,
  Check,
  Copy,
  FileAudio,
  Headphones,
  LifeBuoy,
  Loader2,
  Mic2,
  PhoneCall,
  Save,
  Settings2,
  ShieldCheck,
  Sparkles,
  TestTube2,
  Truck,
  Upload,
  Volume2,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { getApiBase } from "@/lib/api-client";

type AgentType = "mechanic" | "fleet" | "roadside";
type AgentTab = "conversation" | "voice" | "telephony" | "advanced";

type RetellWebClientLike = {
  startCall: (config: { accessToken: string }) => Promise<void>;
  stopCall: () => void;
};

const inputClass =
  "w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-roadcall-cyan/70 focus:ring-2 focus:ring-roadcall-cyan/20";

const textareaClass = `${inputClass} min-h-[150px] resize-y leading-6`;

const agentProfiles = {
  mechanic: {
    label: "Mechanic agent",
    badge: "Inbound only",
    icon: Wrench,
    agentName: "Roadcall Service Advisor",
    businessName: "Diesel repair shop",
    welcome:
      "Thanks for calling. I can help with roadside service, shop availability, location, truck details, and the best next step for your repair.",
    instructions:
      "Act like a calm service advisor for a heavy-duty repair shop. Capture caller name, truck or trailer type, location, issue, urgency, and callback number. Confirm whether the shop offers the requested service before promising availability. Escalate urgent safety issues or pricing disputes to the shop owner.",
    abilities: ["Answer inbound calls", "Qualify repair requests", "Capture lead details", "Escalate to owner"],
  },
  fleet: {
    label: "Fleet agent",
    badge: "Inbound and outbound",
    icon: Truck,
    agentName: "Roadcall Fleet Dispatcher",
    businessName: "Fleet operations team",
    welcome:
      "Roadcall dispatch here. I can help open a breakdown case, collect driver and asset details, contact approved vendors, and keep your team updated.",
    instructions:
      "Act like a fleet roadside dispatcher. Gather driver name, unit number, trailer number, load status, exact location, safety condition, issue type, and preferred vendor rules. For outbound calls, identify yourself as Roadcall dispatch, confirm vendor availability, ETA, pricing basics, and callback information. Never authorize work outside approved fleet rules.",
    abilities: ["Answer driver hotline", "Call approved vendors", "Update dispatch status", "Escalate exceptions"],
  },
  roadside: {
    label: "Roadside dispatch agent",
    badge: "Public dispatch",
    icon: PhoneCall,
    agentName: "Roadcall Roadside Dispatcher",
    businessName: "Roadcall Dispatch",
    welcome:
      "Roadcall dispatch. I can open a roadside case, capture your exact location, find nearby service, and keep you updated.",
    instructions:
      "Act like Roadcall's public roadside dispatcher. Capture caller name, callback number, vehicle type, issue, safety condition, city/state, highway, mile marker, direction, exit, truck stop, or landmark. Send the secure GPS link when exact location is needed. Confirm payment authorization before revealing provider contact details. Escalate injuries, hazmat, police, or unsafe roadside conditions immediately.",
    abilities: ["Open roadside cases", "Capture GPS location", "Match nearby providers", "Escalate emergencies"],
  },
} satisfies Record<AgentType, {
  label: string;
  badge: string;
  icon: typeof Wrench;
  agentName: string;
  businessName: string;
  welcome: string;
  instructions: string;
  abilities: string[];
}>;

const tabs: { id: AgentTab; label: string; icon: typeof Bot }[] = [
  { id: "conversation", label: "Conversation", icon: Bot },
  { id: "voice", label: "Voice", icon: Volume2 },
  { id: "telephony", label: "Phone", icon: PhoneCall },
  { id: "advanced", label: "Advanced", icon: Settings2 },
];

const roleOptions = [
  "Roadside triage",
  "Lead capture",
  "Human handoff",
  "Appointment booking",
  "After-hours coverage",
  "Vendor coordination",
];

export default function AgentDashboard() {
  const [agentType, setAgentType] = useState<AgentType>("mechanic");
  const [activeTab, setActiveTab] = useState<AgentTab>("conversation");
  const profile = agentProfiles[agentType];
  const ProfileIcon = profile.icon;

  const [agentName, setAgentName] = useState(profile.agentName);
  const [businessName, setBusinessName] = useState(profile.businessName);
  const [phone, setPhone] = useState("+1 ");
  const [handoffPhone, setHandoffPhone] = useState("+1 ");
  const [welcomeMessage, setWelcomeMessage] = useState(profile.welcome);
  const [instructions, setInstructions] = useState(profile.instructions);
  const [voice, setVoice] = useState<"female" | "male" | "clone">("female");
  const [voiceCloneEnabled, setVoiceCloneEnabled] = useState(false);
  const [voiceCloneName, setVoiceCloneName] = useState("Owner voice");
  const [sampleName, setSampleName] = useState("");
  const [outboundEnabled, setOutboundEnabled] = useState(agentType === "fleet");
  const [testNumber, setTestNumber] = useState("+1 ");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewActive, setPreviewActive] = useState(false);
  const retellClientRef = useRef<RetellWebClientLike | null>(null);

  const activeRoles = useMemo(
    () => roleOptions.filter((role) => agentType !== "mechanic" || role !== "Vendor coordination"),
    [agentType]
  );

  useEffect(() => {
    const requestedAgent = new URLSearchParams(window.location.search).get("agent");
    if (requestedAgent === "mechanic" || requestedAgent === "fleet" || requestedAgent === "roadside") {
      switchAgentType(requestedAgent);
    }
  }, []);

  useEffect(() => {
    return () => {
      retellClientRef.current?.stopCall();
    };
  }, []);

  function switchAgentType(nextType: AgentType) {
    stopPreviewCall();
    setAgentType(nextType);
    setAgentName(agentProfiles[nextType].agentName);
    setBusinessName(agentProfiles[nextType].businessName);
    setWelcomeMessage(agentProfiles[nextType].welcome);
    setInstructions(agentProfiles[nextType].instructions);
    setOutboundEnabled(nextType === "fleet");
    setMessage(null);
    setError(null);
  }

  function saveSettings() {
    setError(null);
    setMessage("Settings saved locally. Use Preview agent to talk to this agent in your browser before checkout.");
  }

  function hasPhoneValue(value: string) {
    return value.replace(/\D/g, "").length > 1;
  }

  function updateTestNumber(value: string) {
    setTestNumber(value);
    if (!hasPhoneValue(phone)) {
      setPhone(value);
    }
    if (!hasPhoneValue(handoffPhone)) {
      setHandoffPhone(value);
    }
  }

  async function copyInstallSnippet() {
    setError(null);
    const snippet = `<script src="https://roadcall.ai/agent-widget.js" data-roadcall-agent="${agentType}" data-roadcall-business="${businessName || "Roadcall"}"></script>`;
    try {
      await navigator.clipboard.writeText(snippet);
      setMessage("Install snippet copied. Add it to the customer site after Roadcall activation is complete.");
    } catch {
      setError("Could not copy the snippet from this browser. Open the install step and copy it manually.");
    }
  }

  function openVoiceSampleSetup() {
    setActiveTab("voice");
    setVoiceCloneEnabled(true);
    setVoice("clone");
    setError(null);
    setMessage("Voice sample setup is open. Use Upload voice sample in the Voice tab to add the audio file.");
  }

  function openCallQualityChecklist() {
    setActiveTab("advanced");
    setError(null);
    setMessage("Call quality checklist opened. Review the guardrails and roles before starting a live test call.");
  }

  async function startTestCall() {
    if (agentType !== "fleet") {
      setActiveTab("telephony");
      setError("Outbound phone test calls are only available for Fleet agents. Use Preview agent for browser voice testing.");
      return;
    }
    setTesting(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`${getApiBase()}/agent-dashboard/test-call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to_number: testNumber,
          agent_type: agentType,
          agent_name: agentName,
          business_name: businessName,
          welcome_message: welcomeMessage,
          instructions,
        }),
      });
      const body = await response.json().catch(() => null) as { message?: string; detail?: string } | null;
      if (!response.ok) {
        throw new Error(body?.detail || body?.message || "Roadcall could not start the test call.");
      }
      setMessage(body?.message || "Roadcall fleet test call started. Answer your phone to speak with the fleet dispatcher.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Roadcall could not start the test call.");
    } finally {
      setTesting(false);
    }
  }

  async function startPreviewCall() {
    setPreviewing(true);
    setMessage(null);
    setError(null);
    try {
      stopPreviewCall();
      const response = await fetch(`${getApiBase()}/agent-dashboard/web-call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_type: agentType,
          agent_name: agentName,
          business_name: businessName,
          company_phone: phone,
          forward_phone: handoffPhone,
          welcome_message: welcomeMessage,
          instructions,
        }),
      });
      const body = await response.json().catch(() => null) as { access_token?: string; message?: string; detail?: string } | null;
      if (!response.ok || !body?.access_token) {
        throw new Error(body?.detail || body?.message || "Roadcall could not start the browser preview.");
      }
      const { RetellWebClient } = await import("retell-client-js-sdk");
      const client = new RetellWebClient() as RetellWebClientLike;
      retellClientRef.current = client;
      await client.startCall({ accessToken: body.access_token });
      setPreviewActive(true);
      setMessage(body.message || "Browser preview started. Speak naturally to test your agent.");
    } catch (err) {
      retellClientRef.current = null;
      setPreviewActive(false);
      setError(err instanceof Error ? err.message : "Roadcall could not start the browser preview.");
    } finally {
      setPreviewing(false);
    }
  }

  function stopPreviewCall() {
    if (retellClientRef.current) {
      retellClientRef.current.stopCall();
      retellClientRef.current = null;
    }
    setPreviewActive(false);
  }

  function previewAgent() {
    setActiveTab("telephony");
    void startPreviewCall();
  }

  const previewPhone = hasPhoneValue(phone) ? phone : hasPhoneValue(handoffPhone) ? handoffPhone : hasPhoneValue(testNumber) ? testNumber : "Not assigned";

  return (
    <PageLayout>
      <section className="px-4 pb-16 pt-10 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1500px]">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/25 bg-roadcall-cyan/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-roadcall-cyan">
                <Sparkles className="h-4 w-4" /> Agent configuration
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight text-white sm:text-4xl">
                Configure, test, and launch your Roadcall AI agent
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-roadcall-muted sm:text-base">
                Set the voice, phone routing, welcome message, operating rules, and Roadcall-managed test flow after profile setup.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">
                <Link href="/get-started">Get started</Link>
              </Button>
              <Button onClick={saveSettings} className="rounded-xl">
                <Save className="mr-2 h-4 w-4" /> Save changes
              </Button>
            </div>
          </div>

          {message ? (
            <div className="mb-6 rounded-2xl border border-emerald-300/25 bg-emerald-400/10 px-5 py-4 text-sm font-medium text-emerald-100">
              {message}
            </div>
          ) : null}
          {error ? (
            <div className="mb-6 rounded-2xl border border-red-300/25 bg-red-400/10 px-5 py-4 text-sm font-medium text-red-100">
              {error}
            </div>
          ) : null}

          <div className="grid gap-6 xl:grid-cols-[240px_minmax(0,1fr)_390px]">
            <aside className="roadcall-surface rounded-2xl p-4 xl:sticky xl:top-24 xl:self-start">
              <div className="flex items-center gap-3 border-b border-white/10 pb-5">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-roadcall-cyan/15 text-roadcall-cyan ring-1 ring-roadcall-cyan/25">
                  <Bot className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-bold text-white">Roadcall AI</p>
                  <p className="text-xs text-roadcall-muted">Agent builder</p>
                </div>
              </div>

              <nav className="mt-5 space-y-2">
                {[
                  { href: "/mechanic/dashboard?demo=1", label: "Mechanics AI Profile", icon: Building2 },
                  { href: "/fleet/onboarding", label: "Fleet profile", icon: Truck },
                  { href: "/agents/dashboard", label: "Agent Configuration", icon: Bot, active: true },
                  { href: "/ai-telephony", label: "AI Telephony", icon: PhoneCall },
                  { href: "mailto:support@roadcall.ai?subject=Roadcall%20agent%20provisioning%20help", label: "Provisioning support", icon: LifeBuoy },
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={`${item.href}-${item.label}`}
                      href={item.href}
                      className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${
                        item.active
                          ? "bg-roadcall-cyan/15 text-roadcall-cyan ring-1 ring-roadcall-cyan/20"
                          : "text-slate-300 hover:bg-white/5 hover:text-white"
                      }`}
                    >
                      <Icon className="h-4 w-4" /> {item.label}
                    </Link>
                  );
                })}
              </nav>

              <div className="mt-6 rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-roadcall-muted">Setup path</p>
                <div className="mt-4 space-y-3 text-sm text-slate-300">
                  {[
                    "Profile completed",
                    "Agent rules drafted",
                    "Phone number connected",
                    "Live test completed",
                  ].map((step, index) => (
                    <div key={step} className="flex items-center gap-3">
                      <span className={`flex h-6 w-6 items-center justify-center rounded-full ${index < 2 ? "bg-emerald-400/15 text-emerald-200" : "bg-white/10 text-slate-400"}`}>
                        {index < 2 ? <Check className="h-3.5 w-3.5" /> : index + 1}
                      </span>
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            </aside>

            <main className="min-w-0 space-y-6">
              <section className="roadcall-surface overflow-hidden rounded-2xl">
                <div className="border-b border-white/10 bg-slate-950/75 px-5 py-4 sm:px-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-center gap-3">
                      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-roadcall-orange/15 text-roadcall-orange ring-1 ring-roadcall-orange/20">
                        <ProfileIcon className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="text-sm font-bold text-white">{profile.label}</p>
                        <p className="text-xs text-roadcall-muted">{profile.badge} call behavior</p>
                      </div>
                    </div>

                    <div className="grid gap-2 sm:grid-cols-3">
                      {(["mechanic", "fleet", "roadside"] as AgentType[]).map((type) => {
                        const option = agentProfiles[type];
                        const Icon = option.icon;
                        const active = agentType === type;
                        return (
                          <button
                            key={type}
                            type="button"
                            onClick={() => switchAgentType(type)}
                            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
                              active
                                ? "border-roadcall-cyan/60 bg-roadcall-cyan/10 text-white"
                                : "border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/20 hover:bg-white/[0.06]"
                            }`}
                          >
                            <Icon className={active ? "h-5 w-5 text-roadcall-cyan" : "h-5 w-5 text-slate-400"} />
                            <span>
                              <span className="block text-sm font-bold">{type === "mechanic" ? "Mechanic" : type === "fleet" ? "Fleet" : "Roadside"}</span>
                              <span className="block text-xs text-roadcall-muted">{option.badge}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="p-5 sm:p-6">
                  <div className="flex gap-2 overflow-x-auto border-b border-white/10 pb-4">
                    {tabs.map((tab) => {
                      const Icon = tab.icon;
                      const active = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setActiveTab(tab.id)}
                          className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition ${
                            active ? "bg-roadcall-cyan text-slate-950" : "bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white"
                          }`}
                        >
                          <Icon className="h-4 w-4" /> {tab.label}
                        </button>
                      );
                    })}
                  </div>

                  {activeTab === "conversation" ? (
                    <div className="mt-6 grid gap-5 lg:grid-cols-2">
                      <Field label="Agent name" helper="The caller-facing name for the AI.">
                        <input value={agentName} onChange={(event) => setAgentName(event.target.value)} className={inputClass} />
                      </Field>
                      <Field label="Business name" helper="Used in greetings, summaries, and phone agent context.">
                        <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} className={inputClass} />
                      </Field>
                      <Field label="Welcome message" helper="The first thing callers hear or see." className="lg:col-span-2">
                        <textarea value={welcomeMessage} onChange={(event) => setWelcomeMessage(event.target.value)} rows={3} className={textareaClass} />
                      </Field>
                      <Field label="Instructions" helper="Tell the agent what to collect, avoid, confirm, and escalate." className="lg:col-span-2">
                        <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={7} className={textareaClass} />
                      </Field>
                    </div>
                  ) : null}

                  {activeTab === "voice" ? (
                    <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.75fr)]">
                      <div className="space-y-4">
                        {[
                          { id: "female", title: "Female voice", body: "Warm, clear advisor voice for repair and dispatch calls." },
                          { id: "male", title: "Male voice", body: "Direct, steady operations voice for fast triage." },
                          { id: "clone", title: "Cloned voice", body: "Use your saved sample once voice cloning is enabled." },
                        ].map((option) => {
                          const active = voice === option.id;
                          return (
                            <button
                              key={option.id}
                              type="button"
                              onClick={() => setVoice(option.id as typeof voice)}
                              className={`flex w-full items-start gap-4 rounded-2xl border p-4 text-left transition ${
                                active ? "border-roadcall-cyan/70 bg-roadcall-cyan/10" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"
                              }`}
                            >
                              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 text-roadcall-cyan">
                                <Volume2 className="h-5 w-5" />
                              </span>
                              <span className="min-w-0 flex-1">
                                <span className="block font-bold text-white">{option.title}</span>
                                <span className="mt-1 block text-sm leading-5 text-roadcall-muted">{option.body}</span>
                              </span>
                              <span className={`mt-1 h-2.5 w-2.5 rounded-full ${active ? "bg-roadcall-cyan" : "bg-slate-600"}`} />
                            </button>
                          );
                        })}
                      </div>

                      <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-start gap-3">
                            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/15 text-violet-200">
                              <Mic2 className="h-5 w-5" />
                            </span>
                            <div>
                              <p className="font-bold text-white">Voice cloning</p>
                              <p className="mt-1 text-sm leading-5 text-roadcall-muted">Upload or record a short sample to use a custom voice.</p>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              const enabled = !voiceCloneEnabled;
                              setVoiceCloneEnabled(enabled);
                              if (enabled) setVoice("clone");
                            }}
                            className={`rounded-full px-4 py-2 text-xs font-bold transition ${
                              voiceCloneEnabled ? "bg-violet-400 text-white" : "bg-white/10 text-slate-200 ring-1 ring-white/15"
                            }`}
                          >
                            {voiceCloneEnabled ? "Enabled" : "Enable"}
                          </button>
                        </div>

                        {voiceCloneEnabled ? (
                          <div className="mt-5 space-y-4">
                            <Field label="Clone name" helper="Shown internally when selecting the saved voice.">
                              <input value={voiceCloneName} onChange={(event) => setVoiceCloneName(event.target.value)} className={inputClass} />
                            </Field>
                            <label className="flex cursor-pointer items-center justify-center gap-3 rounded-xl border border-dashed border-violet-300/35 bg-violet-400/10 px-4 py-5 text-sm font-bold text-violet-100 transition hover:bg-violet-400/15">
                              <Upload className="h-4 w-4" />
                              {sampleName || "Upload voice sample"}
                              <input
                                type="file"
                                accept="audio/*"
                                className="sr-only"
                                onChange={(event) => setSampleName(event.target.files?.[0]?.name || "")}
                              />
                            </label>
                            <p className="text-xs leading-5 text-roadcall-muted">Sample stays in preview until backend voice-clone storage is connected.</p>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ) : null}

                  {activeTab === "telephony" ? (
                    <div className="mt-6 grid gap-5 lg:grid-cols-2">
                      <Field label="Company Number" helper="The subscriber's public business number. Twilio number purchase can replace this later.">
                        <input value={phone} onChange={(event) => setPhone(event.target.value)} className={inputClass} />
                      </Field>
                      <Field label="Forward Number" helper="Where the AI sends human handoffs, escalations, and missed-call follow-up.">
                        <input value={handoffPhone} onChange={(event) => setHandoffPhone(event.target.value)} className={inputClass} />
                      </Field>

                      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 lg:col-span-2">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="font-bold text-white">Outbound calls</p>
                            <p className="mt-1 text-sm text-roadcall-muted">
                              Fleet agents can place outbound Retell phone calls to vendors and dispatch contacts. Mechanic and roadside previews stay browser-based.
                            </p>
                          </div>
                          <button
                            type="button"
                            disabled={agentType !== "fleet"}
                            onClick={() => setOutboundEnabled((current) => !current)}
                            className={`rounded-full px-4 py-2 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-60 ${
                              outboundEnabled && agentType === "fleet" ? "bg-emerald-400 text-slate-950" : "bg-white/10 text-slate-200 ring-1 ring-white/15"
                            }`}
                          >
                            {agentType !== "fleet" ? "Locked" : outboundEnabled ? "Enabled" : "Disabled"}
                          </button>
                        </div>

                        <div className="mt-5 grid gap-3 md:grid-cols-3">
                          {[
                            { title: "Inbound", body: "Answer calls and qualify the request", active: true },
                            { title: "Outbound", body: "Call vendors and dispatch contacts", active: agentType === "fleet" && outboundEnabled },
                            { title: "Provisioning", body: "Roadcall activates the phone agent and routing", active: false },
                          ].map((item) => (
                            <div key={item.title} className={`rounded-xl border p-4 ${item.active ? "border-emerald-300/25 bg-emerald-400/10" : "border-white/10 bg-slate-950/60"}`}>
                              <p className="font-bold text-white">{item.title}</p>
                              <p className="mt-1 text-xs leading-5 text-roadcall-muted">{item.body}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {agentType === "fleet" ? (
                        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-5 lg:col-span-2">
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
                            <Field label="Your phone number" helper="Fleet preview will call this number through Retell for an outbound phone test." className="flex-1">
                              <input value={testNumber} onChange={(event) => updateTestNumber(event.target.value)} className={inputClass} />
                            </Field>
                            <Button onClick={startTestCall} disabled={testing} className="h-12 rounded-xl bg-emerald-500 text-slate-950 hover:bg-emerald-400 disabled:opacity-70">
                              {testing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PhoneCall className="mr-2 h-4 w-4" />} Start test call
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-roadcall-cyan/20 bg-roadcall-cyan/10 p-5 text-sm leading-6 text-roadcall-silver lg:col-span-2">
                          Use <strong>Preview agent</strong> to start a live browser voice call for this agent. Outbound phone test calls are reserved for Fleet agents.
                        </div>
                      )}
                    </div>
                  ) : null}

                  {activeTab === "advanced" ? (
                    <div className="mt-6 grid gap-5 md:grid-cols-2">
                      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                        <div className="flex items-center gap-3">
                          <Brain className="h-5 w-5 text-roadcall-cyan" />
                          <p className="font-bold text-white">Agent roles</p>
                        </div>
                        <div className="mt-5 grid gap-3">
                          {activeRoles.map((role) => (
                            <label key={role} className="flex items-center gap-3 rounded-xl border border-white/10 bg-slate-950/60 p-3 text-sm text-slate-300">
                              <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-white/20 bg-slate-950 text-roadcall-cyan" />
                              {role}
                            </label>
                          ))}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                        <div className="flex items-center gap-3">
                          <ShieldCheck className="h-5 w-5 text-emerald-300" />
                          <p className="font-bold text-white">Guardrails</p>
                        </div>
                        <div className="mt-5 space-y-3 text-sm text-slate-300">
                          {[
                            "Do not quote final repair prices unless provided by the business.",
                            "Confirm exact location before dispatching or escalating.",
                            "Ask one question at a time during phone calls.",
                            "Escalate safety, hazmat, injury, or police situations immediately.",
                          ].map((rule) => (
                            <div key={rule} className="flex gap-3 rounded-xl border border-white/10 bg-slate-950/60 p-3">
                              <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                              <span>{rule}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              </section>
            </main>

            <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
              <section className="roadcall-surface rounded-2xl p-5 text-center">
                <div className="mx-auto flex h-32 w-32 items-center justify-center rounded-full border border-roadcall-cyan/25 bg-slate-950/70 shadow-[0_0_60px_rgba(20,216,255,0.14)]">
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-roadcall-cyan/10">
                    <span className="absolute inset-0 animate-pulse-ring rounded-full border border-roadcall-cyan/30" />
                    <Mic2 className="relative h-9 w-9 text-roadcall-cyan" />
                  </div>
                </div>
                <h2 className="mt-5 text-xl font-black text-white">{agentName || "Roadcall AI"}</h2>
                <p className="mt-2 text-sm leading-6 text-roadcall-muted">
                  {agentType === "fleet"
                    ? "Fleet dispatcher with inbound hotline and outbound vendor calling."
                    : agentType === "roadside"
                      ? "Roadside dispatcher for public breakdown intake, GPS capture, and provider matching."
                      : "Mechanic service advisor for inbound calls and repair triage."}
                </p>

                <div className="mt-5 grid gap-3 rounded-2xl border border-white/10 bg-slate-950/70 p-4 text-left text-sm">
                  <PreviewRow label="Business" value={businessName || "Not set"} />
                  <PreviewRow label="Company Number" value={previewPhone} />
                  <PreviewRow label="Forward Number" value={hasPhoneValue(handoffPhone) ? handoffPhone : "Not assigned"} />
                  <PreviewRow label="Voice" value={voice === "clone" ? voiceCloneName || "Cloned voice" : voice === "female" ? "Female voice" : "Male voice"} />
                  <PreviewRow label="Outbound" value={agentType === "fleet" && outboundEnabled ? "Enabled" : "Off"} />
                </div>

                <Button onClick={previewActive ? stopPreviewCall : previewAgent} disabled={previewing} className="mt-5 w-full rounded-xl">
                  {previewing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <TestTube2 className="mr-2 h-4 w-4" />}
                  {previewActive ? "End preview call" : previewing ? "Starting preview" : "Preview agent"}
                </Button>
              </section>

              <section className="roadcall-surface rounded-2xl p-5">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-roadcall-muted">Launch utilities</p>
                <div className="mt-4 grid gap-3">
                  <button type="button" onClick={copyInstallSnippet} className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-left text-sm font-semibold text-slate-200 transition hover:bg-white/[0.06]">
                    <span className="inline-flex items-center gap-3"><Copy className="h-4 w-4 text-roadcall-cyan" /> Copy install snippet</span>
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </button>
                  <button type="button" onClick={openVoiceSampleSetup} className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-left text-sm font-semibold text-slate-200 transition hover:bg-white/[0.06]">
                    <span className="inline-flex items-center gap-3"><FileAudio className="h-4 w-4 text-roadcall-cyan" /> Upload voice sample</span>
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </button>
                  <Link href="mailto:support@roadcall.ai?subject=Roadcall%20agent%20provisioning%20help" className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-left text-sm font-semibold text-slate-200 transition hover:bg-white/[0.06]">
                    <span className="inline-flex items-center gap-3"><LifeBuoy className="h-4 w-4 text-roadcall-cyan" /> Ask support to provision</span>
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </Link>
                  <button type="button" onClick={openCallQualityChecklist} className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-left text-sm font-semibold text-slate-200 transition hover:bg-white/[0.06]">
                    <span className="inline-flex items-center gap-3"><Headphones className="h-4 w-4 text-roadcall-cyan" /> Call quality checklist</span>
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </button>
                </div>
              </section>
            </aside>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}

function Field({ label, helper, className = "", children }: { label: string; helper: string; className?: string; children: React.ReactNode }) {
  return (
    <label className={`block ${className}`}>
      <span className="text-sm font-bold text-slate-200">{label}</span>
      <span className="mt-1 block text-xs leading-5 text-roadcall-muted">{helper}</span>
      <span className="mt-2 block">{children}</span>
    </label>
  );
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-roadcall-muted">{label}</span>
      <span className="truncate font-bold text-white">{value}</span>
    </div>
  );
}
