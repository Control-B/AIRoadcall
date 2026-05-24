"use client";

import Link from "next/link";
import {
  Phone,
  MessageSquare,
  TrendingUp,
  Shield,
  MapPin,
  Wrench,
  ArrowRight,
  CheckCircle2,
  Zap,
  BarChart3,
  Bell,
  Clock,
  Globe,
  Users,
  FileText,
  Headphones,
  Settings,
  Smartphone,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

/* ── Deep Feature Blocks ─────────────────────────────────────── */

const deepFeatures = [
  {
    id: "ai-dispatch",
    eyebrow: "AI Voice Agent",
    title: "Sandy, your 24/7 AI dispatcher",
    description:
      "Our AI agent handles inbound calls with human-like conversation. Sandy collects driver name, vehicle details, and issue type — all in under 90 seconds. No hold times. No transfers. Just instant, intelligent dispatch.",
    bullets: [
      "Natural voice conversation — callers can't tell it's AI",
      "Extracts name, phone, vehicle year/make/model, and issue",
      "Handles edge cases: multiple vehicles, vague descriptions, emotional callers",
      "Customizable personality and business-specific knowledge",
      "Seamless handoff to human operators when needed",
    ],
    icon: Phone,
    accent: "from-blue-500 to-cyan-500",
    iconBg: "from-blue-500/20 to-cyan-500/20",
    iconBorder: "border-blue-500/10",
  },
  {
    id: "magic-link",
    eyebrow: "SMS Magic Link",
    title: "One tap to share location & pay",
    description:
      "After the AI call, drivers get an SMS with a secure magic link. One tap opens a mobile-optimized page where they share GPS location and authorize a small secure payment hold — no app download required.",
    bullets: [
      "SMS delivered within seconds of call completion",
      "Mobile-optimized web page — works on any phone",
      "GPS sharing with one-tap browser geolocation",
      "Secure payment authorization",
      "Real-time status updates via the same link",
    ],
    icon: MessageSquare,
    accent: "from-emerald-500 to-green-500",
    iconBg: "from-emerald-500/20 to-green-500/20",
    iconBorder: "border-emerald-500/10",
  },
  {
    id: "matching",
    eyebrow: "Smart Matching",
    title: "The right mechanic, every time",
    description:
      "Our scoring algorithm evaluates 35,000+ mechanics across multiple dimensions to find the optimal match. Distance, specialty, vehicle type expertise, response time, availability, and mobile capability — all weighted and ranked in milliseconds.",
    bullets: [
      "Multi-factor scoring: distance, specialty, availability, response confidence",
      "Vehicle-type matching: cars, trucks, Class 7-8, diesel, electric",
      "Issue-type matching: flat tires, engine, electrical, lockout",
      "Mobile service detection — prioritizes mechanics who come to you",
      "Automatic fallback to second and third best matches",
    ],
    icon: Wrench,
    accent: "from-roadcall-orange to-amber-500",
    iconBg: "from-roadcall-orange/20 to-roadcall-cyan/20",
    iconBorder: "border-roadcall-orange/20",
  },
  {
    id: "tracking",
    eyebrow: "Live Tracking",
    title: "Real-time visibility for everyone",
    description:
      "Once a mechanic accepts the job, both parties get a live tracking view. Drivers see the mechanic's ETA and route on an interactive map. Operators see all active jobs on a unified dashboard.",
    bullets: [
      "Interactive map with real-time mechanic location",
      "ETA calculations with traffic-aware routing",
      "Status updates: accepted, en route, on scene, completed",
      "Driver and mechanic can message through the platform",
      "Admin dashboard with bird's-eye view of all active jobs",
    ],
    icon: MapPin,
    accent: "from-violet-500 to-purple-500",
    iconBg: "from-violet-500/20 to-purple-500/20",
    iconBorder: "border-violet-500/10",
  },
  {
    id: "payments",
    eyebrow: "Secure Payments",
    title: "Authorization holds that protect everyone",
    description:
      "Drivers authorize a small hold before dispatch. This ensures mechanics get paid and drivers aren't charged until service is rendered. The hold converts to a charge only after job completion.",
    bullets: [
      "PCI-compliant payment processing",
      "Authorization hold — no charge until mechanic arrives",
      "Automatic charge on job completion",
      "Refund and dispute handling built in",
      "Driver payment receipts via email and SMS",
    ],
    icon: Shield,
    accent: "from-cyan-500 to-blue-500",
    iconBg: "from-cyan-500/20 to-blue-500/20",
    iconBorder: "border-cyan-500/10",
  },
  {
    id: "dashboard",
    eyebrow: "Admin Dashboard",
    title: "Complete control, zero complexity",
    description:
      "A full-featured admin dashboard gives you visibility into every call, job, mechanic, and payment. Filter, search, export, and manage your entire operation from one place.",
    bullets: [
      "Call logs with transcripts and recordings",
      "Job lifecycle management with status tracking",
      "Mechanic directory with scoring and performance data",
      "Revenue analytics and dispatch metrics",
      "Outreach campaigns to recruit new mechanics",
    ],
    icon: BarChart3,
    accent: "from-pink-500 to-rose-500",
    iconBg: "from-pink-500/20 to-rose-500/20",
    iconBorder: "border-pink-500/10",
  },
];

/* ── Quick Feature Grid ──────────────────────────────────────── */

const quickFeatures = [
  { icon: Clock, label: "24/7 Availability", description: "Never miss a call, day or night" },
  { icon: Globe, label: "50 State Coverage", description: "35,000+ mechanics nationwide" },
  { icon: Smartphone, label: "No App Required", description: "Works in any mobile browser" },
  { icon: Bell, label: "Instant Notifications", description: "SMS and email alerts in real time" },
  { icon: Users, label: "Multi-User Access", description: "Invite your team to the dashboard" },
  { icon: Settings, label: "Custom AI Voice", description: "Train the AI on your shop's info" },
  { icon: FileText, label: "Call Transcripts", description: "Full text of every AI conversation" },
  { icon: Headphones, label: "Human Handoff", description: "Transfer to a human when needed" },
];

/* ── Page ─────────────────────────────────────────────────────── */

export default function FeaturesPage() {
  return (
    <PageLayout>
      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(59,130,246,0.15),transparent_60%)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-5 py-2 mb-8">
              <Zap className="h-4 w-4 text-blue-400" />
              <span className="text-sm font-medium text-blue-300">
                Platform Features
              </span>
            </div>
          </FadeIn>

          <FadeIn delay={0.1}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
              Everything you need to
              <br />
              <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400 bg-clip-text text-transparent">
                dispatch smarter
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={0.2}>
            <p className="text-xl md:text-2xl text-roadcall-silver/85 max-w-3xl mx-auto leading-relaxed">
              From the AI voice call to the live tracking map — every piece
              of the roadside rescue workflow, automated and intelligent.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ── Quick features grid ───────────────────────── */}
      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {quickFeatures.map((f, idx) => (
              <FadeIn key={f.label} delay={idx * 0.05}>
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-xl bg-roadcall-panel/45 border border-roadcall-cyan/10 flex items-center justify-center shrink-0">
                    <f.icon className="h-5 w-5 text-roadcall-muted" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {f.label}
                    </p>
                    <p className="text-xs text-roadcall-muted/70 mt-0.5">
                      {f.description}
                    </p>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Deep Feature Blocks ───────────────────────── */}
      {deepFeatures.map((feature, idx) => (
        <section
          key={feature.id}
          id={feature.id}
          className={`py-24 md:py-32 ${
            idx % 2 === 0
              ? ""
              : "bg-gradient-to-b from-white/[0.02] to-transparent"
          } border-t border-roadcall-cyan/10`}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div
              className={`grid md:grid-cols-2 gap-16 items-center ${
                idx % 2 === 1 ? "md:flex-row-reverse" : ""
              }`}
            >
              {/* Text */}
              <FadeIn direction={idx % 2 === 0 ? "right" : "left"}>
                <div className={idx % 2 === 1 ? "md:order-2" : ""}>
                  <p
                    className={`text-sm font-semibold uppercase tracking-[0.25em] mb-4 bg-gradient-to-r ${feature.accent} bg-clip-text text-transparent`}
                  >
                    {feature.eyebrow}
                  </p>
                  <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-5">
                    {feature.title}
                  </h2>
                  <p className="text-lg text-roadcall-muted leading-relaxed mb-8">
                    {feature.description}
                  </p>
                  <ul className="space-y-3">
                    {feature.bullets.map((bullet) => (
                      <li key={bullet} className="flex items-start gap-3">
                        <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-roadcall-silver/85 text-[15px]">
                          {bullet}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </FadeIn>

              {/* Visual */}
              <FadeIn direction={idx % 2 === 0 ? "left" : "right"}>
                <div
                  className={`${idx % 2 === 1 ? "md:order-1" : ""} flex items-center justify-center`}
                >
                  <div className="relative w-full max-w-md">
                    {/* Glow */}
                    <div
                      className={`absolute inset-0 rounded-3xl bg-gradient-to-br ${feature.accent} opacity-[0.08] blur-xl scale-110`}
                    />
                    {/* Card */}
                    <GlassCard className="relative p-10 flex flex-col items-center justify-center min-h-[280px]">
                      <div
                        className={`h-20 w-20 rounded-3xl bg-gradient-to-br ${feature.iconBg} border ${feature.iconBorder} flex items-center justify-center mb-6`}
                      >
                        <feature.icon className="h-10 w-10 text-white/60" />
                      </div>
                      <p className="text-lg font-semibold text-white text-center">
                        {feature.eyebrow}
                      </p>
                      <p className="text-sm text-roadcall-muted/70 text-center mt-1">
                        Powered by Roadcall.ai
                      </p>
                    </GlassCard>
                  </div>
                </div>
              </FadeIn>
            </div>
          </div>
        </section>
      ))}

      {/* ── Final CTA ─────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="rounded-3xl border border-roadcall-cyan/10 bg-gradient-to-br from-blue-600/10 via-cyan-600/5 to-transparent p-12 md:p-16 relative overflow-hidden">
              <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-blue-600/10 blur-[80px]" />
              <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-cyan-600/10 blur-[80px]" />
              <div className="relative z-10">
                <h2 className="text-3xl md:text-5xl font-bold mb-6">
                  See it in action
                </h2>
                <p className="text-xl text-roadcall-silver/85 mb-10 max-w-xl mx-auto">
                  Call our demo line and experience every feature firsthand
                  — from the AI voice agent to the magic link.
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
