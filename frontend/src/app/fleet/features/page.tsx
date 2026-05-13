"use client";

import Link from "next/link";
import {
  Phone,
  MapPin,
  Wrench,
  Shield,
  Truck,
  CheckCircle2,
  ArrowRight,
  Radio,
  GitBranch,
  BarChart3,
  AlertTriangle,
  Lock,
  Users,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

const features = [
  {
    icon: Phone,
    title: "AI Roadside Intake",
    description:
      "Driver calls from the side of the road. Sandy answers instantly, captures incident type, vehicle info, fault codes, and loaded status — all in under 90 seconds. 24/7, no dispatcher needed.",
    accent: "from-blue-500 to-cyan-500",
  },
  {
    icon: MapPin,
    title: "GPS & Tracker Integration",
    description:
      "A signed one-time SMS link is sent to the driver mid-call. One tap shares exact GPS from their phone — no app download, no account. Connects to Samsara, Motive, and Geotab for automatic location pull.",
    accent: "from-cyan-500 to-teal-500",
  },
  {
    icon: Wrench,
    title: "Mechanic Matching Engine",
    description:
      "Scores 35,000+ roadside vendors in real time by distance, vehicle class (Class 8, reefer, trailer), service specialty, rating, and live availability. Best match auto-dispatched with ETA confirmation.",
    accent: "from-teal-500 to-green-500",
  },
  {
    icon: Radio,
    title: "Dispatch Visibility",
    description:
      "Every active incident streams to your ops board in real time — driver GPS pin, mechanic ETA countdown, status transitions, and escalation flags. No more calling around to find out what's happening.",
    accent: "from-green-500 to-emerald-500",
  },
  {
    icon: AlertTriangle,
    title: "Incident History",
    description:
      "Every breakdown becomes a complete audit record: intake timestamp, location capture, dispatch decision, vendor assigned, ETA, resolution time, and cost. Full incident timeline, always retrievable.",
    accent: "from-emerald-500 to-blue-500",
  },
  {
    icon: GitBranch,
    title: "Fleet System Integrations",
    description:
      "Connect your existing telematics, ELD, and maintenance systems. Samsara, Verizon Connect, Motive, Geotab, Fleetio, and custom integrations via open API. Data flows to Roadcall — not the other way around.",
    accent: "from-blue-500 to-indigo-500",
  },
  {
    icon: Users,
    title: "Driver & Vehicle Database",
    description:
      "Maintain records for all drivers, vehicles, VINs, and unit numbers. Sandy can look up vehicle class and assignment during the call — no dispatcher needed to pull records manually.",
    accent: "from-indigo-500 to-purple-500",
  },
  {
    icon: BarChart3,
    title: "Incident Analytics",
    description:
      "Track breakdown frequency, average resolution time, cost per incident, mechanic performance scores, and driver breakdown patterns across your fleet. Data you can actually act on.",
    accent: "from-purple-500 to-blue-500",
  },
  {
    icon: Lock,
    title: "Enterprise Security",
    description:
      "Full tenant isolation — every query scoped by organization_id. RBAC roles, one-time signed location tokens, encrypted credentials, and audit logs on every state change. Private tenant and hybrid in-house modes available.",
    accent: "from-blue-600 to-slate-600",
  },
];

const workflow = [
  {
    step: "01",
    title: "Driver calls in",
    description:
      "Stranded driver dials your fleet hotline. Sandy picks up instantly — captures truck type, trailer, loaded status, fault codes, and incident description.",
    accent: "from-blue-500 to-cyan-500",
  },
  {
    step: "02",
    title: "Location captured",
    description:
      "Sandy sends a one-time signed SMS link mid-call. Driver taps once — exact GPS shared. Or Sandy collects highway, mile marker, and nearest exit verbally as fallback.",
    accent: "from-cyan-500 to-teal-500",
  },
  {
    step: "03",
    title: "Mechanic matched & dispatched",
    description:
      "Our engine scores nearby vendors by distance, class, specialty, and availability. Best match is dispatched automatically with ETA. Driver gets a confirmation SMS.",
    accent: "from-teal-500 to-green-500",
  },
  {
    step: "04",
    title: "Ops team sees it all",
    description:
      "Incident board updates in real time — driver location, mechanic ETA, status, and full audit trail. Escalate, reassign, or close from one screen.",
    accent: "from-green-500 to-blue-500",
  },
];

const differentiators = [
  "Works on any phone — no app download required for drivers",
  "Class 8 and specialty vehicle matching (reefer, flatbed, tanker, lowboy)",
  "Fault code capture routed to correct specialty mechanic automatically",
  "Loaded status affects dispatch priority — Sandy knows to ask",
  "No third-party CRM — your fleet data never leaves your environment",
  "Private tenant mode for enterprise: dedicated DB, isolated credentials",
  "Open API for custom integrations with your existing dispatch stack",
  "Audit logs on every incident change for DOT and insurance compliance",
];

export default function FleetFeaturesPage() {
  return (
    <PageLayout>
      {/* Hero */}
      <section className="relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(59,130,246,0.15),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_40%_40%_at_90%_60%,rgba(20,184,166,0.08),transparent_50%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-5 py-2 mb-8">
              <Truck className="h-4 w-4 text-blue-400" />
              <span className="text-sm text-blue-300 font-medium">Roadcall Fleet — Feature Overview</span>
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
              Every feature your fleet
              <span className="block bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                ops team actually needs
              </span>
            </h1>
            <p className="text-xl text-roadcall-silver/85 max-w-2xl mx-auto mb-10">
              AI-powered roadside intake, GPS capture, mechanic matching, and full incident
              visibility — built for carriers who can&apos;t afford downtime or data leaks.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild size="lg" className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white px-8">
                <Link href="/fleet/onboarding">Book a Fleet Demo</Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="border-slate-600 text-roadcall-silver hover:bg-roadcall-panel">
                <a href={telHref(HELP_PHONE)}>Call {HELP_PHONE}</a>
              </Button>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* Feature grid */}
      <section className="py-20 bg-roadcall-ink/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            title="Built for real fleet operations"
            description="Not a generic help desk. Every feature maps to a real breakdown scenario your drivers face."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
            {features.map((f) => (
              <GlassCard key={f.title} className="p-6">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${f.accent} flex items-center justify-center mb-4`}>
                  <f.icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">{f.title}</h3>
                <p className="text-roadcall-muted text-sm leading-relaxed">{f.description}</p>
              </GlassCard>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            title="How a breakdown gets resolved"
            description="From first call to mechanic on-site — fully automated, fully audited."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
            {workflow.map((w, i) => (
              <div key={w.step} className="relative">
                {i < workflow.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-slate-600 to-transparent z-0" />
                )}
                <GlassCard className="p-6 relative z-10">
                  <div className={`text-3xl font-black bg-gradient-to-r ${w.accent} bg-clip-text text-transparent mb-4`}>
                    {w.step}
                  </div>
                  <h3 className="text-white font-semibold mb-2">{w.title}</h3>
                  <p className="text-roadcall-muted text-sm leading-relaxed">{w.description}</p>
                </GlassCard>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Differentiators */}
      <section className="py-20 bg-roadcall-ink/50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeading
            title="Why fleets choose Roadcall over generic tools"
            description="Built specifically for commercial vehicles and roadside ops — not adapted from a consumer product."
          />
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {differentiators.map((d) => (
              <div key={d} className="flex items-start gap-3 bg-roadcall-panel/40 border border-slate-700/50 rounded-xl p-4">
                <CheckCircle2 className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <span className="text-roadcall-silver/85 text-sm">{d}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Data ownership callout */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <div className="rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 border border-blue-500/20 p-10 text-center">
            <Shield className="w-12 h-12 text-blue-400 mx-auto mb-5" />
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Your data stays yours
            </h2>
            <p className="text-roadcall-silver/85 text-lg mb-6 max-w-2xl mx-auto">
              Fleet incident data — driver locations, breakdown history, vendor relationships —
              never flows into a shared third-party CRM. Private tenant and hybrid in-house modes
              give you full database isolation and credential ownership.
            </p>
            <div className="flex flex-wrap gap-3 justify-center mb-8">
              {["Tenant Isolation", "RBAC Roles", "Audit Logs", "Encrypted Credentials", "One-Time Location Tokens"].map((tag) => (
                <span key={tag} className="bg-blue-500/10 border border-blue-500/20 text-blue-300 text-sm px-3 py-1 rounded-full">
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild size="lg" className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white px-8">
                <Link href="/fleet/onboarding">
                  Book a Fleet Demo <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="border-slate-600 text-roadcall-silver hover:bg-roadcall-panel">
                <Link href="/fleet/security">Security Details</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Secondary CTA */}
      <section className="py-16 border-t border-slate-800">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <Clock className="w-8 h-8 text-blue-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-3">
            Average roadside intake: under 90 seconds
          </h3>
          <p className="text-roadcall-muted mb-6">
            From first ring to mechanic dispatched — without a single human dispatcher involved.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white">
              <Link href="/fleet/onboarding">Start Fleet Setup</Link>
            </Button>
            <Button asChild variant="ghost" size="lg" className="text-roadcall-silver/85 hover:text-white">
              <Link href="/fleet/pricing">
                See Pricing <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
