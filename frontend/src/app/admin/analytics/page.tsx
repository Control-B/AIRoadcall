"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Phone,
  Users,
  TrendingUp,
  DollarSign,
  MessageSquare,
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

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await adminFetch<DashboardStats>("/outreach/dashboard");
        setStats(data);
      } catch (err) {
        console.error("Failed to fetch stats:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading || !stats) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="grid grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-24 bg-slate-100 animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const leadBreakdown = stats.lead_status_breakdown;
  const contacted = (leadBreakdown.contacted || 0) + (leadBreakdown.interested || 0) +
    (leadBreakdown.demo_scheduled || 0) + (leadBreakdown.demo_completed || 0) +
    (leadBreakdown.negotiating || 0) + (leadBreakdown.signed_up || 0);
  const conversionRate = contacted > 0
    ? ((leadBreakdown.signed_up || 0) / contacted * 100).toFixed(1)
    : "0.0";

  // Revenue projection
  const signups = leadBreakdown.signed_up || 0;
  const avgPlanValue = 149; // weighted avg between starter/pro/enterprise
  const mrr = signups * avgPlanValue;
  const arr = mrr * 12;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">
          Business performance & revenue projections
        </p>
      </div>

      {/* Revenue */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-500" />
          Revenue
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border-green-200 bg-green-50/50">
            <CardContent className="pt-6 text-center">
              <p className="text-4xl font-bold text-green-700">
                ${mrr.toLocaleString()}
              </p>
              <p className="text-sm text-green-600 mt-1">
                Monthly Recurring Revenue
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                {signups} active shops × ${avgPlanValue} avg
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-4xl font-bold">
                ${arr.toLocaleString()}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Annualized Revenue
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-4xl font-bold">{conversionRate}%</p>
              <p className="text-sm text-muted-foreground mt-1">
                Outreach → Signup Rate
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                {leadBreakdown.signed_up || 0} / {contacted} contacted
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Sales Funnel */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-500" />
          Sales Funnel
        </h2>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[
                {
                  label: "Total Database",
                  value: stats.total_mechanics,
                  color: "bg-slate-500",
                  width: 100,
                },
                {
                  label: "Contacted",
                  value: contacted,
                  color: "bg-blue-500",
                  width: stats.total_mechanics > 0
                    ? (contacted / stats.total_mechanics) * 100
                    : 0,
                },
                {
                  label: "Interested",
                  value: (leadBreakdown.interested || 0) +
                    (leadBreakdown.demo_scheduled || 0) +
                    (leadBreakdown.demo_completed || 0) +
                    (leadBreakdown.negotiating || 0) +
                    (leadBreakdown.signed_up || 0),
                  color: "bg-cyan-500",
                  width: stats.total_mechanics > 0
                    ? (((leadBreakdown.interested || 0) +
                        (leadBreakdown.demo_scheduled || 0) +
                        (leadBreakdown.demo_completed || 0) +
                        (leadBreakdown.negotiating || 0) +
                        (leadBreakdown.signed_up || 0)) /
                        stats.total_mechanics) *
                      100
                    : 0,
                },
                {
                  label: "Demo Completed",
                  value: (leadBreakdown.demo_completed || 0) +
                    (leadBreakdown.negotiating || 0) +
                    (leadBreakdown.signed_up || 0),
                  color: "bg-amber-500",
                  width: stats.total_mechanics > 0
                    ? (((leadBreakdown.demo_completed || 0) +
                        (leadBreakdown.negotiating || 0) +
                        (leadBreakdown.signed_up || 0)) /
                        stats.total_mechanics) *
                      100
                    : 0,
                },
                {
                  label: "Signed Up",
                  value: leadBreakdown.signed_up || 0,
                  color: "bg-green-500",
                  width: stats.total_mechanics > 0
                    ? ((leadBreakdown.signed_up || 0) /
                        stats.total_mechanics) *
                      100
                    : 0,
                },
              ].map((stage) => (
                <div key={stage.label}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{stage.label}</span>
                    <span className="text-muted-foreground">
                      {stage.value.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-8 bg-slate-100 rounded-lg overflow-hidden">
                    <div
                      className={`${stage.color} h-full rounded-lg transition-all flex items-center px-3`}
                      style={{
                        width: `${Math.max(stage.width, 1)}%`,
                      }}
                    >
                      {stage.width > 10 && (
                        <span className="text-white text-xs font-medium">
                          {stage.width.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* State Heatmap */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-purple-500" />
          Coverage by State
        </h2>
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
              {stats.top_states.map((s) => (
                <div
                  key={s.state}
                  className="bg-slate-50 rounded-lg p-3 text-center hover:bg-blue-50 transition-colors"
                >
                  <p className="text-lg font-bold">{s.state}</p>
                  <p className="text-xs text-muted-foreground">
                    {s.count.toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
