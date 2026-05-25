"use client";

import Link from "next/link";
import { ArrowRight, Bot, CheckCircle2, Phone, ShieldCheck, Sparkles, Truck } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { GHL_GET_STARTED_URL } from "@/lib/ghl-links";
import { HELP_PHONE, telHref } from "@/lib/phone";

const plans = [
  {
    id: "standard",
    name: "Standard",
    price: "$197",
    period: "/mo",
    setup: "$99 setup",
    description: "Core 24/7 AI service operations for mechanics.",
    features: ["AI phone answering", "AI intake", "Call summaries", "FAQ assistant", "Appointment capture", "Lead capture"],
    cta: "Start Standard",
    ghl: true,
  },
  {
    id: "professional",
    name: "Professional",
    price: "$297",
    period: "/mo",
    setup: "$149 setup",
    description: "Everything in Standard plus conversion and reputation upgrades.",
    features: ["Everything in Standard", "AI Widget", "Reviews"],
    cta: "Start Professional",
    ghl: true,
    highlighted: true,
  },
  {
    id: "advanced",
    name: "Advanced",
    price: "$397",
    period: "/mo",
    setup: "$249 setup",
    description: "Everything in Professional with a Smart Website built for booking.",
    features: ["Everything in Professional", "Smart Website"],
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
              Roadcall gives mechanic shops AI answering and managed growth plans, while Driver Pro gives owner operators premium roadside intelligence.
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
            {["AI phone answering", "Missed-call text-back", "Managed growth plans", "Driver Pro dispatch priority"].map((item) => (
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
              [ShieldCheck, "Managed Growth", "Standard, Professional, and Advanced include managed CRM onboarding."],
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
              <h2 className="mt-3 text-4xl font-black">Simple service plans plus managed growth.</h2>
            </div>
            <div className="grid gap-5 md:grid-cols-3">
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
