"use client";

import Link from "next/link";
import { CheckCircle2, ArrowRight, HelpCircle } from "lucide-react";
import { HELP_PHONE } from "@/lib/phone";

const TIERS = [
  {
    name: "Dispatch MVP",
    tag: "Small fleets · up to 25 vehicles",
    price: "Contact Sales",
    highlight: false,
    color: "border-white/10 bg-slate-950/70",
    cta: "Book Fleet Demo",
    ctaHref: "/fleet/onboarding",
    features: [
      "AI call answering for roadside incidents",
      "One-time GPS location capture links",
      "Manual vendor dispatch via SMS",
      "Incident log with call summaries",
      "Up to 25 vehicles",
      "Up to 100 incidents/mo",
      "Hosted multi-tenant",
    ],
  },
  {
    name: "Fleet Ops",
    tag: "Growing carriers · up to 250 vehicles",
    price: "Contact Sales",
    highlight: true,
    color: "border-roadcall-cyan/60 bg-roadcall-cyan/10 ring-2 ring-roadcall-cyan/30",
    cta: "Book Fleet Demo",
    ctaHref: "/fleet/onboarding",
    features: [
      "Everything in Dispatch MVP",
      "Geo-matched vendor dispatch",
      "Driver & vehicle database",
      "GPS/telematics integration",
      "Maintenance system webhook",
      "Up to 250 vehicles",
      "Unlimited incidents",
      "Priority support + SLA",
    ],
  },
  {
    name: "Enterprise",
    tag: "Large carriers · private or hybrid",
    price: "Custom",
    highlight: false,
    color: "border-white/10 bg-slate-950/70",
    cta: "Contact Sales",
    ctaHref: `tel:${HELP_PHONE}`,
    features: [
      "Everything in Fleet Ops",
      "Private tenant or hybrid in-house",
      "Approved vendor network enforcement",
      "Custom AI voice & call flows",
      "Full API access + webhooks",
      "Unlimited vehicles",
      "Dedicated onboarding engineer",
      "24/7 support + uptime SLA",
    ],
  },
];

const DIMENSIONS = [
  { label: "Vehicles", desc: "Priced per vehicle tier — not per seat." },
  { label: "Incidents / month", desc: "Capped on MVP; unlimited on Fleet Ops+." },
  { label: "AI call minutes", desc: "Included allocation per tier; overage billed at cost." },
  { label: "SMS / location captures", desc: "Per-message pricing above monthly include." },
  { label: "Integrations", desc: "Standard integrations included; custom API work quoted separately." },
  { label: "Private tenant", desc: "Available on Enterprise with dedicated infrastructure pricing." },
  { label: "Support / SLA", desc: "Email on MVP, priority on Fleet Ops, 24/7 on Enterprise." },
];

const FAQS = [
  { q: "Do we need to move our data into Roadcall?", a: "No. Roadcall Fleet supports a hybrid in-house mode where only the AI call layer and dispatch actions touch Roadcall infrastructure. Your core fleet data stays in your own database." },
  { q: "Can Roadcall use our tracker data?", a: "Yes. Roadcall can integrate with fleet tracking systems to pull vehicle location into incidents automatically when a driver calls." },
  { q: "Can we keep our internal roadside process?", a: "Yes. Roadcall Fleet is designed to augment your existing process — not replace your dispatcher. The AI handles first contact and data capture; your team takes over at any point." },
  { q: "Can this work with approved vendors only?", a: "Yes. Enterprise plans support an approved vendor list. The geo-match engine will only surface and dispatch to vendors you have pre-approved." },
];

export default function FleetPricingPage() {
  return (
    <main className="roadcall-page min-h-screen text-roadcall-silver">
      {/* Hero */}
      <section className="bg-gradient-to-br from-slate-800 via-blue-900 to-cyan-900 text-white py-16 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <span className="inline-block bg-white/20 text-sm font-medium px-4 py-1 rounded-full mb-6">Roadcall Fleet — Pricing</span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">Pricing built for fleet operations</h1>
          <p className="text-blue-200 text-lg">Flexible tiers from small fleets to enterprise carriers. All plans start with a live demo.</p>
        </div>
      </section>

      {/* Tier Cards */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {TIERS.map((t) => (
              <div key={t.name} className={`rounded-2xl border-2 p-8 flex flex-col ${t.color}`}>
                {t.highlight && (
                  <span className="inline-block bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white text-xs font-bold px-3 py-1 rounded-full mb-4 self-start">MOST POPULAR</span>
                )}
                <div className="text-sm text-roadcall-muted mb-2">{t.tag}</div>
                <div className="text-3xl font-bold text-white mb-2">{t.price}</div>
                <div className="font-semibold text-xl text-white mb-6">{t.name}</div>
                <ul className="space-y-3 mb-8 flex-1">
                  {t.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                      <CheckCircle2 className="w-4 h-4 text-roadcall-cyan flex-shrink-0 mt-0.5" />{f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={t.ctaHref}
                  className={`w-full text-center font-semibold py-3 rounded-lg transition-colors ${
                    t.highlight ? "bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white hover:brightness-110" : "border border-roadcall-cyan/35 text-roadcall-cyan hover:bg-roadcall-cyan/10"
                  }`}
                >
                  {t.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Dimensions */}
      <section className="py-16 px-4 bg-slate-950/35 border-y border-white/10">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">How pricing is measured</h2>
          <div className="space-y-4">
            {DIMENSIONS.map((d) => (
              <div key={d.label} className="flex gap-4 p-4 bg-slate-950/70 rounded-xl border border-white/10">
                <CheckCircle2 className="w-5 h-5 text-roadcall-cyan flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">{d.label}</span>
                  <span className="text-roadcall-muted"> — {d.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">Frequently asked questions</h2>
          <div className="space-y-6">
            {FAQS.map((faq) => (
              <div key={faq.q} className="border border-white/10 bg-slate-950/55 rounded-xl p-6">
                <div className="flex gap-3 mb-2">
                  <HelpCircle className="w-5 h-5 text-roadcall-cyan flex-shrink-0 mt-0.5" />
                  <p className="font-semibold text-white">{faq.q}</p>
                </div>
                <p className="text-roadcall-muted text-sm ml-8">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-gradient-to-r from-slate-800 to-blue-900 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-2xl font-bold mb-4">Book a Fleet Demo</h2>
          <p className="text-blue-200 mb-6">30-minute live walkthrough of AI call handling, incident management, and vendor dispatch.</p>
          <Link
            href="/fleet/onboarding"
            className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white font-semibold px-8 py-3 rounded-lg hover:brightness-110 transition-colors inline-flex items-center gap-2"
          >
            Book Fleet Demo <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
