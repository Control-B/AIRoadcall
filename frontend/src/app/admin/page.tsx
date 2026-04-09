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
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  const colors: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    amber: "bg-amber-50 text-amber-600",
    purple: "bg-purple-50 text-purple-600",
    rose: "bg-rose-50 text-rose-600",
    cyan: "bg-cyan-50 text-cyan-600",
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground font-medium">{label}</p>
            <p className="text-3xl font-bold mt-1">
              {typeof value === "number" ? value.toLocaleString() : value}
            </p>
            {sublabel && (
              <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>
            )}
          </div>
          <div className={`p-3 rounded-lg ${colors[color]}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await adminFetch<DashboardStats>("/outreach/dashboard");
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-20 bg-slate-100 animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <p>{error || "No data available"}</p>
            <p className="text-sm mt-2">
              Make sure the backend is running and ADMIN_API_KEY is configured.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const leadBreakdown = stats.lead_status_breakdown;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          AI Receptionist — Sales & Outreach Overview
        </p>
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
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              Lead Pipeline
            </CardTitle>
            <CardDescription>
              Breakdown of mechanic lead statuses
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { key: "new", label: "New / Untouched", color: "bg-slate-400" },
                { key: "contacted", label: "Contacted", color: "bg-blue-500" },
                {
                  key: "interested",
                  label: "Interested",
                  color: "bg-cyan-500",
                },
                {
                  key: "demo_scheduled",
                  label: "Demo Scheduled",
                  color: "bg-amber-500",
                },
                {
                  key: "demo_completed",
                  label: "Demo Completed",
                  color: "bg-orange-500",
                },
                {
                  key: "negotiating",
                  label: "Negotiating",
                  color: "bg-purple-500",
                },
                {
                  key: "signed_up",
                  label: "Signed Up ✓",
                  color: "bg-green-500",
                },
                {
                  key: "not_interested",
                  label: "Not Interested",
                  color: "bg-red-400",
                },
              ].map((stage) => {
                const count = leadBreakdown[stage.key] || 0;
                const pct =
                  stats.total_mechanics > 0
                    ? (count / stats.total_mechanics) * 100
                    : 0;
                return (
                  <div key={stage.key} className="flex items-center gap-3">
                    <div className="w-32 text-sm text-muted-foreground shrink-0">
                      {stage.label}
                    </div>
                    <div className="flex-1 bg-slate-100 rounded-full h-6 relative overflow-hidden">
                      <div
                        className={`${stage.color} h-full rounded-full transition-all`}
                        style={{ width: `${Math.max(pct, 0.5)}%` }}
                      />
                    </div>
                    <div className="w-16 text-sm font-medium text-right">
                      {count.toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Top States */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArrowUpRight className="h-5 w-5 text-green-500" />
              Top States
            </CardTitle>
            <CardDescription>
              Mechanic shops by state
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {stats.top_states.slice(0, 12).map((s, i) => (
                <div
                  key={s.state}
                  className="flex items-center justify-between py-1.5 border-b border-slate-100 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground w-6">
                      {i + 1}.
                    </span>
                    <span className="font-medium">{s.state}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {s.count.toLocaleString()} shops
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Coverage */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={Phone}
          label="Has Phone Number"
          value={`${((stats.total_with_phone / stats.total_mechanics) * 100).toFixed(0)}%`}
          sublabel={`${stats.total_with_phone.toLocaleString()} shops`}
          color="green"
        />
        <StatCard
          icon={MessageSquare}
          label="Has Website"
          value={`${((stats.total_with_website / stats.total_mechanics) * 100).toFixed(0)}%`}
          sublabel={`${stats.total_with_website.toLocaleString()} shops`}
          color="cyan"
        />
        <StatCard
          icon={Users}
          label="Has Email"
          value={`${stats.total_mechanics > 0 ? ((stats.total_with_email / stats.total_mechanics) * 100).toFixed(0) : 0}%`}
          sublabel={`${stats.total_with_email.toLocaleString()} shops`}
          color="rose"
        />
      </div>
    </div>
  );
}
