"use client";

import Link from "next/link";
import {
  Phone,
  Wrench,
  Truck,
  ArrowRight,
  CheckCircle2,
  Zap,
  Shield,
  MapPin,
  MessageSquare,
  TrendingUp,
  Building2,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";

const stats = [
  { value: "35,000+", label: "Mechanics in Network" },
  { value: "50", label: "States Covered" },
  { value: "< 90s", label: "Avg Intake Call" },
  { value: "24/7", label: "Always On" },
];

const shopsFeatures = [
  { icon: Phone, title: "AI Phone Answering", description: "Every call answered instantly — day or night. Sandy captures the lead and books the job." },
  { icon: MessageSquare, title: "Missed-Call Text-Back", description: "Missed a call? The AI texts back automatically to recover the lead before they call a competitor." },
  { icon: TrendingUp, title: "CRM Pipeline", description: "Contacts, appointments, follow-ups, and review requests — all powered by GoHighLevel." },
  { icon: Building2, title: "Appointment Booking", description: "AI books directly into your calendar. No back-and-forth, no front-desk required." },
];

const fleetFeatures = [
  { icon: Truck, title: "AI Roadside Intake", description: "Driver calls in stranded. AI collects incident details in under 90 seconds, 24/7." },
  { icon: MapPin, title: "GPS Location Capture", description: "One-tap secure link sent via SMS. Driver shares exact GPS — no app download needed." },
  { icon: Wrench, title: "Mechanic Matching", description: "Score 35,000+ vendors by distance, specialty, vehicle type, and availability in real time." },
  { icon: Shield, title: "Private Data Mode", description: "Fleet data stays in your environment. No forcing enterprise incident data into third-party CRMs." },
];

const testimonials = [
  { name: "Mike's Diesel Repair", location: "Dallas, TX", vertical: "shops", quote: "We were missing 40% of after-hours calls. Now the AI picks up every one and I wake up to a list of qualified leads.", rating: 5 },
  { name: "Coastal Freight Lines", location: "Atlanta, GA", vertical: "fleet", quote: "Our drivers get a text link mid-call and share their GPS without downloading a thing. Dispatch time dropped by 60%.", rating: 5 },
  { name: "Big Rig Solutions", location: "Phoenix, AZ", vertical: "shops", quote: "One after-hours job the AI booked covered two months of the service. Paid for itself week one.", rating: 5 },
];

export default function HomePage() {
  return (
    <PageLayout>
      {/* Hero */}
      <section className="relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(234,88,12,0.18),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_50%_40%_at_80%_50%,rgba(59,130,246,0.08),transparent_50%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 rounded-full px-5 py-2 mb-8">
              <Zap className="h-4 w-4 text-orange-400" />
              <span className="text-sm font-medium text-orange-300">AI Roadside &amp; Telephony for Trucking</span>
            </div>
          </FadeIn>
          <FadeIn delay={0.1}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
              The AI Platform for<br />
              <span className="bg-gradient-to-r from-orange-400 via-amber-400 to-yellow-400 bg-clip-text text-transparent">
                Truck Mechanics &amp; Fleets
              </span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.2}>
            <p className="text-xl md:text-2xl text-slate-300 max-w-2xl mx-auto mb-14 leading-relaxed">
              Roadcall powers two things: AI phones &amp; CRM for mechanic shops, and AI roadside dispatch for fleets — under one platform.
            </p>
          </FadeIn>

          {/* Vertical split CTAs */}
          <FadeIn delay={0.3}>
            <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto mb-12">
              <Link href="/shops">
                <div className="group rounded-3xl border border-orange-500/20 bg-gradient-to-br from-orange-500/10 to-red-500/10 p-8 text-left hover:border-orange-500/40 hover:from-orange-500/15 hover:to-red-500/15 transition-all cursor-pointer">
                  <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center mb-5 shadow-lg shadow-orange-500/20">
                    <Wrench className="h-6 w-6 text-white" />
                  </div>
                  <div className="text-xs font-semibold text-orange-400 uppercase tracking-widest mb-2">Roadcall Shops</div>
                  <h2 className="text-xl font-bold text-white mb-3">AI Phones + CRM for Truck Mechanics</h2>
                  <p className="text-slate-400 text-sm mb-5">Answer every call, recover missed leads, book appointments, and manage your pipeline — powered by AI and GoHighLevel.</p>
                  <div className="flex items-center gap-2 text-orange-400 text-sm font-medium group-hover:gap-3 transition-all">
                    Connect your shop <ArrowRight className="h-4 w-4" />
                  </div>
                </div>
              </Link>
              <Link href="/fleet">
                <div className="group rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 p-8 text-left hover:border-blue-500/40 hover:from-blue-500/15 hover:to-cyan-500/15 transition-all cursor-pointer">
                  <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center mb-5 shadow-lg shadow-blue-500/20">
                    <Truck className="h-6 w-6 text-white" />
                  </div>
                  <div className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-2">Roadcall Fleet</div>
                  <h2 className="text-xl font-bold text-white mb-3">AI Roadside Support for Fleets</h2>
                  <p className="text-slate-400 text-sm mb-5">AI intake, GPS capture, mechanic matching, and dispatch visibility — without forcing your fleet data into a third-party CRM.</p>
                  <div className="flex items-center gap-2 text-blue-400 text-sm font-medium group-hover:gap-3 transition-all">
                    Book a fleet demo <ArrowRight className="h-4 w-4" />
                  </div>
                </div>
              </Link>
            </div>
          </FadeIn>

          <FadeIn delay={0.4}>
            <a href={telHref(HELP_PHONE)}>
              <Button size="lg" className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 rounded-full px-8 shadow-xl shadow-orange-600/20">
                <Phone className="h-5 w-5 mr-2" /> Call {HELP_PHONE}
              </Button>
            </a>
            <p className="text-sm text-slate-500 mt-3">Live demo line · Talk to Sandy · No signup needed</p>
          </FadeIn>
        </div>
      </section>

      {/* Stats strip */}
      <section className="border-y border-white/[0.06] bg-white/[0.02] py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-slate-400">
          {["35,000+ mechanics nationwide","All 50 states covered","No app download needed","Cancel anytime"].map((text) => (
            <div key={text} className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Roadcall Shops section */}
      <section className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <FadeIn direction="left">
              <div className="text-xs font-semibold text-orange-400 uppercase tracking-widest mb-4">Roadcall Shops</div>
              <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
                Your Shop Answers<br />
                <span className="bg-gradient-to-r from-orange-400 to-red-400 bg-clip-text text-transparent">Every Call</span>
              </h2>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                Independent truck mechanics miss up to 40% of calls. Roadcall Shops gives you an AI receptionist that never sleeps, captures every lead, and manages your entire CRM pipeline — without hiring extra staff.
              </p>
              <ul className="space-y-3 mb-10">
                {["AI phone agent answers 24/7","Missed-call text-back in seconds","Appointment booking to your calendar","CRM pipeline with automated follow-up","Review request automation"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-slate-300">
                    <CheckCircle2 className="h-5 w-5 text-orange-400 shrink-0" /> {item}
                  </li>
                ))}
              </ul>
              <Link href="/shops">
                <Button className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 rounded-full px-8">
                  Explore Roadcall Shops <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </FadeIn>
            <FadeIn direction="right">
              <div className="grid grid-cols-2 gap-4">
                {shopsFeatures.map((f) => (
                  <GlassCard key={f.title} className="p-5">
                    <f.icon className="h-7 w-7 text-orange-400 mb-3" />
                    <h3 className="text-sm font-semibold text-white mb-2">{f.title}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">{f.description}</p>
                  </GlassCard>
                ))}
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* Roadcall Fleet section */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <FadeIn direction="left" className="order-2 lg:order-1">
              <div className="grid grid-cols-2 gap-4">
                {fleetFeatures.map((f) => (
                  <GlassCard key={f.title} className="p-5">
                    <f.icon className="h-7 w-7 text-blue-400 mb-3" />
                    <h3 className="text-sm font-semibold text-white mb-2">{f.title}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">{f.description}</p>
                  </GlassCard>
                ))}
              </div>
            </FadeIn>
            <FadeIn direction="right" className="order-1 lg:order-2">
              <div className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-4">Roadcall Fleet</div>
              <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
                Roadside Support,<br />
                <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Built for Fleets</span>
              </h2>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                When your driver breaks down, every minute of downtime costs money. Roadcall Fleet automates the entire roadside intake, GPS capture, and mechanic dispatch — without routing sensitive fleet data through a third-party CRM.
              </p>
              <ul className="space-y-3 mb-10">
                {["AI driver intake in under 90 seconds","One-tap GPS location via SMS link","Matches nearest qualified mechanic instantly","Dispatch status board for your team","Your data stays in your environment"].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-slate-300">
                    <CheckCircle2 className="h-5 w-5 text-blue-400 shrink-0" /> {item}
                  </li>
                ))}
              </ul>
              <Link href="/fleet">
                <Button className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 rounded-full px-8">
                  Explore Roadcall Fleet <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="What customers say" title="Real results from shops and fleets" />
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <FadeIn key={t.name}>
                <GlassCard className="p-6 h-full flex flex-col">
                  <div className="flex gap-1 mb-4">
                    {Array.from({ length: t.rating }).map((_, i) => (
                      <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="text-slate-300 text-sm leading-relaxed flex-1 mb-4">&ldquo;{t.quote}&rdquo;</p>
                  <div>
                    <div className="text-sm font-semibold text-white">{t.name}</div>
                    <div className="text-xs text-slate-500">{t.location}</div>
                    <div className={`text-xs mt-1 font-medium ${t.vertical === "fleet" ? "text-blue-400" : "text-orange-400"}`}>
                      {t.vertical === "fleet" ? "Roadcall Fleet" : "Roadcall Shops"}
                    </div>
                  </div>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <h2 className="text-4xl md:text-5xl font-bold mb-6">Ready to get started?</h2>
            <p className="text-xl text-slate-400 mb-10">Choose your vertical and we&apos;ll have you live in minutes.</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/shops">
                <Button size="lg" className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 rounded-full px-8">
                  <Wrench className="h-5 w-5 mr-2" /> I&apos;m a Mechanic Shop
                </Button>
              </Link>
              <Link href="/fleet">
                <Button size="lg" variant="outline" className="border-blue-500/30 text-blue-300 hover:bg-blue-500/10 hover:text-blue-200 rounded-full px-8">
                  <Truck className="h-5 w-5 mr-2" /> I Manage a Fleet
                </Button>
              </Link>
            </div>
            <p className="text-slate-500 text-sm mt-6">
              Or call us directly:{" "}
              <a href={telHref(HELP_PHONE)} className="text-orange-400 hover:text-orange-300">{HELP_PHONE}</a>
            </p>
          </FadeIn>
        </div>
      </section>
    </PageLayout>
  );
}
