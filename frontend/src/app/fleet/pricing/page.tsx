"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Lock,
  Map,
  RadioTower,
  Route,
  ShieldCheck,
  Sparkles,
  Truck,
  Zap,
} from "lucide-react";
import { motion } from "framer-motion";
import { FLEET_MEMBERSHIP_PLANS } from "@/lib/fleet-memberships";

const intelligenceLayers = [
  "Live provider clustering",
  "AI dispatch zones",
  "Roadside heatmaps",
  "Emergency indicators",
  "Provider availability",
  "Route-aware recommendations",
  "Low coverage alerts",
  "Fleet breakdown visualization",
];

const premiumBadges = [
  "AI Verified",
  "Fleet Preferred",
  "Fastest Response",
  "Emergency Ready",
  "Heavy Duty Expert",
  "Dispatch Priority",
  "24/7 Available",
];

const dispatchSteps = [
  "GPS captured",
  "Truck profile loaded",
  "Issue triaged",
  "Providers ranked",
  "ETA compared",
  "Live tracking opened",
];

export default function FleetPricingPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#02050c] text-white">
      <section className="relative px-4 pb-16 pt-20 sm:pt-24">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(59,130,246,0.28),transparent_32%),radial-gradient(circle_at_80%_0%,rgba(20,216,255,0.18),transparent_30%),linear-gradient(180deg,rgba(2,5,12,0),#02050c_78%)]" />
        <div className="relative mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-300/25 bg-blue-300/10 px-4 py-1.5 text-sm font-semibold text-blue-100">
              <Sparkles className="h-4 w-4 text-cyan-300" /> Roadcall Driver Pro + Fleet Operations
            </div>
            <h1 className="mt-6 max-w-4xl text-5xl font-black leading-[0.95] tracking-tight md:text-7xl">
              AI roadside operations for drivers and fleets.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              Not a trucking directory. Roadcall is the roadside intelligence layer that captures emergencies, ranks providers, opens live dispatch tracking, and gives fleets operational visibility when downtime is burning money.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/mechanic/checkout?plan=driver_pro" className="inline-flex items-center justify-center rounded-xl bg-cyan-300 px-6 py-3 font-black text-slate-950 hover:brightness-110">
                Start Driver Pro <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link href="/fleet/dashboard?demo=1" className="inline-flex items-center justify-center rounded-xl border border-white/15 bg-white/5 px-6 py-3 font-bold text-white hover:bg-white/10">
                Preview operations console
              </Link>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5, delay: 0.08 }} className="rounded-[2rem] border border-blue-300/20 bg-slate-950/75 p-5 shadow-2xl shadow-blue-500/10">
            <div className="rounded-[1.5rem] border border-white/10 bg-[#07101f] p-4">
              <div className="mb-4 flex items-center justify-between text-xs font-bold uppercase tracking-[0.2em] text-blue-200">
                <span>AI Roadside Operations Center</span>
                <span className="text-emerald-300">Live</span>
              </div>
              <div className="relative h-80 overflow-hidden rounded-2xl border border-blue-300/10 bg-[linear-gradient(135deg,#06101e,#0b1d32)]">
                <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(125,211,252,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(125,211,252,0.12)_1px,transparent_1px)] [background-size:34px_34px]" />
                <div className="absolute left-[18%] top-[22%] h-24 w-24 rounded-full border border-cyan-300/40 bg-cyan-300/10" />
                <div className="absolute right-[16%] top-[35%] h-32 w-32 rounded-full border border-blue-300/30 bg-blue-300/10" />
                <div className="absolute bottom-[18%] left-[42%] h-20 w-20 rounded-full border border-emerald-300/35 bg-emerald-300/10" />
                {["I-75", "ATL", "ETA 28", "LOW COVERAGE", "24/7"].map((label, index) => (
                  <div key={label} className="absolute rounded-full border border-white/15 bg-black/55 px-3 py-1 text-xs font-bold text-cyan-100" style={{ left: `${14 + index * 15}%`, top: `${18 + (index % 3) * 22}%` }}>
                    {label}
                  </div>
                ))}
                <div className="absolute bottom-4 left-4 right-4 rounded-2xl border border-white/10 bg-black/60 p-4 backdrop-blur">
                  <div className="flex items-center gap-2 text-sm font-bold text-white"><AlertTriangle className="h-4 w-4 text-orange-300" /> Emergency Breakdown: Unit 441</div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-slate-300">
                    <span>Provider notified</span><span>ETA 28 min</span><span>Priority dispatch</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="px-4 py-10">
        <div className="mx-auto grid max-w-7xl gap-4 md:grid-cols-2 xl:grid-cols-4">
          {FLEET_MEMBERSHIP_PLANS.map((plan) => (
            <article key={plan.id} className={`flex flex-col rounded-[1.5rem] border p-6 ${plan.highlighted ? "border-cyan-300/50 bg-cyan-300/10" : "border-white/10 bg-white/[0.035]"}`}>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-200">{plan.positioning}</p>
              <h2 className="mt-3 text-2xl font-black">{plan.name}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">{plan.range}</p>
              <p className="mt-5 text-4xl font-black">{plan.price}<span className="text-sm font-semibold text-slate-400">{plan.period}</span></p>
              <ul className="mt-6 flex-1 space-y-2 text-sm text-slate-300">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-300" /> {feature}</li>
                ))}
              </ul>
              <Link href={plan.href} className={`mt-7 inline-flex items-center justify-center rounded-xl bg-gradient-to-r ${plan.accent} px-5 py-3 font-black text-slate-950 hover:brightness-110`}>
                {plan.cta} <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="px-4 py-16">
        <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-3">
          <Panel icon={Map} title="Advanced Map Intelligence" items={intelligenceLayers} />
          <Panel icon={Zap} title="AI Provider Ranking" items={premiumBadges} />
          <Panel icon={RadioTower} title="One-Tap AI Dispatch" items={dispatchSteps} />
        </div>
      </section>

      <section className="border-y border-blue-300/10 bg-blue-300/[0.04] px-4 py-16">
        <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.22em] text-cyan-200">Premium access model</p>
            <h2 className="mt-3 text-4xl font-black">Locked intelligence creates the upgrade moment.</h2>
            <p className="mt-4 text-slate-300">
              Non-paid users can see limited providers and basic map context. Paid members unlock dispatch priority, verified responders, ETA intelligence, route-aware insights, analytics, and fleet operations views.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              [Lock, "Locked analytics overlays"],
              [ShieldCheck, "Validated premium access"],
              [Route, "Route-aware provider intelligence"],
              [Activity, "Live dispatch and fleet event timelines"],
              [Truck, "Saved truck and fleet profiles"],
              [AlertTriangle, "Emergency Breakdown workflow"],
            ].map(([Icon, label]) => (
              <div key={label as string} className="rounded-2xl border border-white/10 bg-black/30 p-4 text-sm font-semibold text-slate-200">
                <Icon className="mb-3 h-5 w-5 text-cyan-300" /> {label as string}
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function Panel({ icon: Icon, title, items }: { icon: typeof Map; title: string; items: string[] }) {
  return (
    <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/70 p-6">
      <Icon className="h-6 w-6 text-cyan-300" />
      <h2 className="mt-4 text-xl font-black text-white">{title}</h2>
      <div className="mt-5 grid gap-2">
        {items.map((item) => (
          <div key={item} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-300">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
