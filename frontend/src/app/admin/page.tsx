"use client";

import { useEffect, useState } from "react";
import {
  Users,
  Phone,
  MessageSquare,
  TrendingUp,
  Send,
  UserPlus,
  Building2,
  ArrowUpRight,
  RefreshCw,
  Crown,
  ExternalLink,
} from "lucide-react";
import { adminFetch } from "@/lib/admin-auth";

interface DashboardStats {
  total_mechanics: number;
  total_with_phone: number;
  total_with_email: number;
  total_with_website: number;
  total_campaigns: number;
  total_messages_sent: number;
  total_demos_booked: number;
  total_signups: number;
  lead_status_breakdown: Record<string, number>;
  top_states: { state: string; count: number }[];
}

interface GHLConnectionView {
  location_id?: string | null;
  subaccount_name?: string | null;
  connection_status: string;
}

interface RetellConnectionView {
  agent_id?: string | null;
  agent_name?: string | null;
  provisioning_status: string;
}

interface TenantView {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  current_plan: string;
  subscription_status: string;
  onboarding_status: string;
  setup_fee_status: string;
  ghl_connection?: GHLConnectionView | null;
  retell_connection?: RetellConnectionView | null;
  latest_activity_type?: string | null;
  latest_activity_status?: string | null;
  latest_activity_at?: string | null;
  is_active: boolean;
  created_at: string;
}

interface TenantListResponse {
  tenants: TenantView[];
}

const ACCENT: Record<string, string> = {
  blue: "bg-blue-500/20 text-blue-400",
  green: "bg-emerald-500/20 text-emerald-400",
  amber: "bg-amber-500/20 text-amber-400",
  purple: "bg-purple-500/20 text-purple-400",
  rose: "bg-rose-500/20 text-rose-400",
  cyan: "bg-cyan-500/20 text-cyan-400",
};

function StatCard({
  icon: Icon,
  label,
  value,
  sublabel,
  color = "blue",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sublabel?: string;
  color?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-5 shadow-lg">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {label}
          </p>
          <p className="mt-2 text-3xl font-bold text-white">
            {typeof value === "number" ? value.toLocaleString() : value}
          </p>
          {sublabel && (
            <p className="mt-1 text-xs text-slate-500">{sublabel}</p>
          )}
        </div>
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${ACCENT[color]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function StatusPill({ value, tone }: { value: string; tone?: "green" | "blue" | "amber" | "red" | "slate" | "orange" }) {
  const palette = {
    green: "border-emerald-500/25 bg-emerald-500/15 text-emerald-300",
    blue: "border-blue-500/25 bg-blue-500/15 text-blue-300",
    amber: "border-amber-500/25 bg-amber-500/15 text-amber-300",
    red: "border-red-500/25 bg-red-500/15 text-red-300",
    orange: "border-orange-500/25 bg-orange-500/15 text-orange-300",
    slate: "border-white/10 bg-white/5 text-slate-300",
  }[tone || "slate"];
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${palette}`}>{value.replaceAll("_", " ")}</span>;
}

function statusTone(status?: string | null): "green" | "amber" | "red" | "slate" {
  if (!status) return "slate";
  if (["active", "connected", "completed", "paid", "healthy"].includes(status)) return "green";
  if (["failed", "cancelled", "churned", "error"].includes(status)) return "red";
  if (["pending", "in_progress", "not_started", "unpaid", "provisioning"].includes(status)) return "amber";
  return "slate";
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tenants, setTenants] = useState<TenantView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchStats() {
    setLoading(true);
    setError(null);
    try {
      const [dashboardData, tenantData] = await Promise.all([
        adminFetch<DashboardStats>("/outreach/dashboard"),
        adminFetch<TenantListResponse>("/provisioning/admin/tenants"),
      ]);
      setStats(dashboardData);
      setTenants(tenantData.tenants || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400">
            AI Receptionist — Sales &amp; Outreach Overview
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-2xl bg-slate-900/60 border border-white/5"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <div className="rounded-2xl border border-red-500/20 bg-red-950/30 p-6 text-center text-red-300">
          <p>{error || "No data available"}</p>
          <p className="text-sm mt-2 text-red-400/70">
            Make sure the backend is running and ADMIN_API_KEY is configured.
          </p>
          <button
            onClick={fetchStats}
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-400/30 px-4 py-2 text-sm text-red-300 hover:bg-red-500/10"
          >
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  const leadBreakdown = stats.lead_status_breakdown;
  const activeSubscribers = tenants.filter((tenant) => tenant.is_active && tenant.subscription_status === "active").length;
  const aiPhoneActive = tenants.filter((tenant) => tenant.retell_connection?.provisioning_status === "active").length;
  const proSubscribers = tenants.filter((tenant) => tenant.current_plan === "pro").length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400">
            AI Receptionist — Subscribers, Provisioning &amp; Outreach Overview
          </p>
        </div>
        <button
          onClick={fetchStats}
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Building2}
          label="Total Shops in DB"
          value={stats.total_mechanics}
          sublabel={`${stats.total_with_phone.toLocaleString()} with phone`}
          color="blue"
        />
        <StatCard
          icon={Send}
          label="Messages Sent"
          value={stats.total_messages_sent}
          sublabel={`${stats.total_campaigns} campaigns`}
          color="purple"
        />
        <StatCard
          icon={Phone}
          label="Demos Booked"
          value={stats.total_demos_booked}
          color="amber"
        />
        <StatCard
          icon={UserPlus}
          label="Subscribers"
          value={tenants.length}
          sublabel={`${activeSubscribers} active · ${proSubscribers} Pro`}
          color="green"
        />
      </div>

      <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 shadow-lg">
        <div className="flex flex-col gap-3 border-b border-white/5 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-orange-300" />
            <div>
              <h2 className="font-semibold text-white">Subscribers &amp; Auto-Generated Sub-Accounts</h2>
              <p className="text-xs text-slate-500">Track every Roadcall tenant, plan, AI phone agent, CRM sub-account, and latest activity.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <StatusPill value={`${activeSubscribers} active`} tone="green" />
            <StatusPill value={`${aiPhoneActive} AI phone active`} tone="blue" />
            <a href="/admin/provisioning" className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300 hover:bg-white/10 hover:text-white">
              Configure agents <ExternalLink className="h-3 w-3" />
            </a>
            <a href="https://dashboard.retellai.com/agents" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-blue-400/25 bg-blue-500/10 px-3 py-1.5 text-blue-200 hover:bg-blue-500/20">
              Voice agents <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
        {tenants.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">No subscribers provisioned yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">Subscriber</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3">Sub-Account</th>
                  <th className="px-4 py-3">AI Phone</th>
                  <th className="px-4 py-3">Latest Activity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {tenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-200">{tenant.name}</div>
                      <div className="font-mono text-xs text-slate-600">{tenant.slug}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      <div>{tenant.contact_email || "No email"}</div>
                      <div>{tenant.contact_phone || "No phone"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        <StatusPill value={tenant.current_plan} tone={tenant.current_plan === "pro" ? "orange" : tenant.current_plan === "growth" ? "blue" : "slate"} />
                        <StatusPill value={tenant.subscription_status} tone={statusTone(tenant.subscription_status)} />
                      </div>
                      <div className="mt-1 text-xs text-slate-500">Onboarding: {tenant.onboarding_status.replaceAll("_", " ")}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      <div className="font-medium text-slate-300">{tenant.ghl_connection?.subaccount_name || "Not mapped"}</div>
                      <div>{tenant.ghl_connection?.location_id || "No CRM location"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <StatusPill value={tenant.retell_connection?.provisioning_status || "not_provisioned"} tone={statusTone(tenant.retell_connection?.provisioning_status)} />
                        <span className="font-mono text-xs text-slate-500">{tenant.retell_connection?.agent_id || "No agent"}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      <div className="font-medium text-slate-300">{tenant.latest_activity_type?.replaceAll("_", " ") || "No activity yet"}</div>
                      <div>{tenant.latest_activity_at ? new Date(tenant.latest_activity_at).toLocaleString() : "—"}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lead Pipeline */}
        <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-6 shadow-lg">
          <div className="mb-5 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-400" />
            <div>
              <h2 className="font-semibold text-white">Lead Pipeline</h2>
              <p className="text-xs text-slate-500">
                Breakdown of mechanic lead statuses
              </p>
            </div>
          </div>
          <div className="space-y-3">
            {[
              { key: "new", label: "New / Untouched", bar: "bg-slate-500" },
              { key: "contacted", label: "Contacted", bar: "bg-blue-500" },
              { key: "interested", label: "Interested", bar: "bg-cyan-500" },
              { key: "demo_scheduled", label: "Demo Scheduled", bar: "bg-amber-500" },
              { key: "demo_completed", label: "Demo Completed", bar: "bg-orange-500" },
              { key: "negotiating", label: "Negotiating", bar: "bg-purple-500" },
              { key: "signed_up", label: "Signed Up ✓", bar: "bg-emerald-500" },
              { key: "not_interested", label: "Not Interested", bar: "bg-red-500" },
            ].map((stage) => {
              const count = leadBreakdown[stage.key] || 0;
              const pct =
                stats.total_mechanics > 0
                  ? (count / stats.total_mechanics) * 100
                  : 0;
              return (
                <div key={stage.key} className="flex items-center gap-3">
                  <div className="w-32 shrink-0 text-sm text-slate-400">
                    {stage.label}
                  </div>
                  <div className="flex-1 h-5 overflow-hidden rounded-full bg-white/5">
                    <div
                      className={`${stage.bar} h-full rounded-full transition-all`}
                      style={{ width: `${Math.max(pct, 0.4)}%` }}
                    />
                  </div>
                  <div className="w-14 text-right text-sm font-medium text-slate-300">
                    {count.toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top States */}
        <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-6 shadow-lg">
          <div className="mb-5 flex items-center gap-2">
            <ArrowUpRight className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="font-semibold text-white">Top States</h2>
              <p className="text-xs text-slate-500">Mechanic shops by state</p>
            </div>
          </div>
          <div className="space-y-1">
            {stats.top_states.slice(0, 12).map((s, i) => (
              <div
                key={s.state}
                className="flex items-center justify-between border-b border-white/5 py-2 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="w-6 text-sm text-slate-500">{i + 1}.</span>
                  <span className="font-medium text-slate-200">{s.state}</span>
                </div>
                <span className="text-sm text-slate-400">
                  {s.count.toLocaleString()} shops
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Data Coverage */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={Phone}
          label="Has Phone Number"
          value={`${
            stats.total_mechanics > 0
              ? ((stats.total_with_phone / stats.total_mechanics) * 100).toFixed(0)
              : 0
          }%`}
          sublabel={`${stats.total_with_phone.toLocaleString()} shops`}
          color="green"
        />
        <StatCard
          icon={MessageSquare}
          label="Has Website"
          value={`${
            stats.total_mechanics > 0
              ? ((stats.total_with_website / stats.total_mechanics) * 100).toFixed(0)
              : 0
          }%`}
          sublabel={`${stats.total_with_website.toLocaleString()} shops`}
          color="cyan"
        />
        <StatCard
          icon={Users}
          label="Has Email"
          value={`${
            stats.total_mechanics > 0
              ? ((stats.total_with_email / stats.total_mechanics) * 100).toFixed(0)
              : 0
          }%`}
          sublabel={`${stats.total_with_email.toLocaleString()} shops`}
          color="rose"
        />
      </div>
    </div>
  );
}
