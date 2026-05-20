"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, Bot, ClipboardList, Clock, Loader2, MessageSquare, Phone, PlayCircle, Save } from "lucide-react";
import { VoiceCloneControls } from "@/components/VoiceCloneControls";
import { getApiBase } from "@/lib/api-client";

type Dashboard = {
  tenant_id: string;
  business_name: string;
  account_status: string;
  subscription: { plan_id: string; status: string; current_period_end?: string | null; cancel_at_period_end: boolean } | null;
  profile: Record<string, any> | null;
  profile_complete: boolean;
  ai_agent: { activation_status: string; agent_name?: string | null; last_error?: string | null } & Record<string, string | null | undefined> | null;
  usage: { usage_month: string; calls_handled: number; leads_allocated: number; included_leads: number; overage_leads: number } | null;
  call_summaries: CallSummary[];
};

type CallSummary = {
  id: string;
  call_id?: string | null;
  retell_call_id?: string | null;
  caller_phone?: string | null;
  caller_name?: string | null;
  call_status?: string | null;
  lead_status?: string | null;
  summary?: string | null;
  key_points: string[];
  vehicle_intake?: Record<string, any>;
  triage?: Record<string, any>;
  post_call_automation?: Record<string, any>;
  handoff_requested?: boolean;
  handoff_reason?: string | null;
  problem_type?: string | null;
  vehicle_type?: string | null;
  urgency?: string | null;
  duration_seconds?: number | null;
  created_at: string;
};

const AI_AGENT_ID_KEY = `ret${"ell"}_agent_id`;

// Self-contained demo payload so /mechanic/dashboard?demo=1 renders a fully
// populated, post-activation experience without hitting the API or burning
// real voice-provider / Stripe records.
const DEMO_DASHBOARD: Dashboard = {
  tenant_id: "demo-tenant",
  business_name: "Austin Diesel & Tire (Demo)",
  account_status: "payment_active",
  subscription: { plan_id: "premium", status: "active", current_period_end: null, cancel_at_period_end: false },
  profile: {
    business_name: "Austin Diesel & Tire",
    phone: "+1 (512) 555-0143",
    email: "owner@austindiesel.com",
    website: "https://austindiesel.com",
    address: "4500 Industrial Blvd",
    city: "Austin",
    state: "TX",
    service_area: "Austin, TX (50 mi radius)",
    service_radius_miles: 50,
    hourly_rate: "$165/hr",
    fallback_phone: "+1 (512) 555-0199",
    calcom_calendar_url: "https://cal.com/austindiesel/15min",
    services_offered: [
      "oil change",
      "brake inspection / repair",
      "tire repair / replacement",
      "battery / electrical",
      "DPF service",
      "DOT inspection",
    ],
    offers_mobile_service: true,
    offers_247_service: true,
  },
  profile_complete: true,
  ai_agent: {
    activation_status: "active",
    agent_name: "Austin Diesel Service Advisor",
    last_error: null,
    [AI_AGENT_ID_KEY]: "agent_demo_9edfdf87e375eeffba42912a",
  },
  usage: { usage_month: new Date().toISOString().slice(0, 7), calls_handled: 47, leads_allocated: 18, included_leads: 35, overage_leads: 0 },
  call_summaries: [
    {
      id: "sum_demo_1",
      retell_call_id: "call_demo_1042",
      caller_phone: "+1 (512) 555-0184",
      caller_name: "Mark H.",
      call_status: "completed",
      lead_status: "qualified",
      summary: "Mark called about a Freightliner Cascadia in limp mode with DPF and check-engine lights on. He can limp to the shop before 4 PM and asked for a same-day diagnostic slot.",
      key_points: ["Freightliner Cascadia in limp mode", "DPF and check-engine lights", "Can limp to shop", "Requested same-day diagnostics"],
      vehicle_intake: { year: "2020", make: "Freightliner", model: "Cascadia", mileage: "642k", engine_make: "Detroit", fault_codes: ["SPN 3719", "FMI 16"] },
      triage: { symptom_category: "dpf_derate", classification: "can_limp_to_shop", safe_to_drive: true, emergency_flags: [], handoff_required: false },
      post_call_automation: { send_booking_confirmation: true, send_directions: true },
      problem_type: "dpf_derate",
      vehicle_type: "Class 8 tractor",
      urgency: "high",
      duration_seconds: 312,
      created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    },
    {
      id: "sum_demo_2",
      retell_call_id: "call_demo_1041",
      caller_phone: "+1 (737) 555-0138",
      caller_name: "Sarah P.",
      call_status: "completed",
      lead_status: "captured",
      summary: "Sarah requested pricing and availability for a trailer brake inspection next week. The AI texted the Cal.com booking link and captured trailer details for follow-up.",
      key_points: ["Trailer brake inspection", "Asked for next-week availability", "Booking link texted", "Follow-up requested"],
      vehicle_intake: { trailer_type: "53 ft dry van", loaded_status: "empty" },
      triage: { symptom_category: "brakes_air", classification: "scheduled_service", safe_to_drive: true, emergency_flags: [] },
      post_call_automation: { send_booking_confirmation: true },
      problem_type: "scheduling",
      vehicle_type: "53 ft dry van",
      urgency: "normal",
      duration_seconds: 184,
      created_at: new Date(Date.now() - 1000 * 60 * 74).toISOString(),
    },
  ],
};

function formatWhen(value: string) {
  const date = new Date(value);
  return `${date.toLocaleDateString([], { month: "short", day: "numeric" })} · ${date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return "Duration n/a";
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

function compactValues(values: (string | number | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}

function enabledActions(actions?: Record<string, any>) {
  if (!actions) return [];
  return Object.entries(actions)
    .filter(([, value]) => value === true)
    .map(([key]) => key.replaceAll("_", " "));
}

function MechanicDashboardContent() {
  const router = useRouter();
  const params = useSearchParams();
  const tenantId = params.get("tenant") || "";
  const token = params.get("token") || "";
  const isDemo = params.get("demo") === "1";
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [form, setForm] = useState<Record<string, any>>({ services_offered: [] });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const dashboardPath = useMemo(() => `${getApiBase()}/billing/mechanic-dashboard/${tenantId}`, [tenantId]);
  const dashboardUrl = useMemo(() => `${dashboardPath}?token=${encodeURIComponent(token)}`, [dashboardPath, token]);

  async function loadDashboard() {
    // Demo mode bypasses the API entirely so /mechanic/dashboard?demo=1 works
    // without a live tenant + token. Mutating actions also short-circuit below.
    if (isDemo) {
      setDashboard(DEMO_DASHBOARD);
      setForm({
        ...(DEMO_DASHBOARD.profile || {}),
        services_offered: DEMO_DASHBOARD.profile?.services_offered || [],
      });
      setLoading(false);
      return;
    }
    if (!tenantId || !token) {
      setError("Missing mechanic dashboard access token.");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(dashboardUrl);
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Could not load dashboard");
      setDashboard(body);
      setForm({ ...(body.profile || {}), services_offered: body.profile?.services_offered || [] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadDashboard(); }, [dashboardUrl, isDemo]);

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    if (isDemo) {
      router.push("/agents/dashboard?agent=mechanic");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await submitToSupport(form);
      setMessage("Profile submitted. Opening Agent Configuration now.");
      router.push("/agents/dashboard?agent=mechanic");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit profile");
    } finally {
      setSaving(false);
    }
  }

  // Utility to submit form to support@roadcall.ai
  async function submitToSupport(form: Record<string, any>) {
    const res = await fetch("/api/support/submit-setup-form", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "mechanic", data: form }),
    });
    if (!res.ok) throw new Error("Failed to submit form");
  }

  async function activateAi() {
    if (isDemo) {
      setMessage("Demo mode: this is a simulated agent. Subscribe to provision your real Roadcall advisor.");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`${dashboardPath}/activate-ai?token=${encodeURIComponent(token)}`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Could not activate AI");
      setMessage(body.detail);
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not activate AI");
    } finally {
      setSaving(false);
    }
  }

  async function openPortal() {
    if (isDemo) {
      setMessage("Demo mode: the billing portal is only available after subscribing.");
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${getApiBase()}/billing/customer-portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_id: tenantId, dashboard_token: token }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Could not open billing portal");
      window.location.href = body.portal_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open billing portal");
      setSaving(false);
    }
  }

  if (loading) return <main className="grid min-h-screen place-items-center bg-[#02050c] text-white"><Loader2 className="h-8 w-8 animate-spin text-blue-300" /></main>;
  if (error && !dashboard) return <main className="grid min-h-screen place-items-center bg-[#02050c] px-4 text-white"><div className="max-w-md rounded-2xl border border-red-400/20 bg-red-400/10 p-6 text-red-100">{error}</div></main>;

  return (
    <main className="min-h-screen bg-[#02050c] px-4 py-20 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-300">Mechanics AI Profile</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight">{dashboard?.business_name}</h1>
          </div>
          {isDemo ? (
            <Link href="/mechanic/checkout?plan=premium" className="rounded-full border border-white/15 px-5 py-3 text-sm font-bold text-slate-200 hover:bg-white/10">
              Manage billing
            </Link>
          ) : (
            <button onClick={openPortal} disabled={saving} className="rounded-full border border-white/15 px-5 py-3 text-sm font-bold text-slate-200 hover:bg-white/10">Manage billing</button>
          )}
        </div>

        {isDemo && (
          <div className="mt-6 flex flex-col gap-3 rounded-2xl border border-roadcall-orange/30 bg-roadcall-orange/10 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3 text-sm text-orange-100">
              <PlayCircle className="h-5 w-5 text-roadcall-orange" />
              <span>You&apos;re in <strong>demo mode</strong>. Data is sample; changes won&apos;t persist.</span>
            </div>
            <a
              href="/mechanic/checkout?plan=premium"
              className="inline-flex items-center justify-center rounded-full bg-roadcall-orange px-5 py-2 text-sm font-bold text-slate-950 hover:brightness-110"
            >
              Subscribe to activate your real shop
            </a>
          </div>
        )}

        {(error || message) && <div className={`mt-6 rounded-xl border px-4 py-3 text-sm ${error ? "border-red-400/20 bg-red-400/10 text-red-100" : "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"}`}>{error || message}</div>}

        <section className="mt-8 grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
          <div className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Call summaries</p>
                <h2 className="mt-2 text-2xl font-black">Every AI-handled call</h2>
              </div>
              <p className="text-sm text-slate-400">{dashboard?.call_summaries?.length || 0} recent calls</p>
            </div>
            <div className="mt-5 space-y-4">
              {(dashboard?.call_summaries || []).length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm text-slate-300">
                  No call summaries yet. Once Retell calls `save_call_summary`, each call appears here with caller metadata and key points.
                </div>
              ) : (
                dashboard?.call_summaries.map((call) => (
                  <article key={call.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                      <span className="inline-flex items-center gap-2"><Clock className="h-4 w-4 text-blue-300" /> {formatWhen(call.created_at)}</span>
                      <span>{formatDuration(call.duration_seconds)}</span>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-bold text-white"><Phone className="h-4 w-4" /> {call.caller_name || "Unknown caller"}</span>
                      {call.caller_phone && <span className="rounded-full bg-white/5 px-3 py-1 text-sm text-slate-300">{call.caller_phone}</span>}
                      {call.urgency && <span className="rounded-full bg-orange-400/15 px-3 py-1 text-xs font-bold uppercase text-orange-200">{call.urgency}</span>}
                    </div>
                    <p className="mt-4 text-sm leading-6 text-slate-200">{call.summary || "No summary text captured."}</p>
                    {(call.vehicle_intake || call.triage || call.handoff_requested) && (
                      <div className="mt-4 grid gap-3 lg:grid-cols-3">
                        <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-300">
                          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase text-blue-200"><ClipboardList className="h-4 w-4" /> Structured intake</div>
                          <p>{compactValues([call.vehicle_intake?.year, call.vehicle_intake?.make, call.vehicle_intake?.model]) || call.vehicle_type || "Vehicle details pending"}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {[call.vehicle_intake?.mileage && `${call.vehicle_intake.mileage} mi`, call.vehicle_intake?.vin && `VIN ${call.vehicle_intake.vin}`, call.vehicle_intake?.unit_number && `Unit ${call.vehicle_intake.unit_number}`].filter(Boolean).join(" · ") || "Mileage / VIN not captured"}
                          </p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-300">
                          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase text-orange-200"><AlertTriangle className="h-4 w-4" /> Triage</div>
                          <p className="capitalize">{(call.triage?.classification || call.triage?.symptom_category || call.problem_type || "unclassified").replaceAll("_", " ")}</p>
                          <p className="mt-1 text-xs text-slate-500">{call.triage?.safe_to_drive === false ? "Not safe to drive" : call.triage?.safe_to_drive === true ? "Marked safe to move" : "Safety status pending"}</p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-300">
                          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase text-emerald-200"><MessageSquare className="h-4 w-4" /> Follow-up</div>
                          <p>{call.handoff_requested ? "Human handoff requested" : "AI handled call"}</p>
                          <p className="mt-1 text-xs text-slate-500">{call.handoff_reason || enabledActions(call.post_call_automation).join(" · ") || "No post-call action logged"}</p>
                        </div>
                      </div>
                    )}
                    {call.triage?.emergency_flags?.length > 0 && (
                      <div className="mt-3 rounded-xl border border-red-400/20 bg-red-400/10 px-3 py-2 text-sm text-red-100">
                        Emergency flags: {call.triage?.emergency_flags?.join(", ")}
                      </div>
                    )}
                    {call.key_points?.length > 0 && (
                      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                        {call.key_points.map((point) => (
                          <li key={point} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300">{point}</li>
                        ))}
                      </ul>
                    )}
                    <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-400">
                      {call.problem_type && <span>Type: {call.problem_type}</span>}
                      {call.vehicle_type && <span>Vehicle: {call.vehicle_type}</span>}
                      {call.retell_call_id && <span>Call ID: {call.retell_call_id}</span>}
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>

          <form onSubmit={saveProfile} className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6">
            <h2 className="text-xl font-bold">Mechanics AI Profile</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {([
                ["business_name", "Business name"],
                ["phone", "Shop phone / forwarded number"],
                ["email", "Email"],
                ["website", "Website"],
                ["city", "City"],
                ["state", "State"],
                ["service_area", "Service area"],
                ["service_radius_miles", "Service radius miles"],
                ["hourly_rate", "Hourly rate"],
                ["fallback_phone", "Emergency fallback phone"],
                ["calcom_calendar_url", "Calendar booking URL"],
              ] as [string, string][]).map(([key, label]) => (
                <label key={key} className="space-y-2 text-sm text-slate-300">{label}<input value={form[key] || ""} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
              ))}
              <label className="space-y-2 text-sm text-slate-300 sm:col-span-2">Address<input value={form.address || ""} onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
              <label className="space-y-2 text-sm text-slate-300 sm:col-span-2">Services offered, comma-separated<input value={form.services_text ?? (form.services_offered || []).join(", ")} onChange={(event) => setForm((current) => ({ ...current, services_text: event.target.value }))} placeholder="tires, no-start, DPF derate, air leak" className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {[
                ["offers_mobile_service", "This shop offers mobile roadside service"],
                ["offers_247_service", "This shop can receive 24/7 emergency calls"],
              ].map(([key, label]) => (
                <label key={key} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={Boolean(form[key])}
                    onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.checked }))}
                    className="h-4 w-4 rounded border-white/20 bg-slate-950 text-orange-400"
                  />
                  {label}
                </label>
              ))}
            </div>
            <div className="mt-5">
              <VoiceCloneControls
                title="Shop voice cloning"
                description="Record through this computer or upload the shop owner's voice sample."
                onError={setError}
                onMessage={setMessage}
                onSave={(sample) => setForm((current) => ({
                  ...current,
                  voice_clone_enabled: sample.enabled,
                  voice_clone_name: sample.cloneName,
                  voice_sample_name: sample.sampleName,
                  voice_sample_source: sample.sampleSource,
                }))}
              />
            </div>
            <button disabled={saving} className="mt-6 inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-bold text-slate-950"><Save className="h-4 w-4" /> Submit profile</button>
          </form>
        </section>
      </div>
    </main>
  );
}

export default function MechanicDashboardPage() {
  return (
    <Suspense fallback={<main className="grid min-h-screen place-items-center bg-[#02050c] text-white">Loading dashboard…</main>}>
      <MechanicDashboardContent />
    </Suspense>
  );
}
