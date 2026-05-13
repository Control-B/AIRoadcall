"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, ExternalLink, Mail, MapPinned, Phone, RefreshCw, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { adminFetch } from "@/lib/admin-auth";

interface VendorStats {
  total: number;
  with_phone: number;
  with_email: number;
  with_website: number;
  top_states: { state: string; count: number }[];
  brands: { brand: string; count: number }[];
}

interface VendorRecord {
  id: string;
  brand_name: string;
  location_name: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  rating: number | null;
  review_count: number | null;
  services: string | null;
}

interface ListResponse { total: number; limit: number; offset: number; items: VendorRecord[]; }
const PAGE_SIZE = 100;

function cleanUrl(url: string) { return url.startsWith("http") ? url : `https://${url}`; }
function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) { return <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-5 shadow-lg"><p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p><p className="mt-2 text-3xl font-bold text-white">{typeof value === "number" ? value.toLocaleString() : value}</p>{sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}</div>; }

function exportCsv(rows: VendorRecord[]) {
  const headers = ["brand_name", "location_name", "phone", "email", "website", "city", "state", "address", "services"];
  const csv = [headers.join(","), ...rows.map((row) => headers.map((key) => JSON.stringify((row as unknown as Record<string, unknown>)[key] ?? "")).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  Object.assign(document.createElement("a"), { href: url, download: `national-vendors-${new Date().toISOString().slice(0, 10)}.csv` }).click();
  URL.revokeObjectURL(url);
}

export default function NationalVendorsPage() {
  const [stats, setStats] = useState<VendorStats | null>(null);
  const [data, setData] = useState<ListResponse | null>(null);
  const [search, setSearch] = useState("");
  const [brand, setBrand] = useState("");
  const [state, setState] = useState("");
  const [hasEmail, setHasEmail] = useState("any");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      if (search.trim()) params.set("q", search.trim());
      if (brand.trim()) params.set("brand", brand.trim());
      if (state.trim()) params.set("state", state.trim().toUpperCase());
      if (hasEmail !== "any") params.set("has_email", String(hasEmail === "yes"));
      const [statsData, listData] = await Promise.all([
        adminFetch<VendorStats>("/admin/directories/national-vendors/stats"),
        adminFetch<ListResponse>(`/admin/directories/national-vendors?${params}`),
      ]);
      setStats(statsData); setData(listData);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load national vendors"); }
    finally { setLoading(false); }
  }, [brand, hasEmail, offset, search, state]);

  useEffect(() => { const timeout = window.setTimeout(load, 250); return () => window.clearTimeout(timeout); }, [load]);
  const total = data?.total ?? 0;

  return <div className="space-y-6">
    <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-cyan-950/50 via-slate-950 to-slate-950 p-6 shadow-2xl"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div><h1 className="flex items-center gap-3 text-2xl font-bold text-white"><MapPinned className="h-7 w-7 text-cyan-400" /> National Vendors</h1><p className="mt-1 text-sm text-slate-400">National truck-service, tire, travel center, and roadside vendor locations.</p></div><div className="flex gap-2"><button onClick={load} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh</button><button onClick={() => exportCsv(data?.items || [])} disabled={!data?.items.length} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-40"><Download className="h-4 w-4" /> Export Page</button></div></div>{stats && <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4"><StatCard label="Locations" value={stats.total} /><StatCard label="With Phone" value={stats.with_phone} /><StatCard label="With Website" value={stats.with_website} /><StatCard label="With Email" value={stats.with_email} sub="Email enrichment pending where blank" /></div>}{stats?.brands?.length ? <div className="mt-5 flex flex-wrap gap-2">{stats.brands.slice(0, 12).map((b) => <button key={b.brand} onClick={() => { setBrand(b.brand); setOffset(0); }} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200 hover:bg-cyan-500/10">{b.brand} <span className="text-slate-500">({b.count})</span></button>)}</div> : null}</div>

    <div className="rounded-2xl border border-white/5 bg-slate-950/60 p-4"><div className="grid grid-cols-1 gap-3 lg:grid-cols-[2fr_180px_120px_150px_auto]"><div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /><Input value={search} onChange={(e) => { setSearch(e.target.value); setOffset(0); }} placeholder="Search vendor, location, phone, service..." className="pl-9" /></div><Input value={brand} onChange={(e) => { setBrand(e.target.value); setOffset(0); }} placeholder="Brand" /><Input value={state} onChange={(e) => { setState(e.target.value.slice(0, 2).toUpperCase()); setOffset(0); }} placeholder="State" maxLength={2} /><select value={hasEmail} onChange={(e) => { setHasEmail(e.target.value); setOffset(0); }} className="h-10 rounded-md border border-input bg-background px-3 text-sm"><option value="any">Any email</option><option value="yes">Has email</option><option value="no">No email</option></select><button onClick={() => { setSearch(""); setBrand(""); setState(""); setHasEmail("any"); setOffset(0); }} className="rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/5">Reset</button></div></div>

    {error && <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-200">{error}</div>}

    <div className="rounded-2xl border border-white/5 bg-slate-950/60"><div className="flex items-center justify-between border-b border-white/5 px-6 py-4"><p className="text-sm text-slate-400">{loading ? "Loading..." : `${total.toLocaleString()} records`}</p><div className="flex gap-2"><button disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="rounded border border-white/10 px-3 py-1 text-sm disabled:opacity-40">Previous</button><button disabled={offset + PAGE_SIZE >= total || loading} onClick={() => setOffset(offset + PAGE_SIZE)} className="rounded border border-white/10 px-3 py-1 text-sm disabled:opacity-40">Next</button></div></div><div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-sm"><thead><tr className="border-b border-white/5 text-left text-xs uppercase text-slate-500">{["Vendor", "Contact", "Location", "Services", "Quality"].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-white/5">{(data?.items || []).map((row) => <tr key={row.id} className="hover:bg-white/[0.02]"><td className="px-4 py-3"><div className="font-semibold text-white">{row.brand_name}</div><div className="text-xs text-slate-400">{row.location_name}</div></td><td className="space-y-1 px-4 py-3">{row.phone ? <a href={`tel:${row.phone}`} className="flex items-center gap-2 text-blue-300"><Phone className="h-3.5 w-3.5" />{row.phone}</a> : <span className="text-slate-600">No phone</span>}{row.email ? <a href={`mailto:${row.email}`} className="flex items-center gap-2 text-blue-300"><Mail className="h-3.5 w-3.5" />{row.email}</a> : <div className="text-xs text-slate-600">No email yet</div>}{row.website && <a href={cleanUrl(row.website)} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-xs text-blue-300"><ExternalLink className="h-3.5 w-3.5" />Website</a>}</td><td className="px-4 py-3 text-slate-300"><div>{[row.city, row.state].filter(Boolean).join(", ") || "—"}</div><div className="mt-1 max-w-xs text-xs text-slate-500">{row.address}</div></td><td className="px-4 py-3 text-xs text-slate-400">{(row.services || "").replaceAll(";", ", ")}</td><td className="px-4 py-3 text-slate-300">{row.rating ? `${row.rating.toFixed(1)} ★` : "—"}<div className="text-xs text-slate-500">{row.review_count ? `${row.review_count.toLocaleString()} reviews` : "no reviews"}</div></td></tr>)}</tbody></table></div></div>
  </div>;
}
