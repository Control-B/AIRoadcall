"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Phone,
  ArrowRight,
  Zap,
  Globe,
  Users,
  Target,
  Heart,
  Lightbulb,
  Mail,
  MapPin,
  Wrench,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, SectionHeading, GlassCard } from "@/components/motion";
import { COMPANY_PHONE, HELP_PHONE, telHref } from "@/lib/phone";

/* ── Timeline ────────────────────────────────────────────────── */

const timeline = [
  {
    year: "2024",
    title: "The Problem",
    description:
      "We noticed that getting roadside help still meant 20 minutes on hold, repeating your info three times, and hoping someone showed up. Traditional dispatch was broken.",
  },
  {
    year: "2024",
    title: "The Prototype",
    description:
      "Built the first AI dispatcher — an agent that could take a call, extract vehicle info, and find the nearest mechanic in seconds. Tested it with 50 shops.",
  },
  {
    year: "2025",
    title: "Nationwide Launch",
    description:
      "Scaled to 35,000+ mechanics across all 50 US states. Added SMS magic links, Stripe payments, live tracking, and a full admin dashboard.",
  },
  {
    year: "2025",
    title: "What's Next",
    description:
      "Fleet management, EV-specific dispatch, predictive maintenance alerts, and international expansion. The AI dispatcher that never sleeps.",
  },
];

/* ── Values ──────────────────────────────────────────────────── */

const values = [
  {
    icon: Target,
    title: "Speed Above All",
    description:
      "Every second matters when you're stranded. We obsess over reducing time-to-dispatch.",
  },
  {
    icon: Heart,
    title: "Human-Centered AI",
    description:
      "Our AI sounds human, acts with empathy, and knows when to hand off to a real person.",
  },
  {
    icon: Lightbulb,
    title: "Relentless Simplicity",
    description:
      "No app downloads. No signup forms. One phone call and one text message — that's it.",
  },
  {
    icon: Users,
    title: "Network Effect",
    description:
      "Every new mechanic makes the network better for every driver. We grow together.",
  },
];

/* ── Company facts ───────────────────────────────────────────── */

const companyFacts = [
  { icon: Globe, label: "Parent Company", value: "Omniweb, LLC" },
  { icon: Wrench, label: "Product", value: "Roadcall.ai — AI Roadside Dispatch" },
  { icon: MapPin, label: "Coverage", value: "All 50 US States" },
  { icon: Users, label: "Mechanic Network", value: "35,000+ shops & mobile services" },
  { icon: Mail, label: "Contact", value: "support@roadcall.ai" },
  { icon: Phone, label: "Company Number", value: COMPANY_PHONE },
  { icon: Phone, label: "Help Line", value: HELP_PHONE },
];

/* ── Page ─────────────────────────────────────────────────────── */

export default function CompanyPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    message: "",
  });
  const [formSubmitted, setFormSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: wire to actual API
    setFormSubmitted(true);
  };

  return (
    <PageLayout>
      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(234,88,12,0.12),transparent_60%)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/20 rounded-full px-5 py-2 mb-8">
              <Zap className="h-4 w-4 text-orange-400" />
              <span className="text-sm font-medium text-orange-300">
                About Roadcall.ai
              </span>
            </div>
          </FadeIn>

          <FadeIn delay={0.1}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
              Roadside rescue,
              <br />
              <span className="bg-gradient-to-r from-orange-400 via-amber-400 to-yellow-400 bg-clip-text text-transparent">
                reimagined with AI
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={0.2}>
            <p className="text-xl md:text-2xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
              We&apos;re building the AI infrastructure that makes roadside
              help instant, affordable, and reliable — for drivers and
              mechanics alike.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ── About + Company facts ─────────────────────── */}
      <section
        id="about"
        className="py-24 md:py-32 border-t border-white/[0.06]"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-16 items-start">
            <FadeIn direction="right">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-orange-400 mb-4">
                  Our Story
                </p>
                <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
                  Why we built Roadcall.ai
                </h2>
                <div className="space-y-5 text-slate-400 leading-relaxed">
                  <p>
                    Roadcall.ai is built by{" "}
                    <span className="text-white font-medium">
                      Omniweb, LLC
                    </span>{" "}
                    — an AI company focused on voice agents, chat assistants,
                    and workflow automation for service businesses.
                  </p>
                  <p>
                    We started with a simple question: why does getting
                    roadside help still involve 20 minutes on hold,
                    repeating your info three times, and hoping someone
                    shows up?
                  </p>
                  <p>
                    So we built an AI dispatcher that picks up instantly,
                    collects the right info in 90 seconds, finds the best
                    nearby mechanic, and gets them rolling — all without a
                    human operator.
                  </p>
                  <p>
                    Our network covers{" "}
                    <span className="text-white font-medium">
                      35,000+ mechanics across all 50 states
                    </span>
                    , scored by distance, specialty, rating, and
                    availability.
                  </p>
                </div>
              </div>
            </FadeIn>

            <FadeIn direction="left">
              <GlassCard className="p-8">
                <h3 className="text-lg font-semibold mb-6">Company</h3>
                <div className="space-y-5">
                  {companyFacts.map((item) => (
                    <div key={item.label} className="flex items-start gap-4">
                      <div className="h-9 w-9 rounded-lg bg-white/[0.05] flex items-center justify-center shrink-0">
                        <item.icon className="h-4 w-4 text-slate-400" />
                      </div>
                      <div>
                        <div className="text-xs text-slate-500">
                          {item.label}
                        </div>
                        <div className="text-sm font-medium text-white">
                          {item.value}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ── Timeline ──────────────────────────────────── */}
      <section className="py-24 md:py-32 bg-gradient-to-b from-white/[0.02] to-transparent border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Our Journey"
            title="From idea to 50-state coverage"
          />

          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-orange-500/40 via-orange-500/20 to-transparent" />

            <div className="space-y-12">
              {timeline.map((item, idx) => (
                <FadeIn
                  key={idx}
                  delay={idx * 0.1}
                  direction={idx % 2 === 0 ? "right" : "left"}
                >
                  <div
                    className={`relative grid md:grid-cols-2 gap-8 md:gap-16 ${
                      idx % 2 === 1 ? "md:text-right" : ""
                    }`}
                  >
                    {/* Dot */}
                    <div className="absolute left-8 md:left-1/2 top-0 -translate-x-1/2">
                      <div className="h-4 w-4 rounded-full bg-orange-500 ring-4 ring-[#050a14]" />
                    </div>

                    <div
                      className={`pl-20 md:pl-0 ${
                        idx % 2 === 1 ? "md:order-2 md:pl-16" : "md:pr-16"
                      }`}
                    >
                      <span className="text-sm font-bold text-orange-400">
                        {item.year}
                      </span>
                      <h3 className="text-xl font-bold text-white mt-1 mb-2">
                        {item.title}
                      </h3>
                      <p className="text-slate-400 leading-relaxed">
                        {item.description}
                      </p>
                    </div>

                    {/* Empty cell for grid alignment */}
                    <div
                      className={`hidden md:block ${
                        idx % 2 === 1 ? "md:order-1" : ""
                      }`}
                    />
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Values ────────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Our Values"
            title="What drives us"
          />

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {values.map((val, idx) => (
              <FadeIn key={val.title} delay={idx * 0.1}>
                <GlassCard className="p-7 h-full text-center">
                  <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-orange-500/20 to-red-500/20 border border-orange-500/10 flex items-center justify-center mb-5 mx-auto">
                    <val.icon className="h-7 w-7 text-orange-400" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2 text-white">
                    {val.title}
                  </h3>
                  <p className="text-slate-400 leading-relaxed text-[15px]">
                    {val.description}
                  </p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Contact form ──────────────────────────────── */}
      <section
        id="contact"
        className="py-24 md:py-32 bg-gradient-to-b from-white/[0.02] to-transparent border-t border-white/[0.06]"
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <SectionHeading
            eyebrow="Contact"
            title="Get in touch"
            description="Have a question, want a demo, or interested in partnering? Drop us a line."
          />

          <FadeIn>
            <div className="grid md:grid-cols-2 gap-12">
              {/* Form */}
              <GlassCard className="p-8">
                {formSubmitted ? (
                  <div className="flex flex-col items-center justify-center h-full py-10">
                    <CheckCircle2 className="h-16 w-16 text-emerald-400 mb-4" />
                    <h3 className="text-xl font-bold text-white mb-2">
                      Message sent!
                    </h3>
                    <p className="text-slate-400 text-center">
                      We&apos;ll get back to you within 24 hours.
                    </p>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Name
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.name}
                        onChange={(e) =>
                          setFormData({ ...formData, name: e.target.value })
                        }
                        className="w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-slate-500 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-colors"
                        placeholder="Your name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Email
                      </label>
                      <input
                        type="email"
                        required
                        value={formData.email}
                        onChange={(e) =>
                          setFormData({ ...formData, email: e.target.value })
                        }
                        className="w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-slate-500 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-colors"
                        placeholder="you@company.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Company{" "}
                        <span className="text-slate-500">(optional)</span>
                      </label>
                      <input
                        type="text"
                        value={formData.company}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            company: e.target.value,
                          })
                        }
                        className="w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-slate-500 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-colors"
                        placeholder="Your shop or company"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Message
                      </label>
                      <textarea
                        required
                        rows={4}
                        value={formData.message}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            message: e.target.value,
                          })
                        }
                        className="w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-slate-500 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-colors resize-none"
                        placeholder="How can we help?"
                      />
                    </div>
                    <Button
                      type="submit"
                      className="w-full bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 rounded-xl shadow-lg shadow-orange-600/20"
                      size="lg"
                    >
                      Send Message
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </form>
                )}
              </GlassCard>

              {/* Contact info */}
              <div className="space-y-8">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">
                    Other ways to reach us
                  </h3>
                  <div className="space-y-4">
                    <a
                      href="mailto:support@roadcall.ai"
                      className="flex items-center gap-3 text-slate-400 hover:text-orange-400 transition-colors group"
                    >
                      <div className="h-10 w-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center group-hover:border-orange-500/30 transition-colors">
                        <Mail className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">
                          Email
                        </div>
                        <div className="text-sm">support@roadcall.ai</div>
                      </div>
                    </a>

                    <a
                      href={telHref(COMPANY_PHONE)}
                      className="flex items-center gap-3 text-slate-400 hover:text-orange-400 transition-colors group"
                    >
                      <div className="h-10 w-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center group-hover:border-orange-500/30 transition-colors">
                        <Phone className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">
                          Company Number
                        </div>
                        <div className="text-sm">{COMPANY_PHONE}</div>
                      </div>
                    </a>

                    <a
                      href={telHref(HELP_PHONE)}
                      className="flex items-center gap-3 text-slate-400 hover:text-orange-400 transition-colors group"
                    >
                      <div className="h-10 w-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center group-hover:border-orange-500/30 transition-colors">
                        <Phone className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">
                          Help Line
                        </div>
                        <div className="text-sm">{HELP_PHONE}</div>
                      </div>
                    </a>

                    <div className="flex items-center gap-3 text-slate-400">
                      <div className="h-10 w-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center">
                        <MapPin className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">
                          Coverage
                        </div>
                        <div className="text-sm">
                          All 50 US States
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <GlassCard className="p-6">
                  <h4 className="text-sm font-semibold text-white mb-3">
                    For mechanic shops
                  </h4>
                  <p className="text-sm text-slate-400 mb-4 leading-relaxed">
                    Want Roadcall.ai answering your shop&apos;s calls? Start
                    a free 14-day trial — no credit card needed.
                  </p>
                  <Link href="/pricing">
                    <Button
                      size="sm"
                      variant="outline"
                      className="rounded-full border-white/20 text-white hover:bg-white/5"
                    >
                      View Plans
                      <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                    </Button>
                  </Link>
                </GlassCard>

                <GlassCard className="p-6">
                  <h4 className="text-sm font-semibold text-white mb-3">
                    Partnership inquiries
                  </h4>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    Fleet operator, franchise, or towing network? Let&apos;s
                    talk about custom integrations and volume pricing.
                  </p>
                </GlassCard>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="py-24 md:py-32 border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <FadeIn>
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-orange-600/10 via-red-600/5 to-transparent p-12 md:p-16 relative overflow-hidden">
              <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-orange-600/10 blur-[80px]" />
              <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-red-600/10 blur-[80px]" />
              <div className="relative z-10">
                <h2 className="text-3xl md:text-5xl font-bold mb-6">
                  Ready to get started?
                </h2>
                <p className="text-xl text-slate-300 mb-10 max-w-xl mx-auto">
                  Experience the AI dispatcher firsthand. One call. 60
                  seconds. Zero obligation.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <a href={telHref(HELP_PHONE)}>
                    <Button
                      size="xl"
                      className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-xl gap-3 rounded-2xl shadow-xl shadow-orange-600/20"
                    >
                      <Phone className="h-6 w-6" />
                      Call {HELP_PHONE}
                    </Button>
                  </a>
                  <Link href="/pricing">
                    <Button
                      size="lg"
                      variant="outline"
                      className="rounded-full border-white/20 text-white hover:bg-white/5 px-8"
                    >
                      View Pricing
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>
    </PageLayout>
  );
}
