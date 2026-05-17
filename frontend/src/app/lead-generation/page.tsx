"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Mail, Megaphone, PhoneCall, Search, ShieldCheck, TrendingUp, Users, Wrench } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { FadeIn, GlassCard, SectionHeading } from "@/components/motion";

const leadSources = [
  {
    icon: PhoneCall,
    title: "Inbound call capture",
    copy: "AI telephony catches after-hours and missed calls, qualifies the job, and turns calls into trackable opportunities.",
  },
  {
    icon: Search,
    title: "Directory demand",
    copy: "Search and marketplace pages create high-intent provider discovery without exposing the full protected mechanic database.",
  },
  {
    icon: Mail,
    title: "Email enrichment",
    copy: "Apify/Tavily enrichment can add business emails, websites, and contact context for compliant outreach workflows.",
  },
  {
    icon: Megaphone,
    title: "Campaign follow-up",
    copy: "Roadcall can run targeted campaigns for mechanic shops, towing operators, mobile repair, and heavy-duty providers.",
  },
];

const workflow = [
  "Identify service areas and provider categories",
  "Capture inbound calls, form fills, and directory intent",
  "Enrich shop profiles with verified contact and web signals",
  "Route qualified leads to subscribed providers by plan and quota",
  "Track calls, summaries, outcomes, and follow-up status",
];

export default function LeadGenerationPage() {
  return (
    <PageLayout>
      <section className="relative overflow-hidden border-b border-roadcall-cyan/10 bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.18),transparent_34%),linear-gradient(135deg,#02050c_0%,#07101f_50%,#02050c_100%)] px-4 py-24 sm:px-6 md:py-32">
        <div className="absolute right-[-8%] top-16 h-80 w-80 rounded-full bg-emerald-400/15 blur-3xl" />
        <div className="relative mx-auto grid max-w-7xl gap-12 lg:grid-cols-[1fr_0.9fr] lg:items-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-400/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-emerald-200">
              <TrendingUp className="h-4 w-4" /> Lane 3 · AI Lead Generation
            </div>
            <h1 className="mt-8 max-w-4xl text-5xl font-black tracking-tight text-white md:text-7xl">
              Turn roadside demand into provider revenue.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-roadcall-silver/85">
              Roadcall lead generation is the growth lane: capture calls, enrich provider data,
              qualify opportunities, and route work to subscribed mechanics without exposing your full database.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/pricing">
                <Button size="lg" className="rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-400 px-8 font-bold text-slate-950 hover:brightness-110">
                  View Provider Plans <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/provider">
                <Button size="lg" variant="outline" className="rounded-xl border-white/15 bg-white/[0.04] px-8 text-white hover:bg-white/10">
                  List Your Shop
                </Button>
              </Link>
            </div>
          </FadeIn>

          <FadeIn delay={0.12}>
            <GlassCard className="p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/15 text-emerald-300">
                  <Users className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-roadcall-muted">Lead ops</p>
                  <h2 className="text-xl font-bold text-white">Capture → qualify → route</h2>
                </div>
              </div>
              <div className="mt-6 space-y-3">
                {workflow.map((item) => (
                  <div key={item} className="flex gap-3 rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm text-roadcall-silver/85">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </FadeIn>
        </div>
      </section>

      <section className="px-4 py-20 sm:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <SectionHeading
            eyebrow="Lead sources"
            title="Separate from dispatch, connected to revenue"
            description="Lead generation is not the public directory and not emergency dispatch. It is the business growth layer for providers who want more qualified work."
          />
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {leadSources.map((source, index) => (
              <FadeIn key={source.title} delay={index * 0.05}>
                <GlassCard className="h-full p-6">
                  <source.icon className="h-7 w-7 text-emerald-300" />
                  <h3 className="mt-5 text-lg font-bold text-white">{source.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-roadcall-muted">{source.copy}</p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 px-4 py-20 sm:px-6">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.28em] text-emerald-300">How it differs</p>
            <h2 className="mt-4 text-3xl font-black text-white md:text-5xl">Four lanes, one operating platform.</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["AI Roadside Dispatch", "Handles urgent roadside incidents and mechanic matching."],
              ["AI Telephony", "Answers provider phones as a Roadcall service advisor."],
              ["Lead Generation", "Creates and routes qualified opportunities for providers."],
              ["Search Directory", "Lets users discover truck service providers safely."],
            ].map(([title, copy]) => (
              <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                <ShieldCheck className="h-5 w-5 text-cyan-300" />
                <h3 className="mt-3 font-bold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-roadcall-muted">{copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
