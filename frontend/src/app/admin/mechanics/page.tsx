"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  ExternalLink,
  Mail,
  MapPin,
  Phone,
  PlayCircle,
  RefreshCw,
  Search,
  Sparkles,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { adminFetch } from "@/lib/admin-auth";

interface MechanicStats {
  total_mechanics: number;
  active_mechanics: number;
  state_count: number;
  total_with_phone: number;
  total_with_email: number;
  total_with_website: number;
  roadside_mechanics: number;
  last_updated_at: string | null;
  sources: Record<string, number>;
  top_states: { state: string; count: number }[];
}

interface MechanicRecord {
  id: string;
  company_name: string;
  contact_name: string;
  phone: string;
  email: string | null;
  email_quality: string | null;
  website: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  service_types: string[];
  vehicle_types_supported: string[];
  active: boolean;
  accepts_mobile_roadside: boolean;
  emergency_service: boolean;
  service_radius_miles: number;
  priority_score: number;
  rating: number | null;
  review_count: number | null;
  source: string | null;
  source_confidence: number | null;
  lead_status: string | null;
  last_enriched_at: string | null;
  created_at: string;
}

interface MechanicListResponse {
  total: number;
  limit: number;
  offset: number;
  items: MechanicRecord[];
}

interface CityMechanicGroup {
  city: string;
  items: MechanicRecord[];
}

interface StateMechanicGroup {
  state: string;
  count: number;
  cities: CityMechanicGroup[];
}

interface EnrichmentStatus {
  kind: "emails" | "email_sync" | "mechanics";
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  log_tail: string[];
  enriched_total: number;
  pending_total: number;
}

interface AdminReviewQueues {
  pending_claims: {
    id: string;
    listing_id: string;
    company_name: string;
    claimant_name: string;
    claimant_email: string | null;
    claimant_phone: string;
    method: string;
    notes: string | null;
    created_at: string;
  }[];
  pending_updates: {
    id: string;
    listing_id: string;
    company_name: string;
    requester_name: string;
    requester_email: string;
    requester_role: string;
    match_score: number | null;
    email_domain_matches_website: boolean | null;
    requested_changes: Record<string, unknown>;
    proof_message: string | null;
    created_at: string;
  }[];
  data_quality: {
    missing_websites: number;
    missing_phone_numbers: number;
    pending_public_submissions: number;
    low_confidence_addresses: number;
  };
}

const PAGE_SIZE = 200;
const STATS_REFRESH_MS = 30_000;

function ProgressBar({ value, max, accent = "bg-blue-500" }: { value: number; max: number; accent?: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-800/60">
      <div className={`h-full ${accent} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function HeroStat({
  label,
  value,
  sub,
  accent,
  progressOf,
}: {
  label: string;
  value: number;
  sub?: string;
  accent: string;
  progressOf?: number;
}) {
  return (
    <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-slate-900/80 to-slate-950 p-5 shadow-lg">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold text-white">{value.toLocaleString()}</p>
        </div>
        <div className={`h-9 w-9 rounded-full ${accent} bg-opacity-20 flex items-center justify-center`}>
          <Sparkles className="h-4 w-4 text-white/70" />
        </div>
      </div>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
      {progressOf !== undefined && progressOf > 0 && <ProgressBar value={value} max={progressOf} accent={accent} />}
    </div>
  );
}

function cleanUrl(url: string) {
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `https://${url}`;
}

function emailQualityLabel(kind: string | null) {
  switch (kind) {
    case "domain_match":
      return { text: "Domain match", cls: "bg-emerald-500/15 text-emerald-300" };
    case "domain_role":
      return { text: "Domain role", cls: "bg-cyan-500/15 text-cyan-300" };
    case "role_based":
      return { text: "Role-based", cls: "bg-blue-500/15 text-blue-300" };
    case "noreply":
      return { text: "No-reply", cls: "bg-amber-500/15 text-amber-300" };
    case "unmatched":
      return { text: "Unmatched", cls: "bg-slate-500/20 text-slate-300" };
    default:
      return null;
  }
}

function exportCsv(records: MechanicRecord[]) {
  const headers = [
    "company_name","phone","email","website","city","state","address",
    "accepts_mobile_roadside","emergency_service","service_radius_miles","priority_score",
    "rating","review_count","source","last_enriched_at",
  ];
  const escape = (v: unknown) => {
    if (v === null || v === undefined) return "";
    const s = String(v).replaceAll('"', '""');
    return /[",\n]/.test(s) ? `"${s}"` : s;
  };
  const rows = records.map((r) => headers.map((h) => escape((r as unknown as Record<string, unknown>)[h])).join(","));
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mechanics-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AdminMechanicsPage() {
  const [stats, setStats] = useState<MechanicStats | null>(null);
  const [records, setRecords] = useState<MechanicListResponse | null>(null);
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [hasEmail, setHasEmail] = useState("any");
  const [hasWebsite, setHasWebsite] = useState("any");
  const [serviceType, setServiceType] = useState("");
  const [emergencyOnly, setEmergencyOnly] = useState(false);
  const [roadsideOnly, setRoadsideOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enrichOpen, setEnrichOpen] = useState(false);
  const [enrichStatus, setEnrichStatus] = useState<EnrichmentStatus | null>(null);
  const [enrichStatusKind, setEnrichStatusKind] = useState<EnrichmentStatus["kind"]>("emails");
  const [enrichBusy, setEnrichBusy] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState<Date | null>(null);
  const [reviewQueues, setReviewQueues] = useState<AdminReviewQueues | null>(null);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);

  const queryString = useMemo(() => {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (search.trim()) params.set("q", search.trim());
    if (city.trim()) params.set("city", city.trim());
    if (state.trim()) params.set("state", state.trim().toUpperCase());
    if (serviceType.trim()) params.set("service_type", serviceType.trim());
    if (hasEmail !== "any") params.set("has_email", String(hasEmail === "yes"));
    if (hasWebsite !== "any") params.set("has_website", String(hasWebsite === "yes"));
    if (emergencyOnly) params.set("emergency_only", "true");
    if (roadsideOnly) params.set("roadside_only", "true");
    return params.toString();
  }, [city, emergencyOnly, hasEmail, hasWebsite, offset, roadsideOnly, search, serviceType, state]);

  const loadData = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    setError(null);
    try {
      const [statsData, listData, reviewQueueData] = await Promise.all([
        adminFetch<MechanicStats>("/mechanics/admin/stats"),
        adminFetch<MechanicListResponse>(`/mechanics/admin/list?${queryString}`),
        adminFetch<AdminReviewQueues>("/marketplace/admin/review-queues"),
      ]);
      setStats(statsData);
      setRecords(listData);
      setReviewQueues(reviewQueueData);
      setLastLoadedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load mechanics");
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, [queryString]);

  useEffect(() => {
    const timeout = window.setTimeout(loadData, 250);
    return () => window.clearTimeout(timeout);
  }, [loadData]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadData({ silent: true });
    }, STATS_REFRESH_MS);

    const refreshOnFocus = () => loadData({ silent: true });
    window.addEventListener("focus", refreshOnFocus);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", refreshOnFocus);
    };
  }, [loadData]);

  useEffect(() => {
    if (!enrichOpen) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const s = await adminFetch<EnrichmentStatus>(`/admin/enrichment/status?kind=${enrichStatusKind}`);
        if (!cancelled) setEnrichStatus(s);
      } catch {
        /* ignore */
      }
    };
    poll();
    const id = window.setInterval(poll, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [enrichOpen, enrichStatusKind]);

  async function startEnrichment() {
    setEnrichStatusKind("emails");
    setEnrichBusy(true);
    try {
      const s = await adminFetch<EnrichmentStatus>("/admin/enrichment/start", {
        method: "POST",
        body: JSON.stringify({ kind: "emails", limit: 200, batch: 20, dry_run: false }),
      });
      setEnrichStatus(s);
      loadData({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start enrichment");
    } finally {
      setEnrichBusy(false);
    }
  }

  async function syncApifyDatasets() {
    setEnrichStatusKind("email_sync");
    setEnrichBusy(true);
    try {
      const s = await adminFetch<EnrichmentStatus>("/admin/enrichment/start", {
        method: "POST",
        body: JSON.stringify({ kind: "email_sync", runs: 100, dry_run: false }),
      });
      setEnrichStatus(s);
      loadData({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sync Apify email datasets");
    } finally {
      setEnrichBusy(false);
    }
  }

  async function reviewClaim(claimId: string, status: "approved" | "rejected") {
    setReviewBusy(`claim:${claimId}`);
    try {
      await adminFetch(`/marketplace/admin/claims/${claimId}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await loadData({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to review claim");
    } finally {
      setReviewBusy(null);
    }
  }

  async function reviewUpdateRequest(requestId: string, status: "approved" | "rejected" | "more_info_requested") {
    setReviewBusy(`update:${requestId}`);
    try {
      await adminFetch(`/marketplace/admin/update-requests/${requestId}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await loadData({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to review listing update");
    } finally {
      setReviewBusy(null);
    }
  }

  async function markProviderVerified(mechanicId: string) {
    setReviewBusy(`verify:${mechanicId}`);
    try {
      await adminFetch(`/marketplace/admin/${mechanicId}/verify`, {
        method: "POST",
        body: JSON.stringify({ verification_status: "verified" }),
      });
      await loadData({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to verify provider");
    } finally {
      setReviewBusy(null);
    }
  }

  const total = records?.total || 0;
  const showingStart = total === 0 ? 0 : offset + 1;
  const showingEnd = Math.min(offset + PAGE_SIZE, total);

  const groupedRecords = useMemo<StateMechanicGroup[]>(() => {
    const stateGroups = new Map<string, Map<string, MechanicRecord[]>>();
    for (const mechanic of records?.items || []) {
      const stateKey = mechanic.state || "Unknown";
      const cityKey = mechanic.city || "Unknown";
      if (!stateGroups.has(stateKey)) stateGroups.set(stateKey, new Map());
      const cityGroups = stateGroups.get(stateKey)!;
      if (!cityGroups.has(cityKey)) cityGroups.set(cityKey, []);
      cityGroups.get(cityKey)!.push(mechanic);
    }
    return Array.from(stateGroups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([stateName, cityGroups]) => ({
        state: stateName,
        count: Array.from(cityGroups.values()).reduce((s, c) => s + c.length, 0),
        cities: Array.from(cityGroups.entries())
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([cityName, items]) => ({ city: cityName, items })),
      }));
  }, [records]);

  function resetFilters() {
    setSearch("");
    setCity("");
    setState("");
    setServiceType("");
    setHasEmail("any");
    setHasWebsite("any");
    setEmergencyOnly(false);
    setRoadsideOnly(false);
    setOffset(0);
  }

  const emailCoverage = stats?.total_mechanics ? Math.round((stats.total_with_email / stats.total_mechanics) * 100) : 0;
  const websiteCoverage = stats?.total_mechanics ? Math.round((stats.total_with_website / stats.total_mechanics) * 100) : 0;
  const statsUpdatedAt = stats?.last_updated_at ? new Date(stats.last_updated_at) : lastLoadedAt;

  return (
    <div className="space-y-6">
      {/* Hero header */}
      <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-blue-950/50 via-slate-950 to-slate-950 p-6 shadow-2xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="flex items-center gap-3 text-2xl font-bold text-white">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/20 text-blue-400">
                <Database className="h-5 w-5" />
              </span>
              Mechanic Database
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              {stats ? `${stats.total_mechanics.toLocaleString()} records across ${stats.state_count.toLocaleString()} states.` : "Loading dispatch network..."}
              {" "}Map listing records power dispatch; website-crawler enrichment fills email data.
            </p>
            {statsUpdatedAt && (
              <p className="mt-1 text-xs text-slate-500">
                Auto-refreshes every {Math.round(STATS_REFRESH_MS / 1000)}s · last synced {statsUpdatedAt.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => loadData()} disabled={loading} className="gap-2">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={() => exportCsv(records?.items || [])} disabled={!records?.items.length} className="gap-2">
              <Download className="h-4 w-4" /> Export CSV
            </Button>
            <Button size="sm" onClick={() => setEnrichOpen(true)} className="gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110">
              <Sparkles className="h-4 w-4" /> Email enrichment
            </Button>
          </div>
        </div>

        {stats && (
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            <HeroStat label="Total Records" value={stats.total_mechanics} sub={`${stats.active_mechanics.toLocaleString()} active`} accent="bg-cyan-500" />
            <HeroStat label="With Phone" value={stats.total_with_phone} sub="Dispatch-ready" accent="bg-emerald-500" progressOf={stats.total_mechanics} />
            <HeroStat label="With Email" value={stats.total_with_email} sub={`${emailCoverage}% coverage`} accent="bg-blue-500" progressOf={stats.total_mechanics} />
            <HeroStat label="With Website" value={stats.total_with_website} sub={`${websiteCoverage}% enrichable`} accent="bg-purple-500" progressOf={stats.total_mechanics} />
            <HeroStat label="Roadside / Mobile" value={stats.roadside_mechanics} sub="Accepts mobile service" accent="bg-orange-500" progressOf={stats.total_mechanics} />
          </div>
        )}

        {stats && stats.top_states.length > 0 && (
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="text-xs uppercase tracking-wider text-slate-500">Top states</span>
            {stats.top_states.slice(0, 8).map((s) => (
              <button
                key={s.state}
                onClick={() => { setState(s.state); setOffset(0); }}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-200 hover:border-blue-400/40 hover:bg-blue-500/10"
              >
                {s.state} <span className="text-slate-500">({s.count.toLocaleString()})</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {reviewQueues && (
        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <Card className="border-white/5 bg-slate-950/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <AlertTriangle className="h-4 w-4 text-amber-300" /> Data Quality
              </CardTitle>
              <CardDescription>Provider records that need enrichment or review before they become fully platform-ready.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["Missing websites", reviewQueues.data_quality.missing_websites],
                  ["Missing phones", reviewQueues.data_quality.missing_phone_numbers],
                  ["Public submissions", reviewQueues.data_quality.pending_public_submissions],
                  ["Low-confidence addresses", reviewQueues.data_quality.low_confidence_addresses],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-xl border border-white/5 bg-white/[0.03] p-3">
                    <p className="text-xs text-slate-500">{label}</p>
                    <p className="mt-1 text-2xl font-bold text-white">{Number(value).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/5 bg-slate-950/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CheckCircle2 className="h-4 w-4 text-emerald-300" /> Claim & Update Review Queue
              </CardTitle>
              <CardDescription>Approve ownership claims and pending listing updates. Public data only changes after admin approval.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Pending claims</h3>
                  <Badge variant="outline">{reviewQueues.pending_claims.length}</Badge>
                </div>
                {reviewQueues.pending_claims.length === 0 ? (
                  <p className="rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm text-slate-500">No pending claim requests.</p>
                ) : (
                  <div className="space-y-2">
                    {reviewQueues.pending_claims.slice(0, 4).map((claim) => (
                      <div key={claim.id} className="rounded-xl border border-white/5 bg-white/[0.03] p-3">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div>
                            <p className="font-semibold text-white">{claim.company_name}</p>
                            <p className="mt-1 text-xs text-slate-400">{claim.claimant_name} · {claim.claimant_email || "no email"} · {claim.claimant_phone}</p>
                            {claim.notes && <p className="mt-2 text-xs text-slate-500">{claim.notes}</p>}
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            <Button size="sm" variant="outline" disabled={reviewBusy === `claim:${claim.id}`} onClick={() => reviewClaim(claim.id, "rejected")}>Reject</Button>
                            <Button size="sm" disabled={reviewBusy === `claim:${claim.id}`} onClick={() => reviewClaim(claim.id, "approved")}>Approve claim</Button>
                            <Button size="sm" variant="outline" disabled={reviewBusy === `verify:${claim.listing_id}`} onClick={() => markProviderVerified(claim.listing_id)}>Mark verified</Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Pending listing updates</h3>
                  <Badge variant="outline">{reviewQueues.pending_updates.length}</Badge>
                </div>
                {reviewQueues.pending_updates.length === 0 ? (
                  <p className="rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm text-slate-500">No pending listing updates.</p>
                ) : (
                  <div className="space-y-2">
                    {reviewQueues.pending_updates.slice(0, 4).map((update) => (
                      <div key={update.id} className="rounded-xl border border-white/5 bg-white/[0.03] p-3">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div>
                            <p className="font-semibold text-white">{update.company_name}</p>
                            <p className="mt-1 text-xs text-slate-400">{update.requester_name} · {update.requester_role.replaceAll("_", " ")} · {update.requester_email}</p>
                            <div className="mt-2 flex flex-wrap gap-2 text-xs">
                              <Badge variant="outline">Name match {update.match_score === null ? "n/a" : `${Math.round(update.match_score * 100)}%`}</Badge>
                              <Badge variant="outline">Domain {update.email_domain_matches_website === null ? "unknown" : update.email_domain_matches_website ? "matched" : "mismatch"}</Badge>
                            </div>
                            <pre className="mt-2 max-h-24 overflow-auto rounded-lg bg-slate-950/80 p-2 text-xs text-slate-300">{JSON.stringify(update.requested_changes, null, 2)}</pre>
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            <Button size="sm" variant="outline" disabled={reviewBusy === `update:${update.id}`} onClick={() => reviewUpdateRequest(update.id, "rejected")}>Reject</Button>
                            <Button size="sm" variant="outline" disabled={reviewBusy === `update:${update.id}`} onClick={() => reviewUpdateRequest(update.id, "more_info_requested")}>Request info</Button>
                            <Button size="sm" disabled={reviewBusy === `update:${update.id}`} onClick={() => reviewUpdateRequest(update.id, "approved")}>Approve update</Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card className="border-white/5 bg-slate-950/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Search & Filters</CardTitle>
          <CardDescription>
            Filter by name, phone, email, website, city/state, service type, or enrichment status.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[2fr_1fr_110px_180px_140px_140px_150px_130px_auto]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={search} onChange={(e) => { setSearch(e.target.value); setOffset(0); }} placeholder="Search name, phone, email, website..." className="pl-9" />
            </div>
            <Input value={city} onChange={(e) => { setCity(e.target.value); setOffset(0); }} placeholder="City" />
            <Input value={state} onChange={(e) => { setState(e.target.value.slice(0, 2).toUpperCase()); setOffset(0); }} placeholder="State" maxLength={2} />
            <Input value={serviceType} onChange={(e) => { setServiceType(e.target.value); setOffset(0); }} placeholder="Service e.g. flat_tire" />
            <select value={hasEmail} onChange={(e) => { setHasEmail(e.target.value); setOffset(0); }} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              <option value="any">Any email</option>
              <option value="yes">Has email</option>
              <option value="no">No email</option>
            </select>
            <select value={hasWebsite} onChange={(e) => { setHasWebsite(e.target.value); setOffset(0); }} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              <option value="any">Any website</option>
              <option value="yes">Has website</option>
              <option value="no">No website</option>
            </select>
            <label className="flex h-10 items-center gap-2 rounded-md border border-input px-3 text-sm">
              <input type="checkbox" checked={roadsideOnly} onChange={(e) => { setRoadsideOnly(e.target.checked); setOffset(0); }} />
              Roadside
            </label>
            <label className="flex h-10 items-center gap-2 rounded-md border border-input px-3 text-sm">
              <input type="checkbox" checked={emergencyOnly} onChange={(e) => { setEmergencyOnly(e.target.checked); setOffset(0); }} />
              24/7 only
            </label>
            <Button variant="ghost" onClick={resetFilters}>Reset</Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-200">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div className="flex-1">
            <div className="font-semibold text-red-100">Couldn&apos;t load mechanic data</div>
            <div className="mt-1 text-red-200/80">{error}</div>
            <div className="mt-2 text-xs text-red-200/60">
              If this is a 401, your admin session may have expired —{" "}
              <a href="/admin/login" className="underline">log in again</a>.
            </div>
          </div>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Results */}
      <Card className="border-white/5 bg-slate-950/60">
        <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle className="text-base">Mechanics</CardTitle>
            <CardDescription>
              Showing <span className="font-medium text-slate-300">{showingStart.toLocaleString()}–{showingEnd.toLocaleString()}</span> of <span className="font-medium text-slate-300">{total.toLocaleString()}</span> records, grouped by state and city.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              <ChevronLeft className="mr-1 h-4 w-4" /> Previous
            </Button>
            <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total || loading} onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-lg bg-slate-900/60" />
              ))}
            </div>
          ) : !records || records.items.length === 0 ? (
            <div className="py-16 text-center text-muted-foreground">
              <Wrench className="mx-auto mb-3 h-10 w-10 opacity-40" />
              <p className="text-base font-medium text-slate-300">No mechanics match these filters.</p>
              <p className="mt-1 text-sm">Try clearing filters or expanding your search.</p>
              <Button variant="outline" className="mt-4" onClick={resetFilters}>Reset filters</Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1080px] text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-slate-500">
                    <th className="py-3 pr-4 font-medium">Business</th>
                    <th className="py-3 pr-4 font-medium">Contact</th>
                    <th className="py-3 pr-4 font-medium">Location</th>
                    <th className="py-3 pr-4 font-medium">Specialties</th>
                    <th className="py-3 pr-4 font-medium">Dispatch Fit</th>
                    <th className="py-3 pr-4 font-medium">Quality</th>
                    <th className="py-3 pr-4 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {groupedRecords.map((stateGroup) => (
                    <Fragment key={stateGroup.state}>
                      <tr className="border-y border-white/5 bg-gradient-to-r from-blue-950/40 to-transparent">
                        <td colSpan={7} className="py-3 pr-4">
                          <div className="flex items-center gap-2 text-white">
                            <MapPin className="h-4 w-4 text-orange-400" />
                            <span className="font-semibold">{stateGroup.state}</span>
                            <Badge variant="outline" className="border-blue-400/40 text-blue-200">{stateGroup.count} records</Badge>
                          </div>
                        </td>
                      </tr>
                      {stateGroup.cities.map((cityGroup) => (
                        <Fragment key={`${stateGroup.state}-${cityGroup.city}`}>
                          <tr className="border-b border-white/5 bg-slate-900/30">
                            <td colSpan={7} className="py-2 pr-4 text-sm text-slate-200">
                              <span className="font-medium">{cityGroup.city}</span>
                              <span className="ml-2 text-xs text-slate-500">{cityGroup.items.length} mechanic{cityGroup.items.length === 1 ? "" : "s"}</span>
                            </td>
                          </tr>
                          {cityGroup.items.map((m) => (
                            <tr key={m.id} className="border-b border-white/5 align-top hover:bg-white/[0.02]">
                              <td className="py-4 pr-4">
                                <div className="font-semibold text-white">{m.company_name}</div>
                                <div className="mt-2 flex flex-wrap gap-1">
                                  {m.accepts_mobile_roadside && <Badge variant="secondary" className="bg-orange-500/15 text-orange-300">Roadside</Badge>}
                                  {m.emergency_service && <Badge variant="secondary" className="bg-red-500/15 text-red-300">24/7</Badge>}
                                  {!m.active && <Badge variant="destructive">Inactive</Badge>}
                                  {m.lead_status && <Badge variant="outline">{m.lead_status.replaceAll("_", " ")}</Badge>}
                                </div>
                              </td>
                              <td className="space-y-2 py-4 pr-4">
                                <a href={`tel:${m.phone}`} className="flex items-center gap-2 text-blue-300 hover:underline">
                                  <Phone className="h-3.5 w-3.5" /> {m.phone}
                                </a>
                                {m.email ? (
                                  <div>
                                    <a href={`mailto:${m.email}`} className="flex items-center gap-2 text-blue-300 hover:underline">
                                      <Mail className="h-3.5 w-3.5" /> {m.email}
                                    </a>
                                    {emailQualityLabel(m.email_quality) && (
                                      <Badge className={`mt-1 ${emailQualityLabel(m.email_quality)?.cls}`}>
                                        {emailQualityLabel(m.email_quality)?.text}
                                      </Badge>
                                    )}
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2 text-slate-600">
                                    <Mail className="h-3.5 w-3.5" /> No email
                                  </div>
                                )}
                                {m.website && (
                                  <a href={cleanUrl(m.website)} target="_blank" rel="noreferrer" className="flex max-w-xs items-center gap-2 truncate text-blue-300 hover:underline">
                                    <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                                    <span className="truncate">{m.website}</span>
                                  </a>
                                )}
                              </td>
                              <td className="py-4 pr-4">
                                <div className="flex items-start gap-2 text-slate-200">
                                  <MapPin className="mt-0.5 h-3.5 w-3.5 text-slate-500" />
                                  <div>
                                    <div>{[m.city, m.state].filter(Boolean).join(", ") || "Unknown"}</div>
                                    {m.address && <div className="mt-1 max-w-xs text-xs text-slate-500">{m.address}</div>}
                                  </div>
                                </div>
                              </td>
                              <td className="py-4 pr-4">
                                <div className="flex max-w-xs flex-wrap gap-1">
                                  {[...m.vehicle_types_supported, ...m.service_types].slice(0, 5).map((item) => (
                                    <Badge key={item} variant="outline" className="border-white/10 text-slate-300">{item.replaceAll("_", " ")}</Badge>
                                  ))}
                                </div>
                              </td>
                              <td className="py-4 pr-4 text-slate-200">
                                <div className="font-medium">Radius: <span className="text-white">{m.service_radius_miles} mi</span></div>
                                <div className="mt-1 text-xs text-slate-500">Priority: {m.priority_score}/100</div>
                              </td>
                              <td className="py-4 pr-4 text-slate-200">
                                <div className="font-medium">{m.rating ? `${m.rating.toFixed(1)} ★` : "—"}</div>
                                <div className="text-xs text-slate-500">{m.review_count ? `${m.review_count.toLocaleString()} reviews` : "no reviews"}</div>
                                {m.source_confidence !== null && (
                                  <div className="mt-1 text-xs text-slate-500">{Math.round(m.source_confidence * 100)}% confidence</div>
                                )}
                              </td>
                              <td className="py-4 pr-4 text-slate-300">
                                <div className="text-sm">{m.source || "unknown"}</div>
                                <div className="mt-1 text-xs text-slate-500">
                                  Enriched {m.last_enriched_at ? new Date(m.last_enriched_at).toLocaleDateString() : "never"}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </Fragment>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enrichment drawer */}
      {enrichOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm sm:items-center">
          <div className="w-full max-w-2xl rounded-t-2xl border border-white/10 bg-slate-950 shadow-2xl sm:rounded-2xl">
            <div className="flex items-center justify-between border-b border-white/5 p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/20 text-blue-400">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-white">Apify email enrichment</h2>
                  <p className="text-xs text-slate-400">Run website crawls or sync completed Apify crawler datasets into the dashboard email list.</p>
                </div>
              </div>
              <button onClick={() => setEnrichOpen(false)} className="rounded-md p-1 text-slate-400 hover:bg-white/5 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 p-5">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Enriched</div>
                  <div className="mt-1 text-2xl font-bold text-emerald-400">
                    {enrichStatus?.enriched_total.toLocaleString() ?? "—"}
                  </div>
                </div>
                <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Pending (has website, no email)</div>
                  <div className="mt-1 text-2xl font-bold text-amber-400">
                    {enrichStatus?.pending_total.toLocaleString() ?? "—"}
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-white/5 bg-black/50 p-3 font-mono text-xs">
                <div className="mb-2 flex items-center justify-between text-slate-400">
                  <span>Job log {enrichStatus?.kind ? `(${enrichStatus.kind})` : ""}</span>
                  <span className="flex items-center gap-1">
                    {enrichStatus?.running ? (
                      <><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /> running</>
                    ) : enrichStatus?.exit_code === 0 ? (
                      <><CheckCircle2 className="h-3 w-3 text-emerald-400" /> idle</>
                    ) : enrichStatus?.exit_code != null && enrichStatus.exit_code !== 0 ? (
                      <><AlertTriangle className="h-3 w-3 text-red-400" /> error ({enrichStatus.exit_code})</>
                    ) : (
                      <span className="text-slate-500">idle</span>
                    )}
                  </span>
                </div>
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-slate-300">
                  {enrichStatus?.log_tail?.length ? enrichStatus.log_tail.join("\n") : "No recent runs."}
                </pre>
              </div>

              <div className="flex items-center justify-end gap-2">
                <Button variant="outline" onClick={() => setEnrichOpen(false)}>Close</Button>
                <Button
                  variant="outline"
                  onClick={syncApifyDatasets}
                  disabled={enrichBusy || enrichStatus?.running}
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Sync Apify datasets
                </Button>
                <Button
                  onClick={startEnrichment}
                  disabled={enrichBusy || enrichStatus?.running}
                  className="gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110"
                >
                  <PlayCircle className="h-4 w-4" />
                  {enrichStatus?.running ? "Running..." : "Run website crawl (200)"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
