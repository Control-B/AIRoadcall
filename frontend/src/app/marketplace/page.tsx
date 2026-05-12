"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock,
  Compass,
  Filter,
  Languages,
  MapPin,
  Radar,
  ShieldCheck,
  Sparkles,
  Star,
  Truck,
  Wrench,
  Zap,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type Provider = {
  id: string;
  company_name: string;
  city: string | null;
  state: string | null;
  website: string | null;
  rating: number | null;
  review_count: number | null;
  distance_miles: number | null;
  service_types: string[];
  vehicle_types_supported: string[];
  accepts_mobile_roadside: boolean;
  emergency_service: boolean;
  service_radius_miles: number;
  estimated_response_minutes: number | null;
  availability_status: string;
  marketplace_score: number;
  dispatch_fit_score: number;
  trust_score: number;
  roadside_relevance_score: number;
  response_confidence_score: number;
  quality_score: number;
  trust_level: string;
  badges: string[];
  reasons: string[];
  score_breakdown: Record<string, number>;
};

type MarketplaceResponse = {
  summary: string;
  search_mode: string;
  total_candidates: number;
  returned: number;
  location_label: string;
  issue_type: string;
  vehicle_type: string | null;
  radius_miles: number | null;
  providers: Provider[];
};

const ISSUE_OPTIONS = [
  ["flat_tire", "Flat tire"],
  ["tow_needed", "Tow / recovery"],
  ["dead_battery", "Battery / jump"],
  ["engine_trouble", "Engine / diesel"],
  ["trailer_repair", "Trailer repair"],
  ["fuel_delivery", "Fuel / DEF"],
  ["lockout", "Lockout"],
];

const VEHICLE_OPTIONS = [
  ["car", "Car"],
  ["truck", "Truck"],
  ["heavy_duty", "Heavy-duty"],
  ["rv", "RV"],
  ["trailer", "Trailer"],
  ["fleet", "Fleet"],
];

export default function MarketplacePage() {
  const [city, setCity] = useState("Orlando");
  const [stateCode, setStateCode] = useState("FL");
  const [issueType, setIssueType] = useState("tow_needed");
  const [vehicleType, setVehicleType] = useState("truck");
  const [emergencyOnly, setEmergencyOnly] = useState(false);
  const [data, setData] = useState<MarketplaceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search() {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        city,
        state: stateCode,
        issue_type: issueType,
        vehicle_type: vehicleType,
        radius_miles: "75",
        roadside_only: "true",
        emergency_only: String(emergencyOnly),
        limit: "12",
      });
      const res = await fetch(`${API_URL}/mechanics/marketplace?${params}`);
      if (!res.ok) throw new Error(`Search failed (${res.status})`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to search providers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const topProvider = data?.providers[0];
  const avgTrust = useMemo(() => {
    if (!data?.providers.length) return 0;
    return data.providers.reduce((sum, item) => sum + item.trust_score, 0) / data.providers.length;
  }, [data]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="relative overflow-hidden border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.35),transparent_32%),radial-gradient(circle_at_top_right,rgba(16,185,129,0.24),transparent_30%)]" />
        <div className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-sm text-cyan-100">
                <Radar className="h-4 w-4" /> AI roadside dispatch marketplace
              </div>
              <h1 className="mt-6 max-w-4xl text-4xl font-black tracking-tight sm:text-6xl">
                Find roadside help with deterministic dispatch intelligence.
              </h1>
              <p className="mt-5 max-w-2xl text-lg text-slate-300">
                Roadcall ranks providers by fit, radius, roadside capability, trust, response confidence,
                and operational readiness — before an AI ever spends tokens.
              </p>
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <Metric icon={Truck} label="Provider network" value="35k+" />
                <Metric icon={Zap} label="Layer-1 scoring" value="0 LLM cost" />
                <Metric icon={Languages} label="Multilingual-ready" value="Intake + dispatch" />
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/10 p-4 shadow-2xl backdrop-blur">
              <div className="rounded-2xl bg-slate-900/90 p-5">
                <div className="mb-5 flex items-center gap-3">
                  <div className="rounded-2xl bg-blue-500 p-3">
                    <Bot className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm uppercase tracking-[0.3em] text-blue-200">Need help now?</p>
                    <h2 className="text-xl font-bold">AI intake → ranked providers</h2>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input label="City" value={city} onChange={setCity} />
                  <Input label="State" value={stateCode} onChange={(v) => setStateCode(v.toUpperCase().slice(0, 2))} />
                  <Select label="Issue" value={issueType} onChange={setIssueType} options={ISSUE_OPTIONS} />
                  <Select label="Vehicle" value={vehicleType} onChange={setVehicleType} options={VEHICLE_OPTIONS} />
                </div>
                <label className="mt-4 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-slate-200">
                  <input
                    type="checkbox"
                    checked={emergencyOnly}
                    onChange={(event) => setEmergencyOnly(event.target.checked)}
                    className="h-4 w-4 rounded border-white/20"
                  />
                  Only show 24/7 emergency-capable providers
                </label>
                <button
                  onClick={search}
                  disabled={loading}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-500 px-4 py-3 font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:bg-blue-400 disabled:opacity-60"
                >
                  {loading ? <Activity className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Rank providers
                </button>
                {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-6 grid gap-4 md:grid-cols-4">
          <IntelCard icon={Compass} label="Search mode" value={data?.search_mode?.replace("_", " ") || "—"} />
          <IntelCard icon={Filter} label="Candidates scored" value={data?.total_candidates?.toLocaleString() || "—"} />
          <IntelCard icon={ShieldCheck} label="Avg trust" value={data ? `${Math.round(avgTrust * 100)}%` : "—"} />
          <IntelCard icon={Clock} label="Top ETA" value={topProvider?.estimated_response_minutes ? `${topProvider.estimated_response_minutes} min` : "—"} />
        </div>

        <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <h2 className="text-2xl font-bold">Ranked provider intelligence</h2>
            <p className="mt-1 text-sm text-slate-400">
              {data?.summary || "Search a city/state to see operational marketplace rankings."}
            </p>
          </div>
          <div className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
            Scores combine distance, roadside fit, service match, reliability, availability, reviews, response speed, and fleet fit.
          </div>
        </div>

        {loading ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {[...Array(6)].map((_, index) => <div key={index} className="h-72 animate-pulse rounded-3xl bg-white/10" />)}
          </div>
        ) : data?.providers.length ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {data.providers.map((provider, index) => (
              <ProviderCard key={provider.id} provider={provider} rank={index + 1} />
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-10 text-center text-slate-300">
            No providers found. Try a nearby city, wider radius, or disable 24/7-only.
          </div>
        )}
      </section>
    </main>
  );
}

function Metric({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
      <Icon className="mb-3 h-5 w-5 text-cyan-200" />
      <p className="text-2xl font-black">{value}</p>
      <p className="text-sm text-slate-300">{label}</p>
    </div>
  );
}

function IntelCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4">
      <div className="mb-3 flex items-center gap-2 text-slate-400">
        <Icon className="h-4 w-4" />
        <span className="text-xs uppercase tracking-[0.2em]">{label}</span>
      </div>
      <p className="text-2xl font-bold capitalize">{value}</p>
    </div>
  );
}

function ProviderCard({ provider, rank }: { provider: Provider; rank: number }) {
  const scorePercent = Math.round(provider.marketplace_score * 100);
  return (
    <article className="rounded-3xl border border-white/10 bg-white/[0.06] p-5 shadow-xl transition hover:border-blue-300/40 hover:bg-white/[0.09]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-2 inline-flex rounded-full bg-blue-500/15 px-2.5 py-1 text-xs font-semibold text-blue-200">
            #{rank} dispatch fit
          </div>
          <h3 className="line-clamp-2 text-lg font-bold">{provider.company_name}</h3>
          <p className="mt-1 flex items-center gap-1 text-sm text-slate-400">
            <MapPin className="h-3.5 w-3.5" /> {[provider.city, provider.state].filter(Boolean).join(", ") || "Service area"}
          </p>
        </div>
        <div className="rounded-2xl bg-emerald-400/10 px-3 py-2 text-center">
          <p className="text-2xl font-black text-emerald-200">{scorePercent}</p>
          <p className="text-[10px] uppercase tracking-wider text-emerald-100/70">score</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
        <ScorePill label="Trust" value={provider.trust_score} />
        <ScorePill label="Roadside" value={provider.roadside_relevance_score} />
        <ScorePill label="Response" value={provider.response_confidence_score} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {provider.badges.slice(0, 4).map((badge) => (
          <span key={badge} className="rounded-full border border-white/10 bg-white/10 px-2.5 py-1 text-xs text-slate-200">
            {badge}
          </span>
        ))}
      </div>

      <div className="mt-4 space-y-2 text-sm text-slate-300">
        {provider.reasons.slice(0, 4).map((reason) => (
          <p key={reason} className="flex gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> {reason}
          </p>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/10 pt-4 text-sm text-slate-300">
        <div className="flex items-center gap-2"><Star className="h-4 w-4 text-amber-300" /> {provider.rating ? `${provider.rating.toFixed(1)} (${provider.review_count || 0})` : "Rating pending"}</div>
        <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-cyan-300" /> {provider.estimated_response_minutes ? `${provider.estimated_response_minutes} min` : "ETA unknown"}</div>
        <div className="flex items-center gap-2"><Wrench className="h-4 w-4 text-blue-300" /> {provider.service_radius_miles} mi radius</div>
        <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-300" /> {provider.trust_level.replace("_", " ")}</div>
      </div>
    </article>
  );
}

function ScorePill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-slate-900/70 px-2 py-2">
      <p className="font-bold text-white">{Math.round(value * 100)}%</p>
      <p className="text-slate-500">{label}</p>
    </div>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-400">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none placeholder:text-slate-500 focus:border-blue-300"
      />
    </label>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-white/10 bg-slate-800 px-3 py-2 text-white outline-none focus:border-blue-300"
      >
        {options.map(([id, labelText]) => <option key={id} value={id}>{labelText}</option>)}
      </select>
    </label>
  );
}
