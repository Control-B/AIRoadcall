"use client";

import Link from "next/link";
import {
  Phone,
  MessageSquare,
  TrendingUp,
  Building2,
  CheckCircle2,
  ArrowRight,
  Zap,
  Star,
  Calendar,
  Users,
  Bell,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { HELP_PHONE, telHref } from "@/lib/phone";
import roadcallRoadsideVideo from "@/assets/videos/Roadcall.Roadside.mp4";
import { mediaUrl } from "@/lib/media";

const features = [
  {
    icon: Phone,
    title: "AI Phone Answering",
    description: "Sandy answers every call instantly — day or night. Captures caller name, vehicle, issue, and books the job or escalates to you.",
  },
  {
    icon: Bell,
    title: "Missed-Call Text-Back",
    description: "When a call slips through, the AI texts back within seconds to keep the lead warm before they dial your competitor.",
  },
  {
    icon: Calendar,
    title: "Appointment Booking",
    description: "Callers book directly into your calendar during the call. No back-and-forth, no missed opportunities.",
  },
  {
    icon: Users,
    title: "CRM Contact Management",
    description: "Every caller becomes a Roadcall contact — with call notes, vehicle info, and job history auto-populated.",
  },
  {
    icon: TrendingUp,
    title: "Pipeline Automation",
    description: "Leads move automatically through your pipeline stages. Follow-up sequences trigger without you lifting a finger.",
  },
  {
    icon: MessageSquare,
    title: "Review Requests",
    description: "After a job closes, the AI sends a review request via SMS. More 5-star reviews, zero effort.",
  },
  {
    icon: BarChart3,
    title: "Call Analytics",
    description: "See every call, source, outcome, and conversion rate. Know exactly which marketing is paying off.",
  },
  {
    icon: Building2,
    title: "Shop Profile & Hours",
    description: "Configure your services, service area, business hours, and escalation contacts — Sandy adapts to your shop.",
  },
];

const howItWorks = [
  { step: "01", title: "Connect Your Shop", description: "Set up your Roadcall shop workspace. Takes under 5 minutes.", accent: "from-roadcall-orange to-roadcall-blue" },
  { step: "02", title: "Configure Sandy", description: "Set your services, hours, and escalation rules. Sandy learns your shop.", accent: "from-red-500 to-pink-500" },
  { step: "03", title: "Go Live", description: "Forward your business number to Sandy. Every call answered from minute one.", accent: "from-pink-500 to-purple-500" },
  { step: "04", title: "Watch Leads Flow", description: "Calls become contacts, contacts become jobs, jobs become revenue.", accent: "from-purple-500 to-blue-500" },
];

const plans = [
  {
    name: "Starter",
    price: "$297",
    period: "/mo",
    description: "For solo mechanics and small shops",
    features: ["AI phone answering (500 min/mo)", "Missed-call text-back", "CRM contacts & pipeline", "Appointment booking", "Email support"],
    cta: "Start Free Trial",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$597",
    period: "/mo",
    description: "For shops with high call volume",
    features: ["AI phone answering (unlimited)", "Missed-call text-back", "Full CRM + pipeline automation", "Appointment booking", "Review request automation", "Call analytics dashboard", "Priority support"],
    cta: "Start Free Trial",
    highlighted: true,
  },
  {
    name: "Agency",
    price: "Custom",
    period: "",
    description: "For multi-location or white-label",
    features: ["Everything in Pro", "Multiple locations", "White-label dashboard", "Custom AI agent voice & script", "Dedicated onboarding", "SLA support"],
    cta: "Contact Sales",
    highlighted: false,
  },
];

export default function ShopsPage() {
  return (
    <PageLayout>
      {/* Hero */}
      <section className="relative min-h-[85vh] flex flex-col justify-end overflow-hidden">
        <video
          className="absolute inset-0 h-full w-full object-cover object-center"
          src={mediaUrl("videos/Roadcall.Roadside.mp4", roadcallRoadsideVideo)}
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          aria-hidden="true"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#02050c]/60 via-[#02050c]/30 to-[#02050c] z-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#02050c]/60 via-transparent to-[#02050c]/40 z-10" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(234,88,12,0.2),transparent_70%)] z-10" />
        <div className="relative z-20 max-w-7xl mx-auto px-4 sm:px-6 w-full pb-16 pt-32 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-roadcall-panel/45 border border-roadcall-cyan/10 backdrop-blur-sm rounded-full px-4 py-1.5 mb-8">
              <Zap className="h-3.5 w-3.5 text-roadcall-orange" />
              <span className="text-xs font-medium text-roadcall-silver/85 tracking-wide">Roadcall Shops</span>
            </div>
          </FadeIn>
          <FadeIn delay={0.1}>
            <h1 className="text-6xl sm:text-7xl md:text-8xl font-black tracking-tight leading-[0.95] mb-6">
              <span className="block text-white">AI Phones + CRM</span>
              <span className="block bg-gradient-to-r from-roadcall-orange to-roadcall-cyan bg-clip-text text-transparent">for Truck Mechanics</span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.2}>
            <p className="text-lg md:text-xl text-roadcall-silver/85 max-w-2xl mx-auto mb-12 leading-relaxed">
              Stop losing jobs to voicemail. Your AI receptionist answers every call, texts back missed ones, books appointments, and runs your entire CRM pipeline — without hiring anyone.
            </p>
          </FadeIn>
          <FadeIn delay={0.3}>
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <Link href="/shops/onboarding">
                <Button size="lg" className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-semibold rounded-xl px-8 shadow-xl shadow-blue-500/20">
                  Connect Your Shop <ArrowRight className="h-5 w-5 ml-2" />
                </Button>
              </Link>
              <a href={telHref(HELP_PHONE)}>
                <Button size="lg" variant="outline" className="border-roadcall-cyan/20 bg-roadcall-panel/45 backdrop-blur-sm text-white hover:bg-roadcall-panel/60 rounded-xl px-8">
                  <Phone className="h-5 w-5 mr-2" /> Hear Sandy Live
                </Button>
              </a>
            </div>
            <p className="text-sm text-roadcall-muted">14-day free trial · No credit card · Cancel anytime</p>
          </FadeIn>
        </div>
      </section>

      {/* Social proof strip */}
      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 py-5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-roadcall-muted">
          {["Roadcall CRM included", "Roadcall AI calling", "No extra staff needed", "Works with your existing number"].map((t) => (
            <div key={t} className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-roadcall-orange" /><span>{t}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Features grid */}
      <section className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Everything You Need"
            title="Your shop's AI-powered front desk"
            description="Roadcall Shops gives you enterprise-grade CRM and AI calling without the enterprise price tag."
          />
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map((f, i) => (
              <FadeIn key={f.title} delay={i * 0.05}>
                <GlassCard className="p-6 h-full">
                  <div className="h-10 w-10 rounded-xl bg-roadcall-orange/10 border border-roadcall-orange/25 flex items-center justify-center mb-4">
                    <f.icon className="h-5 w-5 text-roadcall-orange" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{f.description}</p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="Setup in minutes" title="Live before lunch" />
          <div className="grid md:grid-cols-4 gap-6">
            {howItWorks.map((step, i) => (
              <FadeIn key={step.step} delay={i * 0.1}>
                <div className="text-center">
                  <div className={`h-14 w-14 rounded-2xl bg-gradient-to-br ${step.accent} flex items-center justify-center mx-auto mb-4 shadow-lg`}>
                    <span className="text-lg font-bold text-white">{step.step}</span>
                  </div>
                  <h3 className="font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-sm text-roadcall-muted">{step.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-24 md:py-32 border-t border-roadcall-cyan/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading eyebrow="Simple Pricing" title="One price. Everything included." />
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <FadeIn key={plan.name}>
                <div className={`rounded-3xl border p-8 flex flex-col h-full ${plan.highlighted ? "border-roadcall-orange/40 bg-gradient-to-br from-roadcall-orange/10 to-roadcall-blue/5" : "border-roadcall-cyan/10 bg-roadcall-panel/30"}`}>
                  {plan.highlighted && (
                    <div className="text-xs font-semibold text-roadcall-orange uppercase tracking-widest mb-4">Most Popular</div>
                  )}
                  <div className="mb-6">
                    <div className="text-2xl font-bold text-white">{plan.name}</div>
                    <div className="flex items-end gap-1 mt-2">
                      <span className="text-4xl font-bold text-white">{plan.price}</span>
                      <span className="text-roadcall-muted mb-1">{plan.period}</span>
                    </div>
                    <div className="text-sm text-roadcall-muted mt-1">{plan.description}</div>
                  </div>
                  <ul className="space-y-3 mb-8 flex-1">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-roadcall-silver/85">
                        <CheckCircle2 className="h-4 w-4 text-roadcall-orange shrink-0" />{f}
                      </li>
                    ))}
                  </ul>
                  <Link href={plan.cta === "Contact Sales" ? "/company#contact" : "/shops/onboarding"}>
                    <Button className={`w-full rounded-full ${plan.highlighted ? "bg-gradient-to-r from-roadcall-orange to-roadcall-blue hover:from-roadcall-orange hover:to-roadcall-blue" : "bg-roadcall-panel/60 hover:bg-white/15"}`}>
                      {plan.cta}
                    </Button>
                  </Link>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}

      {/* Bottom CTA */}
      <section className="py-24 border-t border-roadcall-cyan/10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <h2 className="text-4xl font-bold mb-4">Stop missing jobs to voicemail.</h2>
            <p className="text-roadcall-muted text-lg mb-8">Get Sandy answering your phone today.</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/shops/onboarding">
                <Button size="lg" className="bg-gradient-to-r from-roadcall-orange to-roadcall-blue hover:from-roadcall-orange hover:to-roadcall-blue rounded-full px-8">
                  Connect Your Shop <ArrowRight className="h-5 w-5 ml-2" />
                </Button>
              </Link>
              <Link href="/shops/features">
                <Button size="lg" variant="outline" className="border-white/15 bg-roadcall-panel/45 text-white hover:bg-roadcall-panel/60 rounded-full px-8">
                  See All Features
                </Button>
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>
    </PageLayout>
  );
}
