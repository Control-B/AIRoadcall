"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Loader2,
  MapPin,
  PhoneCall,
  PlayCircle,
  Truck,
  Users,
  Wrench,
} from "lucide-react";

type Incident = {
  id: string;
  status: "open" | "dispatched" | "on_site" | "resolved";
  driver: string;
  vehicle: string;
  issue: string;
  location: string;
  opened_minutes_ago: number;
  vendor: string | null;
  eta_minutes: number | null;
};

type FleetDashboard = {
  company_name: string;
  data_mode: "Hosted" | "Private Tenant" | "Hybrid";
  ai_agent: { activation_status: string; agent_name: string; calls_handled_today: number };
  fleet: { vehicles: number; trailers: number; drivers: number; active_incidents: number };
  coverage: { approved_vendors: number; states_covered: number; avg_response_minutes: number };
  incidents: Incident[];
};

const DEMO_DASHBOARD: FleetDashboard = {
  company_name: "Acme Trucking LLC (Demo)",
  data_mode: "Hosted",
  ai_agent: {
    activation_status: "active",
    agent_name: "Acme Fleet Dispatcher",
    calls_handled_today: 11,
  },
  fleet: { vehicles: 62, trailers: 87, drivers: 74, active_incidents: 3 },
  coverage: { approved_vendors: 412, states_covered: 31, avg_response_minutes: 47 },
  incidents: [
    {
      id: "RC-104821",
      status: "dispatched",
      driver: "Marcus T.",
      vehicle: "Truck #441 (Freightliner Cascadia)",
      issue: "DPF derate, limp mode",
      location: "I-10 MM 187, Beaumont TX",
      opened_minutes_ago: 28,
      vendor: "Lone Star Diesel (4.8 \u2605)",
      eta_minutes: 35,
    },
    {
      id: "RC-104819",
      status: "on_site",
      driver: "Lisa P.",
      vehicle: "Truck #207 (Peterbilt 579)",
      issue: "Steer tire blowout",
      location: "I-95 N, exit 67, Savannah GA",
      opened_minutes_ago: 71,
      vendor: "Coastal Tire Service",
      eta_minutes: 0,
    },
    {
      id: "RC-104815",
      status: "open",
      driver: "Devon R.",
      vehicle: "Trailer T-318 (53' dry van)",
      issue: "Air leak, brake chamber",
      location: "TA Atlanta South, Jackson GA",
      opened_minutes_ago: 6,
      vendor: null,
      eta_minutes: null,
    },
  ],
};

function statusPill(status: Incident["status"]) {
  const styles: Record<Incident["status"], string> = {
    open: "bg-amber-400/20 text-amber-200 border-amber-400/30",
    dispatched: "bg-blue-400/20 text-blue-200 border-blue-400/30",
    on_site: "bg-emerald-400/20 text-emerald-200 border-emerald-400/30",
    resolved: "bg-slate-400/20 text-slate-200 border-slate-400/30",
  };
  const labels: Record<Incident["status"], string> = {
    open: "Open",
    dispatched: "Dispatched",
    on_site: "On site",
    resolved: "Resolved",
  };
  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

function FleetDashboardContent() {
  const params = useSearchParams();
  const isDemo = params.get("demo") === "1";
  const [dashboard] = useState<FleetDashboard | null>(isDemo ? DEMO_DASHBOARD : null);
  const [toast, setToast] = useState<string | null>(null);

  const greeting = useMemo(() => {
    const now = new Date();
    const hour = now.getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }, []);

  function demoOnly(action: string) {
    setToast(`Demo mode: ${action} is disabled. Start fleet onboarding to set up your real fleet.`);
    setTimeout(() => setToast(null), 4000);
  }

  if (!dashboard) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#02050c] px-4 text-white">
        <div className="max-w-md rounded-2xl border border-amber-400/20 bg-amber-400/10 p-6 text-amber-100">
          <h2 className="text-lg font-bold">Fleet console isn&apos;t live yet</h2>
          <p className="mt-2 text-sm">
            The live fleet console is in private beta. In the meantime, take the
            <Link href="/fleet/dashboard?demo=1" className="underline hover:text-amber-50"> demo for a spin </Link>
            or start
            <Link href="/fleet/onboarding" className="underline hover:text-amber-50"> fleet onboarding</Link>.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#02050c] px-4 py-20 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-300">Fleet AI Console</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight">{dashboard.company_name}</h1>
            <p className="mt-2 text-sm text-slate-400">{greeting}, dispatcher. Data mode: {dashboard.data_mode}.</p>
          </div>
          <button
            onClick={() => demoOnly("Manage billing")}
            className="rounded-full border border-white/15 px-5 py-3 text-sm font-bold text-slate-200 hover:bg-white/10"
          >
            Manage account
          </button>
        </div>

        {isDemo && (
          <div className="mt-6 flex flex-col gap-3 rounded-2xl border border-roadcall-orange/30 bg-roadcall-orange/10 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3 text-sm text-orange-100">
              <PlayCircle className="h-5 w-5 text-roadcall-orange" />
              <span>You&apos;re in <strong>demo mode</strong>. Data is sample; nothing here is dispatching real vendors.</span>
            </div>
            <Link
              href="/fleet/onboarding"
              className="inline-flex items-center justify-center rounded-full bg-roadcall-orange px-5 py-2 text-sm font-bold text-slate-950 hover:brightness-110"
            >
              Start fleet onboarding
            </Link>
          </div>
        )}

        {toast && (
          <div className="mt-4 rounded-xl border border-blue-400/30 bg-blue-400/10 px-4 py-3 text-sm text-blue-100">
            {toast}
          </div>
        )}

        {/* Top stat row */}
        <section className="mt-8 grid gap-4 md:grid-cols-4">
          <StatCard icon={Truck} label="Vehicles" value={dashboard.fleet.vehicles} secondary={`${dashboard.fleet.trailers} trailers`} />
          <StatCard icon={Users} label="Drivers on roster" value={dashboard.fleet.drivers} secondary={null} />
          <StatCard icon={AlertTriangle} label="Active incidents" value={dashboard.fleet.active_incidents} secondary="Live now" highlight />
          <StatCard icon={Bot} label="AI calls today" value={dashboard.ai_agent.calls_handled_today} secondary={dashboard.ai_agent.agent_name} />
        </section>

        {/* Main grid */}
        <section className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">Active incidents</h2>
              <button
                onClick={() => demoOnly("Open the live incident feed")}
                className="rounded-full bg-white/10 px-4 py-2 text-xs font-bold text-white hover:bg-white/15"
              >
                Open live feed
              </button>
            </div>
            <div className="mt-5 space-y-4">
              {dashboard.incidents.map((incident) => (
                <article
                  key={incident.id}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-slate-400">{incident.id}</span>
                      {statusPill(incident.status)}
                    </div>
                    <span className="text-xs text-slate-400">
                      Opened {incident.opened_minutes_ago} min ago
                    </span>
                  </div>
                  <p className="mt-3 text-lg font-bold">{incident.issue}</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2 text-sm text-slate-300">
                    <div className="flex items-center gap-2">
                      <Truck className="h-4 w-4 text-blue-300" /> {incident.vehicle}
                    </div>
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-blue-300" /> {incident.driver}
                    </div>
                    <div className="flex items-center gap-2 sm:col-span-2">
                      <MapPin className="h-4 w-4 text-blue-300" /> {incident.location}
                    </div>
                    {incident.vendor ? (
                      <div className="flex items-center gap-2 sm:col-span-2">
                        <Wrench className="h-4 w-4 text-emerald-300" /> {incident.vendor}
                        {incident.eta_minutes !== null && (
                          <span className="text-emerald-200">
                            — {incident.eta_minutes === 0 ? "on site" : `ETA ${incident.eta_minutes} min`}
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 sm:col-span-2 text-amber-200">
                        <Wrench className="h-4 w-4" /> Searching approved vendors…
                      </div>
                    )}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      onClick={() => demoOnly(`Call ${incident.driver}`)}
                      className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-xs font-bold text-white hover:bg-white/15"
                    >
                      <PhoneCall className="h-3.5 w-3.5" /> Call driver
                    </button>
                    <button
                      onClick={() => demoOnly(`Reassign ${incident.id}`)}
                      className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-xs font-bold text-white hover:bg-white/15"
                    >
                      Reassign vendor
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-orange-300" />
                <h2 className="text-xl font-bold">AI Dispatcher</h2>
              </div>
              <p className="mt-4 text-3xl font-black">{dashboard.ai_agent.agent_name}</p>
              <p className="mt-1 text-sm capitalize text-emerald-300">
                Status: {dashboard.ai_agent.activation_status}
              </p>
              <p className="mt-4 text-sm text-slate-300">
                Handles inbound driver hotline, qualifies the breakdown, geo-locates
                the truck, and dispatches the closest approved vendor automatically.
              </p>
              <button
                onClick={() => demoOnly("Edit agent prompt")}
                className="mt-5 inline-flex items-center gap-2 rounded-full bg-orange-400 px-5 py-3 text-sm font-bold text-slate-950"
              >
                Edit agent prompt
              </button>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-xl font-bold">Vendor coverage</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Approved vendors</dt>
                  <dd className="font-bold">{dashboard.coverage.approved_vendors}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">States covered</dt>
                  <dd className="font-bold">{dashboard.coverage.states_covered}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Avg response time</dt>
                  <dd className="font-bold">{dashboard.coverage.avg_response_minutes} min</dd>
                </div>
              </dl>
              <button
                onClick={() => demoOnly("Manage vendor network")}
                className="mt-5 inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-bold text-slate-200 hover:bg-white/10"
              >
                Manage vendor network
              </button>
            </div>

            <div className="rounded-[2rem] border border-emerald-400/20 bg-emerald-400/10 p-6">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-300" />
                <h2 className="text-lg font-bold text-emerald-100">Activation steps</h2>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-emerald-100">
                {["Onboarding submitted", "Fleet data imported", "Approved vendor network mapped", "Driver hotline live", "AI dispatcher answering"].map((step) => (
                  <li key={step} className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4" /> {step}
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  secondary,
  highlight,
}: {
  icon: typeof Truck;
  label: string;
  value: number | string;
  secondary: string | null;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border p-5 ${
        highlight ? "border-amber-400/30 bg-amber-400/10" : "border-white/10 bg-white/[0.04]"
      }`}
    >
      <Icon className={`h-5 w-5 ${highlight ? "text-amber-300" : "text-blue-300"}`} />
      <p className="mt-3 text-3xl font-black">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
      {secondary && <p className="mt-1 text-xs text-slate-500">{secondary}</p>}
    </div>
  );
}

export default function FleetDashboardPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center bg-[#02050c] text-white">
          <Loader2 className="h-8 w-8 animate-spin text-blue-300" />
        </main>
      }
    >
      <FleetDashboardContent />
    </Suspense>
  );
}
