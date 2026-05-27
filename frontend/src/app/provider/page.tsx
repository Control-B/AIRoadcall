"use client";

import Link from "next/link";
import {
  Wrench,
  Phone,
  Star,
  Globe,
  Users,
  Zap,
  CheckCircle2,
  MapPin,
  BarChart3,
  Shield,
  TrendingUp,
  MessageSquare,
  Building2,
} from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading } from "@/components/motion";
import { supportMailtoHref } from "@/lib/support-email";

const PROVIDER_SIGNUP = supportMailtoHref("Roadcall shop listing request", { request_type: "List my shop free" });
const AI_PHONE_REQUEST = supportMailtoHref("Roadcall AI phone setup request", { request_type: "Configure AI phone for mechanic shop" });
const MAP_BADGE_REQUEST = supportMailtoHref("Roadcall map partner badge request", { request_type: "Map Partner Badge" });
const PARTNER_MAP_DEMO = "/maps?partnerDemo=1&state=FL&city=Tallahassee";

const benefits = [
  {
    icon: Users,
    title: "Reach Stranded Drivers First",
    description: "Thousands of fleet operators and drivers search our platform daily. Your shop gets matched when drivers need your exact services in your area.",
    accent: "text-roadcall-orange",
  },
  {
    icon: Zap,
    title: "AI-Dispatched Leads",
    description: "Our AI dispatcher routes qualified leads directly to you based on service type, location, availability, and verified readiness — no cold calls.",
    accent: "text-cyan-400",
  },
  {
    icon: BarChart3,
    title: "Performance Dashboard",
    description: "Track views, calls, dispatch requests, and close rate. Know exactly how your listing is performing.",
    accent: "text-blue-400",
  },
  {
    icon: Star,
    title: "Verified Readiness",
    description: "Build trust with accurate service areas, specialties, contact details, and operational status after each incident close.",
    accent: "text-amber-400",
  },
  {
    icon: MessageSquare,
    title: "Attach Your Phone Agent",
    description: "Connect your shop number or request a Roadcall number, then configure the AI agent that answers, books, and escalates calls for your business.",
    accent: "text-emerald-400",
  },
  {
    icon: Shield,
    title: "Trusted & Verified Badge",
    description: "Pass our verification process and earn a Trusted Provider badge — the highest trust level shown to fleet dispatchers.",
    accent: "text-purple-400",
  },
];

const howItWorks = [
  { step: "01", title: "Claim or Create Your Profile", description: "Search for your business or add it in minutes. Set services, coverage area, emergency availability, and contact info." },
  { step: "02", title: "Attach Your Phone Number", description: "Forward your existing shop line or request a Roadcall number so the AI agent can answer calls for your business." },
  { step: "03", title: "Configure the AI Agent", description: "Set services, hours, booking rules, escalation contacts, and which calls should become roadside dispatch jobs." },
  { step: "04", title: "Get Verified & Dispatched", description: "After verification, Roadcall can route qualified drivers and fleet jobs to your shop based on service match and location." },
];

export default function ProviderPage() {
  return (
    <PageLayout>
      {/* Hero */}
      <section className="relative min-h-[80vh] flex flex-col justify-center overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-900/20 via-transparent to-blue-900/20 z-0" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-roadcall-void to-transparent z-0" />
        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-roadcall-panel/50 border border-emerald-500/25 backdrop-blur-sm rounded-full px-4 py-1.5 mb-6">
              <Wrench className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-xs font-medium text-roadcall-silver/85 tracking-wide">For Mechanics & Repair Shops — List Free, Get Dispatched</span>
            </div>
          </FadeIn>
          <FadeIn delay={0.1}>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[0.95] mb-6">
              <span className="block text-white">Be the Mechanic</span>
              <span className="block bg-gradient-to-r from-emerald-400 to-cyan-300 bg-clip-text text-transparent">Drivers Find First</span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.2}>
            <p className="text-lg md:text-xl text-roadcall-silver/80 max-w-2xl mx-auto mb-10 leading-relaxed">
              List your shop free, attach your phone number, configure your AI service advisor, and get found by drivers and fleet dispatchers who need your exact services.
            </p>
          </FadeIn>
          <FadeIn delay={0.3}>
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <a href={PROVIDER_SIGNUP}>
                <button className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold text-lg px-10 py-5 rounded-2xl shadow-2xl shadow-blue-900/30 transition-all">
                  <Wrench className="h-5 w-5" /> List My Shop — Free
                </button>
              </a>
              <a href={AI_PHONE_REQUEST}>
                <button className="inline-flex items-center justify-center gap-2 border border-roadcall-cyan/25 bg-roadcall-panel/40 backdrop-blur-sm text-white hover:bg-roadcall-panel/60 font-semibold px-8 py-5 rounded-2xl transition-all">
                  <Phone className="h-5 w-5" /> Configure AI Phone
                </button>
              </a>
            </div>
            <p className="text-sm text-roadcall-muted">No credit card required for free listing · Roadcall profile access · Full profile control</p>
          </FadeIn>
        </div>
      </section>

      {/* Trust strip */}
      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 py-5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-roadcall-muted">
          {["35,000+ providers listed", "All 50 states covered", "Verified daily by our team", "AI-dispatched leads", "No app required for drivers"].map((t) => (
            <div key={t} className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{t}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Paid vendor listing */}
      <section className="border-b border-roadcall-cyan/10 bg-roadcall-panel/10 py-16">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
          <FadeIn>
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-yellow-300/25 bg-yellow-300/10 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-yellow-100">
                <Star className="h-3.5 w-3.5 text-yellow-300" /> Vendor Listing
              </div>
              <h2 className="mt-5 text-3xl font-black leading-tight text-white md:text-5xl">Stand out when drivers zoom into your city.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-roadcall-silver/80 md:text-base">
                Free listings keep your shop searchable. The paid vendor listing adds a Roadcall Partner map treatment: a highlighted pin, hover identity card, selected-provider badge, and a small floating badge only at close city-level zoom so the map stays clean.
              </p>
            </div>
          </FadeIn>
          <FadeIn delay={0.12}>
            <div className="rounded-3xl border border-yellow-300/20 bg-gradient-to-br from-yellow-300/12 via-roadcall-panel/70 to-cyan-500/10 p-6 shadow-2xl shadow-black/20">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-yellow-100">Map Partner Badge</p>
                  <p className="mt-2 text-5xl font-black text-white">$19.99<span className="text-sm font-semibold text-roadcall-muted">/mo</span></p>
                  <p className="mt-2 text-sm text-roadcall-muted">Optional upgrade on top of your free shop listing.</p>
                </div>
                <div className="inline-flex items-center gap-2 rounded-full bg-yellow-300 px-3 py-1.5 text-xs font-black uppercase tracking-wide text-slate-950">
                  <Shield className="h-4 w-4" /> Roadcall Partner
                </div>
              </div>
              <div className="mt-6 grid gap-3 text-sm text-roadcall-silver sm:grid-cols-2">
                {[
                  "Subtle yellow pin ring on the map",
                  "Floating badge at close zoom only",
                  "Partner label in hover and selected cards",
                  "Designed to market your shop without cluttering the map",
                ].map((feature) => (
                  <div key={feature} className="flex gap-2 rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <a href={MAP_BADGE_REQUEST} className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl bg-yellow-300 px-5 py-3 text-sm font-black text-slate-950 hover:bg-yellow-200">
                  <Wrench className="h-4 w-4" /> Request Map Badge
                </a>
                <a href={PROVIDER_SIGNUP} className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-5 py-3 text-sm font-black text-white hover:border-white/20">
                  <Wrench className="h-4 w-4" /> List Free First
                </a>
                <Link href={PARTNER_MAP_DEMO} className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl border border-roadcall-cyan/25 bg-roadcall-panel/50 px-5 py-3 text-sm font-black text-white hover:border-roadcall-cyan/45">
                  <MapPin className="h-4 w-4" /> Preview on Map
                </Link>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Why List on Roadcall"
            title="More than a directory — it's a dispatch engine"
            description="Other directories list your name and phone. Roadcall's AI actively routes verified leads to you based on availability, location, and service match."
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-14">
            {benefits.map((b, i) => (
              <FadeIn key={b.title} delay={i * 0.08}>
                <div className="p-6 rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/35 hover:border-roadcall-cyan/25 transition-all">
                  <b.icon className={`h-7 w-7 ${b.accent} mb-4`} />
                  <h3 className="font-bold text-white mb-2">{b.title}</h3>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{b.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 border-t border-roadcall-cyan/10 bg-roadcall-panel/10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="Getting Started" title="Up and running in 10 minutes" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
            {howItWorks.map((s, i) => (
              <FadeIn key={s.step} delay={i * 0.1}>
                <div className="p-6 rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/40">
                  <div className="text-3xl font-black text-roadcall-cyan/30 mb-3">{s.step}</div>
                  <h4 className="font-bold text-white mb-2">{s.title}</h4>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{s.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-900/30 via-roadcall-panel/60 to-blue-900/25 border border-emerald-500/20 p-10">
            <h2 className="text-3xl font-black text-white mb-4">Ready to grow your shop?</h2>
            <p className="text-roadcall-muted mb-8">List free today. Get your first dispatched lead this week.</p>
            <a href={PROVIDER_SIGNUP}>
              <button className="inline-flex items-center gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold px-10 py-4 rounded-2xl text-lg transition-all shadow-xl shadow-blue-900/20">
                <Wrench className="h-5 w-5" /> List My Shop Free
              </button>
            </a>
            <p className="mt-4 text-xs text-roadcall-muted">Sign in to Roadcall — your profile, your data, your clients.</p>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
