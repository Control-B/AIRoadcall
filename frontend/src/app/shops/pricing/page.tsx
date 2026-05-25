"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Phone, Sparkles, Truck, Wrench } from "lucide-react";
import { GHL_GET_STARTED_URL } from "@/lib/ghl-links";

const plans = [
  {
    name: "Standard",
    price: "$297",
    setup: "$149 setup",
    target: "AI service advisor foundation for shops that need a website, AI telephone, widget, and CRM.",
    href: GHL_GET_STARTED_URL,
    features: ["Website", "AI Telephone", "AI Widget", "CRM", "Managed CRM access"],
  },
  {
    name: "Professional",
    price: "$497",
    setup: "$199 setup",
    target: "Everything in Standard plus mobile app, customer portal, and managed CRM access.",
    href: GHL_GET_STARTED_URL,
    highlighted: true,
    features: ["Everything in Standard", "Mobile App", "Customer Portal", "Managed CRM access"],
  },
  {
    name: "Advanced",
    price: "$997",
    setup: "$299 setup",
    target: "Everything in Professional plus social media marketing and content planning.",
    href: GHL_GET_STARTED_URL,
    features: ["Everything in Professional", "Social Media Marketing", "Content Planning"],
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
            <Link href={plan.href} target="_blank" rel="noreferrer" className="mt-7 inline-flex items-center justify-center rounded-xl bg-white px-5 py-3 font-black text-slate-950 hover:bg-cyan-50">
              Start {plan.name} <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </article>
        ))}
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
