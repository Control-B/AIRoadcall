"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bot,
  CalendarClock,
  CheckCircle2,
  Database,
  ExternalLink,
  Loader2,
  PhoneCall,
  RefreshCw,
  Save,
  Settings2,
  Sparkles,
  Truck,
  Volume2,
  Wrench,
} from "lucide-react";
import { VoiceCloneControls, type VoiceCloneSample } from "@/components/VoiceCloneControls";
import { adminFetch } from "@/lib/admin-auth";

type AgentType = "shops" | "fleet" | "roadside";
type AgentTab = "conversation" | "voice" | "phone" | "calendar" | "advanced";

interface PlanConfig {
  id: string;
  name: string;
  price_monthly: number;
  setup_fee: number;
}

interface RetellConnectionView {
  agent_id?: string | null;
  conversation_flow_id?: string | null;
  phone_number_id?: string | null;
  agent_name?: string | null;
  provisioning_status: string;
  last_error?: string | null;
  last_synced_at?: string | null;
  dynamic_variables: Record<string, unknown>;
}

interface TenantView {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  vertical_type: AgentType | string;
  contact_email?: string | null;
  contact_phone?: string | null;
  current_plan: string;
  subscription_status: string;
  onboarding_status: string;
  setup_fee_status: string;
  retell_connection?: RetellConnectionView | null;
  llm_model?: string | null;
  voice_id?: string | null;
  calls_handled: number;
  vehicle_count: number;
  is_active: boolean;
}

interface TenantListResponse {
  tenants: TenantView[];
  plans: PlanConfig[];
}

const inputClass = "w-full rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-roadcall-cyan/70 focus:ring-2 focus:ring-roadcall-cyan/20";
const textareaClass = `${inputClass} min-h-[142px] resize-y leading-6`;

const profiles = {
  shops: {
    label: "Shop agent",
    badge: "Inbound service advisor",
    icon: Wrench,
    agentName: "Roadcall Service Advisor",
    businessName: "Diesel repair shop",
    welcome: "Thanks for calling. I can help with roadside service, shop availability, location, truck details, and the best next step for your repair.",
    instructions: "Act like a senior heavy-duty service advisor. Capture caller name, callback number, unit number, vehicle year/make/model, location, issue, urgency, warning lamps, and whether the unit is safe to move. Ask one diagnostic question at a time. Confirm scheduling availability before promising a slot and escalate safety issues, pricing disputes, or uncertain diagnosis to the shop owner.",
  },
  fleet: {
    label: "Fleet agent",
    badge: "Inbound and outbound dispatch",
    icon: Truck,
    agentName: "Roadcall Fleet Dispatcher",
    businessName: "Fleet operations team",
    welcome: "Roadcall dispatch here. I can help open a breakdown case, collect driver and asset details, contact approved vendors, and keep your team updated.",
    instructions: "Act like a senior fleet breakdown dispatcher. Gather driver name, callback number, unit number, tractor/trailer type, loaded status, exact location, fault codes, warning lights, and mechanical symptoms. Decide whether the driver can safely move, limp to a shop, needs mobile repair, towing, or is out of service. For outbound vendor calls, confirm capability, ETA, pricing, tools, parts, and callback details.",
  },
  roadside: {
    label: "Roadside agent",
    badge: "Public dispatch",
    icon: PhoneCall,
    agentName: "Roadcall Roadside Dispatcher",
    businessName: "Roadcall Dispatch",
    welcome: "Roadcall dispatch. I can open a roadside case, capture your exact location, find nearby service, and keep you updated.",
    instructions: "Act like Roadcall's public roadside dispatcher. Capture caller name, callback number, vehicle type, issue, warning lights, safety condition, city/state, highway, mile marker, direction, exit, truck stop, or landmark. Send the secure GPS link when exact location is needed. Escalate injuries, hazmat, police, fire, or unsafe roadside conditions immediately.",
  },
} satisfies Record<AgentType, { label: string; badge: string; icon: typeof Wrench; agentName: string; businessName: string; welcome: string; instructions: string }>;

const tabs: { id: AgentTab; label: string; icon: typeof Bot }[] = [
  { id: "conversation", label: "Conversation", icon: Bot },
  { id: "voice", label: "Voice", icon: Volume2 },
  { id: "phone", label: "Phone", icon: PhoneCall },
  { id: "calendar", label: "Cal.com", icon: CalendarClock },
  { id: "advanced", label: "Advanced", icon: Settings2 },
];

function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "emerald" | "amber" | "red" | "blue" | "slate" | "orange" }) {
  const classes = {
    emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/20",
    red: "bg-red-500/15 text-red-300 border-red-500/20",
    blue: "bg-blue-500/15 text-blue-300 border-blue-500/20",
    orange: "bg-orange-500/15 text-orange-300 border-orange-500/20",
    slate: "bg-white/5 text-slate-300 border-white/10",
  }[tone];
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${classes}`}>{children}</span>;
}

function statusTone(status?: string | null): "emerald" | "amber" | "red" | "slate" {
  if (!status) return "slate";
  if (["active", "connected", "installed", "paid", "activated", "healthy", "completed", "ready", "configured"].includes(status)) return "emerald";
  if (["failed", "cancelled", "missing_snapshot_id", "error"].includes(status)) return "red";
  if (["pending", "not_started", "unpaid", "pending_location", "provisioning", "in_progress"].includes(status)) return "amber";
  return "slate";
}

export default function ProvisioningPage() {
  const [tenants, setTenants] = useState<TenantView[]>([]);
  const [plans, setPlans] = useState<PlanConfig[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [agentType, setAgentType] = useState<AgentType>("shops");
  const [activeTab, setActiveTab] = useState<AgentTab>("conversation");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const profile = profiles[agentType];
  const ProfileIcon = profile.icon;
  const selectedTenant = useMemo(() => tenants.find((tenant) => tenant.id === selectedTenantId) || null, [selectedTenantId, tenants]);

  const [form, setForm] = useState({
    organization_name: profile.businessName,
    contact_email: "",
    contact_phone: "",
    plan_id: "growth",
    agent_name: profile.agentName,
    business_name: profile.businessName,
    welcome_message: profile.welcome,
    instructions: profile.instructions,
    voice: "female",
    voice_id: "11labs-Lily",
    company_number: "",
    handoff_phone: "",
    retell_conversation_flow_id: "",
    retell_phone_number_id: "",
    outbound_enabled: false,
    calcom_enabled: true,
    calcom_base_url: "https://app.cal.com",
    calcom_api_key: "",
    calcom_username: "",
    calcom_event_slug: "roadcall-service",
    calcom_event_type_id: "",
    calcom_calendar_url: "",
    calcom_timezone: "America/New_York",
    appointment_rules: "Offer the earliest available appointment, confirm caller name, callback number, vehicle details, problem, and preferred time before booking.",
    service_radius_miles: "50",
    supported_services: "tire, no_start, air_leak, dpf_derate, electrical, trailer_repair, overheating, towing, pm_service",
    fleet_data_url: "",
  });
  const [voiceClone, setVoiceClone] = useState<VoiceCloneSample | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminFetch<TenantListResponse>("/provisioning/admin/tenants");
      setTenants(data.tenants || []);
      setPlans(data.plans || []);
      if (!selectedTenantId && data.tenants?.[0]) setSelectedTenantId(data.tenants[0].id);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load provisioning data");
    } finally {
      setLoading(false);
    }
  }, [selectedTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedTenant) return;
    const selectedType = selectedTenant.vertical_type === "fleet" ? "fleet" : "shops";
    const selectedProfile = profiles[selectedType];
    const variables = selectedTenant.retell_connection?.dynamic_variables || {};
    setAgentType(selectedType);
    setForm((current) => ({
      ...current,
      organization_name: selectedTenant.name,
      contact_email: selectedTenant.contact_email || "",
      contact_phone: selectedTenant.contact_phone || "",
      plan_id: selectedTenant.current_plan || current.plan_id,
      agent_name: selectedTenant.retell_connection?.agent_name || selectedProfile.agentName,
      business_name: selectedTenant.name || selectedProfile.businessName,
      welcome_message: typeof variables.welcome_message === "string" ? variables.welcome_message : selectedProfile.welcome,
      instructions: typeof variables.instructions === "string" ? variables.instructions : selectedProfile.instructions,
      company_number: selectedTenant.contact_phone || current.company_number,
      handoff_phone: selectedTenant.contact_phone || current.handoff_phone,
      retell_conversation_flow_id: selectedTenant.retell_connection?.conversation_flow_id || "",
      retell_phone_number_id: selectedTenant.retell_connection?.phone_number_id || "",
      voice_id: selectedTenant.voice_id || current.voice_id,
    }));
  }, [selectedTenant]);

  function switchAgentType(nextType: AgentType) {
    const nextProfile = profiles[nextType];
    setAgentType(nextType);
    setForm((current) => ({
      ...current,
      organization_name: selectedTenant?.name || nextProfile.businessName,
      agent_name: nextProfile.agentName,
      business_name: selectedTenant?.name || nextProfile.businessName,
      welcome_message: nextProfile.welcome,
      instructions: nextProfile.instructions,
      outbound_enabled: nextType === "fleet",
    }));
  }

  function metadataPayload() {
    return {
      agent_name: form.agent_name,
      business_name: form.business_name,
      welcome_message: form.welcome_message,
      instructions: form.instructions,
      voice: form.voice,
      voice_id: form.voice_id,
      company_number: form.company_number,
      handoff_phone: form.handoff_phone,
      outbound_enabled: form.outbound_enabled,
      service_radius_miles: Number(form.service_radius_miles) || 50,
      supported_services: form.supported_services.split(",").map((item) => item.trim()).filter(Boolean),
      dispatch_phone: form.handoff_phone || form.contact_phone || undefined,
      fleet_data_url: form.fleet_data_url || undefined,
      calcom: {
        enabled: form.calcom_enabled,
        base_url: form.calcom_base_url,
        api_key_configured: Boolean(form.calcom_api_key),
        username: form.calcom_username,
        event_slug: form.calcom_event_slug,
        event_type_id: form.calcom_event_type_id,
        calendar_url: form.calcom_calendar_url,
        timezone: form.calcom_timezone,
        appointment_rules: form.appointment_rules,
      },
      ...(voiceClone
        ? {
            voice_clone_enabled: voiceClone.enabled,
            voice_clone_name: voiceClone.cloneName,
            voice_sample_name: voiceClone.sampleName,
            voice_sample_source: voiceClone.sampleSource,
          }
        : {}),
    };
  }

  async function createClientAccount() {
    if (!form.organization_name.trim()) {
      setError("Client business name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await adminFetch<{ tenant: TenantView; warnings?: string[] }>("/provisioning/tenants", {
        method: "POST",
        body: JSON.stringify({
          plan_id: form.plan_id,
          organization_name: form.organization_name,
          vertical_type: agentType === "roadside" ? "fleet" : agentType,
          contact_email: form.contact_email || null,
          contact_phone: form.contact_phone || null,
          subscription_status: "active",
          setup_fee_status: "paid",
          onboarding_status: "in_progress",
          provision_retell: false,
          retell_conversation_flow_id: form.retell_conversation_flow_id || null,
          retell_phone_number_id: form.retell_phone_number_id || null,
          retell_voice_id: form.voice_id,
          metadata: metadataPayload(),
        }),
      });
      setSelectedTenantId(result.tenant.id);
      setMessage(result.warnings?.length ? `Client account created. ${result.warnings.join(" ")}` : "Client account created. Review settings, then create the Retell agent.");
      await load();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create client account");
    } finally {
      setSaving(false);
    }
  }

  async function provisionRetellAgent() {
    if (!selectedTenant) {
      setError("Create or select a client account before provisioning Retell.");
      return;
    }
    setProvisioning(true);
    setError(null);
    setMessage(null);
    try {
      await adminFetch(`/provisioning/admin/tenants/${selectedTenant.id}/retell/provision`, {
        method: "POST",
        body: JSON.stringify({
          conversation_flow_id: form.retell_conversation_flow_id || null,
          phone_number_id: form.retell_phone_number_id || null,
          voice_id: form.voice_id,
          metadata: metadataPayload(),
        }),
      });
      setMessage("Retell agent created or synced from Roadcall. This page remains the source of truth.");
      await load();
    } catch (provisionError) {
      setError(provisionError instanceof Error ? provisionError.message : "Could not provision Retell agent");
    } finally {
      setProvisioning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/25 bg-roadcall-cyan/10 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-roadcall-cyan">
            <Sparkles className="h-3.5 w-3.5" /> Agent provisioning
          </div>
          <h1 className="mt-4 text-3xl font-black text-white">Configure and launch client AI agents</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Build shop and fleet agents in Roadcall, including Retell voice settings, phone routing, Cal.com OSS scheduling, and subscriber context. Retell becomes the execution layer; Roadcall stays the control room.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={load} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
          <a href="/admin" className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10">
            Overview dashboard <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      {(message || error) && (
        <div className={`rounded-xl border px-4 py-3 text-sm ${error ? "border-red-500/25 bg-red-500/10 text-red-200" : "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"}`}>
          {error || message}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <aside className="space-y-4">
          <div className="rounded-2xl border border-white/5 bg-slate-950/80 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-white">Client accounts</p>
                <p className="text-xs text-slate-500">Select or create</p>
              </div>
              <Badge tone="blue">{tenants.length}</Badge>
            </div>
            <div className="mt-4 max-h-[520px] space-y-2 overflow-y-auto pr-1">
              {loading ? <div className="py-8 text-center text-sm text-slate-500"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Loading clients</div> : null}
              {tenants.map((tenant) => (
                <button
                  key={tenant.id}
                  type="button"
                  onClick={() => setSelectedTenantId(tenant.id)}
                  className={`w-full rounded-xl border p-3 text-left transition ${selectedTenant?.id === tenant.id ? "border-roadcall-cyan/45 bg-roadcall-cyan/10" : "border-white/5 bg-white/[0.03] hover:bg-white/[0.06]"}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-white">{tenant.name}</p>
                      <p className="mt-1 text-xs text-slate-500">{tenant.vertical_type} · {tenant.current_plan}</p>
                    </div>
                    <Badge tone={statusTone(tenant.retell_connection?.provisioning_status)}>{tenant.retell_connection?.provisioning_status || "new"}</Badge>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="overflow-hidden rounded-2xl border border-roadcall-cyan/15 bg-slate-950/80">
          <div className="border-b border-white/5 p-5">
            <div className="grid gap-3 lg:grid-cols-3">
              {(Object.keys(profiles) as AgentType[]).map((type) => {
                const agentProfile = profiles[type];
                const Icon = agentProfile.icon;
                const active = agentType === type;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => switchAgentType(type)}
                    className={`flex items-center gap-3 rounded-xl border p-4 text-left transition ${active ? "border-roadcall-cyan bg-roadcall-cyan/10" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"}`}
                  >
                    <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${active ? "bg-roadcall-cyan/15 text-roadcall-cyan" : "bg-white/10 text-slate-400"}`}><Icon className="h-5 w-5" /></span>
                    <span>
                      <span className="block font-bold text-white">{agentProfile.label}</span>
                      <span className="mt-1 block text-xs text-slate-400">{agentProfile.badge}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border-b border-white/5 px-5 py-4">
            <div className="flex flex-wrap gap-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-roadcall-cyan text-slate-950" : "bg-white/10 text-slate-300 hover:bg-white/15 hover:text-white"}`}
                  >
                    <Icon className="h-4 w-4" /> {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="p-5">
            {activeTab === "conversation" && (
              <div className="grid gap-5 lg:grid-cols-2">
                <Field label="Client business name"><input value={form.organization_name} onChange={(event) => setForm((current) => ({ ...current, organization_name: event.target.value, business_name: event.target.value }))} className={inputClass} /></Field>
                <Field label="Agent name"><input value={form.agent_name} onChange={(event) => setForm((current) => ({ ...current, agent_name: event.target.value }))} className={inputClass} /></Field>
                <Field label="Contact email"><input value={form.contact_email} onChange={(event) => setForm((current) => ({ ...current, contact_email: event.target.value }))} className={inputClass} /></Field>
                <Field label="Contact phone"><input value={form.contact_phone} onChange={(event) => setForm((current) => ({ ...current, contact_phone: event.target.value, company_number: event.target.value, handoff_phone: event.target.value }))} className={inputClass} /></Field>
                <Field label="Welcome message" className="lg:col-span-2"><textarea value={form.welcome_message} onChange={(event) => setForm((current) => ({ ...current, welcome_message: event.target.value }))} className={textareaClass} rows={4} /></Field>
                <Field label="Agent instructions" className="lg:col-span-2"><textarea value={form.instructions} onChange={(event) => setForm((current) => ({ ...current, instructions: event.target.value }))} className={textareaClass} rows={8} /></Field>
              </div>
            )}

            {activeTab === "voice" && (
              <div className="grid gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)]">
                <div className="space-y-3">
                  {[{ id: "female", label: "Female voice", voiceId: "11labs-Lily" }, { id: "male", label: "Male voice", voiceId: "11labs-Adrian" }, { id: "clone", label: "Cloned voice", voiceId: form.voice_id }].map((option) => (
                    <button key={option.id} type="button" onClick={() => setForm((current) => ({ ...current, voice: option.id, voice_id: option.voiceId }))} className={`flex w-full items-center gap-3 rounded-xl border p-4 text-left transition ${form.voice === option.id ? "border-roadcall-cyan bg-roadcall-cyan/10" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"}`}>
                      <Volume2 className="h-5 w-5 text-roadcall-cyan" />
                      <span><span className="block font-bold text-white">{option.label}</span><span className="mt-1 block text-xs text-slate-500">{option.voiceId || "Saved custom voice"}</span></span>
                    </button>
                  ))}
                  <Field label="Retell voice ID"><input value={form.voice_id} onChange={(event) => setForm((current) => ({ ...current, voice_id: event.target.value }))} className={inputClass} /></Field>
                </div>
                <VoiceCloneControls
                  enabled={form.voice === "clone"}
                  initialName={voiceClone?.cloneName || "Owner voice"}
                  onEnabledChange={(enabled) => enabled && setForm((current) => ({ ...current, voice: "clone" }))}
                  onSave={(sample) => { setVoiceClone(sample); setForm((current) => ({ ...current, voice: "clone" })); }}
                  onError={setError}
                  onMessage={setMessage}
                />
              </div>
            )}

            {activeTab === "phone" && (
              <div className="grid gap-5 lg:grid-cols-2">
                <Field label="Company number"><input value={form.company_number} onChange={(event) => setForm((current) => ({ ...current, company_number: event.target.value }))} className={inputClass} placeholder="+1" /></Field>
                <Field label="Human handoff number"><input value={form.handoff_phone} onChange={(event) => setForm((current) => ({ ...current, handoff_phone: event.target.value }))} className={inputClass} placeholder="+1" /></Field>
                <Field label="Retell conversation flow ID"><input value={form.retell_conversation_flow_id} onChange={(event) => setForm((current) => ({ ...current, retell_conversation_flow_id: event.target.value }))} className={inputClass} /></Field>
                <Field label="Retell phone number ID"><input value={form.retell_phone_number_id} onChange={(event) => setForm((current) => ({ ...current, retell_phone_number_id: event.target.value }))} className={inputClass} /></Field>
                <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm font-semibold text-slate-200"><input type="checkbox" checked={form.outbound_enabled} onChange={(event) => setForm((current) => ({ ...current, outbound_enabled: event.target.checked }))} className="h-4 w-4 accent-roadcall-cyan" /> Enable outbound vendor / driver calls</label>
              </div>
            )}

            {activeTab === "calendar" && (
              <div className="grid gap-5 lg:grid-cols-2">
                <label className="flex items-center gap-3 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm font-semibold text-emerald-100 lg:col-span-2"><input type="checkbox" checked={form.calcom_enabled} onChange={(event) => setForm((current) => ({ ...current, calcom_enabled: event.target.checked }))} className="h-4 w-4 accent-emerald-400" /> Enable Cal.com OSS appointment scheduling</label>
                <Field label="Cal.com base URL"><input value={form.calcom_base_url} onChange={(event) => setForm((current) => ({ ...current, calcom_base_url: event.target.value }))} className={inputClass} placeholder="https://cal.yourdomain.com" /></Field>
                <Field label="Cal.com API key"><input type="password" value={form.calcom_api_key} onChange={(event) => setForm((current) => ({ ...current, calcom_api_key: event.target.value }))} className={inputClass} placeholder="Stored when backend secrets are connected" /></Field>
                <Field label="Cal.com username"><input value={form.calcom_username} onChange={(event) => setForm((current) => ({ ...current, calcom_username: event.target.value }))} className={inputClass} /></Field>
                <Field label="Event slug"><input value={form.calcom_event_slug} onChange={(event) => setForm((current) => ({ ...current, calcom_event_slug: event.target.value }))} className={inputClass} /></Field>
                <Field label="Event type ID"><input value={form.calcom_event_type_id} onChange={(event) => setForm((current) => ({ ...current, calcom_event_type_id: event.target.value }))} className={inputClass} /></Field>
                <Field label="Public booking URL"><input value={form.calcom_calendar_url} onChange={(event) => setForm((current) => ({ ...current, calcom_calendar_url: event.target.value }))} className={inputClass} /></Field>
                <Field label="Default timezone"><input value={form.calcom_timezone} onChange={(event) => setForm((current) => ({ ...current, calcom_timezone: event.target.value }))} className={inputClass} /></Field>
                <Field label="Appointment rules" className="lg:col-span-2"><textarea value={form.appointment_rules} onChange={(event) => setForm((current) => ({ ...current, appointment_rules: event.target.value }))} className={textareaClass} rows={5} /></Field>
              </div>
            )}

            {activeTab === "advanced" && (
              <div className="grid gap-5 lg:grid-cols-2">
                <Field label="Plan"><select value={form.plan_id} onChange={(event) => setForm((current) => ({ ...current, plan_id: event.target.value }))} className={inputClass}>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select></Field>
                <Field label="Service radius miles"><input value={form.service_radius_miles} onChange={(event) => setForm((current) => ({ ...current, service_radius_miles: event.target.value }))} className={inputClass} /></Field>
                <Field label="Supported services" className="lg:col-span-2"><textarea value={form.supported_services} onChange={(event) => setForm((current) => ({ ...current, supported_services: event.target.value }))} className={textareaClass} rows={4} /></Field>
                <Field label="Fleet data URL"><input value={form.fleet_data_url} onChange={(event) => setForm((current) => ({ ...current, fleet_data_url: event.target.value }))} className={inputClass} placeholder="Private vehicle data source or API URL" /></Field>
              </div>
            )}
          </div>
        </main>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-roadcall-cyan/15 bg-slate-950/85 p-5 shadow-xl shadow-blue-950/20">
            <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full border border-roadcall-cyan/25 bg-roadcall-cyan/10 text-roadcall-cyan">
              <ProfileIcon className="h-9 w-9" />
            </div>
            <h2 className="mt-5 text-center text-xl font-black text-white">{form.agent_name}</h2>
            <p className="mt-2 text-center text-sm text-slate-400">{profile.badge}</p>
            <div className="mt-5 space-y-3 rounded-xl border border-white/10 bg-black/25 p-4 text-sm">
              <PreviewRow label="Client" value={form.business_name || form.organization_name} />
              <PreviewRow label="Voice" value={form.voice === "clone" ? voiceClone?.cloneName || "Cloned voice" : form.voice === "male" ? "Male voice" : "Female voice"} />
              <PreviewRow label="Phone" value={form.company_number || "Not assigned"} />
              <PreviewRow label="Calendar" value={form.calcom_enabled ? form.calcom_event_slug || "Enabled" : "Off"} />
              <PreviewRow label="Retell" value={selectedTenant?.retell_connection?.provisioning_status || "Not provisioned"} />
            </div>
            {selectedTenant?.retell_connection?.agent_id ? <p className="mt-3 break-all font-mono text-xs text-slate-500">{selectedTenant.retell_connection.agent_id}</p> : null}
            {selectedTenant?.retell_connection?.last_error ? <p className="mt-3 rounded-lg border border-red-500/20 bg-red-500/10 p-2 text-xs text-red-200">{selectedTenant.retell_connection.last_error}</p> : null}
            <div className="mt-5 grid gap-2">
              <button onClick={createClientAccount} disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-xl border border-roadcall-cyan/30 bg-roadcall-cyan/10 px-4 py-3 text-sm font-bold text-roadcall-cyan hover:bg-roadcall-cyan/20 disabled:opacity-50">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save / create client
              </button>
              <button onClick={provisionRetellAgent} disabled={provisioning || !selectedTenant} className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-4 py-3 text-sm font-bold text-white hover:brightness-110 disabled:opacity-50">
                {provisioning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />} Create / sync Retell agent
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-slate-950/80 p-5">
            <div className="mb-4 flex items-center gap-2"><Database className="h-5 w-5 text-blue-300" /><h2 className="font-bold text-white">Roadcall source of truth</h2></div>
            {[
              "Client account and plan",
              "Retell agent metadata",
              "Cal.com OSS scheduling settings",
              "Voice clone sample metadata",
              "Phone routing and handoff rules",
            ].map((item) => <div key={item} className="mb-2 flex items-center gap-2 text-sm text-slate-300"><CheckCircle2 className="h-4 w-4 text-emerald-300" />{item}</div>)}
          </div>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, children, className = "" }: { label: string; children: React.ReactNode; className?: string }) {
  return <label className={`space-y-2 text-sm font-semibold text-slate-300 ${className}`}><span>{label}</span>{children}</label>;
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between gap-4"><span className="text-slate-400">{label}</span><span className="truncate text-right font-bold text-white">{value || "Not assigned"}</span></div>;
}
