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
  Plus,
  Radar,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  Truck,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import { NoCopySurface } from "@/components/privacy/no-copy-surface";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? `${window.location.origin.replace(/\/$/, "")}/api`
    : "https://airoadcall-i76ba.ondigitalocean.app/api");

type Provider = {
  id: string;
  company_name: string;
  city: string | null;
  state: string | null;
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
  const [rateTarget, setRateTarget] = useState<Provider | null>(null);
  const [claimTarget, setClaimTarget] = useState<Provider | null>(null);
  const [submitOpen, setSubmitOpen] = useState(false);

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
    <main className="roadcall-page min-h-screen text-roadcall-silver">
      <NoCopySurface>
      <section className="relative overflow-hidden border-b border-roadcall-cyan/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(20,216,255,0.26),transparent_32%),radial-gradient(circle_at_top_right,rgba(10,132,255,0.26),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(255,138,0,0.13),transparent_26%)]" />
        <div className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div>
              <div className="roadcall-chip inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm">
                <Radar className="h-4 w-4" /> AI roadside dispatch marketplace
              </div>
              <h1 className="mt-6 max-w-4xl text-4xl font-black tracking-tight sm:text-6xl">
                Find roadside help with deterministic dispatch intelligence.
              </h1>
              <p className="mt-5 max-w-2xl text-lg text-roadcall-muted">
                Roadcall ranks providers by fit, radius, roadside capability, trust, response confidence,
                and operational readiness — before an AI ever spends tokens.
              </p>
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <Metric icon={Truck} label="Provider network" value="35k+" />
                <Metric icon={Zap} label="Layer-1 scoring" value="0 LLM cost" />
                <Metric icon={Languages} label="Multilingual-ready" value="Intake + dispatch" />
              </div>
            </div>

            <div className="roadcall-surface rounded-3xl p-4 shadow-2xl">
              <div className="rounded-2xl bg-roadcall-ink/90 p-5">
                <div className="mb-5 flex items-center gap-3">
                  <div className="rounded-2xl bg-gradient-to-br from-roadcall-blue to-roadcall-cyan p-3 shadow-lg shadow-roadcall-blue/25">
                    <Bot className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm uppercase tracking-[0.3em] text-roadcall-cyan">Need help now?</p>
                    <h2 className="text-xl font-bold">AI intake → ranked providers</h2>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input label="City" value={city} onChange={setCity} />
                  <Input label="State" value={stateCode} onChange={(v) => setStateCode(v.toUpperCase().slice(0, 2))} />
                  <Select label="Issue" value={issueType} onChange={setIssueType} options={ISSUE_OPTIONS} />
                  <Select label="Vehicle" value={vehicleType} onChange={setVehicleType} options={VEHICLE_OPTIONS} />
                </div>
                <label className="mt-4 flex items-center gap-2 rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/60 px-3 py-3 text-sm text-roadcall-silver">
                  <input
                    type="checkbox"
                    checked={emergencyOnly}
                    onChange={(event) => setEmergencyOnly(event.target.checked)}
                    className="h-4 w-4 rounded border-roadcall-cyan/20"
                  />
                  Only show 24/7 emergency-capable providers
                </label>
                <button
                  onClick={search}
                  disabled={loading}
                  className="roadcall-primary-button mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 font-semibold transition disabled:opacity-60"
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
            <p className="mt-1 text-sm text-roadcall-muted">
              {data?.summary || "Search a city/state to see operational marketplace rankings."}
            </p>
          </div>
          <div className="rounded-full border border-roadcall-cyan/10 px-3 py-1 text-xs text-roadcall-silver/85">
            Scores combine distance, roadside fit, service match, reliability, availability, reviews, response speed, and fleet fit.
          </div>
        </div>

        {loading ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {[...Array(6)].map((_, index) => <div key={index} className="h-72 animate-pulse rounded-3xl bg-roadcall-panel/60" />)}
          </div>
        ) : data?.providers.length ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {data.providers.map((provider, index) => (
              <ProviderCard
                key={provider.id}
                provider={provider}
                rank={index + 1}
                onRate={() => setRateTarget(provider)}
                onClaim={() => setClaimTarget(provider)}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-roadcall-cyan/10 bg-roadcall-panel/45 p-10 text-center text-roadcall-silver/85">
            No providers found. Try a nearby city, wider radius, or disable 24/7-only.
          </div>
        )}

        <div className="mt-10 flex flex-col items-center gap-3 rounded-3xl border border-roadcall-cyan/10 bg-gradient-to-r from-blue-500/10 to-emerald-500/10 p-8 text-center">
          <h3 className="text-xl font-bold">Own a roadside or repair business?</h3>
          <p className="max-w-2xl text-sm text-roadcall-silver/85">
            Add your business to the Roadcall marketplace for free. To edit a listing later you must claim it as the owner — verified by phone or by an active Roadcall subscription (AI Telephony, AI Voice + Text, Social Media, or Website Management).
          </p>
          <button
            onClick={() => setSubmitOpen(true)}
            className="mt-2 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-5 py-3 font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:brightness-110"
          >
            <Plus className="h-4 w-4" /> Add your business
          </button>
        </div>
      </section>

      {rateTarget && (
        <RateModal provider={rateTarget} onClose={() => setRateTarget(null)} onSaved={() => { setRateTarget(null); search(); }} />
      )}
      {claimTarget && (
        <ClaimModal provider={claimTarget} onClose={() => setClaimTarget(null)} onSaved={() => { setClaimTarget(null); search(); }} />
      )}
      {submitOpen && (
        <SubmitModal onClose={() => setSubmitOpen(false)} onSaved={() => { setSubmitOpen(false); search(); }} />
      )}
      </NoCopySurface>
    </main>
  );
}

function Metric({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/60 p-4 backdrop-blur">
      <Icon className="mb-3 h-5 w-5 text-cyan-200" />
      <p className="text-2xl font-black">{value}</p>
      <p className="text-sm text-roadcall-silver/85">{label}</p>
    </div>
  );
}

function IntelCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/50 p-4">
      <div className="mb-3 flex items-center gap-2 text-roadcall-muted">
        <Icon className="h-4 w-4" />
        <span className="text-xs uppercase tracking-[0.2em]">{label}</span>
      </div>
      <p className="text-2xl font-bold capitalize">{value}</p>
    </div>
  );
}

function ProviderCard({ provider, rank, onRate, onClaim }: { provider: Provider; rank: number; onRate: () => void; onClaim: () => void }) {
  const scorePercent = Math.round(provider.marketplace_score * 100);
  return (
    <article className="rounded-3xl border border-roadcall-cyan/10 bg-roadcall-panel/50 p-5 shadow-xl transition hover:border-blue-300/40 hover:bg-roadcall-panel/70">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-2 inline-flex rounded-full bg-blue-500/15 px-2.5 py-1 text-xs font-semibold text-blue-200">
            #{rank} dispatch fit
          </div>
          <h3 className="line-clamp-2 text-lg font-bold">{provider.company_name}</h3>
          <p className="mt-1 flex items-center gap-1 text-sm text-roadcall-muted">
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
          <span key={badge} className="rounded-full border border-roadcall-cyan/10 bg-roadcall-panel/60 px-2.5 py-1 text-xs text-roadcall-silver">
            {badge}
          </span>
        ))}
      </div>

      <div className="mt-4 space-y-2 text-sm text-roadcall-silver/85">
        {provider.reasons.slice(0, 4).map((reason) => (
          <p key={reason} className="flex gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> {reason}
          </p>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-roadcall-cyan/10 pt-4 text-sm text-roadcall-silver/85">
        <div className="flex items-center gap-2"><Star className="h-4 w-4 text-roadcall-orange" /> {provider.rating ? `${provider.rating.toFixed(1)} (${provider.review_count || 0})` : "Rating pending"}</div>
        <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-cyan-300" /> {provider.estimated_response_minutes ? `${provider.estimated_response_minutes} min` : "ETA unknown"}</div>
        <div className="flex items-center gap-2"><Wrench className="h-4 w-4 text-blue-300" /> {provider.service_radius_miles} mi radius</div>
        <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-300" /> {provider.trust_level.replace("_", " ")}</div>
      </div>

      <div className="mt-4 flex gap-2">
        <button onClick={onRate} className="flex-1 rounded-xl border border-amber-300/40 bg-amber-300/10 px-3 py-2 text-xs font-semibold text-amber-100 transition hover:bg-amber-300/20">
          ⭐ Rate provider
        </button>
        <button onClick={onClaim} className="flex-1 rounded-xl border border-blue-300/40 bg-blue-300/10 px-3 py-2 text-xs font-semibold text-blue-100 transition hover:bg-blue-300/20">
          🔒 Claim listing
        </button>
      </div>
    </article>
  );
}

// ── Modals ─────────────────────────────────────────────────────────────

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg rounded-3xl border border-roadcall-cyan/10 bg-roadcall-ink p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">{title}</h3>
          <button onClick={onClose} className="rounded-full p-1 text-roadcall-muted hover:bg-roadcall-panel/60 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-roadcall-muted">{label}</span>
      {children}
    </label>
  );
}

const INPUT_CLS = "w-full rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/60 px-3 py-2 text-white outline-none placeholder:text-roadcall-muted/70 focus:border-blue-300";

function RateModal({ provider, onClose, onSaved }: { provider: Provider; onClose: () => void; onSaved: () => void }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  async function submit() {
    setBusy(true); setErr(""); setOk("");
    try {
      const res = await fetch(`${API_URL}/marketplace/${provider.id}/review`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, comment: comment || undefined, reviewer_name: name || undefined, reviewer_phone: phone || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not submit review");
      setOk(`Thanks! New average: ${data.new_average.toFixed(1)} (${data.new_review_count})`);
      setTimeout(onSaved, 1200);
    } catch (e) { setErr(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }

  return (
    <Modal title={`Rate ${provider.company_name}`} onClose={onClose}>
      <div className="space-y-4">
        <Field label="Rating">
          <div className="flex gap-2">
            {[1,2,3,4,5].map((n) => (
              <button key={n} onClick={() => setRating(n)} className={`text-3xl ${n <= rating ? "text-roadcall-orange" : "text-roadcall-muted/55"}`}>★</button>
            ))}
          </div>
        </Field>
        <Field label="Comment (optional)">
          <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} className={INPUT_CLS} maxLength={2000} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Your name"><input value={name} onChange={(e) => setName(e.target.value)} className={INPUT_CLS} /></Field>
          <Field label="Your phone (helps prevent spam)"><input value={phone} onChange={(e) => setPhone(e.target.value)} className={INPUT_CLS} /></Field>
        </div>
        {err && <p className="text-sm text-red-300">{err}</p>}
        {ok && <p className="text-sm text-emerald-300">{ok}</p>}
        <button disabled={busy} onClick={submit} className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-3 font-semibold text-slate-900 hover:bg-amber-300 disabled:opacity-60">
          <Send className="h-4 w-4" /> Submit rating
        </button>
      </div>
    </Modal>
  );
}

function ClaimModal({ provider, onClose, onSaved }: { provider: Provider; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [product, setProduct] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  async function submit() {
    setBusy(true); setErr(""); setOk("");
    try {
      const res = await fetch(`${API_URL}/marketplace/${provider.id}/claim`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claimant_name: name, claimant_phone: phone, claimant_email: email || undefined, subscription_product: product || undefined, notes: notes || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not submit claim");
      setOk(data.message);
      setTimeout(onSaved, 1800);
    } catch (e) { setErr(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }

  return (
    <Modal title={`Claim ${provider.company_name}`} onClose={onClose}>
      <p className="mb-4 text-sm text-roadcall-silver/85">
        To prevent competitive or malicious edits, only the verified business owner can edit this listing.
        We'll auto-approve if your phone matches the listing or your active Roadcall subscription.
      </p>
      <div className="space-y-3">
        <Field label="Your full name"><input value={name} onChange={(e) => setName(e.target.value)} className={INPUT_CLS} /></Field>
        <Field label="Your business phone"><input value={phone} onChange={(e) => setPhone(e.target.value)} className={INPUT_CLS} placeholder="(555) 555-1234" /></Field>
        <Field label="Email (optional)"><input value={email} onChange={(e) => setEmail(e.target.value)} className={INPUT_CLS} /></Field>
        <Field label="Roadcall subscription product">
          <select value={product} onChange={(e) => setProduct(e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel px-3 py-2 text-white outline-none focus:border-blue-300">
            <option value="">Not yet a subscriber</option>
            <option value="ai_telephony">AI Telephony</option>
            <option value="ai_voice_text">AI Voice + Text</option>
            <option value="social_media">Social Media Management</option>
            <option value="website_management">Website Management</option>
          </select>
        </Field>
        <Field label="Notes (optional)"><textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className={INPUT_CLS} /></Field>
        {err && <p className="text-sm text-red-300">{err}</p>}
        {ok && <p className="text-sm text-emerald-300">{ok}</p>}
        <button disabled={busy || !name || !phone} onClick={submit} className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-4 py-3 font-semibold text-white hover:brightness-110 disabled:opacity-60">
          <ShieldCheck className="h-4 w-4" /> Submit claim
        </button>
      </div>
    </Modal>
  );
}

function SubmitModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    company_name: "", contact_name: "", phone: "", email: "", website: "",
    address: "", city: "", state: "",
    emergency_service: false, accepts_mobile_roadside: true, service_radius_miles: 50,
  });
  const [services, setServices] = useState("");
  const [vehicles, setVehicles] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  function update<K extends keyof typeof form>(k: K, v: (typeof form)[K]) { setForm((f) => ({ ...f, [k]: v })); }

  async function submit() {
    setBusy(true); setErr(""); setOk("");
    try {
      const res = await fetch(`${API_URL}/marketplace/submit`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          email: form.email || undefined,
          website: form.website || undefined,
          service_types: services.split(",").map((s) => s.trim()).filter(Boolean),
          vehicle_types_supported: vehicles.split(",").map((s) => s.trim()).filter(Boolean),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.[0]?.msg || data.detail || "Could not submit");
      setOk(data.message);
      setTimeout(onSaved, 1800);
    } catch (e) { setErr(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }

  return (
    <Modal title="Add your business" onClose={onClose}>
      <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
        <Field label="Business name *"><input value={form.company_name} onChange={(e) => update("company_name", e.target.value)} className={INPUT_CLS} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Contact name *"><input value={form.contact_name} onChange={(e) => update("contact_name", e.target.value)} className={INPUT_CLS} /></Field>
          <Field label="Phone *"><input value={form.phone} onChange={(e) => update("phone", e.target.value)} className={INPUT_CLS} /></Field>
          <Field label="Email"><input value={form.email} onChange={(e) => update("email", e.target.value)} className={INPUT_CLS} /></Field>
          <Field label="Website"><input value={form.website} onChange={(e) => update("website", e.target.value)} className={INPUT_CLS} /></Field>
          <Field label="City"><input value={form.city} onChange={(e) => update("city", e.target.value)} className={INPUT_CLS} /></Field>
          <Field label="State (2 letters)"><input value={form.state} onChange={(e) => update("state", e.target.value.toUpperCase().slice(0,2))} className={INPUT_CLS} /></Field>
        </div>
        <Field label="Address"><input value={form.address} onChange={(e) => update("address", e.target.value)} className={INPUT_CLS} /></Field>
        <Field label="Services (comma-separated, e.g. tow_needed, flat_tire, lockout)"><input value={services} onChange={(e) => setServices(e.target.value)} className={INPUT_CLS} /></Field>
        <Field label="Vehicle types (comma-separated, e.g. car, truck, heavy_duty)"><input value={vehicles} onChange={(e) => setVehicles(e.target.value)} className={INPUT_CLS} /></Field>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="flex items-center gap-2 text-sm text-roadcall-silver"><input type="checkbox" checked={form.accepts_mobile_roadside} onChange={(e) => update("accepts_mobile_roadside", e.target.checked)} /> Mobile roadside</label>
          <label className="flex items-center gap-2 text-sm text-roadcall-silver"><input type="checkbox" checked={form.emergency_service} onChange={(e) => update("emergency_service", e.target.checked)} /> 24/7 emergency</label>
          <Field label="Service radius (mi)"><input type="number" value={form.service_radius_miles} onChange={(e) => update("service_radius_miles", Number(e.target.value) || 50)} className={INPUT_CLS} /></Field>
        </div>
        {err && <p className="text-sm text-red-300">{err}</p>}
        {ok && <p className="text-sm text-emerald-300">{ok}</p>}
        <button disabled={busy || !form.company_name || !form.contact_name || !form.phone} onClick={submit} className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-4 py-3 font-semibold text-white hover:brightness-110 disabled:opacity-60">
          <Plus className="h-4 w-4" /> Submit listing
        </button>
        <p className="text-xs text-roadcall-muted">Your listing will be reviewed by our team before going live. To edit it later, use the &ldquo;Claim listing&rdquo; option.</p>
      </div>
    </Modal>
  );
}

function ScorePill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-roadcall-ink/70 px-2 py-2">
      <p className="font-bold text-white">{Math.round(value * 100)}%</p>
      <p className="text-roadcall-muted/70">{label}</p>
    </div>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-roadcall-muted">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/60 px-3 py-2 text-white outline-none placeholder:text-roadcall-muted/70 focus:border-blue-300"
      />
    </label>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-roadcall-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel px-3 py-2 text-white outline-none focus:border-blue-300"
      >
        {options.map(([id, labelText]) => <option key={id} value={id}>{labelText}</option>)}
      </select>
    </label>
  );
}
