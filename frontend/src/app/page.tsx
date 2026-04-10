"use client";

import Link from "next/link";
import {
  Phone,
  MessageSquare,
  TrendingUp,
  Shield,
  Zap,
  Star,
  ArrowRight,
  CheckCircle2,
  Headphones,
  MapPin,
  Wrench,
  Car,
  Truck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

/* ── Data ────────────────────────────────────────────────────── */

const stats = [
  { value: "35,000+", label: "Mechanics in Network" },
  { value: "50", label: "States Covered" },
  { value: "< 90s", label: "Avg Call Duration" },
  { value: "24/7", label: "Always On" },
];

const features = [
  {
    icon: Phone,
    title: "AI Dispatch Agent",
    description:
      "Callers speak to Sam, your AI dispatcher. Sam collects vehicle info, issue details, and kicks off the rescue — 24/7, no hold times.",
  },
  {
    icon: MapPin,
    title: "GPS Location Sharing",
    description:
      "Drivers tap a magic link texted to their phone, share their GPS with one tap — no apps to download.",
  },
  {
    icon: Wrench,
    title: "Smart Mechanic Matching",
    description:
      "Our algorithm scores 35,000+ mechanics by distance, issue specialty, vehicle type, rating, and mobile capability.",
  },
  {
    icon: MessageSquare,
    title: "SMS Magic Link",
    description:
      "After the call, drivers get an SMS with a secure link to share location and authorize a small payment hold.",
  },
  {
    icon: Shield,
    title: "Secure Payment Hold",
    description:
      "Stripe-powered authorization hold — no charge until the mechanic arrives. Drivers feel safe, shops get guaranteed payment.",
  },
  {
    icon: TrendingUp,
    title: "Live Tracking Dashboard",
    description:
      "Track every job: driver location, mechanic en route, ETA updates — all in real time on a live map.",
  },
];

const howItWorks = [
  {
    step: "01",
    title: "Driver Calls",
    description:
      "Stranded driver calls the Roadcall.ai toll-free number. Our AI agent, Sam, picks up instantly — no hold music, no transfers.",
    icon: Phone,
    accent: "from-blue-500 to-cyan-500",
  },
  {
    step: "02",
    title: "AI Collects Info",
    description:
      "Sam asks for name, vehicle type, and what happened. The whole call takes under 90 seconds.",
    icon: Car,
    accent: "from-cyan-500 to-emerald-500",
  },
  {
    step: "03",
    title: "Magic Link SMS",
    description:
      "Driver gets a text with a secure link. One tap to share GPS location and authorize a small payment hold via Stripe.",
    icon: MessageSquare,
    accent: "from-emerald-500 to-green-500",
  },
  {
    step: "04",
    title: "Best Mechanic Found",
    description:
      "Our scoring engine ranks nearby mechanics by distance, specialty match, rating, and availability — then auto-calls the best one.",
    icon: Wrench,
    accent: "from-green-500 to-amber-500",
  },
  {
    step: "05",
    title: "Help Is on the Way",
    description:
      "The mechanic accepts, driver gets an ETA, and both can track each other on a live map until the job is done.",
    icon: MapPin,
    accent: "from-amber-500 to-orange-500",
  },
];

const solutions = [
  {
    icon: Car,
    title: "Roadside Assistance",
    description:
      "AI-powered dispatch for stranded drivers. From call to mechanic in under 5 minutes.",
    href: "/solutions#roadside",
    accent: "from-orange-500/20 to-red-500/20",
    border: "border-orange-500/10",
  },
  {
    icon: Wrench,
    title: "Mechanic Shops",
    description:
      "AI receptionist that answers every call, captures leads, and books appointments — even at 3 AM.",
    href: "/solutions#shops",
    accent: "from-cyan-500/20 to-blue-500/20",
    border: "border-cyan-500/10",
  },
  {
    icon: Truck,
    title: "Fleet & Heavy Duty",
    description:
      "Centralized dispatch for fleet breakdowns and Class 7-8 trucking with specialized mechanic matching.",
    href: "/solutions#fleet",
    accent: "from-emerald-500/20 to-green-500/20",
    border: "border-emerald-500/10",
  },
];

const testimonials = [
  {
    name: "Mike's Diesel Repair",
    location: "Dallas, TX",
    quote:
      "We were missing 40% of our after-hours calls. Now the AI picks up every single one and I wake up to a list of qualified leads.",
    rating: 5,
  },
  {
    name: "Interstate Truck Service",
    location: "Atlanta, GA",
    quote:
      "The AI sounds like a real dispatcher who knows our business. Customers can't tell the difference — and they love the text link.",
    rating: 5,
  },
  {
    name: "Big Rig Solutions",
    location: "Phoenix, AZ",
    quote:
      "Paid for itself in the first week. One after-hours tow job the AI booked covered two months of service.",
    rating: 5,
  },
];

/* ── Page ─────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <PageLayout>
      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(234,88,12,0.18),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_50%_40%_at_80%_50%,rgba(59,130,246,0.08),transparent_50%)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto text-center">
            <FadeIn>
              <div className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 rounded-full px-5 py-2 mb-8">
                <Zap className="h-4 w-4 text-orange-400" />
                <span className="text-sm font-medium text-orange-300">
                  AI-Powered Roadside Dispatch
                </span>
              </div>
            </FadeIn>

            <FadeIn delay={0.1}>
              <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
                Stranded?
                <br />
                <span className="bg-gradient-to-r from-orange-400 via-amber-400 to-yellow-400 bg-clip-text text-transparent">
                  Help is 90 seconds
                </span>
                <br />
                away.
              </h1>
            </FadeIn>

            <FadeIn delay={0.2}>
              <p className="text-xl md:text-2xl text-slate-300 max-w-2xl mx-auto mb-12 leading-relaxed">
                Call our AI dispatcher. Share your location with one tap. We
                find the closest, best-rated mechanic and send them straight
                to you.
              </p>
            </FadeIn>

            {/* Demo CTA card */}
            <FadeIn delay={0.3}>
              <div className="bg-white/[0.04] backdrop-blur-sm border border-white/10 rounded-3xl p-8 md:p-10 max-w-lg mx-auto mb-14">
                <div className="flex items-center justify-center gap-3 mb-3">
                  <Headphones className="h-8 w-8 text-orange-400" />
                  <h2 className="text-2xl font-bold">Try It Now — Free</h2>
                </div>
                <p className="text-slate-400 mb-6">
                  Call and talk to Sam, our AI dispatcher. No signup needed.
                </p>
                <a href={telHref(HELP_PHONE)}>
                  <Button
                    size="xl"
                    className="w-full bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-xl gap-3 rounded-2xl shadow-xl shadow-orange-600/20"
                  >
                    <Phone className="h-6 w-6" />
                    {HELP_PHONE}
                  </Button>
                </a>
                <p className="text-sm text-slate-500 mt-3">
                  Free call · No signup · Takes 60 seconds
                </p>
              </div>
            </FadeIn>

            {/* Stats bar */}
            <FadeIn delay={0.4}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
                {stats.map((stat) => (
                  <div key={stat.label} className="text-center">
                    <div className="text-2xl md:text-3xl font-bold text-white">
                      {stat.value}
                    </div>
                    <div className="text-sm text-slate-400 mt-1">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ── Social proof strip ────────────────────────── */}
      <section className="border-y border-white/[0.06] bg-white/[0.02] py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-slate-400">
          {[
            "35,000+ mechanics nationwide",
            "All 50 states covered",
            "No app download needed",
            "Cancel anytime",
          ].map((text) => (
            <div key={text} className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ──────────────────────────────── */}
      <section id="how-it-works" className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="How It Works"
            title="From call to rescue in 5 steps"
            description="No apps. No signup. Just a phone call and a text."
          />

          <div className="relative">
            <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-blue-500/30 via-emerald-500/30 to-orange-500/30" />

            <div className="space-y-16 md:space-y-0">
              {howItWorks.map((item, idx) => (
                <FadeIn
                  key={item.step}
                  delay={idx * 0.1}
                  direction={idx % 2 === 0 ? "left" : "right"}
                >
                  <div
                    className={`md:grid md:grid-cols-2 md:gap-16 md:items-center ${
                      idx > 0 ? "md:mt-24" : ""
                    }`}
                  >
                    <div className={idx % 2 === 1 ? "md:order-2" : ""}>
                      <div className="flex items-center gap-4 mb-4">
                        <div
                          className={`h-12 w-12 rounded-2xl bg-gradient-to-br ${item.accent} flex items-center justify-center shadow-lg`}
                        >
                          <item.icon className="h-6 w-6 text-white" />
                        </div>
                        <span className="text-sm font-bold text-slate-500 tracking-widest">
                          STEP {item.step}
                        </span>
                      </div>
                      <h3 className="text-2xl md:text-3xl font-bold mb-3">
                        {item.title}
                      </h3>
                      <p className="text-lg text-slate-400 leading-relaxed">
                        {item.description}
                      </p>
                    </div>
                    <div
                      className={`hidden md:flex items-center justify-center ${
                        idx % 2 === 1 ? "md:order-1" : ""
                      }`}
                    >
                      <div className="relative">
                        <div
                          className={`h-48 w-48 rounded-3xl bg-gradient-to-br ${item.accent} opacity-10`}
                        />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <item.icon className="h-20 w-20 text-white/20" />
                        </div>
                      </div>
                    </div>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────── */}
      <section
        id="features"
        className="py-24 md:py-32 bg-gradient-to-b from-white/[0.02] to-transparent border-t border-white/[0.06]"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Features"
            title="Built for Roadside & Repair Shops"
            description="Everything you need to catch every call, dispatch faster, and grow revenue — powered by AI."
          />

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, idx) => (
              <FadeIn key={feature.title} delay={idx * 0.08}>
                <GlassCard hover className="p-7 h-full">
                  <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 border border-orange-500/10 flex items-center justify-center mb-5">
                    <feature.icon className="h-6 w-6 text-orange-400" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2 text-white">
                    {feature.title}
                  </h3>
                  <p className="text-slate-400 leading-relaxed text-[15px]">
                    {feature.description}
                  </p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>

          <FadeIn delay={0.3}>
            <div className="text-center mt-12">
              <Link href="/features">
                <Button
                  variant="outline"
                  className="rounded-full border-white/20 text-white hover:bg-white/5 px-8"
                >
                  Explore All Features
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Solutions preview ─────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Solutions"
            title="AI dispatch for every use case"
            description="Whether you're a solo mechanic, a busy shop, or a fleet operator — Roadcall.ai scales to fit."
          />

          <div className="grid md:grid-cols-3 gap-6">
            {solutions.map((sol, idx) => (
              <FadeIn key={sol.title} delay={idx * 0.1}>
                <Link href={sol.href}>
                  <GlassCard
                    hover
                    className="p-8 h-full group cursor-pointer"
                  >
                    <div
                      className={`h-14 w-14 rounded-2xl bg-gradient-to-br ${sol.accent} border ${sol.border} flex items-center justify-center mb-6`}
                    >
                      <sol.icon className="h-7 w-7 text-white/80" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3 text-white group-hover:text-orange-300 transition-colors">
                      {sol.title}
                    </h3>
                    <p className="text-slate-400 leading-relaxed mb-4">
                      {sol.description}
                    </p>
                    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-orange-400 group-hover:gap-2.5 transition-all">
                      Learn more
                      <ArrowRight className="h-4 w-4" />
                    </span>
                  </GlassCard>
                </Link>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── For Mechanic Shops ────────────────────────── */}
      <section className="py-24 md:py-32 bg-gradient-to-b from-white/[0.02] to-transparent border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <FadeIn direction="right">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400 mb-4">
                  For Mechanic Shops
                </p>
                <h2 className="text-4xl font-bold tracking-tight mb-6">
                  Your AI receptionist that never clocks out
                </h2>
                <p className="text-lg text-slate-400 leading-relaxed mb-8">
                  Stop losing after-hours calls. Roadcall.ai answers every
                  call to your shop, qualifies the lead, captures vehicle
                  info, and sends you a text — even at 3 AM.
                </p>
                <div className="space-y-4">
                  {[
                    "AI answers in your shop's voice — knows your services, hours, pricing",
                    "Captures name, phone, vehicle, issue — scored and ready for follow-up",
                    "Books appointments, sends confirmations, forwards urgent calls",
                    "Full dashboard with call logs, recordings, and analytics",
                  ].map((item) => (
                    <div key={item} className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                      <span className="text-slate-300">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </FadeIn>

            <FadeIn direction="left">
              <GlassCard className="p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <Phone className="h-5 w-5 text-emerald-400" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">Incoming Call</div>
                    <div className="text-xs text-slate-500">
                      Today 2:34 AM
                    </div>
                  </div>
                  <div className="ml-auto rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-xs text-emerald-400">
                    Answered by AI
                  </div>
                </div>
                {[
                  { label: "Caller", value: "James Rodriguez" },
                  { label: "Vehicle", value: "2021 Peterbilt 389" },
                  { label: "Issue", value: "Flat tire — driver side rear" },
                  { label: "Location", value: "I-35, mile marker 212" },
                  { label: "Lead Score", value: "92 / 100" },
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex justify-between py-2.5 border-b border-white/[0.06] last:border-0"
                  >
                    <span className="text-sm text-slate-500">
                      {row.label}
                    </span>
                    <span className="text-sm font-medium text-white">
                      {row.value}
                    </span>
                  </div>
                ))}
              </GlassCard>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ── Testimonials ──────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Testimonials"
            title="Shops love Roadcall"
          />

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t, idx) => (
              <FadeIn key={t.name} delay={idx * 0.1}>
                <GlassCard className="p-7 h-full">
                  <div className="flex gap-1 mb-4">
                    {Array.from({ length: t.rating }).map((_, i) => (
                      <Star
                        key={i}
                        className="h-4 w-4 fill-amber-400 text-amber-400"
                      />
                    ))}
                  </div>
                  <p className="text-slate-300 mb-5 leading-relaxed italic">
                    &quot;{t.quote}&quot;
                  </p>
                  <div>
                    <p className="font-semibold text-white text-sm">
                      {t.name}
                    </p>
                    <p className="text-xs text-slate-500">{t.location}</p>
                  </div>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing preview ───────────────────────────── */}
      <section className="py-24 md:py-32 bg-gradient-to-b from-white/[0.02] to-transparent border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Pricing"
            title="Simple, transparent pricing"
            description="No contracts. No hidden fees. Cancel anytime."
          />

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              {
                name: "Starter",
                price: 99,
                description: "For independent shops",
                features: [
                  "AI phone receptionist",
                  "Up to 200 calls/month",
                  "Lead capture & scoring",
                  "Call log dashboard",
                  "Business hours routing",
                  "Email support",
                ],
              },
              {
                name: "Professional",
                price: 199,
                description: "For busy multi-bay shops",
                popular: true,
                features: [
                  "Everything in Starter",
                  "Up to 1,000 calls/month",
                  "SMS dispatch & magic links",
                  "Mechanic matching & dispatch",
                  "Live driver tracking",
                  "Priority support",
                  "Call forwarding to owner",
                ],
              },
              {
                name: "Fleet",
                price: 399,
                description: "For networks & franchises",
                features: [
                  "Everything in Professional",
                  "Unlimited calls & dispatches",
                  "Multi-location support",
                  "Custom AI voice & branding",
                  "Dedicated account manager",
                  "API access",
                  "White-label option",
                ],
              },
            ].map((plan, idx) => (
              <FadeIn key={plan.name} delay={idx * 0.1}>
                <div
                  className={`rounded-2xl border p-8 relative transition-all h-full flex flex-col ${
                    plan.popular
                      ? "border-orange-500/50 bg-orange-500/[0.04] ring-1 ring-orange-500/20"
                      : "border-white/[0.08] bg-white/[0.02]"
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-orange-600 to-red-600 text-white text-xs font-bold px-4 py-1 rounded-full shadow-lg">
                      MOST POPULAR
                    </div>
                  )}
                  <div className="text-center mb-8">
                    <h3 className="text-xl font-bold text-white mb-1">
                      {plan.name}
                    </h3>
                    <p className="text-sm text-slate-400 mb-5">
                      {plan.description}
                    </p>
                    <div>
                      <span className="text-5xl font-bold text-white">
                        ${plan.price}
                      </span>
                      <span className="text-slate-400 ml-1">/mo</span>
                    </div>
                  </div>
                  <ul className="space-y-3 mb-8 flex-1">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-3">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-1" />
                        <span className="text-slate-300 text-sm">{f}</span>
                      </li>
                    ))}
                  </ul>
                  <Link href="/pricing">
                    <Button
                      className={`w-full rounded-xl ${
                        plan.popular
                          ? "bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 shadow-lg shadow-orange-600/20"
                          : "bg-white/10 hover:bg-white/15 border border-white/10"
                      }`}
                      size="lg"
                    >
                      Get Started
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </FadeIn>
            ))}
          </div>

          <FadeIn delay={0.3}>
            <div className="text-center mt-10">
              <Link
                href="/pricing"
                className="text-sm text-orange-400 hover:text-orange-300 inline-flex items-center gap-1.5"
              >
                Compare all plans
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Final CTA ─────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-orange-600/10 via-red-600/5 to-transparent p-12 md:p-16 relative overflow-hidden">
              <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-orange-600/10 blur-[80px]" />
              <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-red-600/10 blur-[80px]" />
              <div className="relative z-10">
                <h2 className="text-3xl md:text-5xl font-bold mb-6">
                  Ready to stop missing calls?
                </h2>
                <p className="text-xl text-slate-300 mb-10 max-w-xl mx-auto">
                  Try the AI demo right now — call and hear it for yourself.
                  Takes 60 seconds.
                </p>
                <a href={telHref(HELP_PHONE)}>
                  <Button
                    size="xl"
                    className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-xl gap-3 rounded-2xl shadow-xl shadow-orange-600/20"
                  >
                    <Phone className="h-6 w-6" />
                    Call {HELP_PHONE}
                  </Button>
                </a>
                <p className="text-sm text-slate-500 mt-4">
                  Or{" "}
                  <Link
                    href="/admin/login"
                    className="text-orange-400 hover:text-orange-300 underline underline-offset-2"
                  >
                    sign in to your dashboard
                  </Link>
                </p>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>
    </PageLayout>
  );
}
