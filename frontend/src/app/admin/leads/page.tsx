"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Download,
  Mail,
  RefreshCw,
  Search,
  Trash2,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { adminFetch } from "@/lib/admin-auth";

interface Lead {
  id: string;
  email: string;
  name: string | null;
  company: string | null;
  vertical: string | null;
  source: string | null;
  unsubscribed: boolean;
  welcome_sent: boolean;
  created_at: string;
}

interface LeadListResponse {
  total: number;
  page: number;
  page_size: number;
  leads: Lead[];
}

const VERTICAL_COLORS: Record<string, string> = {
  shops: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  fleet: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  general: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

export default function LeadsPage() {
  const [data, setData] = useState<LeadListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [vertical, setVertical] = useState<string>("");
  const [page, setPage] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (search) params.set("search", search);
      if (vertical) params.set("vertical", vertical);
      const res = await adminFetch<LeadListResponse>(`/leads?${params}`);
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, search, vertical]);

  useEffect(() => { load(); }, [load]);

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1); }, [search, vertical]);

  async function handleDelete(id: string) {
    if (!confirm("Remove this lead from the list?")) return;
    setDeleting(id);
    try {
      await adminFetch(`/leads/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      console.error(e);
    } finally {
      setDeleting(null);
    }
  }

  function exportCSV() {
    if (!data?.leads.length) return;
    const header = ["email", "name", "company", "vertical", "source", "welcome_sent", "signed_up"];
    const rows = data.leads.map(l => [
      l.email,
      l.name ?? "",
      l.company ?? "",
      l.vertical ?? "",
      l.source ?? "",
      l.welcome_sent ? "yes" : "no",
      new Date(l.created_at).toLocaleDateString(),
    ]);
    const csv = [header, ...rows].map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `roadcall-leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Email List</h1>
          <p className="text-slate-500 text-sm mt-1">
            Website lead magnet sign-ups and newsletter subscribers.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={exportCSV} disabled={!data?.leads.length}>
            <Download className="h-4 w-4 mr-1.5" /> Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Total Subscribers", value: data?.total ?? "—", icon: Users, color: "text-blue-600" },
          { label: "Shops Vertical", value: data?.leads.filter(l => l.vertical === "shops").length ?? "—", icon: Mail, color: "text-orange-500" },
          { label: "Fleet Vertical", value: data?.leads.filter(l => l.vertical === "fleet").length ?? "—", icon: Mail, color: "text-blue-500" },
          { label: "Welcome Sent", value: data?.leads.filter(l => l.welcome_sent).length ?? "—", icon: Mail, color: "text-emerald-500" },
        ].map(s => (
          <Card key={s.label}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-3">
                <s.icon className={`h-5 w-5 ${s.color}`} />
                <div>
                  <p className="text-2xl font-bold text-slate-900">{s.value}</p>
                  <p className="text-xs text-slate-500">{s.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Search & Filter</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3 flex-wrap">
            <div className="relative flex-1 min-w-48">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search email..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={vertical}
              onChange={e => setVertical(e.target.value)}
              className="border border-slate-200 rounded-md px-3 py-2 text-sm bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All verticals</option>
              <option value="shops">Shops</option>
              <option value="fleet">Fleet</option>
              <option value="general">General</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Subscribers</CardTitle>
              <CardDescription>
                {data ? `${data.total.toLocaleString()} total` : "Loading…"}
                {(search || vertical) && " (filtered)"}
              </CardDescription>
            </div>
            {totalPages > 1 && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-2 py-1 rounded border disabled:opacity-40 hover:bg-slate-50"
                >
                  ‹
                </button>
                <span>Page {page} of {totalPages}</span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-2 py-1 rounded border disabled:opacity-40 hover:bg-slate-50"
                >
                  ›
                </button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-slate-400">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading…
            </div>
          ) : !data?.leads.length ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <Mail className="h-8 w-8 mb-3 opacity-40" />
              <p>No leads yet.</p>
              <p className="text-xs mt-1">Sign-ups from roadcall.ai will appear here.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Vertical</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Source</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Welcome</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Signed Up</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.leads.map(lead => (
                    <tr key={lead.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                            <Mail className="h-3.5 w-3.5 text-slate-400" />
                          </div>
                          <span className="font-medium text-slate-800">{lead.email}</span>
                          {lead.unsubscribed && (
                            <Badge variant="outline" className="text-xs text-slate-400 border-slate-200">unsub</Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-600">{lead.name ?? <span className="text-slate-300">—</span>}</td>
                      <td className="px-4 py-3.5">
                        {lead.vertical ? (
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${VERTICAL_COLORS[lead.vertical] ?? VERTICAL_COLORS.general}`}>
                            {lead.vertical}
                          </span>
                        ) : <span className="text-slate-300">—</span>}
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 text-xs">{lead.source ?? "—"}</td>
                      <td className="px-4 py-3.5">
                        {lead.welcome_sent
                          ? <span className="text-emerald-600 text-xs font-medium">✓ Sent</span>
                          : <span className="text-slate-300 text-xs">Pending</span>
                        }
                      </td>
                      <td className="px-4 py-3.5 text-slate-400 text-xs whitespace-nowrap">
                        {new Date(lead.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </td>
                      <td className="px-4 py-3.5">
                        <button
                          onClick={() => handleDelete(lead.id)}
                          disabled={deleting === lead.id}
                          className="p-1.5 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
                          title="Remove lead"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
