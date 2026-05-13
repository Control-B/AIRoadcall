"use client";

import Link from "next/link";
import {
  Phone,
  MapPin,
  Zap,
  Shield,
  Clock,
  CheckCircle2,
  ArrowRight,
  Truck,
  Wrench,
  MessageSquare,
  Search,
  Navigation,
  AlertTriangle,
} from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

const steps = [
  {
    icon: Phone,
    step: "01",
    title: "Call or Text",
    description: "Call our AI dispatcher anytime, 24/7. No hold music. No voicemail. Sandy answers instantly and starts intake in seconds.",
    accent: "from-roadcall-orange to-amber-500",
  },
  {
    icon: MapPin,
    step: "02",
    title: "Share Your Location",
    description: "Sandy texts you a one-tap secure link. Tap once to share your exact GPS — no app download, no login required.",
    accent: "from-blue-500 to-cyan-500",
  },
  {
    icon: Wrench,
    step: "03",
    title: "Get Matched",
    description: "Our AI scores 35,000+ nearby mechanics by distance, rating, service type, and availability. Best match dispatched automatically.",
    accent: "from-emerald-500 to-green-400",
  },
  {
    icon: Navigation,
    step: "04",
    title: "Track Your Help",
    description: "Receive the mechanic's ETA via SMS. No guessing, no waiting in the dark — real-time updates until they arrive.",
    accent: "from-purple-500 to-pink-500",
  },
];

const issues = [
  { icon: Truck, label: "Flat Tire", href: "/search?service=tire_repair", color: "text-roadcall-orange" },
  { icon: Zap, label: "Dead Battery", href: "/search?service=battery_jump", color: "text-amber-400" },
  { icon: AlertTriangle, label: "Engine Problem", href: "/search?service=engine_diesel", color: "text-red-400" },
  { icon: Truck, label: "Need a Tow", href: "/search?service=towing", color: "text-blue-400" },
  { icon: Wrench, label: "Trailer Repair", href: "/search?service=trailer_repair", color: "text-cyan-400" },
  { icon: Phone, label: "Fuel / DEF", href: "/search?service=fuel_delivery", color: "text-emerald-400" },
  { icon: Shield, label: "Lockout", href: "/search?service=lockout", color: "text-purple-400" },
  { icon: Search, label: "Other / Browse All", href: "/search", color: "text-roadcall-muted" },
];

const faqs = [
  {
    q: "Is the AI dispatcher available 24/7?",
    a: "Yes — Sandy answers every call, 365 days a year. No hold times, no voicemail. If Sandy can't resolve your situation, you are immediately connected to a human.",
  },
  {
    q: "Do I need to download an app to share my location?",
    a: "No. Sandy texts you a one-time secure link. One tap shares your exact GPS coordinates — no app, no account needed.",
  },
  {
    q: "How are mechanics selected?",
    a: "Our AI scores nearby providers on distance, service type match, rating, mobile capability, and 24/7 availability. You get the best available option, not just the nearest listing.",
  },
  {
    q: "Is this service free for drivers?",
    a: "Searching and calling mechanics is always free. If you're part of a fleet, your fleet manager may have Roadcall Fleet enabled, which routes your call automatically.",
  },
  {
    q: "What if the first mechanic can't make it?",
    a: "Sandy re-ranks and dispatches the next best match automatically. You stay informed via SMS at every step.",
  },
];

export default function DriverPage() {
  return (
    <PageLayout>
      {/* Hero */}
      <section className="relative min-h-[80vh] flex flex-col justify-center overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-roadcall-orange/10 via-transparent to-blue-900/20 z-0" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-roadcall-void to-transparent z-0" />
        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-roadcall-panel/50 border border-roadcall-orange/25 backdrop-blur-sm rounded-full px-4 py-1.5 mb-6">
              <Truck className="h-3.5 w-3.5 text-roadcall-orange" />
              <span className="text-xs font-medium text-roadcall-silver/85 tracking-wide">For Drivers — Roadside Help in Under 90 Seconds</span>
            </div>
          </FadeIn>
          <FadeIn delay={0.1}>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[0.95] mb-6">
              <span className="block text-white">Stranded?</span>
              <span className="block bg-gradient-to-r from-roadcall-orange to-amber-400 bg-clip-text text-transparent">We&apos;ve Got You.</span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.2}>
            <p className="text-lg md:text-xl text-roadcall-silver/80 max-w-2xl mx-auto mb-10 leading-relaxed">
              Call our AI dispatcher. Share your GPS with one tap. We find the closest, best-rated mechanic and get them to you — no app needed.
            </p>
          </FadeIn>
          <FadeIn delay={0.3}>
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <a href={telHref(HELP_PHONE)}>
                <button className="inline-flex items-center justify-center gap-2 bg-roadcall-orange hover:brightness-110 text-white font-bold text-lg px-10 py-5 rounded-2xl shadow-2xl shadow-orange-900/40 transition-all">
                  <Phone className="h-6 w-6" /> Call Now — {HELP_PHONE}
                </button>
              </a>
              <Link href="/search">
                <button className="inline-flex items-center justify-center gap-2 border border-roadcall-cyan/25 bg-roadcall-panel/40 backdrop-blur-sm text-white hover:bg-roadcall-panel/60 font-semibold px-8 py-5 rounded-2xl transition-all">
                  <Search className="h-5 w-5" /> Search Providers
                </button>
              </Link>
            </div>
            <p className="text-sm text-roadcall-muted">Free to use · No app required · 35,000+ mechanics nationwide</p>
          </FadeIn>
        </div>
      </section>

      {/* Issue type quick links */}
      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 py-8">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm text-roadcall-muted mb-5">What do you need help with?</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {issues.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="flex items-center gap-2.5 p-3.5 rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/40 hover:border-roadcall-cyan/30 hover:bg-roadcall-panel/60 transition-all group"
              >
                <item.icon className={`h-5 w-5 shrink-0 ${item.color}`} />
                <span className="text-sm font-medium text-roadcall-silver group-hover:text-white transition-colors">{item.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 md:py-32">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="How It Works"
            title="Help in 4 simple steps"
            description="From your first call to mechanic on-site — automated, tracked, and stress-free."
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-14">
            {steps.map((s, i) => (
              <FadeIn key={s.step} delay={i * 0.1}>
                <div className="relative p-6 rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/35 hover:border-roadcall-cyan/25 transition-all">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${s.accent} flex items-center justify-center mb-4 shadow-lg`}>
                    <s.icon className="h-5 w-5 text-white" />
                  </div>
                  <div className="text-xs font-bold text-roadcall-muted uppercase tracking-widest mb-2">{s.step}</div>
                  <h3 className="font-bold text-white text-base mb-2">{s.title}</h3>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{s.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Trust points */}
      <section className="py-12 border-t border-roadcall-cyan/10 bg-roadcall-panel/10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center">
            {[
              { icon: Shield, label: "Verified Network", sub: "All providers phone-verified. Ratings tracked per job." },
              { icon: Clock, label: "24/7 Coverage", sub: "AI dispatcher never sleeps. Help available every hour of every day." },
              { icon: MessageSquare, label: "SMS Updates", sub: "Real-time status texts from intake through resolution." },
            ].map((t) => (
              <div key={t.label} className="p-6 rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30">
                <t.icon className="h-8 w-8 text-roadcall-cyan mx-auto mb-3" />
                <h4 className="font-bold text-white mb-1">{t.label}</h4>
                <p className="text-sm text-roadcall-muted">{t.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 md:py-32">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="FAQ" title="Common driver questions" />
          <div className="mt-10 space-y-4">
            {faqs.map((faq) => (
              <div key={faq.q} className="p-6 rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/30">
                <h4 className="font-semibold text-white mb-2">{faq.q}</h4>
                <p className="text-sm text-roadcall-muted leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="pb-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-roadcall-orange/25 via-roadcall-panel/60 to-blue-900/25 border border-roadcall-orange/20 p-10">
            <h2 className="text-3xl font-black text-white mb-4">Stranded right now?</h2>
            <p className="text-roadcall-muted mb-8">Don&apos;t wait — call our AI dispatcher. We&apos;ll have someone on the way fast.</p>
            <a href={telHref(HELP_PHONE)}>
              <button className="inline-flex items-center gap-2 bg-roadcall-orange hover:brightness-110 text-white font-bold px-10 py-4 rounded-2xl text-lg transition-all shadow-xl shadow-orange-900/30">
                <Phone className="h-5 w-5" /> {HELP_PHONE}
              </button>
            </a>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-6 text-xs text-roadcall-muted">
              {["Free to use", "No app needed", "35,000+ mechanics", "All 50 states"].map((t) => (
                <span key={t} className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-emerald-400" />{t}</span>
              ))}
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
