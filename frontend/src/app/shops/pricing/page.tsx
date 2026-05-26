"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, MapPin, Phone, Shield, Sparkles, Truck, Wrench } from "lucide-react";
import { SHOP_CHECKOUT_LINKS } from "@/lib/shop-checkout-links";

const plans = [
  {
    name: "Standard",
    price: "$197",
    setup: "$99 setup",
    target: "Core 24/7 AI Service Operations System for mechanics.",
    href: SHOP_CHECKOUT_LINKS.standard,
    features: ["AI phone answering", "AI intake", "Call summaries", "FAQ assistant", "Appointment capture", "Lead capture"],
  },
  {
    name: "Professional",
    price: "$297",
    setup: "$149 setup",
    target: "Everything in Standard plus conversion and reputation upgrades.",
    href: SHOP_CHECKOUT_LINKS.professional,
    highlighted: true,
    features: ["Everything in Standard", "AI Widget", "Reviews"],
  },
  {
    name: "Advanced",
    price: "$397",
    setup: "$249 setup",
    target: "Everything in Professional with a Smart Website built for booking.",
    href: SHOP_CHECKOUT_LINKS.advanced,
    features: ["Everything in Professional", "Smart Website"],
  },
];

const comparison = [
  ["24/7 AI Telephony", "Direct", "Voice AI answers every call, handles intake, and logs summaries."],
  ["Conversion Engine", "CRM", "Smart AI widget, appointment capture, text-back flows, and reviews."],
  ["Website Upgrade", "Fleet", "Advanced includes a Smart Website tuned for service bookings."],
];

export default function ShopsPricingPage() {
  return (
    <main className="min-h-screen bg-[#02050c] px-4 py-20 text-white">
      <section className="mx-auto max-w-7xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-orange-300/25 bg-orange-300/10 px-4 py-1.5 text-sm font-semibold text-orange-100">
          <Sparkles className="h-4 w-4 text-roadcall-orange" /> Roadcall Shops Pricing
        </div>
        <h1 className="mx-auto mt-6 max-w-4xl text-5xl font-black leading-[0.95] tracking-tight md:text-7xl">
          24/7 AI Service Operations System for Mechanics.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          Start with Standard, grow with Professional, and scale with Advanced.
        </p>
      </section>

      <section className="mx-auto mt-14 grid max-w-7xl gap-5 md:grid-cols-2 xl:grid-cols-3">
        {plans.map((plan) => (
          <article key={plan.name} className={`flex flex-col rounded-[1.5rem] border p-6 ${plan.highlighted ? "border-orange-300/50 bg-orange-300/10" : "border-white/10 bg-white/[0.035]"}`}>
            <h2 className="text-2xl font-black">{plan.name}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{plan.target}</p>
            <p className="mt-5 text-4xl font-black">{plan.price}<span className="text-sm font-semibold text-slate-400">/mo</span></p>
            <p className="mt-1 text-sm font-semibold text-orange-200">{plan.setup}</p>
            <ul className="mt-6 flex-1 space-y-2 text-sm text-slate-300">
              {plan.features.map((feature) => (
                <li key={feature} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-300" /> {feature}</li>
              ))}
            </ul>
            <Link href={plan.href} className="mt-7 inline-flex items-center justify-center rounded-xl bg-white px-5 py-3 font-black text-slate-950 hover:bg-cyan-50">
              Start {plan.name} <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </article>
        ))}
      </section>

      <section className="mx-auto mt-8 max-w-7xl rounded-[1.5rem] border border-yellow-300/25 bg-yellow-300/10 p-6">
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-yellow-300 px-3 py-1 text-xs font-black uppercase tracking-wide text-slate-950">
              <Shield className="h-3.5 w-3.5" /> Vendor Listing Upgrade
            </div>
            <h2 className="mt-4 text-3xl font-black">Roadcall Partner map badge</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Add paid placement signals to your directory profile without cluttering the map. Partner shops get a highlighted pin, hover badge, selected-provider badge, and a floating label only at close city-level zoom.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
            <p className="text-4xl font-black">$19.99<span className="text-sm font-semibold text-slate-400">/mo</span></p>
            <p className="mt-1 text-sm font-semibold text-yellow-100">Optional add-on for vendor listings</p>
            <div className="mt-5 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
              {["Partner pin ring", "Close-zoom floating badge", "Hover identity card", "Selected-provider badge"].map((feature) => (
                <div key={feature} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-300" /> {feature}</div>
              ))}
            </div>
            <Link href="/maps?partnerDemo=1&state=FL&city=Tallahassee" className="mt-6 inline-flex items-center justify-center rounded-xl border border-yellow-300/30 px-5 py-3 font-black text-yellow-100 hover:bg-yellow-300/10">
              <MapPin className="mr-2 h-4 w-4" /> Preview map badge
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-16 grid max-w-5xl gap-4 md:grid-cols-3">
        {comparison.map(([title, owner, copy]) => (
          <div key={title} className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
            <div className="flex items-center gap-2 text-cyan-200">
              {owner === "Direct" ? <Phone className="h-5 w-5" /> : owner === "CRM" ? <Wrench className="h-5 w-5" /> : <Truck className="h-5 w-5" />}
              <span className="text-xs font-bold uppercase tracking-[0.2em]">{owner}</span>
            </div>
            <h2 className="mt-4 text-lg font-black">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{copy}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
