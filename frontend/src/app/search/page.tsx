"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  MapPin,
  Filter,
  Phone,
  Star,
  CheckCircle2,
  Clock,
  Zap,
  Truck,
  Wrench,
  ChevronDown,
  X,
  ArrowRight,
  AlertCircle,
  Shield,
} from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { HELP_PHONE, telHref } from "@/lib/phone";
import { NoCopySurface } from "@/components/privacy/no-copy-surface";
import { getApiBase } from "@/lib/api-client";

const API_URL = getApiBase();

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY",
];

const SERVICE_TYPES = [
  ["", "All Services"],
  ["tire_repair", "Tire Repair / Flat"],
  ["towing", "Towing & Recovery"],
  ["battery_jump", "Battery / Jump Start"],
  ["engine_diesel", "Engine / Diesel"],
  ["trailer_repair", "Trailer Repair"],
  ["fuel_delivery", "Fuel / DEF Delivery"],
  ["lockout", "Lockout Service"],
  ["preventive_maintenance", "Preventive Maintenance"],
  ["heavy_duty", "Heavy Duty Specialist"],
  ["reefer", "Reefer / Refrigeration"],
  ["mobile_repair", "Mobile Repair"],
];

type Mechanic = {
  id: string;
  company_name: string;
  city: string | null;
  state: string | null;
  rating: number | null;
  review_count: number | null;
  accepts_mobile_roadside: boolean;
  emergency_service: boolean;
  is_emergency_24_7: boolean;
  service_types: string[];
  priority_score: number;
};

type SearchResult = {
  mechanics: Mechanic[];
  total: number;
  page: number;
  page_size: number;
};

function StarRating({ rating, count }: { rating: number | null; count: number | null }) {
  if (!rating) return <span className="text-xs text-roadcall-muted">No rating</span>;
  return (
    <span className="flex items-center gap-1">
      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
      <span className="text-sm font-semibold text-white">{rating.toFixed(1)}</span>
      {count && <span className="text-xs text-roadcall-muted">({count})</span>}
    </span>
  );
}

function MechanicCard({ m }: { m: Mechanic }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/40 backdrop-blur-sm hover:border-roadcall-cyan/30 hover:bg-roadcall-panel/60 transition-all duration-200 p-5">
      <div className="absolute inset-0 bg-gradient-to-br from-roadcall-cyan/[0.04] via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-white text-base leading-tight truncate">{m.company_name}</h3>
            {(m.city || m.state) && (
              <p className="flex items-center gap-1 text-xs text-roadcall-muted mt-0.5">
                <MapPin className="h-3 w-3 shrink-0" />
                {[m.city, m.state].filter(Boolean).join(", ")}
              </p>
            )}
          </div>
          <StarRating rating={m.rating} count={m.review_count} />
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {m.is_emergency_24_7 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/25 text-emerald-300 text-[10px] font-semibold">
              <Clock className="h-3 w-3" /> 24/7
            </span>
          )}
          {m.accepts_mobile_roadside && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/15 border border-blue-500/25 text-blue-300 text-[10px] font-semibold">
              <Truck className="h-3 w-3" /> Mobile
            </span>
          )}
          {m.emergency_service && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/15 border border-red-500/25 text-red-300 text-[10px] font-semibold">
              <Zap className="h-3 w-3" /> Emergency
            </span>
          )}
          {m.service_types?.slice(0, 2).map((s) => (
            <span key={s} className="inline-flex items-center px-2 py-0.5 rounded-full bg-roadcall-cyan/10 border border-roadcall-cyan/15 text-roadcall-cyan text-[10px] font-medium">
              {s.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        <div className="rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/50 px-3 py-2.5 text-center text-xs text-roadcall-muted">
          Contact details are protected. Use Roadcall dispatch to connect.
        </div>
      </div>
    </div>
  );
}

function SearchPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [state, setState] = useState(searchParams.get("state") || "");
  const [city, setCity] = useState(searchParams.get("city") || "");
  const [serviceType, setServiceType] = useState(searchParams.get("service") || "");
  const [only24_7, setOnly24_7] = useState(searchParams.get("emergency") === "1");
  const [onlyMobile, setOnlyMobile] = useState(searchParams.get("mobile") === "1");
  const [page, setPage] = useState(1);

  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const doSearch = useCallback(async (resetPage = false) => {
    const currentPage = resetPage ? 1 : page;
    if (resetPage) setPage(1);
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (state) params.set("state", state);
    if (city) params.set("city", city);
    if (serviceType) params.set("service_type", serviceType);
    if (only24_7) params.set("is_24_7", "true");
    if (onlyMobile) params.set("mobile_only", "true");
    params.set("page", String(currentPage));
    params.set("page_size", "24");

    try {
      const res = await fetch(`${API_URL}/mechanics/search?${params}`);
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setResults(data);
    } catch {
      // Fall back to a public-friendly empty state
      setResults({ mechanics: [], total: 0, page: 1, page_size: 24 });
      setError("Search unavailable — try the AI dispatcher for instant help.");
    } finally {
      setLoading(false);
    }
  }, [query, state, city, serviceType, only24_7, onlyMobile, page]);

  useEffect(() => {
    doSearch(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, city, serviceType, only24_7, onlyMobile]);

  const totalPages = results ? Math.ceil(results.total / results.page_size) : 0;

  return (
    <PageLayout>
      <NoCopySurface>
      {/* Hero search header */}
      <section className="relative pt-10 pb-8 border-b border-roadcall-cyan/10 bg-gradient-to-b from-roadcall-panel/30 to-transparent">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="mb-6 text-center">
            <div className="inline-flex items-center gap-2 bg-roadcall-panel/45 border border-roadcall-cyan/15 backdrop-blur-sm rounded-full px-4 py-1.5 mb-4">
              <Shield className="h-3.5 w-3.5 text-roadcall-cyan" />
              <span className="text-xs font-medium text-roadcall-silver/85 tracking-wide">35,000+ Verified Providers · All 50 States</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-white mb-2">Search Truck Service Near You</h1>
            <p className="text-roadcall-muted text-sm">Search mechanics, repair shops, towing, and roadside providers nationwide.</p>
          </div>

          {/* Main search bar */}
          <form
            onSubmit={(e) => { e.preventDefault(); doSearch(true); }}
            className="flex gap-2 mb-4"
          >
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-roadcall-muted pointer-events-none" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Shop name, city, state, or service type…"
                className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-roadcall-panel/60 border border-roadcall-cyan/15 text-white placeholder:text-roadcall-muted/60 focus:outline-none focus:border-roadcall-cyan/40 focus:bg-roadcall-panel/80 text-sm transition-all"
              />
            </div>
            <button
              type="submit"
              className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-semibold px-6 py-3.5 rounded-xl text-sm transition-all shrink-0"
            >
              Search
            </button>
          </form>

          {/* Quick filters row */}
          <div className="flex flex-wrap items-center gap-2">
            {/* State picker */}
            <div className="relative">
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="appearance-none pl-3 pr-8 py-2 rounded-lg bg-roadcall-panel/50 border border-roadcall-cyan/15 text-sm text-roadcall-silver hover:border-roadcall-cyan/35 focus:outline-none focus:border-roadcall-cyan/50 transition-all cursor-pointer"
              >
                <option value="">All States</option>
                {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-roadcall-muted pointer-events-none" />
            </div>

            {/* City */}
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              onBlur={() => doSearch(true)}
              placeholder="City"
              className="px-3 py-2 rounded-lg bg-roadcall-panel/50 border border-roadcall-cyan/15 text-sm text-roadcall-silver placeholder:text-roadcall-muted/50 focus:outline-none focus:border-roadcall-cyan/40 transition-all w-32"
            />

            {/* Service type */}
            <div className="relative">
              <select
                value={serviceType}
                onChange={(e) => setServiceType(e.target.value)}
                className="appearance-none pl-3 pr-8 py-2 rounded-lg bg-roadcall-panel/50 border border-roadcall-cyan/15 text-sm text-roadcall-silver hover:border-roadcall-cyan/35 focus:outline-none focus:border-roadcall-cyan/50 transition-all cursor-pointer"
              >
                {SERVICE_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-roadcall-muted pointer-events-none" />
            </div>

            {/* Toggle filters */}
            <button
              onClick={() => setFiltersOpen(!filtersOpen)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-roadcall-cyan/15 bg-roadcall-panel/50 text-sm text-roadcall-silver hover:border-roadcall-cyan/35 hover:text-white transition-all"
            >
              <Filter className="h-3.5 w-3.5" />
              More Filters
              {(only24_7 || onlyMobile) && (
                <span className="ml-1 w-1.5 h-1.5 rounded-full bg-roadcall-orange" />
              )}
            </button>

            {/* Clear */}
            {(query || state || city || serviceType || only24_7 || onlyMobile) && (
              <button
                onClick={() => {
                  setQuery(""); setState(""); setCity(""); setServiceType("");
                  setOnly24_7(false); setOnlyMobile(false);
                }}
                className="flex items-center gap-1 text-xs text-roadcall-muted hover:text-white transition-colors"
              >
                <X className="h-3.5 w-3.5" /> Clear all
              </button>
            )}
          </div>

          {/* Expanded filters */}
          {filtersOpen && (
            <div className="mt-3 p-4 rounded-xl bg-roadcall-panel/40 border border-roadcall-cyan/10 flex flex-wrap gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={only24_7}
                  onChange={(e) => setOnly24_7(e.target.checked)}
                  className="accent-roadcall-orange w-4 h-4"
                />
                <span className="text-sm text-roadcall-silver">24/7 Emergency Only</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={onlyMobile}
                  onChange={(e) => setOnlyMobile(e.target.checked)}
                  className="accent-roadcall-orange w-4 h-4"
                />
                <span className="text-sm text-roadcall-silver">Mobile / Roadside Only</span>
              </label>
            </div>
          )}
        </div>
      </section>

      {/* Results area */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Result count / error */}
        <div className="flex items-center justify-between mb-5">
          <div>
            {loading ? (
              <span className="text-sm text-roadcall-muted animate-pulse">Searching…</span>
            ) : error ? (
              <span className="flex items-center gap-1.5 text-sm text-amber-400"><AlertCircle className="h-4 w-4" />{error}</span>
            ) : results ? (
              <span className="text-sm text-roadcall-muted">
                <span className="text-white font-semibold">{results.total.toLocaleString()}</span> providers found
                {state && ` in ${state}`}{city && `, ${city}`}
              </span>
            ) : null}
          </div>
          {/* AI CTA */}
          <a
            href={telHref(HELP_PHONE)}
            className="hidden sm:flex items-center gap-2 bg-roadcall-orange/10 border border-roadcall-orange/30 hover:bg-roadcall-orange/20 text-roadcall-orange text-xs font-semibold px-4 py-2 rounded-full transition-all"
          >
            <Zap className="h-3.5 w-3.5" /> Let AI dispatch for you
          </a>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30 h-48 animate-pulse" />
            ))}
          </div>
        ) : results && results.mechanics.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {results.mechanics.map((m) => <MechanicCard key={m.id} m={m} />)}
          </div>
        ) : !loading && (
          <div className="text-center py-20">
            <Wrench className="h-12 w-12 text-roadcall-muted mx-auto mb-4" />
            <p className="text-white font-semibold text-lg mb-2">No providers found</p>
            <p className="text-roadcall-muted text-sm mb-6">Try broadening your search or let our AI dispatcher find the best match instantly.</p>
            <a
              href={telHref(HELP_PHONE)}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-semibold px-6 py-3 rounded-xl text-sm transition-all"
            >
              <Phone className="h-4 w-4" /> Call AI Dispatcher
            </a>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-10">
            <button
              disabled={page <= 1}
              onClick={() => { setPage(page - 1); doSearch(); }}
              className="px-4 py-2 rounded-lg border border-roadcall-cyan/15 bg-roadcall-panel/40 text-sm text-roadcall-silver disabled:opacity-40 hover:border-roadcall-cyan/35 hover:text-white transition-all"
            >
              ← Prev
            </button>
            <span className="text-sm text-roadcall-muted">Page {page} of {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => { setPage(page + 1); doSearch(); }}
              className="px-4 py-2 rounded-lg border border-roadcall-cyan/15 bg-roadcall-panel/40 text-sm text-roadcall-silver disabled:opacity-40 hover:border-roadcall-cyan/35 hover:text-white transition-all"
            >
              Next →
            </button>
          </div>
        )}
      </section>

      {/* AI Roadside Dispatch CTA banner */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-16">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-roadcall-orange/20 via-roadcall-panel/60 to-blue-900/30 border border-roadcall-orange/20 p-8 md:p-12 flex flex-col md:flex-row items-center gap-8">
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 bg-roadcall-orange/15 border border-roadcall-orange/25 rounded-full px-3 py-1 text-xs font-bold text-roadcall-orange uppercase tracking-wide mb-4">
              <Zap className="h-3.5 w-3.5" /> AI Roadside OS
            </div>
            <h2 className="text-2xl md:text-3xl font-black text-white mb-3">Can&apos;t find the right provider?</h2>
            <p className="text-roadcall-muted text-sm leading-relaxed max-w-lg">
              Call our AI dispatcher. Sandy answers in seconds, captures your location, matches the best-rated nearby mechanic, and coordinates the dispatch — all in under 90 seconds.
            </p>
          </div>
          <div className="flex flex-col gap-3 shrink-0">
            <a
              href={telHref(HELP_PHONE)}
              className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold px-8 py-4 rounded-2xl text-sm transition-all shadow-xl shadow-blue-900/30"
            >
              <Phone className="h-5 w-5" /> Call AI Dispatcher
            </a>
            <Link
              href="/marketplace"
              className="inline-flex items-center justify-center gap-2 border border-roadcall-cyan/25 bg-roadcall-panel/40 text-roadcall-silver hover:text-white hover:border-roadcall-cyan/45 px-8 py-4 rounded-2xl text-sm font-semibold transition-all"
            >
              AI-Ranked Marketplace <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
      </NoCopySurface>
    </PageLayout>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-roadcall-void" />}>
      <SearchPageInner />
    </Suspense>
  );
}
