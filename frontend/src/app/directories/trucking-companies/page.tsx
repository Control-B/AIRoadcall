"use client";

import { useCallback, useEffect, useState } from "react";
import { Building2, MapPin, Phone, Search, ShieldCheck, Star, Truck } from "lucide-react";
import Link from "next/link";
import { PageLayout } from "@/components/page-layout";
import { NoCopySurface } from "@/components/privacy/no-copy-surface";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? `${window.location.origin.replace(/\/$/, "")}/api`
    : "https://airoadcall-i76ba.ondigitalocean.app/api");

const PAGE_SIZE = 24;

interface PublicTruckingCompany {
  company_name: string;
  phone: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  rating: number | null;
  review_count: number | null;
  categories: string[];
}

interface DirectoryResponse {
  total: number;
  limit: number;
  offset: number;
  items: PublicTruckingCompany[];
}

interface StatsResponse {
  total: number;
  top_states: { state: string; count: number }[];
}

function Rating({ rating, count }: { rating: number | null; count: number | null }) {
  if (!rating) return <span className="text-xs text-roadcall-muted">Public rating pending</span>;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-roadcall-silver">
      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
      <strong className="text-white">{rating.toFixed(1)}</strong>
      {count ? <span className="text-roadcall-muted">({count.toLocaleString()})</span> : null}
    </span>
  );
}

function filterFallbackRows(rows: PublicTruckingCompany[], query: string, state: string) {
  const needle = query.trim().toLowerCase();
  const stateNeedle = state.trim().toUpperCase();
  return rows.filter((row) => {
    const matchesState = !stateNeedle || row.state?.toUpperCase() === stateNeedle;
    const haystack = [row.company_name, row.city, row.state, row.address, row.phone, ...(row.categories || [])]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return matchesState && (!needle || haystack.includes(needle));
  });
}

function buildFallbackStats(rows: PublicTruckingCompany[]): StatsResponse {
  const counts = rows.reduce<Record<string, number>>((acc, row) => {
    if (row.state) acc[row.state] = (acc[row.state] || 0) + 1;
    return acc;
  }, {});
  return {
    total: rows.length,
    top_states: Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([state, count]) => ({ state, count })),
  };
}

function CompanyCard({ company }: { company: PublicTruckingCompany }) {
  return (
    <article className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/45 p-5 shadow-xl shadow-black/10 backdrop-blur transition hover:border-roadcall-cyan/25">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-bold text-white">{company.company_name}</h2>
          <p className="mt-1 inline-flex items-center gap-1 text-xs text-roadcall-muted">
            <MapPin className="h-3.5 w-3.5" /> {[company.city, company.state].filter(Boolean).join(", ") || "United States"}
          </p>
        </div>
        <Truck className="h-5 w-5 shrink-0 text-roadcall-cyan" />
      </div>
      <div className="mb-4 flex flex-wrap gap-1.5">
        {(company.categories.length ? company.categories : ["Fleet operations", "Trucking"]).slice(0, 4).map((category) => (
          <span key={category} className="rounded-full border border-roadcall-cyan/15 bg-roadcall-cyan/10 px-2 py-0.5 text-[10px] font-medium text-roadcall-cyan">
            {category}
          </span>
        ))}
      </div>
      <div className="mb-4 space-y-2 rounded-xl border border-roadcall-cyan/10 bg-roadcall-ink/45 p-3 text-xs text-roadcall-muted">
        {company.phone ? (
          <a href={`tel:${company.phone}`} className="flex items-center gap-2 text-roadcall-cyan hover:text-white">
            <Phone className="h-3.5 w-3.5" /> {company.phone}
          </a>
        ) : <div className="flex items-center gap-2"><Phone className="h-3.5 w-3.5" /> Phone pending</div>}
        {company.address ? (
          <div className="flex items-start gap-2">
            <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" /> <span>{company.address}</span>
          </div>
        ) : null}
      </div>
      <div className="flex items-center justify-between border-t border-roadcall-cyan/10 pt-3">
        <Rating rating={company.rating} count={company.review_count} />
        <span className="inline-flex items-center gap-1 text-[11px] text-roadcall-muted">No export/download</span>
      </div>
    </article>
  );
}

export default function PublicTruckingCompaniesPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<DirectoryResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      if (query.trim()) params.set("q", query.trim());
      if (state.trim()) params.set("state", state.trim().toUpperCase());
      const [listRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/directories/trucking-companies?${params}`),
        fetch(`${API_URL}/directories/trucking-companies/stats`),
      ]);
      if (!listRes.ok || !statsRes.ok) throw new Error("Directory unavailable");
      const listData = (await listRes.json()) as DirectoryResponse;
      const statsData = (await statsRes.json()) as StatsResponse;
      if (listData.total === 0) {
        const fallbackRes = await fetch("/data/trucking-companies-public.json");
        if (fallbackRes.ok) {
          const fallbackRows = (await fallbackRes.json()) as PublicTruckingCompany[];
          const filtered = filterFallbackRows(fallbackRows, query, state);
          setData({ total: filtered.length, limit: PAGE_SIZE, offset, items: filtered.slice(offset, offset + PAGE_SIZE) });
          setStats(buildFallbackStats(fallbackRows));
          return;
        }
      }
      setData(listData);
      setStats(statsData);
    } catch (err) {
      try {
        const fallbackRes = await fetch("/data/trucking-companies-public.json");
        if (!fallbackRes.ok) throw err;
        const fallbackRows = (await fallbackRes.json()) as PublicTruckingCompany[];
        const filtered = filterFallbackRows(fallbackRows, query, state);
        setData({ total: filtered.length, limit: PAGE_SIZE, offset, items: filtered.slice(offset, offset + PAGE_SIZE) });
        setStats(buildFallbackStats(fallbackRows));
      } catch {
        setError(err instanceof Error ? err.message : "Could not load directory");
      }
    } finally {
      setLoading(false);
    }
  }, [offset, query, state]);

  useEffect(() => {
    const timeout = window.setTimeout(load, 250);
    return () => window.clearTimeout(timeout);
  }, [load]);

  const total = data?.total ?? 0;

  return (
    <PageLayout>
      <NoCopySurface>
        <section className="border-b border-roadcall-cyan/10 bg-gradient-to-b from-roadcall-panel/35 to-transparent">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/15 bg-roadcall-panel/55 px-3 py-1 text-xs font-semibold text-roadcall-cyan">
                <ShieldCheck className="h-3.5 w-3.5" /> Public-safe directory
              </div>
              <h1 className="text-4xl font-black tracking-tight text-white sm:text-5xl">U.S. trucking companies directory</h1>
              <p className="mt-4 text-sm leading-6 text-roadcall-muted">
                Browse public trucking company profiles with names, phone numbers, and addresses. DOT/MC numbers, emails, source data, coordinates, and enrichment metadata remain hidden.
              </p>
            </div>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/50 p-4"><p className="text-2xl font-bold text-white">{stats?.total?.toLocaleString() || "—"}</p><p className="text-xs text-roadcall-muted">Limited public records</p></div>
              <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/50 p-4"><p className="text-2xl font-bold text-white">{stats?.top_states?.[0]?.state || "—"}</p><p className="text-xs text-roadcall-muted">Top state by coverage</p></div>
              <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/50 p-4"><p className="text-2xl font-bold text-white">No</p><p className="text-xs text-roadcall-muted">Download or copy controls</p></div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-5 grid gap-3 rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/45 p-4 lg:grid-cols-[1fr_120px_auto]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-roadcall-muted" />
              <input value={query} onChange={(e) => { setQuery(e.target.value); setOffset(0); }} placeholder="Search by company, city, or category" className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-ink/60 py-3 pl-10 pr-4 text-sm text-white placeholder:text-roadcall-muted/60 focus:border-roadcall-cyan/40 focus:outline-none" />
            </div>
            <input value={state} onChange={(e) => { setState(e.target.value.slice(0, 2).toUpperCase()); setOffset(0); }} placeholder="State" maxLength={2} className="rounded-xl border border-roadcall-cyan/15 bg-roadcall-ink/60 px-4 py-3 text-sm text-white placeholder:text-roadcall-muted/60 focus:border-roadcall-cyan/40 focus:outline-none" />
            <button onClick={() => { setQuery(""); setState(""); setOffset(0); }} className="rounded-xl border border-roadcall-cyan/15 px-4 py-3 text-sm text-roadcall-silver hover:bg-roadcall-cyan/10">Reset</button>
          </div>

          <div className="mb-4 flex items-center justify-between gap-3 text-sm text-roadcall-muted">
            <span>{loading ? "Loading…" : `${total.toLocaleString()} limited records`}</span>
            <Link href="/directories/national-vendors" className="inline-flex items-center gap-2 text-roadcall-cyan hover:text-white"><Building2 className="h-4 w-4" /> National vendors</Link>
          </div>

          {error ? <div className="rounded-2xl border border-red-500/25 bg-red-500/10 p-6 text-red-200">{error}</div> : null}
          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 9 }).map((_, index) => <div key={index} className="h-44 animate-pulse rounded-2xl bg-roadcall-panel/45" />)}</div>
          ) : data?.items.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{data.items.map((company, index) => <CompanyCard key={`${company.company_name}-${company.state}-${index}`} company={company} />)}</div>
          ) : (
            <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/45 p-10 text-center text-roadcall-muted">No public records match those filters.</div>
          )}

          <div className="mt-8 flex justify-center gap-2">
            <button disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="rounded-lg border border-roadcall-cyan/15 px-4 py-2 text-sm disabled:opacity-40">Previous</button>
            <button disabled={offset + PAGE_SIZE >= total || loading} onClick={() => setOffset(offset + PAGE_SIZE)} className="rounded-lg border border-roadcall-cyan/15 px-4 py-2 text-sm disabled:opacity-40">Next</button>
          </div>
        </section>
      </NoCopySurface>
    </PageLayout>
  );
}
