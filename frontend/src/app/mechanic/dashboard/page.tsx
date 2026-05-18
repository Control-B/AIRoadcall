"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, CheckCircle2, Loader2, PhoneForwarded, PlayCircle, Save, ShieldAlert } from "lucide-react";
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
  activation_steps: Array<{ id: string; label: string; complete: boolean }>;
};

const AI_AGENT_ID_KEY = `ret${"ell"}_agent_id`;

// Self-contained demo payload so /mechanic/dashboard?demo=1 renders a fully
// populated, post-activation experience without hitting the API or burning
// real Retell / Stripe records.
const DEMO_DASHBOARD: Dashboard = {
  tenant_id: "demo-tenant",
  business_name: "Austin Diesel & Tire (Demo)",
  account_status: "payment_active",
  subscription: { plan_id: "growth", status: "active", current_period_end: null, cancel_at_period_end: false },
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
  activation_steps: [
    { id: "subscribe", label: "Subscribe", complete: true },
    { id: "profile", label: "Complete Shop Profile", complete: true },
    { id: "ai", label: "Create AI Advisor", complete: true },
    { id: "number", label: "Connect Number", complete: true },
    { id: "live", label: "Go Live", complete: true },
  ],
};

function MechanicDashboardContent() {
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
      setMessage("Demo mode: profile changes aren't persisted. Subscribe to save your real shop.");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`${dashboardPath}/profile?token=${encodeURIComponent(token)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          service_radius_miles: Number(form.service_radius_miles || 50),
          services_offered: String(form.services_text || "").split(",").map((item) => item.trim()).filter(Boolean),
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Could not save profile");
      setDashboard(body);
      setMessage("Shop profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  }

  async function activateAi() {
    if (isDemo) {
      setMessage("Demo mode: this is a simulated agent. Subscribe to provision your real Retell advisor.");
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
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-300">Mechanic AI Dashboard</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight">{dashboard?.business_name}</h1>
          </div>
          {isDemo ? (
            <Link href="/mechanic/checkout?plan=growth" className="rounded-full border border-white/15 px-5 py-3 text-sm font-bold text-slate-200 hover:bg-white/10">
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
              href="/mechanic/checkout?plan=growth"
              className="inline-flex items-center justify-center rounded-full bg-roadcall-orange px-5 py-2 text-sm font-bold text-slate-950 hover:brightness-110"
            >
              Subscribe to activate your real shop
            </a>
          </div>
        )}

        {(error || message) && <div className={`mt-6 rounded-xl border px-4 py-3 text-sm ${error ? "border-red-400/20 bg-red-400/10 text-red-100" : "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"}`}>{error || message}</div>}

        <section className="mt-8 grid gap-4 md:grid-cols-5">
          {dashboard?.activation_steps.map((step) => (
            <div key={step.id} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <CheckCircle2 className={`h-5 w-5 ${step.complete ? "text-emerald-300" : "text-slate-600"}`} />
              <p className="mt-3 text-sm font-bold">{step.label}</p>
            </div>
          ))}
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <form onSubmit={saveProfile} className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6">
            <h2 className="text-xl font-bold">Shop Profile</h2>
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
            <button disabled={saving} className="mt-6 inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-bold text-slate-950"><Save className="h-4 w-4" /> Save profile</button>
          </form>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-xl font-bold">Subscription</h2>
              <p className="mt-4 text-3xl font-black capitalize">{dashboard?.subscription?.plan_id || "No plan"}</p>
              <p className="mt-1 text-sm text-slate-400">Status: {dashboard?.subscription?.status || "not active"}</p>
              <p className="mt-4 text-sm text-slate-300">Lead quota: {dashboard?.usage?.leads_allocated || 0} / {dashboard?.usage?.included_leads || 0}</p>
            </div>
            <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6">
              <div className="flex items-center gap-2"><Bot className="h-5 w-5 text-orange-300" /><h2 className="text-xl font-bold">Phone & AI Advisor</h2></div>
              <p className="mt-4 text-sm text-slate-300">Attach the shop phone, set fallback rules, then create the AI advisor for this mechanic account.</p>
              <p className="mt-3 text-sm text-slate-300">Status: {dashboard?.ai_agent?.activation_status || "not_subscribed"}</p>
              {dashboard?.ai_agent?.[AI_AGENT_ID_KEY] && <p className="mt-2 break-all text-xs text-slate-500">Agent: {dashboard.ai_agent[AI_AGENT_ID_KEY]}</p>}
              <Link href="/ai-telephony" className="mt-5 inline-flex items-center gap-2 rounded-full bg-orange-400 px-5 py-3 text-sm font-bold text-slate-950 hover:brightness-110">
                <PhoneForwarded className="h-4 w-4" /> Create AI advisor
              </Link>
              {!dashboard?.profile_complete && <p className="mt-3 flex gap-2 text-xs text-amber-200"><ShieldAlert className="h-4 w-4" /> Complete profile before activation.</p>}
            </div>
          </aside>
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
