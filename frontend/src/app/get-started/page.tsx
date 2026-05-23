"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  PlayCircle,
  Sparkles,
  Truck,
  Wrench,
} from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { GHL_GET_STARTED_URL } from "@/lib/ghl-links";
import AgentsLink from "./AgentsLink";

type Track = "shop" | "fleet";

const TRACKS: { id: Track; label: string; icon: typeof Wrench; tagline: string }[] = [
  {
    id: "shop",
    label: "Shop / Mechanic",
    icon: Wrench,
    tagline: "AI service advisor that answers calls, qualifies jobs, and books.",
  },
  {
    id: "fleet",
    label: "Fleet Manager",
    icon: Truck,
    tagline: "AI roadside dispatch for trucks, trailers, and drivers.",
  },
];

const SHOP_PLANS = [
  {
    id: "standard",
    name: "Standard",
    price: "$297/mo",
    setup: "$149 setup",
    bullets: ["Website", "AI Telephone", "AI Widget", "CRM", "GHL SaaS Mode"],
    cta: "Start Standard",
    href: GHL_GET_STARTED_URL,
  },
  {
    id: "professional",
    name: "Professional",
    price: "$497/mo",
    setup: "$199 setup",
    bullets: ["Everything in Standard", "Mobile App", "Customer Portal", "GHL SaaS Mode"],
    cta: "Start Professional",
    href: GHL_GET_STARTED_URL,
    accent: true,
  },
  {
    id: "advanced",
    name: "Advanced",
    price: "$997/mo",
    setup: "$299 setup",
    bullets: ["Everything in Professional", "Social Media Marketing", "Content Planning"],
    cta: "Start Advanced",
    href: GHL_GET_STARTED_URL,
  },
];

export default function GetStartedPage() {
  const [track, setTrack] = useState<Track>("shop");

  return (
    <PageLayout>
      <section className="min-h-[85vh] px-4 py-16">
        <div className="mx-auto max-w-6xl">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-orange/25 bg-roadcall-orange/10 px-4 py-1.5 mb-6">
              <Sparkles className="h-4 w-4 text-roadcall-orange" />
              <span className="text-sm font-medium text-orange-100">Get Started</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-black text-white mb-4">
              Activate your AI agent in minutes
            </h1>
            <p className="text-roadcall-muted max-w-2xl mx-auto leading-relaxed">
              Subscribe to launch your live AI receptionist or roadside dispatcher.
              Already a customer?
              <Link href="/sign-in" className="text-roadcall-cyan hover:text-cyan-200 underline ml-1">
                Sign in here
              </Link>
              .
            </p>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2 max-w-2xl mx-auto">
            {TRACKS.map((option) => {
              const Icon = option.icon;
              const active = track === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setTrack(option.id)}
                  className={`rounded-2xl border p-5 text-left transition ${
                    active
                      ? "border-roadcall-orange/60 bg-roadcall-orange/10"
                      : "border-slate-700/60 bg-roadcall-panel/40 hover:border-roadcall-cyan/40"
                  }`}
                >
                  <Icon className={`h-6 w-6 ${active ? "text-roadcall-orange" : "text-roadcall-cyan"}`} />
                  <p className="mt-3 font-bold text-white">{option.label}</p>
                  <p className="mt-1 text-sm text-roadcall-muted">{option.tagline}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-10">
            {track === "shop" ? <ShopSubscribe /> : <FleetSubscribe />}
          </div>
        </div>
      </section>
      <AgentsLink />
    </PageLayout>
  );
}

function ShopSubscribe() {
  return (
    <div>
      <div className="grid gap-4 md:grid-cols-3">
        {SHOP_PLANS.map((plan) => (
          <div
            key={plan.id}
            className={`rounded-[1.75rem] border p-6 flex flex-col ${
              plan.accent
                ? "border-roadcall-orange/50 bg-gradient-to-b from-roadcall-orange/10 to-transparent"
                : "border-white/10 bg-white/[0.03]"
            }`}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white">{plan.name}</h3>
              {plan.accent && (
                <span className="rounded-full bg-roadcall-orange/20 px-3 py-1 text-xs font-bold text-orange-200">
                  Most popular
                </span>
              )}
            </div>
            <p className="mt-3 text-3xl font-black text-white">{plan.price}</p>
            <p className="mt-1 text-xs text-roadcall-muted">{plan.setup}</p>
            <ul className="mt-5 space-y-2 text-sm text-slate-300 flex-1">
              {plan.bullets.map((bullet) => (
                <li key={bullet} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-300 mt-0.5 flex-shrink-0" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
            <Link href={plan.href} className="mt-6 block">
              <Button
                className={`w-full font-bold rounded-xl py-5 ${
                  plan.accent
                    ? "bg-gradient-to-r from-roadcall-orange to-amber-500 hover:brightness-110 text-white"
                    : "bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white"
                }`}
              >
                <ArrowRight className="h-4 w-4 mr-2" /> {plan.cta}
              </Button>
            </Link>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Bot className="h-6 w-6 text-roadcall-cyan flex-shrink-0" />
          <div>
            <p className="font-bold text-white">Want to see it first?</p>
            <p className="text-sm text-roadcall-muted">
              Take the Mechanics AI Profile for a spin — no signup required.
            </p>
          </div>
        </div>
        <Link href="/mechanic/dashboard?demo=1">
          <Button
            variant="outline"
            className="border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl"
          >
            <PlayCircle className="h-4 w-4 mr-2" /> Try the Mechanics AI Profile
          </Button>
        </Link>
      </div>
    </div>
  );
}

function FleetSubscribe() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="rounded-[1.75rem] border border-roadcall-orange/40 bg-gradient-to-b from-roadcall-orange/10 to-transparent p-7">
        <div className="flex items-center gap-2 text-roadcall-orange">
          <Truck className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Fleet subscriptions paused</span>
        </div>
        <h2 className="mt-3 text-2xl font-bold text-white">Fleet plans are on hold for now.</h2>
        <p className="mt-3 text-roadcall-muted">
          Roadcall is focusing on AI roadside support and mechanic shop growth before opening fleet subscriptions more broadly.
        </p>
        <div className="mt-5 rounded-xl border border-white/10 bg-black/25 p-4 text-sm leading-6 text-slate-300">
          Existing fleet product pages, demos, and internal workflows remain available for validation, but public fleet pricing is not being offered yet.
        </div>
        <Link href="/fleet/onboarding" className="mt-6 block">
          <Button variant="outline" className="w-full border-roadcall-orange/40 text-orange-100 hover:bg-roadcall-orange/10 font-bold rounded-xl py-5">
            <ArrowRight className="h-4 w-4 mr-2" /> Request fleet waitlist review
          </Button>
        </Link>
      </div>

      <div className="rounded-[1.75rem] border border-white/10 bg-black/30 p-7">
        <div className="flex items-center gap-2 text-roadcall-cyan">
          <Bot className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Fleet AI Demo</span>
        </div>
        <h2 className="mt-3 text-2xl font-bold text-white">Preview the dispatcher console.</h2>
        <p className="mt-3 text-roadcall-muted">
          See sample incidents, AI dispatcher status, vehicle and driver
          rosters, and vendor coverage — without onboarding first.
        </p>
        <Link href="/fleet/dashboard?demo=1" className="mt-6 block">
          <Button
            variant="outline"
            className="w-full border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl py-5"
          >
            <PlayCircle className="h-4 w-4 mr-2" /> Try the fleet demo dashboard
          </Button>
        </Link>
        <p className="mt-5 text-xs text-roadcall-muted">
          Already onboarded?{" "}
          <Link href="/sign-in" className="text-roadcall-cyan hover:text-cyan-200 underline">
            Sign in to your console
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
