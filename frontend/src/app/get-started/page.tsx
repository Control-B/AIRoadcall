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
    id: "starter",
    name: "Starter",
    price: "$199/mo",
    setup: "$499 setup",
    bullets: ["AI receptionist", "Up to 150 leads / mo", "Cal.com booking", "Email + SMS notifications"],
    cta: "Subscribe to Starter",
    accent: false,
  },
  {
    id: "growth",
    name: "Growth",
    price: "$399/mo",
    setup: "$499 setup",
    bullets: ["Everything in Starter", "Up to 500 leads / mo", "Service area expansion", "Priority support"],
    cta: "Subscribe to Growth",
    accent: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$799/mo",
    setup: "$499 setup",
    bullets: ["Everything in Growth", "Unlimited leads", "Custom AI prompt", "Dedicated success manager"],
    cta: "Subscribe to Pro",
    accent: false,
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
            <Link href={`/mechanic/checkout?plan=${plan.id}`} className="mt-6 block">
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
              Take the shop dashboard for a spin — no signup required.
            </p>
          </div>
        </div>
        <Link href="/mechanic/dashboard?demo=1">
          <Button
            variant="outline"
            className="border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl"
          >
            <PlayCircle className="h-4 w-4 mr-2" /> Try the demo dashboard
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
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Concierge Onboarding</span>
        </div>
        <h2 className="mt-3 text-2xl font-bold text-white">Built around your fleet.</h2>
        <p className="mt-3 text-roadcall-muted">
          Fleet pricing is custom. Tell us your fleet size, asset database state,
          and data mode (hosted, private tenant, or hybrid). Our team configures
          your AI roadside dispatcher and approved vendor network.
        </p>
        <ul className="mt-5 space-y-2 text-sm text-slate-300">
          {[
            "AI driver hotline + dispatch",
            "Approved vendor network mapping",
            "Telematics + TMS integration",
            "Hosted, private tenant, or hybrid data mode",
          ].map((bullet) => (
            <li key={bullet} className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-300 mt-0.5 flex-shrink-0" />
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
        <Link href="/fleet/onboarding" className="mt-6 block">
          <Button className="w-full bg-gradient-to-r from-roadcall-orange to-amber-500 hover:brightness-110 text-white font-bold rounded-xl py-5">
            <ArrowRight className="h-4 w-4 mr-2" /> Start fleet onboarding
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
