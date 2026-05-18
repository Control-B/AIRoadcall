"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Crown,
  ExternalLink,
  Loader2,
  Lock,
  PhoneCall,
  RefreshCw,
  ShieldCheck,
  Truck,
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
  current_plan: string;
  subscription_status: string;
  onboarding_status: string;
  setup_fee_status: string;
  enabled_features: string[];
  locked_features: string[];
  ghl_connection?: GHLConnectionView | null;
  retell_connection?: RetellConnectionView | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface TenantListResponse {
  tenants: TenantView[];
  plans: PlanConfig[];
}

interface DispatchEventView {
  id: string;
  tenant_id?: string | null;
  event_type: string;
  status: string;
  created_at: string;
  payload_json?: Record<string, unknown> | null;
}

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
  if (["active", "connected", "installed", "paid", "activated", "healthy", "completed"].includes(status)) return "emerald";
  if (["failed", "cancelled", "missing_snapshot_id"].includes(status)) return "red";
  if (["pending", "not_started", "unpaid", "pending_location"].includes(status)) return "amber";
  return "slate";
}

export default function ProvisioningPage() {
  const [tenants, setTenants] = useState<TenantView[]>([]);
  const [plans, setPlans] = useState<PlanConfig[]>([]);
  const [dispatchEvents, setDispatchEvents] = useState<DispatchEventView[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPlan, setSavingPlan] = useState<string | null>(null);
  const [provisioningRetell, setProvisioningRetell] = useState<string | null>(null);
  const [creatingSubscriber, setCreatingSubscriber] = useState(false);
  const [newSubscriber, setNewSubscriber] = useState({
    organization_name: "",
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
  const proTenants = tenants.filter((tenant) => tenant.current_plan === "pro").length;
  const activeRetell = tenants.filter((tenant) => tenant.retell_connection?.provisioning_status === "active").length;

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
      };
      const result = await adminFetch<{ tenant: TenantView; warnings?: string[] }>("/provisioning/tenants", {
        method: "POST",
        body: JSON.stringify({
          plan_id: newSubscriber.plan_id,
          organization_name: newSubscriber.organization_name,
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
          metadata: selectedTenant.retell_connection?.dynamic_variables || {},
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
            Provision mechanic subscribers in Roadcall and mirror their AI telephony agent into the voice system. Roadcall stays the operating system for profiles, quotas, leads, and dispatch.
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
        <Card className="p-5"><div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-cyan-300" /><div><p className="text-2xl font-bold text-white">{loading ? "—" : tenants.length}</p><p className="text-xs text-slate-400">Tenants</p></div></div></Card>
        <Card className="p-5"><div className="flex items-center gap-3"><Workflow className="h-5 w-5 text-blue-300" /><div><p className="text-2xl font-bold text-white">{activeRetell}</p><p className="text-xs text-slate-400">AI phone active</p></div></div></Card>
        <Card className="p-5"><div className="flex items-center gap-3"><Truck className="h-5 w-5 text-orange-300" /><div><p className="text-2xl font-bold text-white">{proTenants}</p><p className="text-xs text-slate-400">Pro dispatch</p></div></div></Card>
        <Card className="p-5"><div className="flex items-center gap-3"><CheckCircle2 className="h-5 w-5 text-emerald-300" /><div><p className="text-2xl font-bold text-white">Healthy</p><p className="text-xs text-slate-400">Backend status</p></div></div></Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card>
          <div className="border-b border-white/5 px-6 py-4">
            <h2 className="font-semibold text-white">Tenant Plans</h2>
            <p className="mt-1 text-xs text-slate-500">Upgrade/downgrade subscribers and verify AI telephony provisioning state.</p>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12 text-slate-400"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading tenants…</div>
          ) : tenants.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-500">No tenants provisioned yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-white/5 text-left text-xs uppercase tracking-wide text-slate-500"><th className="px-4 py-3">Subscriber</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3">Setup</th><th className="px-4 py-3">AI Phone</th><th className="px-4 py-3">Agent</th><th className="px-4 py-3">Change Plan</th></tr></thead>
                <tbody className="divide-y divide-white/5">
                  {tenants.map((tenant) => (
                    <tr key={tenant.id} onClick={() => setSelectedTenantId(tenant.id)} className={`cursor-pointer hover:bg-white/[0.03] ${selectedTenant?.id === tenant.id ? "bg-blue-500/5" : ""}`}>
                      <td className="px-4 py-3"><p className="font-medium text-slate-200">{tenant.name}</p><p className="font-mono text-xs text-slate-500">{tenant.organization_id}</p></td>
                      <td className="px-4 py-3"><Badge tone={tenant.current_plan === "pro" ? "orange" : tenant.current_plan === "growth" ? "blue" : "slate"}>{tenant.current_plan}</Badge></td>
                      <td className="px-4 py-3"><Badge tone={statusTone(tenant.setup_fee_status)}>{tenant.setup_fee_status}</Badge></td>
                      <td className="px-4 py-3"><Badge tone={statusTone(tenant.retell_connection?.provisioning_status)}>{tenant.retell_connection?.provisioning_status || "not_provisioned"}</Badge></td>
                      <td className="px-4 py-3"><span className="font-mono text-xs text-slate-400">{tenant.retell_connection?.agent_id || "—"}</span></td>
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
            <p className="mt-1 text-xs text-slate-500">Creates the Roadcall tenant and provisions an AI service-desk agent.</p>
            <div className="mt-4 grid gap-3">
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
                {creatingSubscriber && <Loader2 className="h-4 w-4 animate-spin" />} Provision AI Phone
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
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Badge tone={statusTone(selectedTenant.onboarding_status)}>Onboarding: {selectedTenant.onboarding_status}</Badge>
                  <Badge tone={statusTone(selectedTenant.setup_fee_status)}>Setup: {selectedTenant.setup_fee_status}</Badge>
                  <Badge tone={statusTone(selectedTenant.retell_connection?.provisioning_status)}>AI Phone: {selectedTenant.retell_connection?.provisioning_status || "not_provisioned"}</Badge>
                  <Badge tone={selectedTenant.retell_connection?.agent_id ? "emerald" : "amber"}>Agent: {selectedTenant.retell_connection?.agent_id ? "created" : "missing"}</Badge>
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