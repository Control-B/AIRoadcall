"use client";

import Link from "next/link";
import {
  Phone,
  Car,
  Wrench,
  Truck,
  ArrowRight,
  CheckCircle2,
  Zap,
  Star,
  MapPin,
  Clock,
  Shield,
  Users,
  BarChart3,
  MessageSquare,
  Cog,
  Search,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

/* ── Solution cards ──────────────────────────────────────────── */

const solutionBlocks = [
  {
    id: "roadside",
    eyebrow: "Lane 1 · AI Roadside Dispatch",
    title: "AI-powered matching and dispatch for roadside incidents",
    description:
      "Replace your call center with an AI dispatcher that picks up every call instantly, collects the right information, and dispatches the closest qualified mechanic — all in under 5 minutes.",
    icon: Car,
    accent: "from-roadcall-orange to-roadcall-blue",
    iconBg: "from-roadcall-orange/20 to-roadcall-blue/20",
    benefits: [
      "Zero hold time — AI answers every call instantly",
      "SMS magic link for GPS sharing and payment authorization",
      "Automatic mechanic matching from 35,000+ providers",
      "Live tracking for drivers, mechanics, and operators",
      "Works 24/7/365 — no staffing, no overtime, no sick days",
    ],
    stats: [
      { value: "< 90s", label: "Avg call time" },
      { value: "< 5 min", label: "Time to dispatch" },
      { value: "99.9%", label: "Uptime" },
    ],
  },
  {
    id: "shops",
    eyebrow: "Lane 2 · AI Telephony",
    title: "Never miss another shop call",
    description:
      "Your AI receptionist answers every call to your shop phone — day or night. It qualifies leads, captures vehicle info, books appointments, and sends you a text with the details. Wake up to a pipeline of qualified leads.",
    icon: Wrench,
    accent: "from-cyan-500 to-blue-500",
    iconBg: "from-cyan-500/20 to-blue-500/20",
    benefits: [
      "AI trained on your shop's services, hours, and pricing",
      "Lead scoring — see which callers are most valuable",
      "Appointment booking with confirmation SMS",
      "Call forwarding for urgent requests",
      "Full call log with transcripts and recordings",
    ],
    stats: [
      { value: "40%", label: "More leads captured" },
      { value: "0", label: "Missed calls" },
      { value: "$0", label: "Per-call cost vs. answering service" },
    ],
  },
  {
    id: "fleet",
    eyebrow: "Lane 3 · AI Lead Generation",
    title: "Capture and route qualified provider leads",
    description:
      "Roadcall turns inbound demand, directory activity, missed calls, and enrichment into qualified opportunities for subscribed providers.",
    icon: TrendingUp,
    accent: "from-emerald-500 to-green-500",
    iconBg: "from-emerald-500/20 to-green-500/20",
    benefits: [
      "Inbound and missed-call lead capture",
      "Provider data enrichment and email discovery workflows",
      "Campaign follow-up for mechanics and roadside operators",
      "Plan-based lead quotas for subscribed providers",
      "Call summaries and lead outcomes tracked in Roadcall",
    ],
    stats: [
      { value: "24/7", label: "Lead capture" },
      { value: "Plan", label: "Quota routing" },
      { value: "AI", label: "Qualification" },
    ],
  },
  {
    id: "directory",
    eyebrow: "Lane 4 · General Search",
    title: "Find Truck Service-style provider search",
    description:
      "A public search lane for truck repair, towing, national vendors, and marketplace discovery — separate from private dispatch and lead routing.",
    icon: Search,
    accent: "from-violet-500 to-purple-500",
    iconBg: "from-violet-500/20 to-purple-500/20",
    benefits: [
      "Search by city, state, service category, and provider type",
      "Public-friendly listings with protected contact details",
      "Separate from secured mechanic admin database access",
      "Supports national vendors and trucking directories",
      "Routes urgent users into AI dispatch when needed",
    ],
    stats: [
      { value: "35K+", label: "Provider records" },
      { value: "50", label: "States indexed" },
      { value: "Safe", label: "Protected data" },
    ],
  },
];

/* ── Why Roadcall ────────────────────────────────────────────── */

const whyBlocks = [
  {
    icon: Clock,
    title: "Instant Response",
    description:
      "AI picks up in under 1 second. No hold queues, no IVR trees, no transfers.",
  },
  {
    icon: Cog,
    title: "Fully Automated",
    description:
      "From call to dispatch — no human operator needed for standard requests.",
  },
  {
    icon: MapPin,
    title: "Nationwide Coverage",
    description:
      "35,000+ mechanics across all 50 US states, scored and ranked in real time.",
  },
  {
    icon: Shield,
    title: "Secure Payments",
    description:
      "Stripe-powered authorization holds protect drivers and guarantee mechanic payment.",
  },
  {
    icon: BarChart3,
    title: "Full Visibility",
    description:
      "Live tracking, call logs, transcripts, and analytics — all in one dashboard.",
  },
  {
    icon: Users,
    title: "Scalable",
    description:
      "Handles 10 calls a day or 10,000. No infrastructure changes needed.",
  },
];


export default function SolutionsPage() {
  return (
    <PageLayout>
      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(234,88,12,0.15),transparent_60%)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-roadcall-orange/10 border border-roadcall-orange/25 rounded-full px-5 py-2 mb-8">
              <Zap className="h-4 w-4 text-roadcall-orange" />
              <span className="text-sm font-medium text-roadcall-orange">
                Solutions
              </span>
            </div>
          </FadeIn>

          <FadeIn delay={0.1}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
              Four lanes for
              <br />
              <span className="bg-gradient-to-r from-roadcall-orange via-amber-400 to-yellow-400 bg-clip-text text-transparent">
                truck service
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={0.2}>
            <p className="text-xl md:text-2xl text-roadcall-silver/85 max-w-3xl mx-auto leading-relaxed">
              Roadcall is AI dispatch, AI telephony, AI lead generation, and
              a general truck service search directory — one platform with
              four clearly separated workflows.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ── Solution Blocks ───────────────────────────── */}
      {solutionBlocks.map((sol, idx) => (
        <section
          key={sol.id}
          id={sol.id}
          className={`py-24 md:py-32 ${
            idx % 2 === 0
              ? ""
              : "bg-gradient-to-b from-white/[0.02] to-transparent"
          } border-t border-roadcall-cyan/10`}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="grid md:grid-cols-2 gap-16 items-start">
              {/* Content */}
              <FadeIn direction={idx % 2 === 0 ? "right" : "left"}>
                <div className={idx % 2 === 1 ? "md:order-2" : ""}>
                  <p
                    className={`text-sm font-semibold uppercase tracking-[0.25em] mb-4 bg-gradient-to-r ${sol.accent} bg-clip-text text-transparent`}
                  >
                    {sol.eyebrow}
                  </p>
                  <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-5">
                    {sol.title}
                  </h2>
                  <p className="text-lg text-roadcall-muted leading-relaxed mb-8">
                    {sol.description}
                  </p>

                  <ul className="space-y-3 mb-10">
                    {sol.benefits.map((b) => (
                      <li key={b} className="flex items-start gap-3">
                        <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-roadcall-silver/85 text-[15px]">
                          {b}
                        </span>
                      </li>
                    ))}
                  </ul>

                  {/* Stats row */}
                  <div className="grid grid-cols-3 gap-4">
                    {sol.stats.map((s) => (
                      <div
                        key={s.label}
                        className="rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/20 p-4 text-center"
                      >
                        <div className="text-2xl font-bold text-white">
                          {s.value}
                        </div>
                        <div className="text-xs text-roadcall-muted/70 mt-1">
                          {s.label}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </FadeIn>

              {/* Visual */}
              <FadeIn direction={idx % 2 === 0 ? "left" : "right"}>
                <div
                  className={`${
                    idx % 2 === 1 ? "md:order-1" : ""
                  } flex items-center justify-center`}
                >
                  <div className="relative w-full max-w-md">
                    <div
                      className={`absolute inset-0 rounded-3xl bg-gradient-to-br ${sol.accent} opacity-[0.08] blur-xl scale-110`}
                    />
                    <GlassCard className="relative p-10 flex flex-col items-center justify-center min-h-[320px]">
                      <div
                        className={`h-24 w-24 rounded-3xl bg-gradient-to-br ${sol.iconBg} flex items-center justify-center mb-6`}
                      >
                        <sol.icon className="h-12 w-12 text-white/60" />
                      </div>
                      <p className="text-xl font-bold text-white text-center mb-2">
                        {sol.eyebrow}
                      </p>
                      <p className="text-sm text-roadcall-muted/70 text-center max-w-xs">
                        {sol.description.split(".")[0]}.
                      </p>
                    </GlassCard>
                  </div>
                </div>
              </FadeIn>
            </div>
          </div>
        </section>
      ))}

      {/* ── Why Roadcall ──────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Why Roadcall.ai"
            title="The unfair advantage"
            description="Traditional dispatch services can't match AI speed, consistency, and scalability."
          />

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {whyBlocks.map((block, idx) => (
              <FadeIn key={block.title} delay={idx * 0.08}>
                <GlassCard className="p-7 h-full">
                  <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-white/[0.05] to-white/[0.02] border border-roadcall-cyan/10 flex items-center justify-center mb-5">
                    <block.icon className="h-6 w-6 text-roadcall-orange" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2 text-white">
                    {block.title}
                  </h3>
                  <p className="text-roadcall-muted leading-relaxed text-[15px]">
                    {block.description}
                  </p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ──────────────────────────────── */}

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="rounded-3xl border border-roadcall-cyan/10 bg-gradient-to-br from-roadcall-orange/10 via-roadcall-blue/5 to-transparent p-12 md:p-16 relative overflow-hidden">
              <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-roadcall-orange/10 blur-[80px]" />
              <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-red-600/10 blur-[80px]" />
              <div className="relative z-10">
                <h2 className="text-3xl md:text-5xl font-bold mb-6">
                  Find your solution
                </h2>
                <p className="text-xl text-roadcall-silver/85 mb-10 max-w-xl mx-auto">
                  Try the AI dispatcher yourself — one phone call, 60
                  seconds, and you&apos;ll see why shops are switching.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <a href={telHref(HELP_PHONE)}>
                    <Button
                      size="xl"
                      className="bg-gradient-to-r from-roadcall-orange to-roadcall-blue hover:from-roadcall-orange hover:to-roadcall-blue text-xl gap-3 rounded-2xl shadow-xl shadow-roadcall-orange/20"
                    >
                      <Phone className="h-6 w-6" />
                      Call {HELP_PHONE}
                    </Button>
                  </a>
                  <Link href="/pricing">
                    <Button
                      size="lg"
                      variant="outline"
                      className="rounded-full border-roadcall-cyan/20 text-white hover:bg-roadcall-panel/45 px-8"
                    >
                      View Pricing
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>
    </PageLayout>
  );
}
