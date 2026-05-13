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

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchStats() {
    setLoading(true);
    setError(null);
    try {
      const data = await adminFetch<DashboardStats>("/outreach/dashboard");
      setStats(data);
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

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400">
            AI Receptionist — Sales &amp; Outreach Overview
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
          label="Signups"
          value={stats.total_signups}
          color="green"
        />
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
