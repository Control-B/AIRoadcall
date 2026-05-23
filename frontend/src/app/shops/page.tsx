"use client";

import Link from "next/link";
import { ArrowRight, Bot, CheckCircle2, Phone, ShieldCheck, Sparkles, Truck } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { GHL_GET_STARTED_URL } from "@/lib/ghl-links";
import { HELP_PHONE, telHref } from "@/lib/phone";

const plans = [
  {
    id: "widget_only",
    name: "Widget Only",
    price: "$99.99",
    period: "/mo",
    setup: "$49.99 setup",
    description: "AI widget for mechanics that do not want a new website.",
    features: ["AI widget", "FAQ assistant", "Appointment capture", "Lead capture"],
    cta: "Start Widget Only",
  },
  {
    id: "ai_telephony",
    name: "AI Telephony Only",
    price: "$99.99",
    period: "/mo",
    setup: "$49.99 setup",
    description: "AI answering and intake without a website or widget package.",
    features: ["AI phone answering", "AI intake", "Missed-call text-back", "Call summaries"],
    cta: "Start AI Telephony",
  },
  {
    id: "widget_voice",
    name: "Widget + AI Telephony",
    price: "$149.99",
    period: "/mo",
    setup: "$97.99 setup",
    description: "AI widget plus AI phone answering for shops that do not need GHL.",
    features: ["AI widget", "AI phone answering", "Lead capture", "Call summaries"],
    cta: "Start Widget + AI Telephony",
    highlighted: true,
  },
  {
    id: "driver_pro",
    name: "Driver Pro",
    price: "$19.99",
    period: "/mo",
    setup: "No setup fee",
    description: "AI roadside intelligence membership for owner operators and independent drivers.",
    features: ["AI dispatch priority", "Saved truck profile", "Emergency roadside mode", "Live dispatch tracking"],
    cta: "Start Driver Pro",
  },
  {
    id: "standard",
    name: "Standard",
    price: "$297",
    period: "/mo",
    setup: "$149 setup",
    description: "GHL website, AI telephone, widget, CRM, and workflow foundation.",
    features: ["Website", "AI telephone", "AI widget", "CRM workflows"],
    cta: "Start Standard",
    ghl: true,
  },
  {
    id: "professional",
    name: "Professional",
    price: "$497",
    period: "/mo",
    setup: "$199 setup",
    description: "Everything in Standard plus mobile app access.",
    features: ["Everything in Standard", "Mobile app", "Customer portal", "GHL SaaS Mode"],
    cta: "Start Professional",
    ghl: true,
  },
  {
    id: "advanced",
    name: "Advanced",
    price: "$997",
    period: "/mo",
    setup: "$299 setup",
    description: "Everything in Professional plus social media marketing.",
    features: ["Everything in Professional", "Social media marketing", "Content planning", "GHL SaaS Mode"],
    cta: "Start Advanced",
    ghl: true,
  },
];

export default function ShopsPage() {
  return (
    <PageLayout>
      <main className="min-h-screen bg-[#02050c] text-white">
        <section className="relative overflow-hidden px-4 pb-16 pt-24">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(234,88,12,0.22),transparent_30%),radial-gradient(circle_at_85%_5%,rgba(20,216,255,0.18),transparent_28%)]" />
          <div className="relative mx-auto max-w-7xl text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-orange-300/25 bg-orange-300/10 px-4 py-1.5 text-sm font-semibold text-orange-100">
              <Sparkles className="h-4 w-4 text-roadcall-orange" /> Roadcall Shops
            </div>
            <h1 className="mx-auto mt-6 max-w-4xl text-5xl font-black leading-[0.95] tracking-tight md:text-7xl">
              AI phones, widgets, CRM, and roadside intelligence.
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              Roadcall gives mechanic shops AI answering and GHL-powered growth plans, while Driver Pro gives owner operators premium roadside intelligence.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link href="/shops/pricing">
                <Button className="rounded-xl bg-gradient-to-r from-roadcall-orange to-roadcall-cyan px-7 py-6 font-black text-white hover:brightness-110">
                  View Plans <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <a href={telHref(HELP_PHONE)}>
                <Button variant="outline" className="rounded-xl border-white/15 bg-white/5 px-7 py-6 text-white hover:bg-white/10">
                  <Phone className="mr-2 h-4 w-4" /> Hear Sandy Live
                </Button>
              </a>
            </div>
          </div>
        </section>

        <section className="border-y border-white/10 bg-white/[0.03] px-4 py-5">
          <div className="mx-auto flex max-w-7xl flex-wrap justify-center gap-x-8 gap-y-3 text-sm text-slate-300">
            {["AI phone answering", "Missed-call text-back", "GHL growth plans", "Driver Pro dispatch priority"].map((item) => (
              <span key={item} className="inline-flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-300" /> {item}</span>
            ))}
          </div>
        </section>

        <section className="px-4 py-16">
          <div className="mx-auto grid max-w-7xl gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              [Bot, "AI Intake", "Capture caller, vehicle, issue, location, and urgency before a human picks up."],
              [Phone, "AI Telephony", "Answer every call, summarize every conversation, and text back missed calls."],
              [Truck, "Driver Pro", "Unlock saved truck profiles, emergency mode, route intelligence, and live dispatch tracking."],
              [ShieldCheck, "GHL Growth", "Standard, Professional, and Advanced run through GHL SaaS Mode and onboarding."],
            ].map(([Icon, title, copy]) => (
              <div key={title as string} className="rounded-2xl border border-white/10 bg-slate-950/70 p-6">
                <Icon className="h-6 w-6 text-cyan-300" />
                <h2 className="mt-4 text-xl font-black">{title as string}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{copy as string}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="px-4 pb-24">
          <div className="mx-auto max-w-7xl">
            <div className="mb-8 text-center">
              <p className="text-sm font-bold uppercase tracking-[0.22em] text-cyan-200">Hybrid Pricing</p>
              <h2 className="mt-3 text-4xl font-black">Simple Stripe plans plus GHL-powered growth.</h2>
            </div>
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              {plans.map((plan) => (
                <article key={plan.id} className={`flex flex-col rounded-[1.5rem] border p-6 ${plan.highlighted ? "border-orange-300/50 bg-orange-300/10" : "border-white/10 bg-white/[0.035]"}`}>
                  <h3 className="text-xl font-black">{plan.name}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{plan.description}</p>
                  <p className="mt-5 text-4xl font-black">{plan.price}<span className="text-sm font-semibold text-slate-400">{plan.period}</span></p>
                  <p className="mt-1 text-sm font-semibold text-orange-200">{plan.setup}</p>
                  <ul className="mt-5 flex-1 space-y-2 text-sm text-slate-300">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-300" /> {feature}</li>
                    ))}
                  </ul>
                  <Link href={plan.ghl ? GHL_GET_STARTED_URL : `/mechanic/checkout?plan=${plan.id}`} className="mt-6 inline-flex items-center justify-center rounded-xl bg-white px-5 py-3 font-black text-slate-950 hover:bg-cyan-50">
                    {plan.cta} <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>
    </PageLayout>
  );
}
