"use client";

import Link from "next/link";
import Image from "next/image";
import {
  Phone,
  MapPin,
  Wrench,
  Shield,
  Truck,
  CheckCircle2,
  ArrowRight,
  Zap,
  Star,
  Users,
  BarChart3,
  Lock,
  GitBranch,
  AlertTriangle,
  Radio,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";
import roadcallSupportVideo from "@/assets/videos/RoadcallSupport.mp4";
import { mediaUrl } from "@/lib/media";

const features = [
  { icon: Phone, title: "AI Roadside Intake", description: "Driver calls from the side of the road. Sandy collects incident type, vehicle, location description, and driver info in under 90 seconds." },
  { icon: MapPin, title: "GPS Location Capture", description: "A one-time signed link is texted to the driver. One tap shares exact GPS coordinates — no app, no account needed." },
  { icon: Wrench, title: "Mechanic Matching Engine", description: "Scores 35,000+ vendors by distance, service type, vehicle class, rating, and availability. Best match dispatched automatically." },
  { icon: AlertTriangle, title: "Incident Management", description: "Every breakdown becomes a tracked incident with full timeline: intake, location, dispatch, ETA, resolution, and audit trail." },
  { icon: Radio, title: "Dispatch Status Board", description: "Your team sees every active incident in real time — driver GPS, mechanic ETA, status updates, and escalations." },
  { icon: Users, title: "Driver & Vehicle Database", description: "Maintain a database of your drivers, vehicles, VINs, and unit numbers. Sandy can look up vehicle info during the call." },
  { icon: GitBranch, title: "Fleet Tracker Integrations", description: "Connect your existing telematics and fleet systems. Pull live GPS and alert data automatically." },
  { icon: BarChart3, title: "Incident Analytics", description: "Track breakdown frequency, resolution time, cost per incident, mechanic performance, and driver patterns over time." },
  { icon: Lock, title: "Private Data Mode", description: "Your fleet incident data stays inside Roadcall's protected workflow. Full tenant isolation, RBAC, and audit logs for compliance." },
  { icon: Shield, title: "Enterprise Security", description: "Role-based access control, encrypted credentials, one-time location tokens, organization scoping on every API call." },
];

const howItWorks = [
  { step: "01", title: "Driver Calls In", description: "Stranded driver calls your fleet hotline. Sandy answers instantly and begins incident intake.", accent: "from-blue-500 to-cyan-500" },
  { step: "02", title: "Location Captured", description: "Sandy sends a secure one-time SMS link. Driver taps once to share exact GPS.", accent: "from-cyan-500 to-emerald-500" },
  { step: "03", title: "Mechanic Matched", description: "Our engine scores nearby vendors and dispatches the best available match automatically.", accent: "from-emerald-500 to-green-500" },
  { step: "04", title: "Your Team Sees It All", description: "The incident board updates in real time. ETA, status, and audit trail all logged.", accent: "from-green-500 to-blue-500" },
];

const securityPoints = [
  "All data scoped by organization_id — never cross-contaminated",
  "One-time signed location tokens with configurable expiration",
  "RBAC roles: fleet_manager, dispatcher, driver_support, viewer",
  "Audit logs on every incident change, dispatch decision, and location capture",
  "Credentials encrypted at rest — no API keys in the frontend",
  "Private tenant isolation for enterprise deployments",
];

export default function FleetPage() {
  return (
    <PageLayout>
      {/* Hero */}
      <section className="relative min-h-[85vh] flex flex-col justify-end overflow-hidden">
        <video
          className="absolute inset-0 h-full w-full object-cover object-center"
          src={mediaUrl("videos/RoadcallSupport.mp4", roadcallSupportVideo)}
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          aria-hidden="true"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-roadcall-void/70 via-roadcall-void/35 to-roadcall-void z-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-roadcall-void/70 via-roadcall-void/25 to-roadcall-void/55 z-10" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(20,216,255,0.24),transparent_70%)] z-10" />
        <div className="relative z-20 max-w-7xl mx-auto px-4 sm:px-6 w-full pb-16 pt-32 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-roadcall-panel/45 border border-roadcall-cyan/10 backdrop-blur-sm rounded-full px-4 py-1.5 mb-8">
              <Zap className="h-3.5 w-3.5 text-blue-400" />
              <span className="text-xs font-medium text-roadcall-silver/85 tracking-wide">Roadcall Fleet</span>
            </div>
          </FadeIn>
          <FadeIn delay={0.1}>
            <h1 className="text-6xl sm:text-7xl md:text-8xl font-black tracking-tight leading-[0.95] mb-6">
              <span className="block text-white">AI Roadside Support</span>
              <span className="block bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">Built for Fleets</span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.2}>
            <p className="text-lg md:text-xl text-roadcall-silver/85 max-w-2xl mx-auto mb-12 leading-relaxed">
              Every driver breakdown automated — from AI intake to mechanic dispatch. Without forcing your fleet&apos;s sensitive data into an outside CRM.
            </p>
          </FadeIn>
          <FadeIn delay={0.3}>
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <Link href="/fleet/onboarding">
                <Button size="lg" className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-semibold rounded-xl px-8 shadow-xl shadow-blue-600/20">
                  Book Fleet Demo <ArrowRight className="h-5 w-5 ml-2" />
                </Button>
              </Link>
              <a href={telHref(HELP_PHONE)}>
                <Button size="lg" variant="outline" className="border-roadcall-cyan/20 bg-roadcall-panel/45 backdrop-blur-sm text-white hover:bg-roadcall-panel/60 rounded-xl px-8">
                  <Phone className="h-5 w-5 mr-2" /> Hear Sandy Live
                </Button>
              </a>
            </div>
            <p className="text-sm text-roadcall-muted">No commitment · Enterprise pricing available · White-glove onboarding</p>
          </FadeIn>
        </div>
      </section>

      {/* Social proof strip */}
      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 py-5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-roadcall-muted">
          {["Your data stays controlled", "Private tenant isolation", "35,000+ mechanics nationwide", "Fleet system integrations"].map((t) => (
            <div key={t} className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-400" /><span>{t}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Features grid */}
      <section className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Platform Capabilities"
            title="End-to-end roadside automation"
            description="Roadcall Fleet is built on our own backend. Your incident data, driver records, and dispatch history stay in a fully isolated, RBAC-controlled environment."
          />
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <FadeIn key={f.title} delay={i * 0.05}>
                <GlassCard className="p-6 h-full">
                  <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4">
                    <f.icon className="h-5 w-5 text-blue-400" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{f.description}</p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="The Flow" title="From breakdown to mechanic in 4 steps" />
          <div className="grid md:grid-cols-4 gap-6">
            {howItWorks.map((step, i) => (
              <FadeIn key={step.step} delay={i * 0.1}>
                <div className="text-center">
                  <div className={`h-14 w-14 rounded-2xl bg-gradient-to-br ${step.accent} flex items-center justify-center mx-auto mb-4 shadow-lg`}>
                    <span className="text-lg font-bold text-white">{step.step}</span>
                  </div>
                  <h3 className="font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-sm text-roadcall-muted">{step.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Security section */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <FadeIn direction="left">
              <div className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-4">Security & Data Control</div>
              <h2 className="text-4xl font-bold mb-6 leading-tight">
                Your fleet data is<br />
                <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">yours. Full stop.</span>
              </h2>
              <p className="text-roadcall-muted text-lg mb-8 leading-relaxed">
                Unlike solutions that route incident data through outside CRMs, Roadcall Fleet keeps every driver call, location record, dispatch event, and audit trail in your own isolated environment.
              </p>
              <ul className="space-y-3 mb-8">
                {securityPoints.map((point) => (
                  <li key={point} className="flex items-start gap-3 text-roadcall-silver/85 text-sm">
                    <Shield className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" /> {point}
                  </li>
                ))}
              </ul>
              <Link href="/fleet/security">
                <Button variant="outline" className="border-blue-500/30 text-blue-300 hover:bg-blue-500/10 rounded-full px-6">
                  Read Security Details <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </FadeIn>
            <FadeIn direction="right">
              <div className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 p-8">
                <div className="text-sm font-semibold text-roadcall-silver/85 mb-6">Data Architecture</div>
                {[
                  { label: "Incident Records", owner: "Your DB", color: "bg-blue-500" },
                  { label: "Driver Profiles", owner: "Your DB", color: "bg-blue-500" },
                  { label: "GPS Location Data", owner: "Your DB (one-time tokens)", color: "bg-cyan-500" },
                  { label: "Dispatch History", owner: "Your DB", color: "bg-blue-500" },
                  { label: "Audit Logs", owner: "Your DB", color: "bg-cyan-500" },
                  { label: "AI Call Transcripts", owner: "Your DB", color: "bg-blue-500" },
                  { label: "External CRM Data", owner: "Not required", color: "bg-red-500/50" },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
                    <span className="text-sm text-roadcall-silver/85">{item.label}</span>
                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${item.color}`} />
                      <span className="text-xs text-roadcall-muted">{item.owner}</span>
                    </div>
                  </div>
                ))}
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* Testimonials */}

      {/* Bottom CTA */}
      <section className="py-24 border-t border-roadcall-cyan/10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <h2 className="text-4xl font-bold mb-4">Ready to automate your roadside support?</h2>
            <p className="text-roadcall-muted text-lg mb-8">Let&apos;s walk through a live demo built around your fleet.</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/fleet/onboarding">
                <Button size="lg" className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 rounded-full px-8">
                  Book Fleet Demo <ArrowRight className="h-5 w-5 ml-2" />
                </Button>
              </Link>
              <Link href="/fleet/features">
                <Button size="lg" variant="outline" className="border-white/15 bg-roadcall-panel/45 text-white hover:bg-roadcall-panel/60 rounded-full px-8">
                  See All Features
                </Button>
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>
    </PageLayout>
  );
}
