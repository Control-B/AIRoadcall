

"use client";
export const dynamic = "force-dynamic";

import { useEffect, useState, useCallback, Suspense, useMemo, useRef, type FormEvent, type ReactNode } from "react";
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
  Map as MapIcon,
  LayoutGrid,
  Maximize2,
  PanelRightClose,
  PanelRightOpen,
  RectangleHorizontal,
  Rows3,
  Loader2,
  Activity,
  RadioTower,
  Layers3,
  Satellite,
} from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { HELP_PHONE, telHref } from "@/lib/phone";
import { NoCopySurface } from "@/components/privacy/no-copy-surface";
import { getApiBase } from "@/lib/api-client";
import { useMapboxToken } from "@/lib/mapbox-token";
// ...existing code...
// Intake modal and form
function IntakeModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    company: "",
    city: "",
    state: "",
    vehicle: "",
    problem: "",
    urgency: "normal",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [triage, setTriage] = useState<{ questions: string[]; answers: string[]; label?: string } | null>(null);
  const [triageBusy, setTriageBusy] = useState(false);

  function update<K extends keyof typeof form>(k: K, v: (typeof form)[K]) { setForm((f) => ({ ...f, [k]: v })); }

  // Step 2 -> Step 3: Fetch triage questions
  async function handleStep2Next() {
    setTriageBusy(true); setError("");
    try {
      // TODO: Replace with real tenant_id if available
      const tenant_id = "public-demo-tenant";
      const res = await fetch("/api/shop-ai/intake-guide", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer demo-public-token` },
        body: JSON.stringify({
          tenant_id,
          complaint: form.problem,
          vehicle_type: form.vehicle,
          caller_type: "shop",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not get triage questions");
      setTriage({ questions: data.questions, answers: Array(data.questions.length).fill(""), label: data.label });
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setTriageBusy(false);
    }
  }

  // Final submit: intake + triage
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(""); setOk("");
    try {
      // TODO: Replace with real tenant_id if available
      const tenant_id = "public-demo-tenant";
      const triageAnswers = triage?.questions?.map((q, i) => ({ question: q, answer: triage.answers[i] })) || [];
      const res = await fetch("/api/shop-ai/save-lead", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer demo-public-token` },
        body: JSON.stringify({
          tenant_id,
          caller_name: form.name,
          caller_phone: form.phone,
          service_type: form.problem,
          vehicle: form.vehicle,
          intent: "new_lead",
          urgency: form.urgency,
          notes: form.problem,
          triage: {
            symptom_category: triage?.label || "",
            answers: triageAnswers,
          },
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not submit");
      setOk("Thank you! Our team will review your request and connect you with the best provider.");
      setStep(99);
    } catch (e) { setError(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg rounded-3xl border border-roadcall-cyan/10 bg-roadcall-ink p-6 shadow-2xl relative">
        <button onClick={onClose} className="absolute right-4 top-4 rounded-full p-1 text-roadcall-muted hover:bg-roadcall-panel/60 hover:text-white"><X className="h-5 w-5" /></button>
        <h2 className="text-xl font-black mb-2 text-white">Request Truck Service</h2>
        <p className="text-sm text-roadcall-muted mb-4">Fill out this form and Roadcall will match you with the best provider for your needs.</p>
        {step === 0 && (
          <form onSubmit={e => { e.preventDefault(); setStep(1); }}>
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-roadcall-silver">Your Name*
                <input required value={form.name} onChange={e => update("name", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
              </label>
              <label className="block text-sm font-semibold text-roadcall-silver">Phone*
                <input required value={form.phone} onChange={e => update("phone", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
              </label>
              <label className="block text-sm font-semibold text-roadcall-silver">Email
                <input value={form.email} onChange={e => update("email", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
              </label>
            </div>
            <button type="button" onClick={() => setStep(1)} className="mt-6 w-full rounded-xl bg-roadcall-cyan px-4 py-3 font-bold text-slate-950">Next</button>
          </form>
        )}
        {step === 1 && (
          <form onSubmit={e => { e.preventDefault(); setStep(2); }}>
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-roadcall-silver">Company (optional)
                <input value={form.company} onChange={e => update("company", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
              </label>
              <div className="grid gap-3 grid-cols-2">
                <label className="block text-sm font-semibold text-roadcall-silver">City
                  <input value={form.city} onChange={e => update("city", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
                </label>
                <label className="block text-sm font-semibold text-roadcall-silver">State
                  <input value={form.state} maxLength={2} onChange={e => update("state", e.target.value.toUpperCase())} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
                </label>
              </div>
              <label className="block text-sm font-semibold text-roadcall-silver">Vehicle (year/make/model)
                <input value={form.vehicle} onChange={e => update("vehicle", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
              </label>
            </div>
            <div className="mt-6 flex gap-2">
              <button type="button" onClick={() => setStep(0)} className="rounded-xl border border-white/10 px-5 py-3 text-sm font-bold text-roadcall-silver hover:text-white">Back</button>
              <button type="button" onClick={() => setStep(2)} className="flex-1 rounded-xl bg-roadcall-cyan px-4 py-3 font-bold text-slate-950">Next</button>
            </div>
          </form>
        )}
        {step === 2 && (
          <form onSubmit={e => { e.preventDefault(); handleStep2Next(); }}>
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-roadcall-silver">Describe the Problem*
                <textarea required value={form.problem} onChange={e => update("problem", e.target.value)} rows={3} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1" />
              </label>
              <label className="block text-sm font-semibold text-roadcall-silver">Urgency
                <select value={form.urgency} onChange={e => update("urgency", e.target.value)} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1">
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="emergency">Emergency</option>
                </select>
              </label>
            </div>
            <div className="mt-6 flex gap-2">
              <button type="button" onClick={() => setStep(1)} className="rounded-xl border border-white/10 px-5 py-3 text-sm font-bold text-roadcall-silver hover:text-white">Back</button>
              <button type="submit" disabled={triageBusy} className="flex-1 rounded-xl bg-roadcall-cyan px-4 py-3 font-bold text-slate-950 disabled:opacity-60">{triageBusy ? <Loader2 className="h-4 w-4 animate-spin inline" /> : "Next: AI Triage"}</button>
            </div>
            {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
            {ok && <p className="mt-3 text-sm text-emerald-300">{ok}</p>}
          </form>
        )}
        {step === 3 && triage && (
          <form onSubmit={submit}>
            <div className="space-y-3">
              <h3 className="font-bold text-lg mb-2 text-white">AI Triage Questions</h3>
              {triage.questions.map((q, i) => (
                <label key={i} className="block text-sm font-semibold text-roadcall-silver">
                  {q}
                  <input
                    required
                    value={triage.answers[i]}
                    onChange={e => setTriage(t => t && { ...t, answers: t.answers.map((a, j) => j === i ? e.target.value : a) })}
                    className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white mt-1"
                  />
                </label>
              ))}
            </div>
            <div className="mt-6 flex gap-2">
              <button type="button" onClick={() => setStep(2)} className="rounded-xl border border-white/10 px-5 py-3 text-sm font-bold text-roadcall-silver hover:text-white">Back</button>
              <button type="submit" disabled={busy} className="flex-1 rounded-xl bg-roadcall-cyan px-4 py-3 font-bold text-slate-950 disabled:opacity-60">{busy ? <Loader2 className="h-4 w-4 animate-spin inline" /> : "Submit Request"}</button>
            </div>
            {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
            {ok && <p className="mt-3 text-sm text-emerald-300">{ok}</p>}
          </form>
        )}
        {step === 99 && (
          <div className="py-10 text-center">
            <h3 className="text-xl font-bold text-emerald-300 mb-3">Request submitted!</h3>
            <p className="text-roadcall-silver mb-6">Our team will review your request and connect you with the best provider. For urgent help, call our AI dispatcher.</p>
            <button onClick={onClose} className="rounded-xl bg-roadcall-cyan px-6 py-3 font-bold text-slate-950">Close</button>
          </div>
        )}
      </div>
    </div>
  );
}

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
  business_category?: string | null;
  address?: string | null;
  city: string | null;
  state: string | null;
  zip_code?: string | null;
  lat?: number | null;
  lng?: number | null;
  phone?: string | null;
  website?: string | null;
  source_url?: string | null;
  google_maps_url?: string | null;
  last_verified_at?: string | null;
  verification_status?: "unverified" | "claimed" | "verified" | "needs_review" | null;
  claim_status?: string | null;
  contact_protected?: boolean;
  export_status?: string | null;
  rating: number | null;
  review_count: number | null;
  accepts_mobile_roadside: boolean;
  emergency_service: boolean;
  is_emergency_24_7: boolean;
  service_types: string[];
  priority_score: number;
  distance_miles?: number | null;
  marketplace_score?: number | null;
  dispatch_fit_score?: number | null;
  trust_level?: string | null;
  availability_status?: string | null;
  estimated_response_minutes?: number | null;
  badges?: string[];
  reasons?: string[];
};

type MapBounds = {
  min_lat: number;
  max_lat: number;
  min_lng: number;
  max_lng: number;
};

type MapWorkspaceMode = "split" | "wide" | "fullscreen";
type ProviderViewMode = "map" | "cards" | "list";
type PremiumMapMode = "basic" | "operations" | "satellite" | "density" | "hotspots";

const VIEW_STORAGE_KEY = "roadcall-provider-view";

type QuickFilter = {
  label: string;
  kind?: "mobile" | "emergency" | "verified";
  service?: string;
  query?: string;
};

const QUICK_FILTERS: QuickFilter[] = [
  { label: "Mobile", kind: "mobile" },
  { label: "24/7", kind: "emergency" },
  { label: "Tire repair", service: "tire_repair" },
  { label: "Trailer repair", service: "trailer_repair" },
  { label: "Engine trouble", service: "engine_diesel" },
  { label: "Towing", service: "towing" },
  { label: "Trucking company", query: "trucking company" },
  { label: "Verified provider", kind: "verified" },
];

const PREMIUM_MAP_MODES: { id: PremiumMapMode; label: string; description: string; icon: typeof Activity; fleetOnly?: boolean }[] = [
  { id: "basic", label: "City", description: "Standard city map, provider pins, and simple search.", icon: MapIcon },
  { id: "operations", label: "Operations", description: "Provider readiness, mobile service, emergency support, and dispatch-fit signals from Roadcall data.", icon: RadioTower },
  { id: "satellite", label: "Satellite", description: "Premium imagery for industrial zones, truck stops, rural access, and service roads.", icon: Satellite },
  { id: "density", label: "Density", description: "Coverage heatmaps for mobile repair, towing, tires, and after-hours support from provider data.", icon: Layers3, fleetOnly: true },
  { id: "hotspots", label: "Hotspots", description: "Coverage gaps and high-priority service clusters from Roadcall provider signals.", icon: Zap, fleetOnly: true },
];

function safeExternalUrl(value?: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value.includes("://") ? value : `https://${value}`);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.toString();
  } catch {
    return null;
  }
}

function formatServiceLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function providerTypeColor(mechanic: Mechanic) {
  const category = (mechanic.business_category || "").toLowerCase();
  const services = (mechanic.service_types || []).join(" ").toLowerCase();
  if (category.includes("towing") || services.includes("tow")) return "#ef4444";
  if (category.includes("tire") || services.includes("tire")) return "#f59e0b";
  if (category.includes("freight") || category.includes("trucking")) return "#64748b";
  if (category.includes("truck repair") || services.includes("engine")) return "#22c55e";
  if (mechanic.accepts_mobile_roadside) return "#0ea5e9";
  return "#06b6d4";
}

function verificationLabel(status?: Mechanic["verification_status"]) {
  switch (status) {
    case "verified": return "Verified provider";
    case "claimed": return "Claimed listing";
    case "needs_review": return "Needs review";
    default: return "Unverified";
  }
}

function hasCoordinates(mechanic: Mechanic): mechanic is Mechanic & { lat: number; lng: number } {
  return typeof mechanic.lat === "number" && Number.isFinite(mechanic.lat) && typeof mechanic.lng === "number" && Number.isFinite(mechanic.lng);
}

function SearchResultsMap({ mechanics, onSearchArea, searchingArea, className = "h-[520px] min-h-[420px]", layoutKey, workspaceControls, premiumMode }: { mechanics: Mechanic[]; onSearchArea: (bounds: MapBounds) => void; searchingArea: boolean; className?: string; layoutKey?: string; workspaceControls?: ReactNode; premiumMode: PremiumMapMode }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const { token, configured, loading } = useMapboxToken(process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN);
  const points = useMemo(() => mechanics.filter(hasCoordinates), [mechanics]);
  const [visibleBounds, setVisibleBounds] = useState<MapBounds | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<Mechanic | null>(null);
  const premiumModeEnabled = premiumMode !== "basic";
  const mapStyle = premiumMode === "satellite"
    ? "mapbox://styles/mapbox/satellite-streets-v12"
    : premiumModeEnabled
      ? "mapbox://styles/mapbox/dark-v11"
      : "mapbox://styles/mapbox/streets-v12";

  useEffect(() => {
    if (!containerRef.current || !configured || points.length === 0) return;

    let map: any;
    let cancelled = false;

    import("mapbox-gl").then((mapboxModule) => {
      if (cancelled || !containerRef.current) return;
      const mapboxgl = (mapboxModule as any).default ?? mapboxModule;
      mapboxgl.accessToken = token;
      const first = points[0];
      map = new mapboxgl.Map({
        container: containerRef.current,
        style: mapStyle,
        center: [first.lng, first.lat],
        zoom: points.length === 1 ? 10 : 4,
        pitch: premiumModeEnabled ? 48 : 0,
        bearing: premiumModeEnabled ? -18 : 0,
      });
      mapRef.current = map;
      map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-left");
      map.addControl(new mapboxgl.AttributionControl({ compact: true }), "bottom-right");

      const updateVisibleBounds = () => {
        const bounds = map.getBounds();
        setVisibleBounds({
          min_lat: bounds.getSouth(),
          max_lat: bounds.getNorth(),
          min_lng: bounds.getWest(),
          max_lng: bounds.getEast(),
        });
      };
      map.on("moveend", updateVisibleBounds);
      map.once("idle", updateVisibleBounds);

      map.on("load", () => {
        const bounds = new mapboxgl.LngLatBounds();
        const geojson = {
          type: "FeatureCollection",
          features: points.map((mechanic) => {
            bounds.extend([mechanic.lng, mechanic.lat]);
            return {
              type: "Feature",
              properties: {
                mechanic_id: mechanic.id,
                company_name: mechanic.company_name,
                category: mechanic.business_category || "Roadside Provider",
                color: providerTypeColor(mechanic),
                priority_score: mechanic.priority_score || mechanic.dispatch_fit_score || mechanic.marketplace_score || 0.5,
              },
              geometry: { type: "Point", coordinates: [mechanic.lng, mechanic.lat] },
            };
          }),
        };

        map.addSource("providers", {
          type: "geojson",
          data: geojson,
          cluster: true,
          clusterMaxZoom: 11,
          clusterRadius: 44,
        });
        map.addLayer({
          id: "provider-clusters",
          type: "circle",
          source: "providers",
          filter: ["has", "point_count"],
          paint: {
            "circle-color": ["step", ["get", "point_count"], "#0891b2", 20, "#f97316", 75, "#ef4444"],
            "circle-radius": ["step", ["get", "point_count"], 18, 20, 24, 75, 32],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
          },
        });
        map.addLayer({
          id: "provider-cluster-count",
          type: "symbol",
          source: "providers",
          filter: ["has", "point_count"],
          layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12 },
          paint: { "text-color": "#ffffff" },
        });
        map.addLayer({
          id: "provider-pins",
          type: "circle",
          source: "providers",
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-color": ["get", "color"],
            "circle-radius": 8,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
          },
        });
        if (premiumModeEnabled && ["operations", "density", "hotspots"].includes(premiumMode)) {
          map.addLayer({
            id: "roadside-intelligence-heat",
            type: "heatmap",
            source: "providers",
            maxzoom: 11,
            paint: {
              "heatmap-weight": ["interpolate", ["linear"], ["coalesce", ["get", "priority_score"], 0.5], 0, 0.25, 1, 1],
              "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 0.6, 9, 1.8],
              "heatmap-color": [
                "interpolate",
                ["linear"],
                ["heatmap-density"],
                0, "rgba(8,47,73,0)",
                0.25, "rgba(14,165,233,0.28)",
                0.55, "rgba(34,211,238,0.42)",
                0.8, "rgba(251,146,60,0.52)",
                1, "rgba(239,68,68,0.62)",
              ],
              "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 18, 9, 42],
              "heatmap-opacity": premiumMode === "density" || premiumMode === "hotspots" ? 0.82 : 0.45,
            },
          }, "provider-pins");
        }
        map.addLayer({
          id: "provider-pin-labels",
          type: "symbol",
          source: "providers",
          filter: ["!", ["has", "point_count"]],
          layout: {
            "text-field": ["get", "company_name"],
            "text-size": 11,
            "text-offset": [0, 1.35],
            "text-anchor": "top",
          },
          paint: { "text-color": "#0f172a", "text-halo-color": "#ffffff", "text-halo-width": 1.2 },
        });
        map.on("click", "provider-clusters", (event: any) => {
          const features = map.queryRenderedFeatures(event.point, { layers: ["provider-clusters"] });
          const clusterId = features[0]?.properties?.cluster_id;
          const source = map.getSource("providers");
          source.getClusterExpansionZoom(clusterId, (err: Error | null, zoom: number) => {
            if (err) return;
            map.easeTo({ center: (features[0].geometry as any).coordinates, zoom });
          });
        });
        map.on("click", "provider-pins", (event: any) => {
          const mechanicId = event.features?.[0]?.properties?.mechanic_id;
          const provider = points.find((mechanic) => mechanic.id === mechanicId);
          if (provider) setSelectedProvider(provider);
        });
        map.on("mouseenter", "provider-clusters", () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", "provider-clusters", () => { map.getCanvas().style.cursor = ""; });
        map.on("mouseenter", "provider-pins", () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", "provider-pins", () => { map.getCanvas().style.cursor = ""; });
        if (points.length > 1) {
          map.fitBounds(bounds, { padding: 64, maxZoom: 10, duration: 0 });
        }
      });
    });

    return () => {
      cancelled = true;
      if (map) map.remove();
      mapRef.current = null;
    };
  }, [configured, mapStyle, points, premiumMode, premiumModeEnabled, token]);

  useEffect(() => {
    const timeout = window.setTimeout(() => mapRef.current?.resize(), 120);
    return () => window.clearTimeout(timeout);
  }, [layoutKey]);

  if (loading) {
    return <div className={`grid place-items-center rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30 text-sm text-roadcall-muted ${className}`}>Loading map…</div>;
  }

  if (!configured) {
    return <div className={`grid place-items-center rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30 px-6 text-center text-sm text-roadcall-muted ${className}`}>Map view needs a configured Mapbox public token.</div>;
  }

  if (points.length === 0) {
    return <div className={`grid place-items-center rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30 px-6 text-center text-sm text-roadcall-muted ${className}`}>No mapped providers in these results yet. Try a state or city with geocoded mechanics.</div>;
  }

  return (
    <div className={`relative overflow-hidden rounded-2xl border border-roadcall-cyan/15 bg-roadcall-panel/30 ${className}`}>
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute left-4 top-4 z-10 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!visibleBounds || searchingArea}
          onClick={() => visibleBounds && onSearchArea(visibleBounds)}
          className="rounded-full border border-slate-900/10 bg-white px-4 py-2 text-xs font-black text-slate-950 shadow-xl transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {searchingArea ? "Searching map area..." : "Search this map area"}
        </button>
      </div>
      {workspaceControls ? <div className="absolute right-4 top-4 z-10 max-w-[calc(100%-2rem)] overflow-x-auto">{workspaceControls}</div> : null}
      {premiumModeEnabled ? <PremiumOperationsOverlay mechanics={points} mode={premiumMode} /> : null}
      {selectedProvider ? (
        <div className="absolute bottom-4 right-4 z-20 w-[min(360px,calc(100%-2rem))] rounded-2xl border border-slate-200 bg-white p-4 text-slate-950 shadow-2xl">
          <button type="button" onClick={() => setSelectedProvider(null)} className="absolute right-3 top-3 rounded-full p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900"><X className="h-4 w-4" /></button>
          <p className="pr-8 text-base font-black leading-tight">{selectedProvider.company_name}</p>
          <p className="mt-1 text-xs font-bold text-cyan-700">{selectedProvider.business_category || "Roadside Provider"}</p>
          <p className="mt-3 text-sm text-slate-700">{selectedProvider.address || [selectedProvider.city, selectedProvider.state].filter(Boolean).join(", ") || "Address unavailable"}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {(selectedProvider.service_types || []).slice(0, 4).map((tag) => <span key={tag} className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-700">{formatServiceLabel(tag)}</span>)}
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {selectedProvider.phone ? <a href={telHref(selectedProvider.phone)} className="rounded-xl bg-slate-950 px-3 py-2 text-center text-xs font-black text-white">Call Provider</a> : <span className="rounded-xl bg-slate-100 px-3 py-2 text-center text-xs font-bold text-slate-500">Phone protected</span>}
            {safeExternalUrl(selectedProvider.website) ? <a href={safeExternalUrl(selectedProvider.website)!} target="_blank" rel="noreferrer" className="rounded-xl border border-slate-200 px-3 py-2 text-center text-xs font-black text-slate-900">Visit Website</a> : <span className="rounded-xl border border-slate-200 px-3 py-2 text-center text-xs font-bold text-slate-500">Website unavailable</span>}
          </div>
          {selectedProvider.contact_protected ? <p className="mt-3 rounded-xl bg-cyan-50 px-3 py-2 text-xs font-semibold text-cyan-800">Contact details are protected. Use Roadcall dispatch to connect.</p> : null}
        </div>
      ) : null}
    </div>
  );
}

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

function MechanicCard({ m, onClaim, onViewMap }: { m: Mechanic; onClaim: (mechanic: Mechanic) => void; onViewMap: (mechanic: Mechanic) => void }) {
  const topReason = m.reasons?.[0];
  const trustLabel = m.trust_level ? m.trust_level.replace(/_/g, " ") : null;
  const websiteUrl = safeExternalUrl(m.website);
  const status = m.verification_status || "unverified";

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/40 backdrop-blur-sm transition-all duration-200 p-5 hover:-translate-y-1 hover:border-roadcall-cyan/35 hover:bg-roadcall-panel/60 hover:shadow-2xl hover:shadow-roadcall-cyan/10">
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
            <p className="mt-2 inline-flex rounded-full border border-roadcall-cyan/15 bg-roadcall-cyan/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-roadcall-cyan">
              {m.business_category || "Roadside Provider"}
            </p>
          </div>
          <StarRating rating={m.rating} count={m.review_count} />
        </div>

        <div className="mb-3 space-y-1.5 text-xs text-roadcall-muted">
          <p className="line-clamp-2">{m.address || "Full address unavailable"}</p>
          <p>{m.phone ? m.phone : "Phone protected or unavailable"}</p>
          <p>{websiteUrl ? <a href={websiteUrl} target="_blank" rel="noreferrer" className="text-roadcall-cyan hover:text-white">{websiteUrl.replace(/^https?:\/\//, "")}</a> : "Website unavailable"}</p>
        </div>

        {(m.distance_miles != null || m.estimated_response_minutes != null || trustLabel) && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {m.distance_miles != null && (
              <span className="rounded-full border border-roadcall-cyan/15 bg-roadcall-cyan/10 px-2 py-0.5 text-[10px] font-semibold text-roadcall-cyan">
                {m.distance_miles.toFixed(1)} mi
              </span>
            )}
            {m.estimated_response_minutes != null && (
              <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                ~{m.estimated_response_minutes} min
              </span>
            )}
            {trustLabel && (
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] font-semibold capitalize text-roadcall-silver">
                {trustLabel}
              </span>
            )}
          </div>
        )}

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
          {m.badges?.slice(0, 2).map((badge) => (
            <span key={badge} className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/10 text-roadcall-silver text-[10px] font-medium">
              {badge}
            </span>
          ))}
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold ${status === "verified" ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300" : status === "claimed" ? "border-cyan-400/25 bg-cyan-400/10 text-cyan-300" : status === "needs_review" ? "border-amber-400/25 bg-amber-400/10 text-amber-300" : "border-white/10 bg-white/[0.04] text-roadcall-silver"}`}>
            {verificationLabel(status)}
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/10 text-roadcall-silver text-[10px] font-medium">
            Export {m.export_status === "ready" ? "ready" : "needs enrichment"}
          </span>
        </div>

        {topReason && (
          <p className="mb-4 rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/40 px-3 py-2 text-xs font-medium leading-relaxed text-roadcall-muted">
            {topReason}
          </p>
        )}

        <div className="grid grid-cols-2 gap-2">
          <button type="button" onClick={() => onViewMap(m)} className="rounded-xl border border-roadcall-cyan/20 bg-roadcall-cyan/10 px-3 py-2 text-xs font-black text-roadcall-cyan transition group-hover:border-roadcall-cyan/40 group-hover:bg-roadcall-cyan/15">View on Map</button>
          {websiteUrl ? <a href={websiteUrl} target="_blank" rel="noreferrer" className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-center text-xs font-black text-roadcall-silver transition hover:text-white">Visit Website</a> : <span className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-center text-xs font-bold text-roadcall-muted">Website unavailable</span>}
          {m.phone ? <a href={telHref(m.phone)} className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-center text-xs font-black text-emerald-300 transition hover:bg-emerald-400/15">Call Provider</a> : <a href={telHref(HELP_PHONE)} className="rounded-xl border border-roadcall-orange/25 bg-roadcall-orange/10 px-3 py-2 text-center text-xs font-black text-roadcall-orange transition hover:bg-roadcall-orange/15">Roadcall Dispatch</a>}
          <button type="button" onClick={() => onClaim(m)} className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-black text-roadcall-silver transition hover:border-white/20 hover:text-white">Claim / Update Listing</button>
        </div>
        {m.contact_protected ? <p className="mt-3 rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/50 px-3 py-2.5 text-center text-xs text-roadcall-muted">Contact details are protected. Use Roadcall dispatch to connect.</p> : null}
        {m.claim_status !== "claimed" ? <p className="mt-3 text-[11px] font-semibold text-roadcall-muted">Own or represent this company? Claim this listing to update details.</p> : null}
      </div>
    </div>
  );
}

function groupMechanicsByCity(mechanics: Mechanic[]) {
  const groups = new Map<string, { label: string; providers: Mechanic[] }>();
  mechanics.forEach((mechanic) => {
    const label = [mechanic.city, mechanic.state].filter(Boolean).join(", ") || "Mapped providers";
    const key = label.toLowerCase();
    const group = groups.get(key) || { label, providers: [] };
    group.providers.push(mechanic);
    groups.set(key, group);
  });
  return Array.from(groups.values()).sort((a, b) => b.providers.length - a.providers.length || a.label.localeCompare(b.label));
}

function CityMechanicGroup({ label, providers, onClaim, onViewMap }: { label: string; providers: Mechanic[]; onClaim: (mechanic: Mechanic) => void; onViewMap: (mechanic: Mechanic) => void }) {
  return (
    <section className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30 p-3">
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <h3 className="min-w-0 truncate text-sm font-black text-white">{label}</h3>
        <span className="shrink-0 rounded-full border border-roadcall-cyan/20 bg-roadcall-cyan/10 px-2.5 py-1 text-[11px] font-bold text-roadcall-cyan">
          {providers.length} {providers.length === 1 ? "provider" : "providers"}
        </span>
      </div>
      <div className="space-y-3">
        {providers.map((mechanic) => <MechanicCard key={mechanic.id} m={mechanic} onClaim={onClaim} onViewMap={onViewMap} />)}
      </div>
    </section>
  );
}

function MechanicListView({ mechanics, onClaim, onViewMap }: { mechanics: Mechanic[]; onClaim: (mechanic: Mechanic) => void; onViewMap: (mechanic: Mechanic) => void }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/35">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-roadcall-cyan/10 bg-roadcall-panel/60 text-xs uppercase tracking-wide text-roadcall-muted">
            <tr>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">City/state</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Website</th>
              <th className="px-4 py-3">Rating</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-roadcall-cyan/10">
            {mechanics.map((mechanic) => {
              const websiteUrl = safeExternalUrl(mechanic.website);
              return (
                <tr key={mechanic.id} className="text-roadcall-silver hover:bg-roadcall-cyan/[0.04]">
                  <td className="px-4 py-3">
                    <div className="font-bold text-white">{mechanic.company_name}</div>
                    <div className="mt-1 max-w-xs truncate text-xs text-roadcall-muted">{mechanic.address || "Address unavailable"}</div>
                  </td>
                  <td className="px-4 py-3">{[mechanic.city, mechanic.state].filter(Boolean).join(", ") || "-"}</td>
                  <td className="px-4 py-3">{mechanic.business_category || "Roadside Provider"}</td>
                  <td className="px-4 py-3">{mechanic.phone || "Protected"}</td>
                  <td className="px-4 py-3">{websiteUrl ? <a href={websiteUrl} target="_blank" rel="noreferrer" className="text-roadcall-cyan hover:text-white">Open</a> : "Unavailable"}</td>
                  <td className="px-4 py-3">{mechanic.rating ? `${mechanic.rating.toFixed(1)} (${mechanic.review_count || 0})` : "-"}</td>
                  <td className="px-4 py-3">{verificationLabel(mechanic.verification_status)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => onViewMap(mechanic)} className="rounded-full border border-roadcall-cyan/20 px-3 py-1 text-xs font-bold text-roadcall-cyan hover:bg-roadcall-cyan/10">View on Map</button>
                      {websiteUrl ? <a href={websiteUrl} target="_blank" rel="noreferrer" className="rounded-full border border-white/10 px-3 py-1 text-xs font-bold text-roadcall-silver hover:text-white">Visit Website</a> : null}
                      <button type="button" onClick={() => onClaim(mechanic)} className="rounded-full border border-white/10 px-3 py-1 text-xs font-bold text-roadcall-silver hover:text-white">Claim listing</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ClaimUpdateModal({ mechanic, onClose, onSubmitted }: { mechanic: Mechanic; onClose: () => void; onSubmitted: (message: string) => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const requestedChanges: Record<string, string> = {};
    ["company_name", "address", "phone", "website", "city", "state", "google_maps_url"].forEach((field) => {
      const value = String(form.get(field) || "").trim();
      if (value) requestedChanges[field] = value;
    });
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/marketplace/${mechanic.id}/update-request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: form.get("role"),
          full_name: form.get("full_name"),
          work_email: form.get("work_email"),
          phone_number: form.get("phone_number"),
          company_name: form.get("submitted_company_name") || mechanic.company_name,
          company_address: form.get("submitted_company_address"),
          website: form.get("submitted_website"),
          proof_message: form.get("proof_message"),
          requested_changes: requestedChanges,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Could not submit update request");
      onSubmitted(data.message || "Update request submitted for Roadcall admin review.");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit update request");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-4 backdrop-blur-sm">
      <form onSubmit={submit} className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-roadcall-cyan/15 bg-[#06101f] p-6 shadow-2xl shadow-black/60">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.2em] text-roadcall-cyan">Claim / Update Listing</p>
            <h2 className="mt-2 text-2xl font-black text-white">{mechanic.company_name}</h2>
            <p className="mt-2 text-sm text-roadcall-muted">Requests are ownership-checked and reviewed by Roadcall before public data changes.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-full border border-white/10 p-2 text-roadcall-muted hover:text-white"><X className="h-4 w-4" /></button>
        </div>
        {error ? <div className="mt-4 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm font-semibold text-red-200">{error}</div> : null}
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Role<select name="role" required className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white"><option value="owner">Owner</option><option value="manager">Manager</option><option value="dispatcher">Dispatcher</option><option value="authorized_company_rep">Authorized company rep</option></select></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Full name<input name="full_name" required className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Work email<input name="work_email" type="email" required className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Phone number<input name="phone_number" required className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Company name<input name="submitted_company_name" defaultValue={mechanic.company_name} required className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Company address<input name="submitted_company_address" defaultValue={mechanic.address || ""} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Website<input name="submitted_website" defaultValue={mechanic.website || ""} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Google Maps URL<input name="google_maps_url" defaultValue={mechanic.google_maps_url || ""} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">Public phone update<input name="phone" defaultValue={mechanic.phone || ""} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">City<input name="city" defaultValue={mechanic.city || ""} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver">State<input name="state" defaultValue={mechanic.state || ""} maxLength={2} className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
          <label className="space-y-1 text-sm font-semibold text-roadcall-silver md:col-span-2">Proof message<textarea name="proof_message" rows={4} placeholder="Tell us how you are connected to this company." className="w-full rounded-xl border border-roadcall-cyan/15 bg-roadcall-panel/70 px-3 py-2 text-white" /></label>
        </div>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="rounded-xl border border-white/10 px-5 py-3 text-sm font-bold text-roadcall-silver hover:text-white">Cancel</button>
          <button disabled={submitting} className="rounded-xl bg-roadcall-cyan px-5 py-3 text-sm font-black text-slate-950 disabled:opacity-60">{submitting ? "Submitting..." : "Suggest an Update"}</button>
        </div>
      </form>
    </div>
  );
}

function PremiumMapModeControls({ mode, onModeChange }: { mode: PremiumMapMode; onModeChange: (mode: PremiumMapMode) => void }) {
  return (
    <div className="rounded-2xl border border-roadcall-cyan/15 bg-[#06101f]/90 p-3 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-roadcall-cyan">Premium map modes</p>
          <p className="mt-1 text-xs text-roadcall-muted">Mapbox views plus Roadcall provider intelligence.</p>
        </div>
        <Activity className="h-4 w-4 text-emerald-300" />
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {PREMIUM_MAP_MODES.map((item) => {
          const Icon = item.icon;
          const active = mode === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onModeChange(item.id)}
              className={`rounded-xl border p-3 text-left transition ${active ? "border-roadcall-cyan bg-roadcall-cyan/15" : "border-white/10 bg-white/[0.035] hover:border-roadcall-cyan/30"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <Icon className={active ? "h-4 w-4 text-roadcall-cyan" : "h-4 w-4 text-roadcall-silver"} />
              </div>
              <p className="mt-2 text-xs font-black text-white">{item.label}</p>
              <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-roadcall-muted">{item.description}</p>
              {item.fleetOnly ? <p className="mt-2 text-[10px] font-bold uppercase tracking-wide text-blue-200">Fleet plan</p> : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function FullscreenMapModeControls({ mode, onModeChange }: { mode: PremiumMapMode; onModeChange: (mode: PremiumMapMode) => void }) {
  return (
    <div className="flex max-w-[min(72vw,760px)] items-center gap-1 overflow-x-auto rounded-full border border-roadcall-cyan/15 bg-roadcall-panel/85 p-1 shadow-2xl shadow-black/30 backdrop-blur-md">
      {PREMIUM_MAP_MODES.map((item) => {
        const Icon = item.icon;
        const active = mode === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onModeChange(item.id)}
            title={item.description}
            className={`inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs font-black transition ${active ? "bg-roadcall-cyan text-slate-950" : "text-roadcall-silver hover:bg-white/10 hover:text-white"}`}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function PremiumOperationsOverlay({ mechanics, mode }: { mechanics: (Mechanic & { lat: number; lng: number })[]; mode: PremiumMapMode }) {
  const emergencyReady = mechanics.filter((mechanic) => mechanic.emergency_service || mechanic.is_emergency_24_7).length;
  const mobileActive = mechanics.filter((mechanic) => mechanic.accepts_mobile_roadside).length;
  const avgEta = Math.round(
    mechanics.reduce((sum, mechanic) => sum + (mechanic.estimated_response_minutes || 38), 0) / Math.max(1, mechanics.length),
  );
  const message = mode === "density"
    ? "Provider coverage density highlights service availability by geography."
    : mode === "hotspots"
      ? "Roadcall provider signals highlight service gaps and high-priority clusters."
      : mode === "satellite"
        ? "Mapbox satellite imagery is active for rural access, yards, and service roads."
        : "Roadcall provider readiness and dispatch-fit signals are active.";
  return (
    <div className="pointer-events-none absolute left-4 top-20 z-10 w-[min(360px,calc(100%-2rem))] space-y-3">
      <div className="rounded-2xl border border-roadcall-cyan/20 bg-[#02050c]/80 p-4 shadow-2xl shadow-cyan-500/10 backdrop-blur-xl">
        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-roadcall-cyan">AI roadside operations center</p>
        <p className="mt-2 text-sm font-bold text-white">{message}</p>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2"><p className="text-lg font-black text-white">{emergencyReady}</p><p className="text-[10px] text-roadcall-muted">Emergency</p></div>
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2"><p className="text-lg font-black text-white">{mobileActive}</p><p className="text-[10px] text-roadcall-muted">Mobile</p></div>
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2"><p className="text-lg font-black text-white">{avgEta}m</p><p className="text-[10px] text-roadcall-muted">ETA</p></div>
        </div>
      </div>
      <div className="rounded-2xl border border-red-400/25 bg-red-400/10 p-3 text-xs font-bold text-red-100 shadow-2xl backdrop-blur-xl">
        <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-red-300" /> Emergency Breakdown workflow armed
      </div>
    </div>
  );
}

function MapWorkspaceControls({
  mode,
  sidePanelOpen,
  onModeChange,
  onToggleSidePanel,
}: {
  mode: MapWorkspaceMode;
  sidePanelOpen: boolean;
  onModeChange: (mode: MapWorkspaceMode) => void;
  onToggleSidePanel: () => void;
}) {
  if (mode === "fullscreen") {
    return (
      <div className="inline-flex items-center rounded-full border border-roadcall-cyan/15 bg-roadcall-panel/80 p-1 shadow-2xl shadow-black/30 backdrop-blur-md">
        <button
          type="button"
          onClick={() => onModeChange("split")}
          title="Exit full page map"
          className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-roadcall-cyan text-slate-950 transition hover:brightness-110"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
    );
  }

  const controls = [
    { id: "split" as const, label: "Split map and list", icon: Rows3 },
    { id: "wide" as const, label: "Focus map", icon: RectangleHorizontal },
    { id: "fullscreen" as const, label: "Expand map to full page", icon: Maximize2 },
  ];
  return (
    <div className="inline-flex items-center rounded-full border border-roadcall-cyan/15 bg-roadcall-panel/80 p-1 shadow-2xl shadow-black/30 backdrop-blur-md">
      <button
        type="button"
        onClick={onToggleSidePanel}
        title={sidePanelOpen ? "Hide provider panel" : "Show provider panel"}
        className={`inline-flex h-8 w-8 items-center justify-center rounded-full transition ${sidePanelOpen ? "text-roadcall-cyan hover:bg-white/10" : "bg-roadcall-cyan text-slate-950"}`}
      >
        {sidePanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
      </button>
      <span className="mx-1 h-5 w-px bg-white/10" />
      {controls.map((control) => {
        const Icon = control.icon;
        const active = mode === control.id;
        return (
          <button
            key={control.id}
            type="button"
            onClick={() => onModeChange(control.id)}
            title={control.label}
            className={`inline-flex h-8 w-8 items-center justify-center rounded-full transition ${active ? "bg-roadcall-cyan text-slate-950" : "text-roadcall-silver hover:bg-white/10 hover:text-white"}`}
          >
            <Icon className="h-4 w-4" />
          </button>
        );
      })}
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
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [radiusMiles, setRadiusMiles] = useState(75);
  const [page, setPage] = useState(1);

  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [view, setView] = useState<ProviderViewMode>("map");
  const [mapWorkspaceMode, setMapWorkspaceMode] = useState<MapWorkspaceMode>("split");
  const [premiumMapMode, setPremiumMapMode] = useState<PremiumMapMode>("basic");
  const [mapSidePanelOpen, setMapSidePanelOpen] = useState(true);
  const [mapAreaSummary, setMapAreaSummary] = useState<string | null>(null);
  const [searchingArea, setSearchingArea] = useState(false);
  const [claimTarget, setClaimTarget] = useState<Mechanic | null>(null);
  const [claimStatus, setClaimStatus] = useState<string | null>(null);
  const [intakeOpen, setIntakeOpen] = useState(false);
  useEffect(() => {
    const storedView = window.localStorage.getItem(VIEW_STORAGE_KEY) as ProviderViewMode | null;
    if (storedView === "map" || storedView === "cards" || storedView === "list") setView(storedView);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(VIEW_STORAGE_KEY, view);
  }, [view]);

  const buildSearchParams = useCallback((options?: { bounds?: MapBounds; pageOverride?: number; pageSize?: number }) => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (state) params.set("state", state);
    if (city && !options?.bounds) params.set("city", city);
    if (serviceType) params.set("service_type", serviceType);
    if (only24_7) params.set("is_24_7", "true");
    if (onlyMobile) params.set("mobile_only", "true");
    if (verifiedOnly) params.set("verified_only", "true");
    if (options?.bounds) {
      params.set("min_lat", String(options.bounds.min_lat));
      params.set("max_lat", String(options.bounds.max_lat));
      params.set("min_lng", String(options.bounds.min_lng));
      params.set("max_lng", String(options.bounds.max_lng));
    }
    params.set("page", String(options?.pageOverride ?? page));
    params.set("page_size", String(options?.pageSize ?? 24));
    return params;
  }, [city, only24_7, onlyMobile, page, query, serviceType, state, verifiedOnly]);

  const doSearch = useCallback(async (resetPage = false, pageOverride?: number) => {
    const currentPage = resetPage ? 1 : pageOverride ?? page;
    if (resetPage || pageOverride) setPage(currentPage);
    setLoading(true);
    setError(null);
    setMapAreaSummary(null);
    const params = buildSearchParams({ pageOverride: currentPage });

    try {
      const res = await fetch(`${API_URL}/mechanics/search?${params}`);
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setResults(verifiedOnly ? { ...data, mechanics: data.mechanics.filter((m: Mechanic) => m.verification_status === "verified" || m.verification_status === "claimed") } : data);
    } catch {
      // Fall back to a public-friendly empty state
      setResults({ mechanics: [], total: 0, page: 1, page_size: 24 });
      setError("Search unavailable — try the AI dispatcher for instant help.");
    } finally {
      setLoading(false);
    }
  }, [buildSearchParams, page, verifiedOnly]);

  const searchMapArea = useCallback(async (bounds: MapBounds) => {
    setSearchingArea(true);
    setLoading(true);
    setError(null);
    setPage(1);
    const params = buildSearchParams({ bounds, pageOverride: 1, pageSize: 100 });

    try {
      const res = await fetch(`${API_URL}/mechanics/search?${params}`);
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setResults(verifiedOnly ? { ...data, mechanics: data.mechanics.filter((m: Mechanic) => m.verification_status === "verified" || m.verification_status === "claimed") } : data);
      setMapAreaSummary(`Showing ${data.mechanics.length.toLocaleString()} mapped providers in the visible map area`);
      setView("map");
    } catch {
      setError("Map area search unavailable — try zooming out or clearing filters.");
    } finally {
      setLoading(false);
      setSearchingArea(false);
    }
  }, [buildSearchParams, verifiedOnly]);

  const searchNearMe = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Near me search needs browser location access.");
      return;
    }
    setSearchingArea(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const latDelta = radiusMiles / 69;
        const lngDelta = radiusMiles / Math.max(20, Math.cos((lat * Math.PI) / 180) * 69);
        searchMapArea({ min_lat: lat - latDelta, max_lat: lat + latDelta, min_lng: lng - lngDelta, max_lng: lng + lngDelta });
      },
      () => {
        setSearchingArea(false);
        setError("Location permission was not granted. Try searching by city or ZIP.");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }, [radiusMiles, searchMapArea]);

  useEffect(() => {
    doSearch(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, city, serviceType, only24_7, onlyMobile, verifiedOnly]);

  const totalPages = results ? Math.ceil(results.total / results.page_size) : 0;
  const cityGroups = useMemo(() => groupMechanicsByCity(results?.mechanics || []), [results]);
  const handleViewMap = useCallback((mechanic: Mechanic) => {
    setView("map");
    setMapWorkspaceMode("split");
    setMapSidePanelOpen(true);
    if (mechanic.city || mechanic.state) setMapAreaSummary(`Showing map near ${[mechanic.city, mechanic.state].filter(Boolean).join(", ")}`);
  }, []);
  const isFullscreenMap = mapWorkspaceMode === "fullscreen";
  useEffect(() => {
    if (!isFullscreenMap) return;
    const previousOverflow = document.body.style.overflow;
    const footers = Array.from(document.querySelectorAll<HTMLElement>("footer"));
    const previousFooterDisplays = footers.map((footer) => footer.style.display);
    document.body.style.overflow = "hidden";
    footers.forEach((footer) => {
      footer.style.display = "none";
    });
    return () => {
      document.body.style.overflow = previousOverflow;
      footers.forEach((footer, index) => {
        footer.style.display = previousFooterDisplays[index] || "";
      });
    };
  }, [isFullscreenMap]);

  const showMapSidePanel = mapSidePanelOpen && mapWorkspaceMode !== "wide" && !isFullscreenMap;
  const mapShellClass = mapWorkspaceMode === "fullscreen"
    ? "fixed inset-x-0 bottom-0 top-20 z-[60] overflow-hidden bg-[#02050c] shadow-2xl shadow-black/80"
    : "";
  const mapGridClass = mapWorkspaceMode === "fullscreen"
    ? "absolute inset-0 h-full min-h-0"
    : showMapSidePanel
      ? "grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]"
      : "grid gap-4";
  const mapHeightClass = mapWorkspaceMode === "fullscreen"
    ? "h-full min-h-0 rounded-none border-0"
    : mapWorkspaceMode === "wide"
      ? "h-[680px] min-h-[520px]"
      : "h-[520px] min-h-[420px]";
  const premiumModeLabel = PREMIUM_MAP_MODES.find((mode) => mode.id === premiumMapMode)?.label || "Basic";

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
            <h1 className="text-3xl sm:text-4xl font-black text-white mb-2">AI Roadside Operations Center</h1>
            <p className="text-roadcall-muted text-sm">Mapbox satellite views, provider coverage, and Roadcall operational signals are open while we continue tuning the experience.</p>
          </div>

          {/* Main search bar + intake button */}
          <div className="flex gap-2 mb-4">
            <form
              onSubmit={(e) => { e.preventDefault(); doSearch(true); }}
              className="flex-1 flex gap-2"
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
            <button
              type="button"
              onClick={() => setIntakeOpen(true)}
              className="rounded-xl bg-gradient-to-r from-emerald-400 to-cyan-400 px-6 py-3.5 font-bold text-slate-950 hover:brightness-110 text-sm shadow-lg"
            >
              Request Service
            </button>
          </div>
  {intakeOpen && <IntakeModal onClose={() => setIntakeOpen(false)} />}

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
                  setOnly24_7(false); setOnlyMobile(false); setVerifiedOnly(false);
                  setMapAreaSummary(null);
                }}
                className="flex items-center gap-1 text-xs text-roadcall-muted hover:text-white transition-colors"
              >
                <X className="h-3.5 w-3.5" /> Clear all
              </button>
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {QUICK_FILTERS.map((filter) => {
              const active = filter.kind === "mobile" ? onlyMobile : filter.kind === "emergency" ? only24_7 : filter.kind === "verified" ? verifiedOnly : filter.service ? serviceType === filter.service : query === filter.query;
              return (
                <button
                  key={filter.label}
                  type="button"
                  onClick={() => {
                    if (filter.kind === "mobile") setOnlyMobile((value) => !value);
                    else if (filter.kind === "emergency") setOnly24_7((value) => !value);
                    else if (filter.kind === "verified") setVerifiedOnly((value) => !value);
                    else if (filter.service) setServiceType(active ? "" : filter.service);
                    else if (filter.query) setQuery(active ? "" : filter.query);
                  }}
                  className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${active ? "border-roadcall-cyan bg-roadcall-cyan text-slate-950" : "border-roadcall-cyan/15 bg-roadcall-panel/40 text-roadcall-silver hover:border-roadcall-cyan/35 hover:text-white"}`}
                >
                  {filter.label}
                </button>
              );
            })}
          </div>

          {/* Expanded filters */}
          {filtersOpen && (
            <div className="mt-3 p-4 rounded-xl bg-roadcall-panel/40 border border-roadcall-cyan/10 flex flex-wrap items-center gap-4">
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
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={verifiedOnly}
                  onChange={(e) => setVerifiedOnly(e.target.checked)}
                  className="accent-roadcall-orange w-4 h-4"
                />
                <span className="text-sm text-roadcall-silver">Verified / Claimed Only</span>
              </label>
              <label className="flex items-center gap-2 text-sm text-roadcall-silver">
                Radius
                <select
                  value={radiusMiles}
                  onChange={(event) => setRadiusMiles(Number(event.target.value))}
                  className="rounded-lg border border-roadcall-cyan/15 bg-roadcall-panel/70 px-2 py-1 text-sm text-roadcall-silver"
                >
                  {[25, 50, 75, 100, 150, 250].map((value) => <option key={value} value={value}>{value} mi</option>)}
                </select>
              </label>
              <button
                type="button"
                onClick={searchNearMe}
                className="rounded-lg border border-roadcall-cyan/20 bg-roadcall-cyan/10 px-3 py-2 text-sm font-bold text-roadcall-cyan hover:bg-roadcall-cyan/15"
              >
                Near me
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Results area */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Result count / error */}
        <div className="flex flex-col gap-3 mb-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {loading ? (
              <span className="text-sm text-roadcall-muted animate-pulse">Searching…</span>
            ) : error ? (
              <span className="flex items-center gap-1.5 text-sm text-amber-400"><AlertCircle className="h-4 w-4" />{error}</span>
            ) : results ? (
              <div className="space-y-1">
                <span className="block text-sm text-roadcall-muted">
                  <span className="text-white font-semibold">{results.total.toLocaleString()}</span> providers found
                  {state && ` in ${state}`}{city && !mapAreaSummary && `, ${city}`}
                </span>
                {mapAreaSummary ? <span className="block text-xs font-semibold text-roadcall-cyan">{mapAreaSummary}</span> : null}
              </div>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            {results && results.mechanics.length > 0 && (
              <div className="inline-flex rounded-full border border-roadcall-cyan/15 bg-roadcall-panel/50 p-1">
                <button
                  type="button"
                  onClick={() => setView("map")}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition ${view === "map" ? "bg-roadcall-cyan text-slate-950" : "text-roadcall-silver hover:text-white"}`}
                >
                  <MapIcon className="h-3.5 w-3.5" /> Map View
                </button>
                <button
                  type="button"
                  onClick={() => setView("cards")}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition ${view === "cards" ? "bg-roadcall-cyan text-slate-950" : "text-roadcall-silver hover:text-white"}`}
                >
                  <LayoutGrid className="h-3.5 w-3.5" /> Card View
                </button>
                <button
                  type="button"
                  onClick={() => setView("list")}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition ${view === "list" ? "bg-roadcall-cyan text-slate-950" : "text-roadcall-silver hover:text-white"}`}
                >
                  <Rows3 className="h-3.5 w-3.5" /> List View
                </button>
              </div>
            )}
            <a
              href={telHref(HELP_PHONE)}
              className="hidden sm:flex items-center gap-2 bg-roadcall-orange/10 border border-roadcall-orange/30 hover:bg-roadcall-orange/20 text-roadcall-orange text-xs font-semibold px-4 py-2 rounded-full transition-all"
            >
              <Zap className="h-3.5 w-3.5" /> Let AI dispatch for you
            </a>
          </div>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30 h-48 animate-pulse" />
            ))}
          </div>
        ) : results && results.mechanics.length > 0 && view === "map" ? (
          <div className={mapShellClass}>
            {!isFullscreenMap ? <div className="mb-3">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-roadcall-cyan">{premiumModeLabel} map workspace</p>
                <p className="mt-1 text-sm text-roadcall-muted">
                  Advanced map modes are open for this session. Use the controls to focus, expand, or hide panels.
                </p>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto] lg:items-start">
                <PremiumMapModeControls mode={premiumMapMode} onModeChange={setPremiumMapMode} />
                <button
                  type="button"
                  onClick={() => setIntakeOpen(true)}
                  className="inline-flex items-center justify-center rounded-2xl border border-red-400/35 bg-red-400/15 px-5 py-4 text-sm font-black text-red-100 shadow-xl shadow-red-950/20 hover:bg-red-400/20"
                >
                  <Zap className="mr-2 h-4 w-4" /> Emergency Breakdown
                </button>
              </div>
            </div> : null}
            <div className={mapGridClass}>
              <SearchResultsMap
                mechanics={results.mechanics}
                onSearchArea={searchMapArea}
                searchingArea={searchingArea}
                className={mapHeightClass}
                layoutKey={`${mapWorkspaceMode}-${mapSidePanelOpen}`}
                premiumMode={premiumMapMode}
                workspaceControls={(
                  <div className="flex items-center gap-2">
                    {isFullscreenMap ? <FullscreenMapModeControls mode={premiumMapMode} onModeChange={setPremiumMapMode} /> : null}
                    <MapWorkspaceControls
                      mode={mapWorkspaceMode}
                      sidePanelOpen={mapSidePanelOpen}
                      onToggleSidePanel={() => setMapSidePanelOpen((open) => !open)}
                      onModeChange={(mode) => {
                        setMapWorkspaceMode(mode);
                        if (mode === "fullscreen") setMapSidePanelOpen(false);
                      }}
                    />
                  </div>
                )}
              />
              {showMapSidePanel ? (
                <div className="max-h-[520px] space-y-4 overflow-y-auto pr-1">
                  <div className="rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/40 p-4">
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-roadcall-muted">Visible cities</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {cityGroups.slice(0, 8).map((group) => (
                        <span key={group.label} className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-bold text-roadcall-silver">
                          {group.label} · {group.providers.length}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-4">
                    {cityGroups.map((group) => <CityMechanicGroup key={group.label} label={group.label} providers={group.providers} onClaim={setClaimTarget} onViewMap={handleViewMap} />)}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ) : results && results.mechanics.length > 0 && view === "list" ? (
          <MechanicListView mechanics={results.mechanics} onClaim={setClaimTarget} onViewMap={handleViewMap} />
        ) : results && results.mechanics.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {results.mechanics.map((m) => <MechanicCard key={m.id} m={m} onClaim={setClaimTarget} onViewMap={handleViewMap} />)}
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
              onClick={() => doSearch(false, page - 1)}
              className="px-4 py-2 rounded-lg border border-roadcall-cyan/15 bg-roadcall-panel/40 text-sm text-roadcall-silver disabled:opacity-40 hover:border-roadcall-cyan/35 hover:text-white transition-all"
            >
              ← Prev
            </button>
            <span className="text-sm text-roadcall-muted">Page {page} of {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => doSearch(false, page + 1)}
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
      {claimStatus ? (
        <div className="fixed bottom-4 left-1/2 z-50 w-[min(520px,calc(100%-2rem))] -translate-x-1/2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-center text-sm font-bold text-emerald-200 shadow-2xl backdrop-blur">
          {claimStatus}
          <button type="button" onClick={() => setClaimStatus(null)} className="ml-3 text-emerald-100/80 hover:text-white">Dismiss</button>
        </div>
      ) : null}
      {claimTarget ? <ClaimUpdateModal mechanic={claimTarget} onClose={() => setClaimTarget(null)} onSubmitted={setClaimStatus} /> : null}
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
