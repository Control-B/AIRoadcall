"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import {
  Phone,
  Wrench,
  Truck,
  ArrowRight,
  CheckCircle2,
  Shield,
  MapPin,
  MessageSquare,
  TrendingUp,
  Building2,
  Star,
  Zap,
  Lock,
  GitBranch,
  Radio,
  Mail,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

const shopsFeatures = [
  { icon: Phone,        title: "AI Call Answering",      description: "Sandy answers every call instantly — day or night — and captures lead details." },
  { icon: MessageSquare,title: "Missed-Call Text-Back",  description: "Texts back missed callers within seconds so they don't dial a competitor." },
  { icon: Building2,    title: "Appointment Booking",    description: "Books directly into your calendar during the call. Zero back-and-forth." },
  { icon: TrendingUp,   title: "CRM & Follow-Up",        description: "Full pipeline automation with follow-ups and review requests via GoHighLevel." },
];

const fleetFeatures = [
  { icon: Phone,      title: "AI Roadside Intake",       description: "Driver calls in stranded. Incident collected in under 90 seconds, 24/7." },
  { icon: MapPin,     title: "GPS & Tracker Integration",description: "One-tap secure SMS link. Driver shares exact GPS — no app download needed." },
  { icon: Wrench,     title: "Mechanic Matching",         description: "Score 35,000+ vendors by distance, class, specialty, and availability." },
  { icon: Radio,      title: "Dispatch & Tracking",       description: "Real-time ops board — driver pin, mechanic ETA, full incident audit trail." },
];

const testimonials = [
  { name: "Mike's Diesel Repair",  location: "Dallas, TX",   vertical: "shops", quote: "We were missing 40% of after-hours calls. Now the AI picks up every one and I wake up to a list of qualified leads.", rating: 5 },
  { name: "Coastal Freight Lines", location: "Atlanta, GA",  vertical: "fleet", quote: "Our drivers get a text link mid-call and share their GPS without downloading a thing. Dispatch time dropped by 60%.", rating: 5 },
  { name: "Big Rig Solutions",     location: "Phoenix, AZ",  vertical: "shops", quote: "One after-hours job the AI booked covered two months of the subscription. Paid for itself week one.", rating: 5 },
];

const integrations = [
  "Samsara", "Geotab", "Motive", "ELD", "Fleetio", "Zenduit", "Google Maps", "Custom API",
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://airoadcall-i76ba.ondigitalocean.app/api";

function LeadMagnetForm({ vertical }: { vertical?: "shops" | "fleet" | "general" }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setStatus("loading");
    try {
      const res = await fetch(`${API_URL}/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name: name || undefined, vertical: vertical || "general", source: "homepage" }),
      });
      if (res.ok || res.status === 201) {
        setStatus("done");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  }

  if (status === "done") {
    return (
      <div className="flex flex-col items-center gap-3 py-4">
        <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
          <CheckCircle2 className="h-6 w-6 text-emerald-400" />
        </div>
        <p className="text-white font-semibold text-lg">You&apos;re on the list.</p>
        <p className="text-slate-400 text-sm">Check your inbox — we sent you a welcome note.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md mx-auto">
      <div className="flex flex-col sm:flex-row gap-3 mb-3">
        <input
          type="text"
          placeholder="First name (optional)"
          value={name}
          onChange={e => setName(e.target.value)}
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-orange-500/50 focus:bg-white/8 transition-all"
        />
        <input
          type="email"
          required
          placeholder="your@email.com"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="flex-[2] bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-orange-500/50 focus:bg-white/8 transition-all"
        />
      </div>
      <button
        type="submit"
        disabled={status === "loading"}
        className="w-full bg-orange-500 hover:bg-orange-400 disabled:opacity-60 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors flex items-center justify-center gap-2"
      >
        {status === "loading" ? (
          <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
        ) : (
          <><Mail className="h-4 w-4" /> Get the weekly dispatch</>
        )}
      </button>
      {status === "error" && (
        <p className="text-red-400 text-xs mt-2 text-center">Something went wrong — try again in a moment.</p>
      )}
      <p className="text-slate-500 text-xs mt-3 text-center">No spam. Unsubscribe anytime.</p>
    </form>
  );
}

export default function HomePage() {
  return (
    <PageLayout>

      {/* ═══════════════════════════════════════════════════════════════
          HERO — Full-viewport cinematic truck section
      ═══════════════════════════════════════════════════════════════ */}
      <section className="relative min-h-screen flex flex-col justify-end overflow-hidden">

        {/* Truck background image */}
        <Image
          src="https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=1920&q=80"
          alt="Semi truck on night highway"
          fill
          priority
          className="object-cover object-center"
          sizes="100vw"
        />

        {/* Layered overlays for cinematic depth */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#02050c]/70 via-[#02050c]/40 to-[#02050c] z-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#02050c]/60 via-transparent to-[#02050c]/40 z-10" />
        {/* Orange headlight bloom */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(234,88,12,0.18),transparent_70%)] z-10" />

        {/* Hero content */}
        <div className="relative z-20 max-w-7xl mx-auto px-4 sm:px-6 w-full pb-16 pt-32">

          {/* Badge */}
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-white/5 border border-white/10 backdrop-blur-sm rounded-full px-4 py-1.5 mb-10">
              <Zap className="h-3.5 w-3.5 text-orange-400" />
              <span className="text-xs font-medium text-slate-300 tracking-wide">AI-Driven Roadside Support &amp; AI Phones for the Trucking Industry</span>
            </div>
          </FadeIn>

          {/* Headline */}
          <FadeIn delay={0.1}>
            <h1 className="text-6xl sm:text-7xl md:text-8xl font-black tracking-tight leading-[0.95] mb-6">
              <span className="block text-white">AI That Answers.</span>
              <span className="block text-white">Jobs That Get Done.</span>
            </h1>
          </FadeIn>

          <FadeIn delay={0.2}>
            <p className="text-lg md:text-xl text-slate-300 max-w-xl mb-12 leading-relaxed">
              24/7 AI phone agents for mechanics. Less downtime for fleets.
              <br className="hidden sm:block" />
              One platform. Two powerful solutions.
            </p>
          </FadeIn>

          {/* Vertical split cards */}
          <FadeIn delay={0.3}>
            <div className="grid sm:grid-cols-2 gap-4 max-w-2xl mb-10">

              {/* Shops card */}
              <Link href="/shops">
                <div className="group relative rounded-2xl border border-orange-500/25 bg-black/40 backdrop-blur-md p-6 text-left hover:border-orange-500/50 hover:bg-black/60 transition-all duration-200 cursor-pointer overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-orange-500/8 to-transparent" />
                  <div className="relative">
                    <div className="text-[10px] font-bold text-orange-400 uppercase tracking-[0.2em] mb-3">Roadcall Shops</div>
                    <h2 className="text-base font-bold text-white mb-1">AI Phones + CRM</h2>
                    <p className="text-xs font-medium text-orange-300 mb-4">for Truck Mechanics</p>
                    <ul className="space-y-1.5 mb-5">
                      {["AI Call Answering","Missed-Call Text Back","Appointment Booking","CRM & Follow-Up"].map(i => (
                        <li key={i} className="flex items-center gap-2 text-xs text-slate-300">
                          <CheckCircle2 className="h-3 w-3 text-orange-400 shrink-0" />{i}
                        </li>
                      ))}
                    </ul>
                    <div className="inline-flex items-center gap-1.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors">
                      For Mechanics <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                </div>
              </Link>

              {/* Fleet card */}
              <Link href="/fleet">
                <div className="group relative rounded-2xl border border-blue-500/25 bg-black/40 backdrop-blur-md p-6 text-left hover:border-blue-500/50 hover:bg-black/60 transition-all duration-200 cursor-pointer overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/8 to-transparent" />
                  <div className="relative">
                    <div className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] mb-3">Roadcall Fleet</div>
                    <h2 className="text-base font-bold text-white mb-1">AI Roadside Support</h2>
                    <p className="text-xs font-medium text-blue-300 mb-4">for Fleets</p>
                    <ul className="space-y-1.5 mb-5">
                      {["AI Roadside Intake","GPS & Tracker Integration","Mechanic Matching","Dispatch & Tracking"].map(i => (
                        <li key={i} className="flex items-center gap-2 text-xs text-slate-300">
                          <CheckCircle2 className="h-3 w-3 text-blue-400 shrink-0" />{i}
                        </li>
                      ))}
                    </ul>
                    <div className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors">
                      For Fleets <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                </div>
              </Link>
            </div>
          </FadeIn>

          {/* Phone CTA */}
          <FadeIn delay={0.4}>
            <div className="flex flex-wrap items-center gap-3">
              <a href={telHref(HELP_PHONE)} className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm">
                <div className="w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center">
                  <Phone className="h-3.5 w-3.5 text-white" />
                </div>
                <span>Call <strong className="text-white">{HELP_PHONE}</strong> — talk to Sandy live</span>
              </a>
              <Link href="/marketplace" className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-400/15">
                Explore marketplace <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link href="/shops/operations" className="inline-flex items-center gap-2 rounded-full border border-orange-400/30 bg-orange-400/10 px-4 py-2 text-sm font-semibold text-orange-100 hover:bg-orange-400/15">
                Provider operations <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Trust strip ─────────────────────────────────────────────── */}
      <section className="border-y border-white/[0.06] bg-white/[0.02] py-5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-slate-400">
          {["35,000+ mechanics nationwide","All 50 states covered","No app download needed","Cancel anytime"].map((text) => (
            <div key={text} className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Never Miss Another Repair Call (Shops deep-dive) ────────── */}
      <section className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <FadeIn direction="left">
              <div className="text-xs font-bold text-orange-400 uppercase tracking-[0.2em] mb-4">Roadcall Shops</div>
              <h2 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
                Never Miss Another
                <span className="block bg-gradient-to-r from-orange-400 to-red-400 bg-clip-text text-transparent">Repair Call</span>
              </h2>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                Your AI receptionist answers every call, captures the details, and books more jobs — while you focus on what you do best: fixing trucks.
              </p>
              <ul className="space-y-3 mb-10">
                {["AI answers instantly, 24/7","Missed-call text-back in seconds","Appointment booking to your calendar","CRM pipeline with automated follow-up","Review request automation after jobs"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-slate-300">
                    <CheckCircle2 className="h-4 w-4 text-orange-400 shrink-0" /> {item}
                  </li>
                ))}
              </ul>
              <div className="flex gap-3">
                <Link href="/shops/onboarding">
                  <Button className="bg-orange-500 hover:bg-orange-400 text-white font-semibold rounded-xl px-6">
                    Start All Phones
                  </Button>
                </Link>
                <Link href="/shops/features">
                  <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800 rounded-xl px-6">
                    See Features
                  </Button>
                </Link>
              </div>
            </FadeIn>
            <FadeIn direction="right">
              <div className="grid grid-cols-2 gap-4">
                {shopsFeatures.map((f) => (
                  <GlassCard key={f.title} className="p-5">
                    <f.icon className="h-6 w-6 text-orange-400 mb-3" />
                    <h3 className="text-sm font-semibold text-white mb-1.5">{f.title}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">{f.description}</p>
                  </GlassCard>
                ))}
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ── AI Roadside Support That Delivers (Fleet deep-dive) ──────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <FadeIn direction="left" className="order-2 lg:order-1">
              <div className="grid grid-cols-2 gap-4">
                {fleetFeatures.map((f) => (
                  <GlassCard key={f.title} className="p-5">
                    <f.icon className="h-6 w-6 text-blue-400 mb-3" />
                    <h3 className="text-sm font-semibold text-white mb-1.5">{f.title}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">{f.description}</p>
                  </GlassCard>
                ))}
              </div>
            </FadeIn>
            <FadeIn direction="right" className="order-1 lg:order-2">
              <div className="text-xs font-bold text-blue-400 uppercase tracking-[0.2em] mb-4">Roadcall Fleet</div>
              <h2 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
                AI Roadside Support
                <span className="block bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">That Delivers</span>
              </h2>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                Fast intake. Accurate data. The right mechanic dispatched — faster. Your fleet data stays in your control.
              </p>
              <ul className="space-y-3 mb-10">
                {["AI driver intake in under 90 seconds","GPS location via one-tap SMS link","Matches nearest qualified mechanic instantly","Real-time dispatch board for your team","Your data never touches a third-party CRM"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-slate-300">
                    <CheckCircle2 className="h-4 w-4 text-blue-400 shrink-0" /> {item}
                  </li>
                ))}
              </ul>
              <div className="flex gap-3">
                <Link href="/fleet/onboarding">
                  <Button className="bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl px-6">
                    Book a Demo
                  </Button>
                </Link>
                <Link href="/fleet/features">
                  <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800 rounded-xl px-6">
                    See Features
                  </Button>
                </Link>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ── Built for Fleets. Trusted by Operators. (Security) ──────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="text-xs font-bold text-blue-400 uppercase tracking-[0.2em] mb-4">Enterprise Security</div>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Built for Fleets.
              <span className="block text-slate-300 font-light">Trusted by Operators.</span>
            </h2>
            <p className="text-slate-400 text-lg mb-12 max-w-2xl mx-auto">
              Enterprise-grade security with flexible deployment options. Security that meets your standards. Support that exceeds them.
            </p>
          </FadeIn>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: Shield,    label: "Tenant Isolation",       sub: "Your data. Your control." },
              { icon: Lock,      label: "RBAC & Audit Logs",      sub: "Secure access. Full visibility." },
              { icon: GitBranch, label: "Private or Hybrid",      sub: "Private Tenant, or In-House." },
              { icon: Zap,       label: "Data Minimization",      sub: "We only collect what's needed." },
            ].map((item) => (
              <FadeIn key={item.label}>
                <GlassCard className="p-6 flex flex-col items-center text-center">
                  <item.icon className="h-7 w-7 text-blue-400 mb-3" />
                  <div className="text-sm font-semibold text-white mb-1">{item.label}</div>
                  <div className="text-xs text-slate-400">{item.sub}</div>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
          <FadeIn delay={0.2}>
            <div className="mt-8">
              <Link href="/fleet/security">
                <Button variant="outline" className="border-blue-500/30 text-blue-300 hover:bg-blue-500/10 rounded-xl px-6">
                  Request Security Review <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Seamless Integrations ───────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="text-xs font-bold text-emerald-400 uppercase tracking-[0.2em] mb-4">Integrations</div>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Seamless Integrations.
              <span className="block bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">Stronger Operations.</span>
            </h2>
            <p className="text-slate-400 text-lg mb-12">
              Connect the tools you use. Sync what matters. Automate the rest.
            </p>
          </FadeIn>
          <div className="flex flex-wrap justify-center gap-3 mb-10">
            {integrations.map((name) => (
              <div key={name} className="bg-slate-800/60 border border-slate-700/50 text-slate-300 text-sm font-medium px-5 py-2.5 rounded-xl">
                {name}
              </div>
            ))}
          </div>
          <FadeIn delay={0.1}>
            <Link href="/fleet/integrations">
              <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800 rounded-xl">
                View All Integrations <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </FadeIn>
        </div>
      </section>

      {/* ── Testimonials ────────────────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="What customers say" title="Real results from shops and fleets" />
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <FadeIn key={t.name}>
                <GlassCard className="p-6 h-full flex flex-col">
                  <div className="flex gap-1 mb-4">
                    {Array.from({ length: t.rating }).map((_, i) => (
                      <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="text-slate-300 text-sm leading-relaxed flex-1 mb-4">&ldquo;{t.quote}&rdquo;</p>
                  <div>
                    <div className="text-sm font-semibold text-white">{t.name}</div>
                    <div className="text-xs text-slate-500">{t.location}</div>
                    <div className={`text-xs mt-1 font-medium ${t.vertical === "fleet" ? "text-blue-400" : "text-orange-400"}`}>
                      {t.vertical === "fleet" ? "Roadcall Fleet" : "Roadcall Shops"}
                    </div>
                  </div>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Lead Magnet — Weekly Dispatch newsletter ──────────────── */}
      <section className="py-24 md:py-28 border-t border-white/[0.06]">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 rounded-full px-4 py-1.5 mb-6">
              <Mail className="h-3.5 w-3.5 text-orange-400" />
              <span className="text-xs font-semibold text-orange-300 uppercase tracking-wide">Free Weekly Dispatch</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-black mb-4 leading-tight">
              AI tips for the
              <span className="block bg-gradient-to-r from-orange-400 to-amber-300 bg-clip-text text-transparent">
                trucking industry.
              </span>
            </h2>
            <p className="text-slate-400 text-lg mb-10 leading-relaxed">
              Join 500+ fleet managers and shop owners getting weekly insights on AI phones, driver downtime, dispatch ops, and more.
            </p>
            <LeadMagnetForm vertical="general" />
          </FadeIn>
        </div>
      </section>

      {/* ── Final CTA — Roadcall. We Keep You Moving. ───────────────── */}
      <section className="relative py-32 md:py-40 border-t border-white/[0.06] overflow-hidden">
        <Image
          src="https://images.unsplash.com/photo-1519003722824-194d4455a60c?w=1920&q=80"
          alt="Truck on highway at sunset"
          fill
          className="object-cover object-center opacity-20"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#02050c] via-[#02050c]/60 to-[#02050c]" />
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <h2 className="text-5xl md:text-6xl font-black mb-4">
              Roadcall.
              <span className="block bg-gradient-to-r from-orange-400 to-amber-300 bg-clip-text text-transparent">
                We Keep You Moving.
              </span>
            </h2>
            <p className="text-xl text-slate-400 mb-10">
              AI-driven roadside support and AI phones for the trucking industry.<br />
              Less downtime. Lower costs. <span className="text-orange-400 font-medium">That&apos;s the Roadcall promise.</span>
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/shops/onboarding">
                <Button size="lg" className="bg-orange-500 hover:bg-orange-400 text-white font-semibold rounded-xl px-8">
                  <Wrench className="h-5 w-5 mr-2" /> I&apos;m a Mechanic Shop
                </Button>
              </Link>
              <Link href="/fleet/onboarding">
                <Button size="lg" className="bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl px-8">
                  <Truck className="h-5 w-5 mr-2" /> I Manage a Fleet
                </Button>
              </Link>
            </div>
            <p className="text-slate-500 text-sm mt-6">
              Or call us:{" "}
              <a href={telHref(HELP_PHONE)} className="text-orange-400 hover:text-orange-300 font-medium">{HELP_PHONE}</a>
            </p>
          </FadeIn>
        </div>
      </section>

    </PageLayout>
  );
}
