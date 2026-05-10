"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Mail,
  MapPin,
  Phone,
  RefreshCw,
  Search,
  Wrench,
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
  total_with_phone: number;
  total_with_email: number;
  total_with_website: number;
  roadside_mechanics: number;
  sources: Record<string, number>;
  top_states: { state: string; count: number }[];
}

interface MechanicRecord {
  id: string;
  company_name: string;
  contact_name: string;
  phone: string;
  email: string | null;
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

const PAGE_SIZE = 50;

function StatCard({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: number;
  sublabel?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <p className="mt-1 text-3xl font-bold">{value.toLocaleString()}</p>
        {sublabel && <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>}
      </CardContent>
    </Card>
  );
}

function cleanUrl(url: string) {
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `https://${url}`;
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

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        adminFetch<MechanicStats>("/mechanics/admin/stats"),
        adminFetch<MechanicListResponse>(`/mechanics/admin/list?${queryString}`),
      ]);
      setStats(statsData);
      setRecords(listData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load mechanics");
    } finally {
      setLoading(false);
    }
  }, [queryString]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      loadData();
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [loadData]);

  const total = records?.total || 0;
  const showingStart = total === 0 ? 0 : offset + 1;
  const showingEnd = Math.min(offset + PAGE_SIZE, total);

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Wrench className="h-6 w-6 text-blue-600" />
            Mechanic Database
          </h1>
          <p className="text-muted-foreground">
            View truck mechanics, towing providers, mobile repair shops, and enrichment coverage.
          </p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading} className="gap-2">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Total Records" value={stats.total_mechanics} sublabel={`${stats.active_mechanics.toLocaleString()} active`} />
          <StatCard label="With Phone" value={stats.total_with_phone} sublabel="Dispatch-ready contacts" />
          <StatCard label="With Email" value={stats.total_with_email} sublabel={`${stats.total_mechanics ? Math.round((stats.total_with_email / stats.total_mechanics) * 100) : 0}% coverage`} />
          <StatCard label="With Website" value={stats.total_with_website} sublabel="Enrichment targets" />
          <StatCard label="Roadside/Mobile" value={stats.roadside_mechanics} sublabel="Accepts mobile service" />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Search & Filters</CardTitle>
          <CardDescription>
            Filter by business name, phone, email, website, city, state, and enrichment fields.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[2fr_1fr_110px_160px_140px_140px_150px_130px_auto]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setOffset(0);
                }}
                placeholder="Search name, phone, email, website..."
                className="pl-9"
              />
            </div>
            <Input
              value={city}
              onChange={(event) => {
                setCity(event.target.value);
                setOffset(0);
              }}
              placeholder="City"
            />
            <Input
              value={state}
              onChange={(event) => {
                setState(event.target.value.slice(0, 2).toUpperCase());
                setOffset(0);
              }}
              placeholder="State"
              maxLength={2}
            />
            <Input
              value={serviceType}
              onChange={(event) => {
                setServiceType(event.target.value);
                setOffset(0);
              }}
              placeholder="Service e.g. flat_tire"
            />
            <select
              value={hasEmail}
              onChange={(event) => {
                setHasEmail(event.target.value);
                setOffset(0);
              }}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="any">Any email</option>
              <option value="yes">Has email</option>
              <option value="no">No email</option>
            </select>
            <select
              value={hasWebsite}
              onChange={(event) => {
                setHasWebsite(event.target.value);
                setOffset(0);
              }}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="any">Any website</option>
              <option value="yes">Has website</option>
              <option value="no">No website</option>
            </select>
            <label className="flex h-10 items-center gap-2 rounded-md border border-input px-3 text-sm">
              <input
                type="checkbox"
                checked={roadsideOnly}
                onChange={(event) => {
                  setRoadsideOnly(event.target.checked);
                  setOffset(0);
                }}
              />
              Roadside only
            </label>
            <label className="flex h-10 items-center gap-2 rounded-md border border-input px-3 text-sm">
              <input
                type="checkbox"
                checked={emergencyOnly}
                onChange={(event) => {
                  setEmergencyOnly(event.target.checked);
                  setOffset(0);
                }}
              />
              24/7 only
            </label>
            <Button variant="ghost" onClick={resetFilters}>Reset</Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle>Mechanics</CardTitle>
            <CardDescription>
              Showing {showingStart.toLocaleString()}–{showingEnd.toLocaleString()} of {total.toLocaleString()} records.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="h-20 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : !records || records.items.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <Wrench className="mx-auto mb-3 h-10 w-10" />
              <p>No mechanics match these filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1080px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
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
                  {records.items.map((mechanic) => (
                    <tr key={mechanic.id} className="border-b align-top last:border-0">
                      <td className="py-4 pr-4">
                        <div className="font-semibold text-slate-900">{mechanic.company_name}</div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {mechanic.accepts_mobile_roadside && <Badge variant="secondary">Roadside</Badge>}
                          {mechanic.emergency_service && <Badge variant="secondary">24/7</Badge>}
                          {!mechanic.active && <Badge variant="destructive">Inactive</Badge>}
                          {mechanic.lead_status && <Badge variant="outline">{mechanic.lead_status.replaceAll("_", " ")}</Badge>}
                        </div>
                      </td>
                      <td className="space-y-2 py-4 pr-4">
                        <a href={`tel:${mechanic.phone}`} className="flex items-center gap-2 text-blue-700 hover:underline">
                          <Phone className="h-3.5 w-3.5" /> {mechanic.phone}
                        </a>
                        {mechanic.email ? (
                          <a href={`mailto:${mechanic.email}`} className="flex items-center gap-2 text-blue-700 hover:underline">
                            <Mail className="h-3.5 w-3.5" /> {mechanic.email}
                          </a>
                        ) : (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Mail className="h-3.5 w-3.5" /> No email
                          </div>
                        )}
                        {mechanic.website && (
                          <a
                            href={cleanUrl(mechanic.website)}
                            target="_blank"
                            rel="noreferrer"
                            className="flex max-w-xs items-center gap-2 truncate text-blue-700 hover:underline"
                          >
                            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                            <span className="truncate">{mechanic.website}</span>
                          </a>
                        )}
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex items-start gap-2">
                          <MapPin className="mt-0.5 h-3.5 w-3.5 text-muted-foreground" />
                          <div>
                            <div>{[mechanic.city, mechanic.state].filter(Boolean).join(", ") || "Unknown"}</div>
                            {mechanic.address && <div className="mt-1 max-w-xs text-xs text-muted-foreground">{mechanic.address}</div>}
                          </div>
                        </div>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex max-w-xs flex-wrap gap-1">
                          {[...mechanic.vehicle_types_supported, ...mechanic.service_types].slice(0, 5).map((item) => (
                            <Badge key={item} variant="outline">{item.replaceAll("_", " ")}</Badge>
                          ))}
                        </div>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="font-medium">Radius: {mechanic.service_radius_miles} mi</div>
                        <div className="text-xs text-muted-foreground">Priority: {mechanic.priority_score}/100</div>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="font-medium">{mechanic.rating ? `${mechanic.rating.toFixed(1)} ★` : "No rating"}</div>
                        <div className="text-xs text-muted-foreground">
                          {mechanic.review_count ? `${mechanic.review_count.toLocaleString()} reviews` : "No review count"}
                        </div>
                        {mechanic.source_confidence !== null && (
                          <div className="mt-1 text-xs text-muted-foreground">
                            {Math.round(mechanic.source_confidence * 100)}% confidence
                          </div>
                        )}
                      </td>
                      <td className="py-4 pr-4">
                        <div>{mechanic.source || "unknown"}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          Enriched {mechanic.last_enriched_at ? new Date(mechanic.last_enriched_at).toLocaleDateString() : "never"}
                        </div>
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
