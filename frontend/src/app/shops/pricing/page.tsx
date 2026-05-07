"use client";

import Link from "next/link";
import Image from "next/image";
import { CheckCircle2, ArrowRight, HelpCircle } from "lucide-react";
import { HELP_PHONE } from "@/lib/phone";

const TIERS = [
  {
    name: "Starter",
    price: "$297",
    period: "/mo",
    tag: "Best for solo shops",
    color: "border-gray-200",
    cta: "Get Started",
    ctaHref: "/shops/onboarding",
    features: [
      "AI call answering (up to 200 calls/mo)",
      "Missed-call text-back",
      "Call summaries to email",
      "Basic CRM contact capture",
      "1 shop location",
      "Email support",
    ],
  },
  {
    name: "Growth",
    price: "$597",
    period: "/mo",
    tag: "Most popular",
    color: "border-orange-500 ring-2 ring-orange-500",
    highlight: true,
    cta: "Get Started",
    ctaHref: "/shops/onboarding",
    features: [
      "Everything in Starter",
      "Unlimited AI call answering",
      "Appointment booking",
      "Full CRM pipeline",
      "Automated follow-up sequences",
      "Review request automation",
      "Service-area routing",
      "Priority support",
    ],
  },
  {
    name: "Pro",
    price: "Custom",
    period: "",
    tag: "Multi-location / Agency",
    color: "border-gray-200",
    cta: "Contact Sales",
    ctaHref: `tel:${HELP_PHONE}`,
    features: [
      "Everything in Growth",
      "Multi-location support",
      "Custom AI voice & persona",
      "White-label option",
      "Dedicated onboarding manager",
      "SLA + phone support",
    ],
  },
];

const COMPARISON = [
  { feature: "AI call answering", starter: true, growth: true, pro: true },
  { feature: "Missed-call text-back", starter: true, growth: true, pro: true },
  { feature: "Call summaries", starter: true, growth: true, pro: true },
  { feature: "Appointment booking", starter: false, growth: true, pro: true },
  { feature: "CRM pipeline", starter: false, growth: true, pro: true },
  { feature: "Follow-up automation", starter: false, growth: true, pro: true },
  { feature: "Review requests", starter: false, growth: true, pro: true },
  { feature: "Multi-location", starter: false, growth: false, pro: true },
  { feature: "White-label", starter: false, growth: false, pro: true },
];

const FAQS = [
  { q: "Can I keep my existing phone number?", a: "Yes. We port or forward your current number — customers dial the same number they always have." },
  { q: "Does it work after hours?", a: "Absolutely. The AI answers 24/7, including nights, weekends, and holidays." },
  { q: "Can it book appointments?", a: "Yes on Growth and Pro plans. The AI checks your availability and books directly during the call." },
  { q: "Can it send follow-up texts?", a: "Yes. Automated SMS sequences for job status, invoices, and review requests run on Growth and Pro." },
  { q: "What CRM does Roadcall Shops use?", a: "Roadcall Shops uses a purpose-built CRM and phone layer designed for shop communication, reminders, and follow-up — integrated with LC Phone for reliable SMS delivery." },
];

export default function ShopsPricingPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Hero */}
      <section className="relative min-h-[50vh] flex flex-col justify-end overflow-hidden">
        <Image
          src="https://images.unsplash.com/photo-1487754180451-c456f719a1fc?w=1920&q=80"
          alt="Mechanic at work in truck repair shop"
          fill
          priority
          className="object-cover object-center"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-black/90 z-10" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(234,88,12,0.18),transparent_70%)] z-10" />
        <div className="relative z-20 max-w-3xl mx-auto px-4 sm:px-6 w-full pb-14 pt-28 text-center">
          <span className="inline-flex items-center gap-2 bg-white/10 border border-white/20 backdrop-blur-sm text-sm font-medium px-4 py-1.5 rounded-full mb-8 text-slate-200">
            Roadcall Shops — Pricing
          </span>
          <h1 className="text-5xl md:text-6xl font-black text-white mb-4 leading-tight">Simple, transparent pricing</h1>
          <p className="text-slate-300 text-lg">Pick a plan. Set up in under 30 minutes. No contracts on entry plans.</p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {TIERS.map((t) => (
              <div key={t.name} className={`rounded-2xl border-2 p-8 flex flex-col ${t.color} ${t.highlight ? "bg-orange-50" : "bg-white"}`}>
                {t.highlight && (
                  <span className="inline-block bg-orange-600 text-white text-xs font-bold px-3 py-1 rounded-full mb-4 self-start">
                    MOST POPULAR
                  </span>
                )}
                <div className="text-sm text-gray-500 font-medium mb-2">{t.tag}</div>
                <div className="text-3xl font-bold text-gray-900 mb-1">{t.price}<span className="text-base font-normal text-gray-500">{t.period}</span></div>
                <div className="font-semibold text-xl text-gray-900 mb-6">{t.name}</div>
                <ul className="space-y-3 mb-8 flex-1">
                  {t.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle2 className="w-4 h-4 text-orange-500 flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={t.ctaHref}
                  className={`w-full text-center font-semibold py-3 rounded-lg transition-colors ${
                    t.highlight
                      ? "bg-orange-600 text-white hover:bg-orange-700"
                      : "border border-orange-600 text-orange-600 hover:bg-orange-50"
                  }`}
                >
                  {t.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">Feature comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 pr-4 font-semibold text-gray-700">Feature</th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700">Starter</th>
                  <th className="text-center py-3 px-4 font-semibold text-orange-600">Growth</th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700">Pro</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map((row) => (
                  <tr key={row.feature} className="border-b border-gray-100">
                    <td className="py-3 pr-4 text-gray-700">{row.feature}</td>
                    {([row.starter, row.growth, row.pro] as boolean[]).map((has, i) => (
                      <td key={i} className="text-center py-3 px-4">
                        {has ? <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" /> : <span className="text-gray-300">—</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">Frequently asked questions</h2>
          <div className="space-y-6">
            {FAQS.map((faq) => (
              <div key={faq.q} className="border border-gray-100 rounded-xl p-6">
                <div className="flex gap-3 mb-2">
                  <HelpCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                  <p className="font-semibold text-gray-900">{faq.q}</p>
                </div>
                <p className="text-gray-600 text-sm ml-8">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-gradient-to-r from-orange-600 to-red-600 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-2xl font-bold mb-4">Start your shop profile today</h2>
          <p className="text-orange-100 mb-6">30-day money-back guarantee on Starter and Growth plans.</p>
          <Link
            href="/shops/onboarding"
            className="bg-white text-orange-600 font-semibold px-8 py-3 rounded-lg hover:bg-orange-50 transition-colors inline-flex items-center gap-2"
          >
            Get Started <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
