"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Download,
  Mail,
  RefreshCw,
  Search,
  Trash2,
  Users,
  Wrench,
  ExternalLink,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { adminFetch } from "@/lib/admin-auth";

interface Lead {
  id: string; email: string; name: string | null; company: string | null;
  vertical: string | null; source: string | null; unsubscribed: boolean;
  welcome_sent: boolean; created_at: string;
}
interface LeadListResponse { total: number; page: number; page_size: number; leads: Lead[]; }
interface MechanicItem {
  id: string; company_name: string; contact_name: string; phone: string;
  email_quality: string | null;
  email: string | null; website: string | null; city: string | null;
  state: string | null; rating: number | null; source: string | null;
}
interface MechanicListResponse { total: number; limit: number; offset: number; items: MechanicItem[]; }
interface MechanicStats { total_mechanics: number; total_with_email: number; }
const VERTICAL_COLORS: Record<string, string> = {
  shops:   "bg-orange-500/15 text-orange-300 border border-orange-500/25",
  fleet:   "bg-blue-500/15 text-blue-300 border border-blue-500/25",
  general: "bg-slate-500/15 text-slate-300 border border-slate-500/25",
};

function DarkCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 shadow-lg ${className}`}>
      {children}
    </div>
  );
}

function StatCard({ icon: Icon, color, value, label }: { icon: React.ElementType; color: string; value: string | number; label: string }) {
  return (
    <DarkCard className="p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5">
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-xs text-slate-400">{label}</p>
        </div>
      </div>
    </DarkCard>
  );
}

function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <button onClick={() => onChange(Math.max(1, page - 1))} disabled={page === 1} className="px-2 py-1 rounded border border-white/10 disabled:opacity-40 hover:bg-white/5">‹</button>
      <span>Page {page} of {totalPages}</span>
      <button onClick={() => onChange(Math.min(totalPages, page + 1))} disabled={page === totalPages} className="px-2 py-1 rounded border border-white/10 disabled:opacity-40 hover:bg-white/5">›</button>
    </div>
  );
}

function LoadingRow() {
  return <div className="flex items-center justify-center py-16 text-slate-400"><RefreshCw className="h-5 w-5 animate-spin mr-2" />Loading…</div>;
}

function EmptyRow({ icon: Icon, message, sub }: { icon: React.ElementType; message: string; sub: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
      <Icon className="h-8 w-8 mb-3 opacity-40" />
      <p className="font-medium text-slate-300">{message}</p>
      <p className="text-xs mt-1 text-slate-500">{sub}</p>
    </div>
  );
}

function emailQualityBadge(kind: string | null) {
  switch (kind) {
    case "domain_match":
      return { label: "Domain match", cls: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/25" };
    case "domain_role":
      return { label: "Domain role", cls: "bg-cyan-500/15 text-cyan-300 border border-cyan-500/25" };
    case "role_based":
      return { label: "Role-based", cls: "bg-blue-500/15 text-blue-300 border border-blue-500/25" };
    case "noreply":
      return { label: "No-reply", cls: "bg-amber-500/15 text-amber-300 border border-amber-500/25" };
    case "unmatched":
      return { label: "Unmatched", cls: "bg-slate-500/15 text-slate-300 border border-slate-500/25" };
    default:
      return { label: "Unknown", cls: "bg-slate-500/15 text-slate-400 border border-slate-500/25" };
  }
}

export default function LeadsPage() {
  const [tab, setTab] = useState<"signups" | "mechanics">("signups");
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Email List</h1>
        <p className="text-slate-400 text-sm mt-1">Website sign-ups and mechanic contacts. Outreach stays separate from live driver-to-mechanic dispatch matching.</p>
      </div>
      <div className="flex gap-1 rounded-xl border border-white/5 bg-slate-900/60 p-1 w-fit">
        {([["signups", Mail, "Sign-ups"], ["mechanics", Wrench, "Mechanic Emails"]] as const).map(([id, Icon, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === id ? "bg-roadcall-blue text-white shadow" : "text-slate-400 hover:text-slate-200"
            }`}>
            <Icon className="h-4 w-4" />{label}
          </button>
        ))}
      </div>
      {tab === "signups" ? <SignupsTab /> : <MechanicEmailsTab />}
    </div>
  );
}

function SignupsTab() {
  const [data, setData] = useState<LeadListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [vertical, setVertical] = useState("");
  const [page, setPage] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (search) params.set("search", search);
      if (vertical) params.set("vertical", vertical);
      setData(await adminFetch<LeadListResponse>(`/leads?${params}`));
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [page, search, vertical]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [search, vertical]);

  async function handleDelete(id: string) {
    if (!confirm("Remove this lead?")) return;
    setDeleting(id);
    try { await adminFetch(`/leads/${id}`, { method: "DELETE" }); await load(); }
    catch (e) { console.error(e); } finally { setDeleting(null); }
  }

  function exportCSV() {
    if (!data?.leads.length) return;
    const rows = [["email","name","company","vertical","source","welcome_sent","signed_up"],
      ...data.leads.map(l => [l.email, l.name??"", l.company??"", l.vertical??"", l.source??"", l.welcome_sent?"yes":"no", new Date(l.created_at).toLocaleDateString()])];
    const blob = new Blob([rows.map(r => r.map(c=>`"${c}"`).join(",")).join("\n")], { type: "text/csv" });
    Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `signups-${new Date().toISOString().slice(0,10)}.csv` }).click();
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard icon={Users} color="text-blue-400"    value={data?.total ?? "—"} label="Total Sign-ups" />
        <StatCard icon={Mail}  color="text-emerald-400" value={data?.leads.filter(l=>l.welcome_sent).length ?? "—"} label="Welcome Sent" />
        <StatCard icon={Mail}  color="text-slate-400"   value={data?.leads.filter(l=>l.unsubscribed).length ?? "—"} label="Unsubscribed" />
      </div>
      <DarkCard className="p-4">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <Input placeholder="Search email…" value={search} onChange={e=>setSearch(e.target.value)} className="pl-9 bg-white/5 border-white/10 text-slate-200 placeholder:text-slate-500" />
          </div>
          <select value={vertical} onChange={e=>setVertical(e.target.value)}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300">
            <option value="">All verticals</option>
            <option value="shops">Shops</option>
            <option value="fleet">Fleet</option>
            <option value="general">General</option>
          </select>
          <button onClick={exportCSV} disabled={!data?.leads.length}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-40">
            <Download className="h-4 w-4"/>Export CSV
          </button>
          <button onClick={() => load()} disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-40">
            <RefreshCw className={`h-4 w-4 ${loading?"animate-spin":""}`}/>
          </button>
        </div>
      </DarkCard>
      <DarkCard>
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <p className="text-sm text-slate-400">{data ? `${data.total.toLocaleString()} total` : "Loading…"}</p>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </div>
        {loading ? <LoadingRow /> : !data?.leads.length
          ? <EmptyRow icon={Mail} message="No sign-ups yet." sub="Form submissions from roadcall.ai will appear here." />
          : <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    {["Email","Name","Vertical","Source","Welcome","Date",""].map(h=>(
                      <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.leads.map(lead=>(
                    <tr key={lead.id} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3 font-medium text-slate-200">{lead.email}{lead.unsubscribed&&<span className="ml-2 text-xs text-slate-500">(unsub)</span>}</td>
                      <td className="px-4 py-3 text-slate-400">{lead.name??<span className="text-slate-600">—</span>}</td>
                      <td className="px-4 py-3">{lead.vertical?<span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${VERTICAL_COLORS[lead.vertical]??VERTICAL_COLORS.general}`}>{lead.vertical}</span>:<span className="text-slate-600">—</span>}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{lead.source??"—"}</td>
                      <td className="px-4 py-3">{lead.welcome_sent?<span className="text-emerald-400 text-xs font-medium">✓ Sent</span>:<span className="text-slate-600 text-xs">Pending</span>}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{new Date(lead.created_at).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"})}</td>
                      <td className="px-4 py-3"><button onClick={()=>handleDelete(lead.id)} disabled={deleting===lead.id} className="p-1.5 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 disabled:opacity-40"><Trash2 className="h-3.5 w-3.5"/></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        }
      </DarkCard>
    </div>
  );
}

function MechanicEmailsTab() {
  const [data, setData] = useState<MechanicListResponse | null>(null);
  const [stats, setStats] = useState<MechanicStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const PAGE_SIZE = 50;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        has_email: "true",
        limit: String(PAGE_SIZE),
        offset: String(offset),
        sort_by: "company_name",
        sort_dir: "desc",
      });
      if (search) params.set("q", search);
      if (stateFilter) params.set("state", stateFilter);
      const [listData, statsData] = await Promise.all([
        adminFetch<MechanicListResponse>(`/mechanics/admin/list?${params}`),
        adminFetch<MechanicStats>("/mechanics/admin/stats"),
      ]);
      setData(listData);
      setStats(statsData);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Failed to load mechanic emails");
    } finally { setLoading(false); }
  }, [offset, search, stateFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setOffset(0); }, [search, stateFilter]);

  function exportCSV() {
    if (!data?.items.length) return;
    const rows = [["email","company_name","contact_name","phone","city","state","website","rating","source"],
      ...data.items.map(m=>[m.email??"",m.company_name,m.contact_name,m.phone,m.city??"",m.state??"",m.website??"",m.rating??"",m.source??""])];
    const blob = new Blob([rows.map(r=>r.map(c=>`"${c}"`).join(",")).join("\n")],{type:"text/csv"});
    Object.assign(document.createElement("a"),{href:URL.createObjectURL(blob),download:`mechanic-emails-${new Date().toISOString().slice(0,10)}.csv`}).click();
  }

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;
  const totalMechanics = stats?.total_mechanics ?? 0;
  const withEmail = stats?.total_with_email ?? data?.total ?? 0;
  const pending = Math.max(0, totalMechanics - withEmail);
  const coverage = totalMechanics > 0 ? `${((withEmail / totalMechanics) * 100).toFixed(1)}%` : "0.0%";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard icon={Wrench} color="text-orange-400"  value={withEmail || "—"} label="Mechanics with Email" />
        <StatCard icon={Mail}   color="text-blue-400"    value={pending || "—"} label="Websites Pending" />
        <StatCard icon={Users}  color="text-emerald-400" value={coverage} label="Coverage" />
      </div>
      <DarkCard className="p-4">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <Input placeholder="Search name, email…" value={search} onChange={e=>setSearch(e.target.value)} className="pl-9 bg-white/5 border-white/10 text-slate-200 placeholder:text-slate-500" />
          </div>
          <Input placeholder="State e.g. TX" value={stateFilter} onChange={e=>setStateFilter(e.target.value.toUpperCase().slice(0,2))} className="w-32 bg-white/5 border-white/10 text-slate-200 placeholder:text-slate-500" />
          <button onClick={exportCSV} disabled={!data?.items.length}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-40">
            <Download className="h-4 w-4"/>Export CSV
          </button>
          <button onClick={() => load()} disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-40">
            <RefreshCw className={`h-4 w-4 ${loading?"animate-spin":""}`}/>
          </button>
        </div>
      </DarkCard>
      {error && <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-3 text-sm text-red-200">{error}</div>}
      <DarkCard>
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <p className="text-sm text-slate-400">{data ? `${data.total.toLocaleString()} mechanics with email` : "Loading…"}</p>
          <Pagination page={page} totalPages={totalPages} onChange={p=>setOffset((p-1)*PAGE_SIZE)} />
        </div>
        {loading ? <LoadingRow /> : !data?.items.length
          ? <EmptyRow icon={Wrench} message="No mechanic emails yet." sub="Mechanic contacts with emails will appear here." />
          : <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    {["Business","Email","Quality","Location","Phone","Website"].map(h=>(
                      <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.items.map(m=>(
                    <tr key={m.id} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3"><div className="font-medium text-slate-200 max-w-[180px] truncate">{m.company_name}</div><div className="text-xs text-slate-500">{m.contact_name}</div></td>
                      <td className="px-4 py-3"><a href={`mailto:${m.email}`} className="text-blue-400 hover:underline text-sm">{m.email}</a></td>
                      <td className="px-4 py-3"><span className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium ${emailQualityBadge(m.email_quality).cls}`}>{emailQualityBadge(m.email_quality).label}</span></td>
                      <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">{[m.city,m.state].filter(Boolean).join(", ")||"—"}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs">{m.phone}</td>
                      <td className="px-4 py-3">{m.website?<a href={m.website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-blue-400"><ExternalLink className="h-3 w-3"/>Visit</a>:<span className="text-slate-600">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        }
      </DarkCard>
    </div>
  );
}
