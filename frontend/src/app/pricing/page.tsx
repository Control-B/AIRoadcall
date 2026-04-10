"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Phone,
  ArrowRight,
  CheckCircle2,
  X,
  Zap,
  Star,
  ChevronDown,
  Shield,
  Clock,
  Headphones,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

/* ── Plans ───────────────────────────────────────────────────── */

const plans = [
  {
    name: "Starter",
    price: 99,
    description: "For independent shops",
    cta: "Start Free Trial",
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
    cta: "Start Free Trial",
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
    cta: "Contact Sales",
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
];

/* ── Comparison table ────────────────────────────────────────── */

interface CompRow {
  feature: string;
  starter: boolean | string;
  professional: boolean | string;
  fleet: boolean | string;
}

const comparisonRows: CompRow[] = [
  { feature: "AI phone receptionist", starter: true, professional: true, fleet: true },
  { feature: "Calls per month", starter: "200", professional: "1,000", fleet: "Unlimited" },
  { feature: "Lead capture & scoring", starter: true, professional: true, fleet: true },
  { feature: "Call log dashboard", starter: true, professional: true, fleet: true },
  { feature: "Business hours routing", starter: true, professional: true, fleet: true },
  { feature: "SMS dispatch", starter: false, professional: true, fleet: true },
  { feature: "Magic link flow", starter: false, professional: true, fleet: true },
  { feature: "Mechanic matching", starter: false, professional: true, fleet: true },
  { feature: "Live driver tracking", starter: false, professional: true, fleet: true },
  { feature: "Call forwarding", starter: false, professional: true, fleet: true },
  { feature: "Multi-location", starter: false, professional: false, fleet: true },
  { feature: "Custom AI voice", starter: false, professional: false, fleet: true },
  { feature: "API access", starter: false, professional: false, fleet: true },
  { feature: "White-label option", starter: false, professional: false, fleet: true },
  { feature: "Dedicated account manager", starter: false, professional: false, fleet: true },
  { feature: "Support", starter: "Email", professional: "Priority", fleet: "Dedicated" },
];

/* ── FAQ ──────────────────────────────────────────────────────── */

const faqs = [
  {
    q: "How does the free trial work?",
    a: "Start any plan with a 14-day free trial. No credit card required. You'll get full access to all features in your chosen plan. Cancel anytime during the trial and you won't be charged.",
  },
  {
    q: "Can I change plans later?",
    a: "Absolutely. Upgrade or downgrade at any time from your dashboard. Changes take effect immediately, and we'll prorate your billing.",
  },
  {
    q: "What happens if I exceed my call limit?",
    a: "We'll notify you when you're approaching your limit. Additional calls are billed at $0.50 each, or you can upgrade to a higher plan for a better per-call rate.",
  },
  {
    q: "Is there a setup fee?",
    a: "No. Zero setup fees. You sign up, configure your shop details, and the AI starts answering calls. Most shops are live within 15 minutes.",
  },
  {
    q: "Can the AI handle multiple calls at once?",
    a: "Yes. Unlike a human receptionist, the AI handles unlimited concurrent calls. No caller ever gets a busy signal.",
  },
  {
    q: "Do I need any special hardware?",
    a: "No. Roadcall.ai works with your existing phone system. We provide a dedicated phone number, or you can forward your current number to us.",
  },
  {
    q: "How accurate is the AI?",
    a: "Our AI correctly captures caller information 97%+ of the time. It's trained specifically for automotive and roadside scenarios, and it improves continuously.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. No contracts, no cancellation fees. Cancel from your dashboard with one click. Your service continues until the end of your billing period.",
  },
];

/* ── Trust signals ───────────────────────────────────────────── */

const trustSignals = [
  { icon: Shield, label: "PCI Compliant", description: "Stripe-powered payments" },
  { icon: Clock, label: "99.9% Uptime", description: "Enterprise-grade reliability" },
  { icon: Headphones, label: "US-Based Support", description: "Real humans when you need them" },
];

/* ── FAQ Accordion Item ──────────────────────────────────────── */

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-white/[0.06]">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-5 text-left group"
      >
        <span className="text-[15px] font-medium text-white group-hover:text-orange-300 transition-colors pr-4">
          {q}
        </span>
        <ChevronDown
          className={`h-5 w-5 text-slate-500 shrink-0 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && (
        <div className="pb-5 pr-8">
          <p className="text-slate-400 text-[15px] leading-relaxed">{a}</p>
        </div>
      )}
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────────── */

export default function PricingPage() {
  return (
    <PageLayout>
      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(168,85,247,0.12),transparent_60%)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-violet-500/10 border border-violet-500/20 rounded-full px-5 py-2 mb-8">
              <Zap className="h-4 w-4 text-violet-400" />
              <span className="text-sm font-medium text-violet-300">
                Pricing
              </span>
            </div>
          </FadeIn>

          <FadeIn delay={0.1}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
              Simple pricing,
              <br />
              <span className="bg-gradient-to-r from-violet-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                serious results
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={0.2}>
            <p className="text-xl md:text-2xl text-slate-300 max-w-2xl mx-auto leading-relaxed">
              No contracts. No hidden fees. Start with a 14-day free trial
              on any plan. Cancel anytime.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ── Plan cards ────────────────────────────────── */}
      <section className="pb-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan, idx) => (
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
                  <Button
                    className={`w-full rounded-xl ${
                      plan.popular
                        ? "bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 shadow-lg shadow-orange-600/20"
                        : "bg-white/10 hover:bg-white/15 border border-white/10"
                    }`}
                    size="lg"
                  >
                    {plan.cta}
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Trust signals ─────────────────────────────── */}
      <section className="border-y border-white/[0.06] bg-white/[0.02] py-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {trustSignals.map((s, idx) => (
              <FadeIn key={s.label} delay={idx * 0.1}>
                <div className="flex items-center gap-4 justify-center md:justify-start">
                  <div className="h-12 w-12 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center">
                    <s.icon className="h-6 w-6 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {s.label}
                    </p>
                    <p className="text-xs text-slate-500">{s.description}</p>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Comparison table ──────────────────────────── */}
      <section className="py-24 md:py-32">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Compare Plans"
            title="Feature-by-feature breakdown"
          />

          <FadeIn>
            <div className="rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px]">
                  <thead>
                    <tr className="border-b border-white/[0.08] bg-white/[0.02]">
                      <th className="text-left text-sm font-medium text-slate-400 px-6 py-4 w-1/3">
                        Feature
                      </th>
                      <th className="text-center text-sm font-medium text-slate-400 px-4 py-4">
                        Starter
                      </th>
                      <th className="text-center text-sm font-medium text-orange-400 px-4 py-4">
                        Professional
                      </th>
                      <th className="text-center text-sm font-medium text-slate-400 px-4 py-4">
                        Fleet
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonRows.map((row) => (
                      <tr
                        key={row.feature}
                        className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="text-sm text-slate-300 px-6 py-3">
                          {row.feature}
                        </td>
                        {(
                          ["starter", "professional", "fleet"] as const
                        ).map((plan) => (
                          <td
                            key={plan}
                            className="text-center px-4 py-3"
                          >
                            {typeof row[plan] === "boolean" ? (
                              row[plan] ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-400 mx-auto" />
                              ) : (
                                <X className="h-4 w-4 text-slate-600 mx-auto" />
                              )
                            ) : (
                              <span className="text-sm text-slate-300">
                                {row[plan]}
                              </span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Testimonials ──────────────────────────────── */}
      <section className="py-24 md:py-32 bg-gradient-to-b from-white/[0.02] to-transparent border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Testimonials"
            title="Don't take our word for it"
          />

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                name: "Mike's Diesel Repair",
                location: "Dallas, TX",
                quote:
                  "Paid for itself in the first week. One after-hours tow job the AI booked covered two months of the Professional plan.",
                rating: 5,
              },
              {
                name: "Interstate Truck Service",
                location: "Atlanta, GA",
                quote:
                  "Switched from a $2,000/month answering service to the Starter plan. Capturing 3x more leads at a fraction of the cost.",
                rating: 5,
              },
              {
                name: "Big Rig Solutions",
                location: "Phoenix, AZ",
                quote:
                  "The Fleet plan with multi-location support was exactly what we needed. All 4 shops on one dashboard — game changer.",
                rating: 5,
              },
            ].map((t, idx) => (
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

      {/* ── FAQ ───────────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="FAQ"
            title="Common questions"
          />

          <FadeIn>
            <div className="divide-y divide-white/[0.06] border-t border-white/[0.06]">
              {faqs.map((faq) => (
                <FaqItem key={faq.q} q={faq.q} a={faq.a} />
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-violet-600/10 via-purple-600/5 to-transparent p-12 md:p-16 relative overflow-hidden">
              <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-violet-600/10 blur-[80px]" />
              <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-purple-600/10 blur-[80px]" />
              <div className="relative z-10">
                <h2 className="text-3xl md:text-5xl font-bold mb-6">
                  Try it free for 14 days
                </h2>
                <p className="text-xl text-slate-300 mb-10 max-w-xl mx-auto">
                  No credit card required. Set up in 15 minutes. Cancel
                  anytime.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <a href={telHref(HELP_PHONE)}>
                    <Button
                      size="xl"
                      className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-xl gap-3 rounded-2xl shadow-xl shadow-orange-600/20"
                    >
                      <Phone className="h-6 w-6" />
                      Call {HELP_PHONE}
                    </Button>
                  </a>
                  <Link href="/company#contact">
                    <Button
                      size="lg"
                      variant="outline"
                      className="rounded-full border-white/20 text-white hover:bg-white/5 px-8"
                    >
                      Talk to Sales
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
