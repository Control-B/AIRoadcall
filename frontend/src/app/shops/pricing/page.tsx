"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Phone, Sparkles, Truck, Wrench } from "lucide-react";
import { GHL_GET_STARTED_URL } from "@/lib/ghl-links";

const plans = [
  {
    name: "Widget Only",
    price: "$99.99",
    setup: "$49.99 setup",
    target: "For mechanics that do not want a new website.",
    href: "/mechanic/checkout?plan=widget_only",
    category: "Simple Stripe Plan",
    features: ["AI widget", "FAQ assistant", "Appointment capture", "Lead capture", "No SaaS Mode provisioning"],
  },
  {
    name: "AI Telephony Only",
    price: "$99.99",
    setup: "$49.99 setup",
    target: "For shops that want AI phone answering without a website package.",
    href: "/mechanic/checkout?plan=ai_telephony",
    category: "Simple Stripe Plan",
    features: ["AI phone answering", "AI intake", "Missed-call text-back", "Call summaries", "No SaaS Mode provisioning"],
  },
  {
    name: "Widget + AI Telephony",
    price: "$149.99",
    setup: "$97.99 setup",
    target: "For shops that want both website widget capture and AI phone intake.",
    href: "/mechanic/checkout?plan=widget_voice",
    category: "Simple Stripe Plan",
    highlighted: true,
    features: ["AI widget", "AI phone answering", "Lead capture", "Call summaries", "No SaaS Mode provisioning"],
  },
  {
    name: "Driver Pro",
    price: "$19.99",
    setup: "No setup fee",
    target: "For owner operators and independent drivers that need AI roadside intelligence.",
    href: "/mechanic/checkout?plan=driver_pro",
    category: "Driver Membership",
    features: ["AI dispatch priority", "Saved truck profile", "Emergency roadside mode", "Live dispatch tracking", "Route-aware intelligence"],
  },
  {
    name: "Standard",
    price: "$297",
    setup: "$149 setup",
    target: "Website, AI telephone, widget, CRM, and GHL workflow foundation.",
    href: GHL_GET_STARTED_URL,
    category: "GHL SaaS Plan",
    features: ["Website", "AI telephone", "AI widget", "CRM workflows", "GHL SaaS Mode"],
  },
  {
    name: "Professional",
    price: "$497",
    setup: "$199 setup",
    target: "Everything in Standard plus mobile app and customer portal access.",
    href: GHL_GET_STARTED_URL,
    category: "GHL SaaS Plan",
    features: ["Everything in Standard", "Mobile app", "Customer portal", "Team access", "GHL SaaS Mode"],
  },
  {
    name: "Advanced",
    price: "$997",
    setup: "$299 setup",
    target: "Everything in Professional plus social media marketing and campaigns.",
    href: GHL_GET_STARTED_URL,
    category: "GHL SaaS Plan",
    features: ["Everything in Professional", "Social media marketing", "Content planning", "Campaign automation", "GHL SaaS Mode"],
  },
];

const comparison = [
  ["Simple Roadcall services", "Stripe", "Widget, AI telephony, and Driver Pro memberships."],
  ["GHL growth plans", "GHL", "Standard, Professional, and Advanced checkout/onboarding."],
  ["Fleet Operations", "Stripe", "Fleet plans live on the fleet pricing page."],
];

export default function ShopsPricingPage() {
  return (
    <main className="min-h-screen bg-[#02050c] px-4 py-20 text-white">
      <section className="mx-auto max-w-7xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-orange-300/25 bg-orange-300/10 px-4 py-1.5 text-sm font-semibold text-orange-100">
          <Sparkles className="h-4 w-4 text-roadcall-orange" /> Roadcall Shops Pricing
        </div>
        <h1 className="mx-auto mt-6 max-w-4xl text-5xl font-black leading-[0.95] tracking-tight md:text-7xl">
          AI service plans for shops, drivers, and GHL-powered growth.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          Use Stripe checkout for simple Roadcall services and Driver Pro. Use GHL for Standard, Professional, and Advanced.
        </p>
      </section>

      <section className="mx-auto mt-14 grid max-w-7xl gap-5 md:grid-cols-2 xl:grid-cols-4">
        {plans.map((plan) => (
          <article key={plan.name} className={`flex flex-col rounded-[1.5rem] border p-6 ${plan.highlighted ? "border-orange-300/50 bg-orange-300/10" : "border-white/10 bg-white/[0.035]"}`}>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">{plan.category}</p>
            <h2 className="mt-3 text-2xl font-black">{plan.name}</h2>
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

      <section className="mx-auto mt-16 grid max-w-5xl gap-4 md:grid-cols-3">
        {comparison.map(([title, owner, copy]) => (
          <div key={title} className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
            <div className="flex items-center gap-2 text-cyan-200">
              {owner === "Stripe" ? <Phone className="h-5 w-5" /> : owner === "GHL" ? <Wrench className="h-5 w-5" /> : <Truck className="h-5 w-5" />}
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
