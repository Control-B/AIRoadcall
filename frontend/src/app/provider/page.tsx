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
  ArrowRight,
  MapPin,
  BarChart3,
  Shield,
  TrendingUp,
  MessageSquare,
  Building2,
} from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

const PROVIDER_SIGNUP = "/provider/register";

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
    description: "Our AI dispatcher routes qualified leads directly to you based on service type, location, availability, and rating — no cold calls.",
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
    title: "Verified Reviews",
    description: "Build your reputation with verified post-job reviews collected automatically via SMS after each incident close.",
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

const tiers = [
  {
    name: "Free Listing",
    price: "$0",
    period: "/mo",
    setup: null,
    description: "Get found. Build your presence.",
    features: [
      "Directory listing in all 50 states",
      "Phone number & website display",
      "Basic service type & hours info",
      "Appear in search results",
      "Claim & verify your profile",
    ],
    cta: "Claim Free Listing",
    href: PROVIDER_SIGNUP,
    highlighted: false,
  },
  {
    name: "Verified Provider",
    price: "$97",
    period: "/mo",
    setup: null,
    description: "Get dispatched. Build trust.",
    features: [
      "Everything in Free",
      "Verified badge — priority ranking",
      "AI dispatch lead routing",
      "Performance analytics dashboard",
      "Post-job review automation",
      "Priority placement in search",
      "SMS dispatch notifications",
    ],
    cta: "Start Verified Trial",
    href: PROVIDER_SIGNUP,
    highlighted: true,
  },
  {
    name: "Roadcall Standard",
    price: "$299",
    period: "/mo",
    setup: "$99 setup",
    description: "AI telephony and growth essentials.",
    features: [
      "Everything in Verified",
      "AI Telephony",
      "Leads",
      "Calendar",
      "CRM",
      "Form Builder",
      "Missed Call Text Back",
    ],
    cta: "Start Free Trial",
    href: "https://buy.stripe.com/4gMbJ3gwE4pg0IG5Aa1sQ0g",
    highlighted: false,
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
              <Link href="/ai-telephony#setup">
                <button className="inline-flex items-center justify-center gap-2 border border-roadcall-cyan/25 bg-roadcall-panel/40 backdrop-blur-sm text-white hover:bg-roadcall-panel/60 font-semibold px-8 py-5 rounded-2xl transition-all">
                  <Phone className="h-5 w-5" /> Configure AI Phone
                </button>
              </Link>
              <a href={telHref(HELP_PHONE)}>
                <button className="inline-flex items-center justify-center gap-2 border border-roadcall-cyan/25 bg-roadcall-panel/20 backdrop-blur-sm text-roadcall-silver hover:bg-roadcall-panel/50 hover:text-white font-semibold px-8 py-5 rounded-2xl transition-all">
                  <Phone className="h-5 w-5" /> Talk to Our Team
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

      {/* Pricing */}
      <section className="py-24 md:py-32">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Provider Plans"
            title="Start free. Scale with AI."
            description="Every business gets a free listing. Upgrade when you're ready to receive dispatched leads and automate your phone."
          />
          <div className="grid sm:grid-cols-3 gap-6 mt-14">
            {tiers.map((tier, i) => (
              <FadeIn key={tier.name} delay={i * 0.1}>
                <div className={`relative p-7 rounded-2xl border flex flex-col transition-all ${
                  tier.highlighted
                    ? "border-emerald-500/40 bg-gradient-to-b from-emerald-900/20 to-roadcall-panel/50 shadow-xl shadow-emerald-900/20"
                    : "border-roadcall-cyan/15 bg-roadcall-panel/35"
                }`}>
                  {tier.highlighted && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full">
                      Most Popular
                    </div>
                  )}
                  <div className="mb-5">
                    <h3 className="font-bold text-white text-lg mb-1">{tier.name}</h3>
                    <div className="flex items-end gap-1 mb-1">
                      <span className="text-3xl font-black text-white">{tier.price}</span>
                      <span className="text-roadcall-muted text-sm mb-1">{tier.period}</span>
                    </div>
                    {tier.setup && <p className="mb-1 text-xs font-semibold text-roadcall-orange">{tier.setup}</p>}
                    <p className="text-xs text-roadcall-muted">{tier.description}</p>
                  </div>
                  <ul className="space-y-2 mb-6 flex-1">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm text-roadcall-silver/90">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <a href={tier.href}>
                    <button className={`w-full py-3 rounded-xl font-semibold text-sm transition-all ${
                      tier.highlighted
                        ? "bg-emerald-500 hover:bg-emerald-400 text-white"
                        : "border border-roadcall-cyan/20 bg-roadcall-panel/50 text-roadcall-silver hover:text-white hover:border-roadcall-cyan/40"
                    }`}>
                      {tier.cta} <ArrowRight className="inline h-4 w-4 ml-1" />
                    </button>
                  </a>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="pb-24">
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
