"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BadgeCheck,
  Bot,
  Building2,
  CheckCircle2,
  Crown,
  ExternalLink,
  Loader2,
  Lock,
  Mic2,
  Play,
  PhoneCall,
  RefreshCw,
  ShieldCheck,
  Square,
  Truck,
  Upload,
  Workflow,
  Zap,
} from "lucide-react";
import { adminFetch } from "@/lib/admin-auth";

interface PlanConfig {
  id: string;
  name: string;
  price_monthly: number;
  setup_fee: number;
  enabled_features: string[];
  ghl_snapshot_id: string;
  allowed_modules: string[];
  webhook_permissions: string[];
  dashboard_permissions: string[];
  dispatch_permissions: string[];
  ai_feature_permissions: string[];
}

interface GHLConnectionView {
  location_id?: string | null;
  subaccount_name?: string | null;
  snapshot_id?: string | null;
  snapshot_status: string;
  connection_status: string;
  last_synced_at?: string | null;
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
  vertical_type: "shops" | "fleet" | string;
  contact_email?: string | null;
  contact_phone?: string | null;
  current_plan: string;
  subscription_status: string;
  onboarding_status: string;
  setup_fee_status: string;
  enabled_features: string[];
  locked_features: string[];
  ghl_connection?: GHLConnectionView | null;
  retell_connection?: RetellConnectionView | null;
  llm_model?: string | null;
  voice_id?: string | null;
  calls_handled: number;
  leads_allocated: number;
  vehicle_count: number;
  fleet_size?: number | null;
  snapshot_status?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ProvisioningSnapshotView {
  vertical_type: "shops" | "fleet" | string;
  label: string;
  description: string;
  tenant_count: number;
  active_subscribers: number;
  ai_phone_active: number;
  calls_handled: number;
  vehicle_count: number;
  fleet_size: number;
  snapshot_ready: number;
  snapshot_pending: number;
  llm_models: string[];
}

interface TenantListResponse {
  tenants: TenantView[];
  plans: PlanConfig[];
  snapshots?: ProvisioningSnapshotView[];
}

interface DispatchEventView {
  id: string;
  tenant_id?: string | null;
  event_type: string;
  status: string;
  created_at: string;
  payload_json?: Record<string, unknown> | null;
}

type VoiceSampleSource = "recorded" | "uploaded" | null;

const FEATURE_LABELS: Record<string, string> = {
  ai_answering: "AI answering",
  missed_call_text_back: "Missed-call text back",
  basic_crm_sync: "Basic CRM sync",
  lead_capture: "Lead capture",
  sms_follow_up: "SMS follow-up",
  basic_ai_summaries: "AI summaries",
  website_widget: "Website widget",
  advanced_ai_workflows: "Advanced AI workflows",
  appointment_scheduling: "Appointment scheduling",
  smart_routing: "Smart routing",
  advanced_analytics: "Advanced analytics",
  team_notifications: "Team notifications",
  multi_location_support: "Multi-location support",
  gps_capture: "SMS GPS capture",
  roadside_intake: "Roadside intake",
  dispatch_workflow: "Dispatch workflows",
  mechanic_assignment: "Mechanic assignment",
  fleet_notification: "Fleet notifications",
  dispatch_dashboard: "Dispatch dashboard",
  emergency_routing: "Emergency routing",
  real_time_roadside_status: "Real-time roadside status",
  external_dispatch_api: "External dispatch API",
};

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/85 to-slate-950 shadow-lg ${className}`}>{children}</div>;
}

function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "emerald" | "amber" | "red" | "blue" | "slate" | "orange" }) {
  const classes = {
    emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/20",
    red: "bg-red-500/15 text-red-300 border-red-500/20",
    blue: "bg-blue-500/15 text-blue-300 border-blue-500/20",
    orange: "bg-orange-500/15 text-orange-300 border-orange-500/20",
    slate: "bg-white/5 text-slate-300 border-white/10",
  }[tone];
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${classes}`}>{children}</span>;
}

function featureLabel(feature: string) {
  return FEATURE_LABELS[feature] || feature.replaceAll("_", " ");
}

function statusTone(status?: string | null): "emerald" | "amber" | "red" | "slate" {
  if (!status) return "slate";
  if (["active", "connected", "installed", "paid", "activated", "healthy", "completed", "ready", "configured"].includes(status)) return "emerald";
  if (["failed", "cancelled", "missing_snapshot_id"].includes(status)) return "red";
  if (["pending", "not_started", "unpaid", "pending_location"].includes(status)) return "amber";
  return "slate";
}

function SnapshotPanel({ snapshot, selected, onSelect }: { snapshot: ProvisioningSnapshotView; selected: boolean; onSelect: () => void }) {
  const isFleet = snapshot.vertical_type === "fleet";
  const Icon = isFleet ? Truck : Building2;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group rounded-2xl border p-5 text-left transition ${selected ? "border-blue-400/45 bg-blue-500/10 shadow-lg shadow-blue-950/25" : "border-white/5 bg-slate-950/70 hover:border-white/15 hover:bg-white/[0.04]"}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${isFleet ? "bg-orange-500/15 text-orange-300" : "bg-cyan-500/15 text-cyan-300"}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-white">{snapshot.label}</p>
            <p className="mt-1 text-xs text-slate-500">{snapshot.description}</p>
          </div>
        </div>
        <Badge tone={snapshot.snapshot_pending ? "amber" : "emerald"}>{snapshot.snapshot_pending ? `${snapshot.snapshot_pending} pending` : "ready"}</Badge>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
        <div><p className="text-xl font-bold text-white">{snapshot.active_subscribers}</p><p className="text-xs text-slate-500">Active</p></div>
        <div><p className="text-xl font-bold text-white">{snapshot.ai_phone_active}</p><p className="text-xs text-slate-500">AI phone</p></div>
        <div><p className="text-xl font-bold text-white">{snapshot.calls_handled.toLocaleString()}</p><p className="text-xs text-slate-500">Calls</p></div>
        <div><p className="text-xl font-bold text-white">{isFleet ? snapshot.vehicle_count.toLocaleString() : snapshot.tenant_count}</p><p className="text-xs text-slate-500">{isFleet ? "Vehicles" : "Accounts"}</p></div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {(snapshot.llm_models.length ? snapshot.llm_models : ["Retell conversation flow"]).slice(0, 3).map((model) => <Badge key={model} tone="blue"><Bot className="mr-1 h-3 w-3" />{model}</Badge>)}
      </div>
    </button>
  );
}

export default function ProvisioningPage() {
  const [tenants, setTenants] = useState<TenantView[]>([]);
  const [plans, setPlans] = useState<PlanConfig[]>([]);
  const [snapshots, setSnapshots] = useState<ProvisioningSnapshotView[]>([]);
  const [dispatchEvents, setDispatchEvents] = useState<DispatchEventView[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPlan, setSavingPlan] = useState<string | null>(null);
  const [provisioningRetell, setProvisioningRetell] = useState<string | null>(null);
  const [creatingSubscriber, setCreatingSubscriber] = useState(false);
  const [voiceCloneEnabled, setVoiceCloneEnabled] = useState(false);
  const [voiceCloneName, setVoiceCloneName] = useState("Owner voice");
  const [sampleName, setSampleName] = useState("");
  const [sampleSource, setSampleSource] = useState<VoiceSampleSource>(null);
  const [sampleUrl, setSampleUrl] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<BlobPart[]>([]);
  const sampleUrlRef = useRef<string | null>(null);
  const [newSubscriber, setNewSubscriber] = useState({
    organization_name: "",
    vertical_type: "shops",
    contact_email: "",
    contact_phone: "",
    plan_id: "growth",
    service_radius_miles: "50",
    supported_services: "tire, no_start, air_leak, dpf_derate, electrical, trailer_repair, overheating, towing, pm_service",
  });
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedTenant = useMemo(() => tenants.find((tenant) => tenant.id === selectedTenantId) || tenants[0], [selectedTenantId, tenants]);
  const selectedPlan = useMemo(() => plans.find((plan) => plan.id === selectedTenant?.current_plan), [plans, selectedTenant]);
  const activeSubscribers = tenants.filter((tenant) => tenant.is_active && tenant.subscription_status === "active").length;
  const activeRetell = tenants.filter((tenant) => tenant.retell_connection?.provisioning_status === "active").length;
  const totalCalls = tenants.reduce((sum, tenant) => sum + (tenant.calls_handled || 0), 0);
  const totalVehicles = tenants.reduce((sum, tenant) => sum + (tenant.vehicle_count || 0), 0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tenantData, dispatchData] = await Promise.all([
        adminFetch<TenantListResponse>("/provisioning/admin/tenants"),
        adminFetch<DispatchEventView[]>("/provisioning/admin/dispatch-events?limit=25"),
      ]);
      setTenants(tenantData.tenants);
      setPlans(tenantData.plans);
      setSnapshots(tenantData.snapshots || []);
      setDispatchEvents(dispatchData);
      if (!selectedTenantId && tenantData.tenants[0]) setSelectedTenantId(tenantData.tenants[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load provisioning status");
    } finally {
      setLoading(false);
    }
  }, [selectedTenantId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    return () => {
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());
      if (sampleUrlRef.current) URL.revokeObjectURL(sampleUrlRef.current);
    };
  }, []);

  function setVoiceSample(next: { name: string; source: Exclude<VoiceSampleSource, null>; url: string }) {
    if (sampleUrlRef.current) URL.revokeObjectURL(sampleUrlRef.current);
    sampleUrlRef.current = next.url;
    setSampleUrl(next.url);
    setSampleName(next.name);
    setSampleSource(next.source);
    setVoiceCloneEnabled(true);
    setError(null);
  }

  async function startVoiceRecording() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser cannot record audio here. Upload an audio sample instead.");
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
          setError("No audio was captured. Try recording again or upload a sample.");
          return;
        }
        const url = URL.createObjectURL(blob);
        const extension = recorder.mimeType.includes("mp4") ? "m4a" : "webm";
        setVoiceSample({ name: `Recorded voice sample.${extension}`, source: "recorded", url });
        setMessage("Voice sample recorded. Listen back, then save the clone when it sounds right.");
      };
      recorder.start();
      setRecording(true);
      setMessage("Recording voice sample. Speak naturally, then stop recording.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone access was blocked. Upload an audio sample instead.");
    }
  }

  function stopVoiceRecording() {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    setRecording(false);
  }

  function handleVoiceUpload(file?: File) {
    if (!file) return;
    if (!file.type.startsWith("audio/")) {
      setError("Upload an audio file such as MP3, WAV, M4A, or WEBM.");
      return;
    }
    const url = URL.createObjectURL(file);
    setVoiceSample({ name: file.name, source: "uploaded", url });
    setMessage("Voice sample uploaded. Listen back, then save the clone when it sounds right.");
  }

  function saveVoiceClone() {
    if (!sampleName || !sampleSource) {
      setError("Record or upload a voice sample before saving the clone.");
      return;
    }
    setVoiceCloneEnabled(true);
    setMessage(`${voiceCloneName || "Cloned voice"} saved from ${sampleSource === "recorded" ? "a recorded" : "an uploaded"} voice sample.`);
    setError(null);
  }

  async function changePlan(tenantId: string, planId: string) {
    setSavingPlan(tenantId);
    setError(null);
    setMessage(null);
    try {
      await adminFetch(`/provisioning/admin/tenants/${tenantId}/plan`, {
        method: "PATCH",
        body: JSON.stringify({ plan_id: planId, subscription_status: "active" }),
      });
      setMessage("Subscriber plan updated. Sync the AI phone agent to apply telephony changes.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update plan");
    } finally {
      setSavingPlan(null);
    }
  }

  async function createSubscriber() {
    if (!newSubscriber.organization_name.trim()) {
      setError("Business name is required");
      return;
    }
    setCreatingSubscriber(true);
    setError(null);
    setMessage(null);
    try {
      const metadata = {
        service_radius_miles: Number(newSubscriber.service_radius_miles) || 50,
        supported_services: newSubscriber.supported_services.split(",").map((item) => item.trim()).filter(Boolean),
        mobile_service_available: true,
        after_hours_mode: "capture_and_escalate",
        dispatch_phone: newSubscriber.contact_phone || undefined,
        vertical_type: newSubscriber.vertical_type,
      };
      const result = await adminFetch<{ tenant: TenantView; warnings?: string[] }>("/provisioning/tenants", {
        method: "POST",
        body: JSON.stringify({
          plan_id: newSubscriber.plan_id,
          organization_name: newSubscriber.organization_name,
          vertical_type: newSubscriber.vertical_type,
          contact_email: newSubscriber.contact_email || null,
          contact_phone: newSubscriber.contact_phone || null,
          subscription_status: "active",
          setup_fee_status: "paid",
          onboarding_status: "in_progress",
          provision_retell: true,
          metadata,
        }),
      });
      setMessage(result.warnings?.length ? `Subscriber created. ${result.warnings.join(" ")}` : "Subscriber created and AI phone provisioning started.");
      setSelectedTenantId(result.tenant.id);
      setNewSubscriber((current) => ({ ...current, organization_name: "", contact_email: "", contact_phone: "" }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create subscriber");
    } finally {
      setCreatingSubscriber(false);
    }
  }

  async function provisionSelectedRetell() {
    if (!selectedTenant) return;
    setProvisioningRetell(selectedTenant.id);
    setError(null);
    setMessage(null);
    try {
      await adminFetch(`/provisioning/admin/tenants/${selectedTenant.id}/retell/provision`, {
        method: "POST",
        body: JSON.stringify({
          metadata: {
            ...(selectedTenant.retell_connection?.dynamic_variables || {}),
            ...(voiceCloneEnabled && sampleName
              ? {
                  voice_clone_enabled: true,
                  voice_clone_name: voiceCloneName || "Cloned voice",
                  voice_sample_name: sampleName,
                  voice_sample_source: sampleSource,
                }
              : {}),
          },
        }),
      });
      setMessage("AI phone agent provisioned. The subscriber should now appear in the voice dashboard.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not provision AI phone agent");
    } finally {
      setProvisioningRetell(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-white"><Crown className="h-7 w-7 text-orange-300" /> SaaS Provisioning</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Provision shop and fleet accounts, manage subscriber plans, and track AI phone usage, LLM routing, calls, vehicles, and dispatch readiness from one SaaS control room.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <a href="https://dashboard.retellai.com/agents" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-blue-400/25 bg-blue-500/10 px-3 py-2 text-sm font-semibold text-blue-200 hover:bg-blue-500/20">
            <PhoneCall className="h-4 w-4" /> Retell Agents <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <button onClick={load} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {(message || error) && (
        <div className={`rounded-xl border px-4 py-3 text-sm ${error ? "border-red-500/25 bg-red-500/10 text-red-200" : "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"}`}>
          {error || message}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-5"><div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-cyan-300" /><div><p className="text-2xl font-bold text-white">{loading ? "—" : activeSubscribers}</p><p className="text-xs text-slate-400">Active subscribers</p></div></div></Card>
        <Card className="p-5"><div className="flex items-center gap-3"><Workflow className="h-5 w-5 text-blue-300" /><div><p className="text-2xl font-bold text-white">{activeRetell}</p><p className="text-xs text-slate-400">AI phone active</p></div></div></Card>
        <Card className="p-5"><div className="flex items-center gap-3"><PhoneCall className="h-5 w-5 text-emerald-300" /><div><p className="text-2xl font-bold text-white">{totalCalls.toLocaleString()}</p><p className="text-xs text-slate-400">Calls handled</p></div></div></Card>
        <Card className="p-5"><div className="flex items-center gap-3"><Truck className="h-5 w-5 text-orange-300" /><div><p className="text-2xl font-bold text-white">{totalVehicles.toLocaleString()}</p><p className="text-xs text-slate-400">Fleet vehicles</p></div></div></Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {(snapshots.length ? snapshots : [
          { vertical_type: "shops", label: "Shop AI Snapshot", description: "Provision repair shop AI reception and follow-up workflows.", tenant_count: 0, active_subscribers: 0, ai_phone_active: 0, calls_handled: 0, vehicle_count: 0, fleet_size: 0, snapshot_ready: 0, snapshot_pending: 0, llm_models: [] },
          { vertical_type: "fleet", label: "Fleet AI Snapshot", description: "Provision fleet dispatch, vehicles, and roadside workflows.", tenant_count: 0, active_subscribers: 0, ai_phone_active: 0, calls_handled: 0, vehicle_count: 0, fleet_size: 0, snapshot_ready: 0, snapshot_pending: 0, llm_models: [] },
        ]).map((snapshot) => (
          <SnapshotPanel
            key={snapshot.vertical_type}
            snapshot={snapshot}
            selected={newSubscriber.vertical_type === snapshot.vertical_type}
            onSelect={() => setNewSubscriber((current) => ({ ...current, vertical_type: snapshot.vertical_type }))}
          />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card>
          <div className="border-b border-white/5 px-6 py-4">
            <h2 className="font-semibold text-white">Subscriber Operations</h2>
            <p className="mt-1 text-xs text-slate-500">Manage plans, AI agents, LLM routing, call volume, and fleet assets for every Roadcall subscriber.</p>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12 text-slate-400"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading tenants…</div>
          ) : tenants.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-500">No tenants provisioned yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-white/5 text-left text-xs uppercase tracking-wide text-slate-500"><th className="px-4 py-3">Subscriber</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3">LLM</th><th className="px-4 py-3">Calls</th><th className="px-4 py-3">Vehicles</th><th className="px-4 py-3">AI Phone</th><th className="px-4 py-3">Snapshot</th><th className="px-4 py-3">Change Plan</th></tr></thead>
                <tbody className="divide-y divide-white/5">
                  {tenants.map((tenant) => (
                    <tr key={tenant.id} onClick={() => setSelectedTenantId(tenant.id)} className={`cursor-pointer hover:bg-white/[0.03] ${selectedTenant?.id === tenant.id ? "bg-blue-500/5" : ""}`}>
                      <td className="px-4 py-3"><p className="font-medium text-slate-200">{tenant.name}</p><p className="text-xs text-slate-500">{tenant.contact_email || tenant.contact_phone || tenant.organization_id}</p></td>
                      <td className="px-4 py-3"><Badge tone={tenant.vertical_type === "fleet" ? "orange" : "blue"}>{tenant.vertical_type}</Badge></td>
                      <td className="px-4 py-3"><Badge tone={tenant.current_plan === "pro" ? "orange" : tenant.current_plan === "growth" ? "blue" : "slate"}>{tenant.current_plan}</Badge></td>
                      <td className="px-4 py-3"><span className="max-w-[180px] truncate text-xs text-slate-300">{tenant.llm_model || "Retell conversation flow"}</span></td>
                      <td className="px-4 py-3"><span className="font-semibold text-slate-200">{(tenant.calls_handled || 0).toLocaleString()}</span></td>
                      <td className="px-4 py-3"><span className="font-semibold text-slate-200">{tenant.vertical_type === "fleet" ? (tenant.vehicle_count || tenant.fleet_size || 0).toLocaleString() : "—"}</span></td>
                      <td className="px-4 py-3"><Badge tone={statusTone(tenant.retell_connection?.provisioning_status)}>{tenant.retell_connection?.provisioning_status || "not_provisioned"}</Badge></td>
                      <td className="px-4 py-3"><Badge tone={statusTone(tenant.snapshot_status)}>{tenant.snapshot_status || "unknown"}</Badge></td>
                      <td className="px-4 py-3">
                        <select
                          value={tenant.current_plan}
                          disabled={savingPlan === tenant.id}
                          onClick={(event) => event.stopPropagation()}
                          onChange={(event) => changePlan(tenant.id, event.target.value)}
                          className="rounded-lg border border-white/10 bg-slate-950 px-2 py-1 text-xs text-slate-200"
                        >
                          {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="font-semibold text-white">Provision Subscriber</h2>
            <p className="mt-1 text-xs text-slate-500">Creates a shop or fleet tenant and provisions the matching AI service-desk agent.</p>
            <div className="mt-4 grid gap-3">
              <div className="grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-slate-950 p-1">
                {[
                  { value: "shops", label: "Shop", icon: Building2 },
                  { value: "fleet", label: "Fleet", icon: Truck },
                ].map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setNewSubscriber((current) => ({ ...current, vertical_type: item.value }))}
                    className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${newSubscriber.vertical_type === item.value ? "bg-blue-500 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
                  >
                    <item.icon className="h-4 w-4" /> {item.label}
                  </button>
                ))}
              </div>
              <input value={newSubscriber.organization_name} onChange={(event) => setNewSubscriber((current) => ({ ...current, organization_name: event.target.value }))} placeholder="Shop / subscriber name" className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-400" />
              <input value={newSubscriber.contact_email} onChange={(event) => setNewSubscriber((current) => ({ ...current, contact_email: event.target.value }))} placeholder="Contact email" className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-400" />
              <input value={newSubscriber.contact_phone} onChange={(event) => setNewSubscriber((current) => ({ ...current, contact_phone: event.target.value }))} placeholder="Dispatch phone" className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-400" />
              <div className="grid grid-cols-2 gap-3">
                <select value={newSubscriber.plan_id} onChange={(event) => setNewSubscriber((current) => ({ ...current, plan_id: event.target.value }))} className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200">
                  {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}
                </select>
                <input value={newSubscriber.service_radius_miles} onChange={(event) => setNewSubscriber((current) => ({ ...current, service_radius_miles: event.target.value }))} placeholder="Radius miles" className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-400" />
              </div>
              <textarea value={newSubscriber.supported_services} onChange={(event) => setNewSubscriber((current) => ({ ...current, supported_services: event.target.value }))} rows={3} placeholder="Supported services" className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-400" />
              <button onClick={createSubscriber} disabled={creatingSubscriber || loading} className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-400 disabled:opacity-50">
                {creatingSubscriber && <Loader2 className="h-4 w-4 animate-spin" />} Provision {newSubscriber.vertical_type === "fleet" ? "Fleet" : "Shop"} Account
              </button>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="font-semibold text-white">Current Plan</h2>
            {selectedTenant && selectedPlan ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
                  <div className="flex items-start justify-between gap-3"><div><p className="text-lg font-bold text-white">{selectedTenant.name}</p><p className="text-sm text-slate-400">{selectedPlan.name} · ${selectedPlan.price_monthly}/mo · ${selectedPlan.setup_fee} setup</p></div><Badge tone={selectedTenant.is_active ? "emerald" : "red"}>{selectedTenant.subscription_status}</Badge></div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl border border-white/5 bg-slate-950/70 p-3"><p className="text-xl font-bold text-white">{(selectedTenant.calls_handled || 0).toLocaleString()}</p><p className="text-xs text-slate-500">Calls handled</p></div>
                  <div className="rounded-xl border border-white/5 bg-slate-950/70 p-3"><p className="text-xl font-bold text-white">{selectedTenant.vertical_type === "fleet" ? (selectedTenant.vehicle_count || selectedTenant.fleet_size || 0).toLocaleString() : (selectedTenant.leads_allocated || 0).toLocaleString()}</p><p className="text-xs text-slate-500">{selectedTenant.vertical_type === "fleet" ? "Vehicles" : "Leads"}</p></div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Badge tone={selectedTenant.vertical_type === "fleet" ? "orange" : "blue"}>Type: {selectedTenant.vertical_type}</Badge>
                  <Badge tone={statusTone(selectedTenant.snapshot_status)}>Snapshot: {selectedTenant.snapshot_status || "unknown"}</Badge>
                  <Badge tone={statusTone(selectedTenant.onboarding_status)}>Onboarding: {selectedTenant.onboarding_status}</Badge>
                  <Badge tone={statusTone(selectedTenant.setup_fee_status)}>Setup: {selectedTenant.setup_fee_status}</Badge>
                  <Badge tone={statusTone(selectedTenant.retell_connection?.provisioning_status)}>AI Phone: {selectedTenant.retell_connection?.provisioning_status || "not_provisioned"}</Badge>
                  <Badge tone={selectedTenant.retell_connection?.agent_id ? "emerald" : "amber"}>Agent: {selectedTenant.retell_connection?.agent_id ? "created" : "missing"}</Badge>
                </div>
                <div className="rounded-xl border border-white/5 bg-slate-950/70 p-3 text-xs text-slate-400">
                  <p className="font-semibold text-slate-300">LLM / voice routing</p>
                  <p className="mt-1">{selectedTenant.llm_model || "Retell conversation flow"}{selectedTenant.voice_id ? ` · ${selectedTenant.voice_id}` : ""}</p>
                </div>
                <div className="rounded-xl border border-violet-300/20 bg-violet-500/10 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/15 text-violet-200">
                        <Mic2 className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="font-semibold text-white">Voice cloning</p>
                        <p className="mt-1 text-xs text-slate-400">Record through this computer or upload an existing voice sample.</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setVoiceCloneEnabled((enabled) => !enabled)}
                      className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${voiceCloneEnabled ? "bg-violet-400 text-white" : "bg-white/10 text-slate-200 ring-1 ring-white/15"}`}
                    >
                      {voiceCloneEnabled ? "Enabled" : "Enable"}
                    </button>
                  </div>
                  {voiceCloneEnabled && (
                    <div className="mt-4 space-y-4">
                      <input
                        value={voiceCloneName}
                        onChange={(event) => setVoiceCloneName(event.target.value)}
                        placeholder="Clone name"
                        className="w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-violet-300"
                      />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-xl border border-dashed border-violet-300/35 bg-slate-950/70 p-4">
                          <div className="flex items-center gap-2 text-sm font-semibold text-violet-100"><Mic2 className="h-4 w-4" /> Speak to computer</div>
                          <button
                            type="button"
                            onClick={recording ? stopVoiceRecording : startVoiceRecording}
                            className={`mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${recording ? "bg-red-400 text-slate-950 hover:bg-red-300" : "bg-slate-900 text-white ring-1 ring-white/10 hover:bg-white/10"}`}
                          >
                            {recording ? <Square className="h-4 w-4" /> : <Mic2 className="h-4 w-4" />}
                            {recording ? "Stop recording" : "Record sample"}
                          </button>
                        </div>
                        <label className="flex cursor-pointer flex-col rounded-xl border border-dashed border-violet-300/35 bg-slate-950/70 p-4 transition hover:bg-white/[0.04]">
                          <span className="flex items-center gap-2 text-sm font-semibold text-violet-100"><Upload className="h-4 w-4" /> Upload voice</span>
                          <span className="mt-3 inline-flex w-full items-center justify-center rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white ring-1 ring-white/10">Choose audio file</span>
                          <input type="file" accept="audio/*" className="sr-only" onChange={(event) => handleVoiceUpload(event.target.files?.[0])} />
                        </label>
                      </div>
                      {sampleName && (
                        <div className="rounded-xl border border-white/10 bg-slate-950/80 p-3">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <p className="text-sm font-semibold text-white">{sampleName}</p>
                              <p className="mt-1 text-xs capitalize text-slate-500">{sampleSource} voice sample ready.</p>
                            </div>
                            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200"><BadgeCheck className="h-4 w-4" /> Ready</span>
                          </div>
                          {sampleUrl && <audio controls src={sampleUrl} className="mt-3 w-full" aria-label="Voice sample playback" />}
                        </div>
                      )}
                      <button
                        type="button"
                        disabled={!sampleName || recording}
                        onClick={saveVoiceClone}
                        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-violet-400 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                      >
                        <Play className="h-4 w-4" /> Save voice clone
                      </button>
                    </div>
                  )}
                </div>
                <button onClick={provisionSelectedRetell} disabled={provisioningRetell === selectedTenant.id} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-blue-400/30 bg-blue-500/10 px-3 py-2 text-sm font-semibold text-blue-200 hover:bg-blue-500/20 disabled:opacity-50">
                  {provisioningRetell === selectedTenant.id && <Loader2 className="h-4 w-4 animate-spin" />} Sync / Provision AI Agent
                </button>
                {selectedTenant.retell_connection?.agent_id && <p className="font-mono text-xs text-slate-500">{selectedTenant.retell_connection.agent_id}</p>}
                {selectedTenant.retell_connection?.last_error && <p className="rounded-lg border border-red-500/20 bg-red-500/10 p-2 text-xs text-red-200">{selectedTenant.retell_connection.last_error}</p>}
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Onboarding checklist</p>
                  {["Setup fee paid", "AI agent created", "Phone routing configured", "Service advisor prompt ready", "Calendar scheduling pending", selectedTenant.current_plan === "pro" ? "Dispatch enabled" : "Dispatch locked until Pro"].map((item) => (
                    <div key={item} className="mb-2 flex items-center gap-2 text-sm text-slate-300"><CheckCircle2 className="h-4 w-4 text-emerald-300" /> {item}</div>
                  ))}
                </div>
              </div>
            ) : <p className="mt-4 text-sm text-slate-500">Select a tenant to inspect plan status.</p>}
          </Card>

          <Card className="p-6">
            <h2 className="font-semibold text-white">System Status</h2>
            <div className="mt-4 grid gap-2 text-sm">
              <div className="flex items-center justify-between"><span className="flex items-center gap-2 text-slate-400"><PhoneCall className="h-4 w-4" /> AI phone</span><Badge tone={selectedTenant?.enabled_features.includes("ai_answering") ? "emerald" : "red"}>{selectedTenant?.enabled_features.includes("ai_answering") ? "enabled" : "locked"}</Badge></div>
              <div className="flex items-center justify-between"><span className="flex items-center gap-2 text-slate-400"><Zap className="h-4 w-4" /> Widget</span><Badge tone={selectedTenant?.enabled_features.includes("website_widget") ? "emerald" : "red"}>{selectedTenant?.enabled_features.includes("website_widget") ? "enabled" : "locked"}</Badge></div>
              <div className="flex items-center justify-between"><span className="flex items-center gap-2 text-slate-400"><Truck className="h-4 w-4" /> Dispatch</span><Badge tone={selectedTenant?.current_plan === "pro" ? "emerald" : "amber"}>{selectedTenant?.current_plan === "pro" ? "pro enabled" : "upgrade required"}</Badge></div>
            </div>
          </Card>
        </div>
      </div>

      {selectedTenant && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="p-6">
            <h2 className="font-semibold text-white">Enabled Features</h2>
            <div className="mt-4 flex flex-wrap gap-2">{selectedTenant.enabled_features.map((feature) => <Badge key={feature} tone="emerald">{featureLabel(feature)}</Badge>)}</div>
          </Card>
          <Card className="p-6">
            <h2 className="font-semibold text-white">Locked Features</h2>
            <div className="mt-4 flex flex-wrap gap-2">{selectedTenant.locked_features.slice(0, 18).map((feature) => <Badge key={feature} tone="slate"><Lock className="mr-1 h-3 w-3" />{featureLabel(feature)}</Badge>)}</div>
            {selectedTenant.locked_features.length > 18 && <p className="mt-3 text-xs text-slate-500">+{selectedTenant.locked_features.length - 18} more locked features</p>}
          </Card>
        </div>
      )}

      <Card>
        <div className="border-b border-white/5 px-6 py-4"><h2 className="font-semibold text-white">Pro Dispatch Activity</h2><p className="text-xs text-slate-500">Visible for Pro tenants and admin operations.</p></div>
        {dispatchEvents.length === 0 ? <div className="py-8 text-center text-sm text-slate-500"><AlertTriangle className="mx-auto mb-2 h-5 w-5" />No dispatch events recorded yet.</div> : (
          <div className="divide-y divide-white/5">
            {dispatchEvents.map((event) => <div key={event.id} className="flex items-center justify-between gap-3 px-6 py-3 text-sm"><div><p className="font-medium text-slate-200">{event.event_type}</p><p className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</p></div><Badge tone={statusTone(event.status)}>{event.status}</Badge></div>)}
          </div>
        )}
      </Card>
    </div>
  );
}