"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, CheckCircle2, Copy, Loader2, RefreshCw, Save, ShieldCheck, Workflow } from "lucide-react";
import { Input } from "@/components/ui/input";
import { adminFetch } from "@/lib/admin-auth";

interface TenantMapping {
  id: string;
  organization_id: string;
  location_id: string;
  subaccount_name: string | null;
  pipeline_id: string | null;
  default_workflow_id: string | null;
  is_active: boolean;
}

interface TenantMappingListResponse {
  mappings: TenantMapping[];
}

interface RetryOverviewResponse {
  pending: number;
  succeeded: number;
  failed: number;
}

interface FormState {
  organization_id: string;
  location_id: string;
  subaccount_name: string;
  access_token: string;
  refresh_token: string;
  webhook_secret: string;
  pipeline_id: string;
  default_workflow_id: string;
}

const initialForm: FormState = {
  organization_id: "",
  location_id: "",
  subaccount_name: "",
  access_token: "",
  refresh_token: "",
  webhook_secret: "",
  pipeline_id: "",
  default_workflow_id: "",
};

const GHL_DASHBOARD_URL = "https://app.roadcall.ai/v2/location/ZRZKlNyMxEmu0yppEcE3/dashboard";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 shadow-lg ${className}`}>
      {children}
    </div>
  );
}

function Field({ label, note, children }: { label: string; note?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-300">{label}</label>
      {children}
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

function EndpointRow({ label, path }: { label: string; path: string }) {
  async function copy() {
    await navigator.clipboard.writeText(path);
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2">
      <div>
        <p className="text-xs font-medium text-slate-300">{label}</p>
        <code className="text-xs text-slate-500">{path}</code>
      </div>
      <button onClick={copy} className="rounded-md p-2 text-slate-500 transition-colors hover:bg-white/10 hover:text-white" title="Copy endpoint">
        <Copy className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function GHLIntegrationPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [mappings, setMappings] = useState<TenantMapping[]>([]);
  const [retry, setRetry] = useState<RetryOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [processingRetry, setProcessingRetry] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const webhookBase = useMemo(() => {
    if (typeof window === "undefined") return "/api/ghl/webhooks";
    return `${window.location.origin}/api/ghl/webhooks`;
  }, []);

  const inputCls = "bg-white/5 border-white/10 text-slate-200 placeholder:text-slate-500 focus:border-blue-500/50";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [mappingData, retryData] = await Promise.all([
        adminFetch<TenantMappingListResponse>("/ghl/admin/tenant-mappings"),
        adminFetch<RetryOverviewResponse>("/ghl/retry/overview"),
      ]);
      setMappings(mappingData.mappings);
      setRetry(retryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load GHL integration status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    window.location.replace(GHL_DASHBOARD_URL);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function updateField(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setMessage(null);
    setError(null);
  }

  async function saveMapping(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, value.trim() || null])
      );
      await adminFetch("/ghl/admin/tenant-mappings", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setForm(initialForm);
      setMessage("GHL tenant mapping saved. Secrets were encrypted before storage.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save mapping");
    } finally {
      setSaving(false);
    }
  }

  async function processRetryQueue() {
    setProcessingRetry(true);
    setMessage(null);
    setError(null);
    try {
      const result = await adminFetch<{ ok: boolean; result: Record<string, number> }>("/ghl/retry/process", {
        method: "POST",
        body: JSON.stringify({ limit: 25 }),
      });
      setMessage(`Retry queue processed: ${result.result?.processed ?? 0} checked, ${result.result?.succeeded ?? 0} succeeded.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process retry queue");
    } finally {
      setProcessingRetry(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">GoHighLevel Integration</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Configure GHL as the CRM/workflow layer only. Roadcall remains source of truth for dispatch, matching, billing, status, mechanics, fleets, vendors, geolocation, and analytics.
          </p>
        </div>
        <button onClick={load} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {(message || error) && (
        <div className={`rounded-xl border px-4 py-3 text-sm ${error ? "border-red-500/25 bg-red-500/10 text-red-200" : "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"}`}>
          {error || message}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-cyan-300" />
            <div>
              <p className="text-2xl font-bold text-white">{loading ? "—" : mappings.length}</p>
              <p className="text-xs text-slate-400">Tenant mappings</p>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-amber-300" />
            <div>
              <p className="text-2xl font-bold text-white">{retry?.pending ?? "—"}</p>
              <p className="text-xs text-slate-400">Pending retries</p>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-300" />
            <div>
              <p className="text-2xl font-bold text-white">{retry?.succeeded ?? "—"}</p>
              <p className="text-xs text-slate-400">Succeeded retries</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/15">
              <Workflow className="h-5 w-5 text-blue-300" />
            </div>
            <div>
              <h2 className="font-semibold text-white">Tenant Mapping</h2>
              <p className="text-xs text-slate-400">Map a Roadcall organization to a GHL location/subaccount.</p>
            </div>
          </div>

          <form onSubmit={saveMapping} className="grid gap-4 md:grid-cols-2">
            <Field label="Roadcall Organization ID" note="The Roadcall tenant/account UUID.">
              <Input value={form.organization_id} onChange={(e) => updateField("organization_id", e.target.value)} required className={inputCls} />
            </Field>
            <Field label="GHL Location ID" note="The GoHighLevel location/subaccount ID.">
              <Input value={form.location_id} onChange={(e) => updateField("location_id", e.target.value)} required className={inputCls} />
            </Field>
            <Field label="Subaccount Name">
              <Input value={form.subaccount_name} onChange={(e) => updateField("subaccount_name", e.target.value)} className={inputCls} />
            </Field>
            <Field label="Pipeline ID">
              <Input value={form.pipeline_id} onChange={(e) => updateField("pipeline_id", e.target.value)} className={inputCls} />
            </Field>
            <Field label="Default Workflow ID">
              <Input value={form.default_workflow_id} onChange={(e) => updateField("default_workflow_id", e.target.value)} className={inputCls} />
            </Field>
            <Field label="Webhook Secret" note="Stored encrypted; used to verify inbound GHL webhook signatures.">
              <Input type="password" value={form.webhook_secret} onChange={(e) => updateField("webhook_secret", e.target.value)} className={inputCls} />
            </Field>
            <Field label="Access Token" note="Stored encrypted; used for outbound contact/workflow/pipeline sync.">
              <Input type="password" value={form.access_token} onChange={(e) => updateField("access_token", e.target.value)} className={inputCls} />
            </Field>
            <Field label="Refresh Token">
              <Input type="password" value={form.refresh_token} onChange={(e) => updateField("refresh_token", e.target.value)} className={inputCls} />
            </Field>
            <div className="md:col-span-2 flex justify-end">
              <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-roadcall-blue px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-roadcall-blue/20 hover:bg-blue-600 disabled:opacity-50">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Mapping
              </button>
            </div>
          </form>
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="font-semibold text-white">Webhook URLs</h2>
            <p className="mt-1 text-xs text-slate-400">Add these signed endpoints in GHL. Each payload must include a mapped location ID.</p>
            <div className="mt-4 space-y-2">
              <EndpointRow label="Form submissions" path={`${webhookBase}/forms`} />
              <EndpointRow label="Contact updates" path={`${webhookBase}/contact-updates`} />
              <EndpointRow label="Appointment bookings" path={`${webhookBase}/appointments`} />
              <EndpointRow label="AI voice call events" path={`${webhookBase}/voice-call`} />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold text-white">Retry Queue</h2>
                <p className="text-xs text-slate-400">Failed outbound syncs are queued instead of blocking Roadcall.</p>
              </div>
              <button onClick={processRetryQueue} disabled={processingRetry} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-50">
                {processingRetry ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Process
              </button>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-lg bg-white/[0.03] p-3"><p className="text-lg font-bold text-amber-300">{retry?.pending ?? 0}</p><p className="text-slate-500">Pending</p></div>
              <div className="rounded-lg bg-white/[0.03] p-3"><p className="text-lg font-bold text-emerald-300">{retry?.succeeded ?? 0}</p><p className="text-slate-500">Succeeded</p></div>
              <div className="rounded-lg bg-white/[0.03] p-3"><p className="text-lg font-bold text-red-300">{retry?.failed ?? 0}</p><p className="text-slate-500">Failed</p></div>
            </div>
          </Card>
        </div>
      </div>

      <Card>
        <div className="border-b border-white/5 px-6 py-4">
          <h2 className="font-semibold text-white">Configured Mappings</h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-400"><Loader2 className="mr-2 h-5 w-5 animate-spin" />Loading mappings…</div>
        ) : mappings.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">No GHL tenant mappings configured yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">Subaccount</th>
                  <th className="px-4 py-3">Roadcall Org</th>
                  <th className="px-4 py-3">GHL Location</th>
                  <th className="px-4 py-3">Pipeline</th>
                  <th className="px-4 py-3">Workflow</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {mappings.map((mapping) => (
                  <tr key={mapping.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-medium text-slate-200">{mapping.subaccount_name || "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{mapping.organization_id}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{mapping.location_id}</td>
                    <td className="px-4 py-3 text-slate-400">{mapping.pipeline_id || "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{mapping.default_workflow_id || "—"}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs ${mapping.is_active ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-500/15 text-slate-400"}`}>{mapping.is_active ? "Active" : "Inactive"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
