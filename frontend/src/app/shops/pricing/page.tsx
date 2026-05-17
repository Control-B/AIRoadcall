"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bot,
  CalendarClock,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Cpu,
  Gauge,
  Globe2,
  Headphones,
  HelpCircle,
  MapPin,
  MessageSquare,
  Mic2,
  Network,
  Phone,
  Radio,
  Route,
  ShieldCheck,
  Sparkles,
  Truck,
  Volume2,
  Wrench,
  Zap,
} from "lucide-react";

const TRUST = [
  { icon: Clock3, label: "24/7 AI Answering" },
  { icon: Globe2, label: "Multilingual AI" },
  { icon: Route, label: "AI Dispatch Workflows" },
  { icon: MessageSquare, label: "Missed Call Text Back" },
  { icon: Wrench, label: "Built for Roadside Operations" },
];

const PLANS = [
  {
    name: "Starter",
    price: "$149",
    setup: "$99 AI setup",
    target: "Small mechanics and mobile roadside businesses",
    icon: Headphones,
    accent: "from-sky-400 to-blue-500",
    cta: "Start Starter Plan",
    href: "/mechanic/checkout?plan=starter",
    features: [
      "24/7 AI phone answering",
      "Missed call text back",
      "AI call summaries",
      "Multilingual support",
      "Basic CRM pipeline",
      "SMS follow-up",
      "Website AI widget",
      "Business hours automation",
      "Lead capture",
      "Customer intake automation",
    ],
  },
  {
    name: "Growth",
    price: "$299",
    setup: "$99 AI setup",
    target: "Growing diesel shops, towing companies, and repair teams",
    icon: Mic2,
    accent: "from-roadcall-orange via-amber-400 to-blue-400",
    badge: "Most Popular",
    cta: "Start Growth Plan",
    href: "/mechanic/checkout?plan=growth",
    features: [
      "Everything in Starter",
      "Advanced AI voice workflows",
      "Appointment scheduling",
      "Smart call routing",
      "Website voice assistant",
      "AI lead qualification",
      "Advanced analytics",
      "Team notifications",
      "Custom workflows",
      "AI customer follow-up",
      "Review automation",
      "Multi-location support",
      "Priority onboarding",
    ],
  },
  {
    name: "Pro",
    price: "$499",
    setup: "$99 AI setup",
    target: "Roadside service providers ready to operationalize dispatch",
    icon: Radio,
    accent: "from-roadcall-orange to-roadcall-blue",
    cta: "Start Pro Plan",
    href: "/mechanic/checkout?plan=pro",
    features: [
      "Everything in Growth",
      "AI roadside intake",
      "SMS GPS capture",
      "Dispatch workflows",
      "Driver intake automation",
      "Mechanic assignment workflows",
      "Fleet notifications",
      "Dispatch dashboard",
      "Emergency call routing",
      "Real-time roadside workflows",
      "API-ready infrastructure",
    ],
  },
];

const ADD_ONS = [
  { icon: Sparkles, title: "AI Website Setup", copy: "Launch a conversion-ready site with AI voice and chat intake." },
  { icon: Phone, title: "Additional Phone Numbers", copy: "Dedicated lines for service areas, locations, and campaigns." },
  { icon: Volume2, title: "Custom Voice Training", copy: "Train the AI to sound like your dispatcher or brand voice." },
  { icon: Network, title: "Enterprise Integrations", copy: "Connect calendars, CRM systems, forms, APIs, and fleet tools." },
  { icon: Truck, title: "Fleet Portal Setup", copy: "Give fleet accounts structured intake and reporting workflows." },
  { icon: Bot, title: "AI Knowledge Base Training", copy: "Load services, pricing rules, coverage areas, and policies." },
  { icon: ShieldCheck, title: "White Label Deployment", copy: "Deploy branded AI telephony for multi-location operators." },
];

const COMPARISON = [
  ["24/7 AI coverage", "Always on", "Limited shifts"],
  ["Multilingual intake", "Built in", "Usually unavailable"],
  ["Instant response", "Answers immediately", "Hold queues and callbacks"],
  ["No hold times", "AI handles spikes", "Staffing bottlenecks"],
  ["Dispatch workflows", "Roadside-ready", "Message taking only"],
  ["AI summaries", "Structured call notes", "Manual notes"],
  ["CRM automation", "Follow-up and review flows", "Separate admin work"],
  ["Roadside specialization", "Mechanic, towing, fleet logic", "Generic operators"],
];

const ROI_STATS = [
  { value: "$350+", label: "average roadside ticket value", icon: Gauge },
  { value: "24/7", label: "availability for after-hours emergencies", icon: Clock3 },
  { value: "0s", label: "hold time before AI intake starts", icon: Zap },
  { value: "100%", label: "captured call summaries and lead details", icon: BarChart3 },
];

const FAQS = [
  ["How does AI roadside intake work?", "The AI answers the call, captures the vehicle, breakdown details, location context, urgency, and customer information, then routes the workflow to your team."],
  ["Can I keep my existing phone number?", "Yes. You can forward calls, port a number, or use a dedicated Roadcall AI number while keeping your customer-facing brand intact."],
  ["Does it support multiple languages?", "Yes. Roadcall AI can handle multilingual intake so after-hours and emergency callers can still be understood and routed."],
  ["Can the AI schedule appointments?", "Yes. AI Telephony Pro and Dispatch Lite can schedule service appointments and notify your team instantly."],
  ["How long does onboarding take?", "AI Receptionist can launch quickly after setup details are collected. Pro and Dispatch deployments include workflow configuration and testing."],
  ["Can I upgrade later?", "Yes. You can start with AI answering, then add advanced telephony, dispatch workflows, fleet portals, and integrations as call volume grows."],
  ["Does it work after business hours?", "Yes. The platform is designed for nights, weekends, holidays, and emergency roadside calls when missed calls are most expensive."],
  ["Can it integrate with my website?", "Yes. Roadcall AI can add website voice/chat intake, forms, lead routing, and service-area workflows."],
];

function fadeUp(delay = 0) {
  return {
    initial: { opacity: 0, y: 24 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px" },
    transition: { duration: 0.65, delay, ease: [0.16, 1, 0.3, 1] as const },
  };
}

export default function ShopsPricingPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#02050c] text-white selection:bg-roadcall-orange/30 selection:text-white">
      <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_10%,rgba(37,99,235,0.22),transparent_30%),radial-gradient(circle_at_78%_8%,rgba(234,88,12,0.18),transparent_28%),linear-gradient(180deg,#02050c_0%,#07111f_46%,#02050c_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:72px_72px] opacity-20" />
      </div>

      <section className="relative z-10 px-4 pb-16 pt-28 sm:px-6 lg:pb-24 lg:pt-36">
        <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[1.02fr_0.98fr]">
          <motion.div {...fadeUp()}>
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-400/10 px-4 py-2 text-sm font-medium text-blue-100 shadow-[0_0_40px_rgba(37,99,235,0.12)] backdrop-blur-xl">
              <Activity className="h-4 w-4 text-roadcall-orange" />
              AI telephony for roadside revenue operations
            </div>
            <h1 className="max-w-4xl text-5xl font-black tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl">
              Never Miss Another Roadside Call.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-roadcall-silver/85 sm:text-xl">
              AI-powered telephony and roadside operations built for truck mechanics, towing companies,
              and roadside service providers.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/shops/onboarding"
                className="group inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-4 text-sm font-bold text-slate-950 shadow-[0_0_45px_rgba(255,255,255,0.18)] transition hover:-translate-y-0.5 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                Start Free Trial <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
              </Link>
              <Link
                href="/demo"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-roadcall-panel/45 px-6 py-4 text-sm font-bold text-white backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-roadcall-cyan/50 hover:bg-roadcall-cyan/10 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan"
              >
                Book Demo <CalendarClock className="h-4 w-4 text-roadcall-orange" />
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {TRUST.map(({ icon: Icon, label }) => (
                <span key={label} className="inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/10 bg-roadcall-panel/35 px-3 py-2 text-xs font-medium text-roadcall-silver/85 backdrop-blur-xl">
                  <Icon className="h-3.5 w-3.5 text-blue-300" />
                  {label}
                </span>
              ))}
            </div>
          </motion.div>

          <motion.div {...fadeUp(0.12)} className="relative">
            <div className="absolute -inset-8 rounded-[3rem] bg-[radial-gradient(circle,rgba(37,99,235,0.25),transparent_58%)] blur-2xl" aria-hidden="true" />
            <div className="relative rounded-[2rem] border border-roadcall-cyan/10 bg-white/[0.055] p-3 shadow-2xl backdrop-blur-2xl">
              <div className="rounded-[1.5rem] border border-roadcall-cyan/10 bg-[#06101e]/90 p-4">
                <div className="mb-4 flex items-center justify-between border-b border-roadcall-cyan/10 pb-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-roadcall-muted/70">Roadcall Command</p>
                    <p className="mt-1 text-lg font-bold">Live AI Intake Console</p>
                  </div>
                  <div className="flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-300" />
                    Online
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-blue-400/15 bg-blue-400/10 p-4">
                    <div className="mb-5 flex items-center gap-2 text-sm font-semibold text-blue-100">
                      <Phone className="h-4 w-4" /> Incoming roadside call
                    </div>
                    <div className="space-y-3">
                      {["Caller: FreightPro Driver", "Issue: Air leak", "Vehicle: Class 8 tractor"].map((item) => (
                        <div key={item} className="rounded-xl bg-roadcall-panel/50 px-3 py-2 text-xs text-roadcall-silver/85">{item}</div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-roadcall-orange/25 bg-roadcall-orange/10 p-4">
                    <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-roadcall-orange">
                      <MapPin className="h-4 w-4" /> Dispatch workflow
                    </div>
                    <div className="space-y-2">
                      {[
                        ["GPS link sent", "complete"],
                        ["Mechanic match", "running"],
                        ["ETA notification", "queued"],
                      ].map(([label, status]) => (
                        <div key={label} className="flex items-center justify-between rounded-xl bg-black/20 px-3 py-2 text-xs">
                          <span className="text-roadcall-silver/85">{label}</span>
                          <span className={status === "complete" ? "text-emerald-300" : status === "running" ? "text-roadcall-orange" : "text-roadcall-muted/70"}>{status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="mt-3 rounded-2xl border border-roadcall-cyan/10 bg-black/20 p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-semibold text-roadcall-silver">
                      <Volume2 className="h-4 w-4 text-blue-300" /> AI voice waveform
                    </div>
                    <span className="text-xs text-roadcall-muted/70">00:42 active call</span>
                  </div>
                  <div className="flex h-20 items-center gap-1 overflow-hidden" aria-hidden="true">
                    {Array.from({ length: 44 }).map((_, index) => (
                      <motion.span
                        key={index}
                        animate={{ height: [14, 54 - (index % 7) * 4, 18] }}
                        transition={{ duration: 1.15, repeat: Infinity, delay: index * 0.025 }}
                        className="w-1 flex-1 rounded-full bg-gradient-to-t from-blue-500 via-cyan-300 to-orange-300 opacity-80"
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="pricing" className="relative z-10 px-4 py-16 sm:px-6 lg:py-24">
        <motion.div {...fadeUp()} className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-bold uppercase tracking-[0.3em] text-roadcall-orange">Roadside AI Pricing</p>
          <h2 className="mt-4 text-4xl font-black tracking-[-0.04em] sm:text-5xl">Plans built for mechanics, towers, and mobile repair operators.</h2>
          <p className="mt-5 text-roadcall-muted">Start with AI answering, then scale into telephony workflows and dispatch infrastructure when your operation is ready.</p>
        </motion.div>

        <div className="mx-auto mt-12 grid max-w-7xl gap-5 lg:grid-cols-3">
          {PLANS.map((plan, index) => {
            const Icon = plan.icon;
            return (
              <motion.article
                key={plan.name}
                {...fadeUp(index * 0.08)}
                className={`group relative flex min-h-full flex-col overflow-hidden rounded-[2rem] border bg-white/[0.045] p-[1px] backdrop-blur-xl transition duration-500 hover:-translate-y-2 hover:shadow-[0_0_70px_rgba(37,99,235,0.22)] ${plan.badge ? "border-orange-300/40 shadow-[0_0_55px_rgba(234,88,12,0.18)]" : "border-roadcall-cyan/10"}`}
              >
                <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r ${plan.accent} opacity-70`} />
                <div className="absolute -right-20 -top-20 h-44 w-44 rounded-full bg-blue-500/20 blur-3xl transition group-hover:bg-roadcall-orange/20" />
                <div className="relative flex flex-1 flex-col rounded-[calc(2rem-1px)] bg-[#06101e]/75 p-6 sm:p-7">
                  <div className="mb-7 flex items-start justify-between gap-4">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${plan.accent} text-slate-950 shadow-lg`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    {plan.badge && (
                      <span className="rounded-full border border-roadcall-orange/30 bg-roadcall-orange/15 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-roadcall-orange">
                        {plan.badge}
                      </span>
                    )}
                  </div>
                  <h3 className="text-2xl font-black tracking-tight">{plan.name}</h3>
                  <p className="mt-2 min-h-12 text-sm leading-6 text-roadcall-muted">{plan.target}</p>
                  <div className="mt-7">
                    <span className="text-5xl font-black tracking-[-0.05em]">{plan.price}</span>
                    <span className="ml-2 text-roadcall-muted">/month</span>
                    <p className="mt-3 text-sm font-medium text-roadcall-orange">Setup: {plan.setup}</p>
                  </div>
                  <a
                    href={plan.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`mt-7 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3.5 text-sm font-bold transition hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-300 ${plan.badge ? "bg-white text-slate-950 hover:bg-roadcall-panel/40" : "border border-white/15 bg-roadcall-panel/45 text-white hover:border-blue-300/50 hover:bg-blue-400/10"}`}
                  >
                    {plan.cta} <ChevronRight className="h-4 w-4" />
                  </a>
                  <ul className="mt-7 space-y-3">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex gap-3 text-sm leading-6 text-roadcall-silver/85">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-300" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </motion.article>
            );
          })}
        </div>
      </section>

      <section className="relative z-10 px-4 py-16 sm:px-6">
        <div className="mx-auto max-w-7xl">
          <motion.div {...fadeUp()} className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.3em] text-blue-300">Add-ons</p>
              <h2 className="mt-3 text-3xl font-black tracking-[-0.035em] sm:text-4xl">Extend the platform around your operation.</h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-roadcall-muted">Add deeper automation, additional numbers, enterprise integrations, or fleet-facing workflows without rebuilding your phone stack.</p>
          </motion.div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {ADD_ONS.map(({ icon: Icon, title, copy }, index) => (
              <motion.div key={title} {...fadeUp(index * 0.04)} className="group rounded-3xl border border-roadcall-cyan/10 bg-white/[0.045] p-5 backdrop-blur-xl transition hover:-translate-y-1 hover:border-blue-300/35 hover:bg-blue-400/10">
                <Icon className="mb-5 h-6 w-6 text-roadcall-orange" />
                <h3 className="font-bold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-roadcall-muted">{copy}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative z-10 px-4 py-16 sm:px-6 lg:py-24">
        <motion.div {...fadeUp()} className="mx-auto max-w-7xl overflow-hidden rounded-[2rem] border border-roadcall-cyan/10 bg-white/[0.045] backdrop-blur-xl">
          <div className="border-b border-roadcall-cyan/10 p-6 sm:p-8">
            <p className="text-sm font-bold uppercase tracking-[0.3em] text-roadcall-orange">Comparison</p>
            <h2 className="mt-3 text-3xl font-black tracking-[-0.035em] sm:text-4xl">Roadcall AI vs. traditional answering services</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-white/[0.035] text-roadcall-silver/85">
                <tr>
                  <th className="px-6 py-4 font-semibold">Capability</th>
                  <th className="px-6 py-4 font-semibold text-blue-200">Roadcall AI</th>
                  <th className="px-6 py-4 font-semibold text-roadcall-muted">Traditional Answering Service</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map(([capability, roadcall, traditional]) => (
                  <tr key={capability} className="border-t border-roadcall-cyan/10">
                    <td className="px-6 py-4 font-medium text-white">{capability}</td>
                    <td className="px-6 py-4 text-roadcall-silver/85"><Check className="mr-2 inline h-4 w-4 text-emerald-300" />{roadcall}</td>
                    <td className="px-6 py-4 text-roadcall-muted/70">{traditional}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </section>

      <section className="relative z-10 px-4 py-16 sm:px-6">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <motion.div {...fadeUp()}>
            <p className="text-sm font-bold uppercase tracking-[0.3em] text-blue-300">ROI</p>
            <h2 className="mt-3 text-4xl font-black tracking-[-0.045em] sm:text-5xl">One Missed Roadside Call Can Cost Hundreds.</h2>
            <p className="mt-5 text-lg leading-8 text-roadcall-muted">After-hours breakdown calls are high-intent revenue. Roadcall AI captures the caller, qualifies the issue, sends follow-up, and moves the work into your operation before a competitor answers.</p>
          </motion.div>
          <motion.div {...fadeUp(0.08)} className="rounded-[2rem] border border-roadcall-cyan/10 bg-white/[0.045] p-5 backdrop-blur-xl sm:p-7">
            <div className="grid gap-4 sm:grid-cols-2">
              {ROI_STATS.map(({ icon: Icon, value, label }, index) => (
                <div key={label} className="rounded-3xl border border-roadcall-cyan/10 bg-black/20 p-5">
                  <Icon className="mb-6 h-6 w-6 text-roadcall-orange" />
                  <motion.div
                    initial={{ opacity: 0, scale: 0.94 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.08, duration: 0.5 }}
                    className="text-4xl font-black tracking-[-0.05em] text-white"
                  >
                    {value}
                  </motion.div>
                  <p className="mt-2 text-sm leading-6 text-roadcall-muted">{label}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 rounded-3xl border border-blue-400/15 bg-blue-400/10 p-5">
              <div className="mb-4 flex items-center justify-between text-sm">
                <span className="font-semibold text-blue-100">Captured emergency revenue</span>
                <span className="text-roadcall-muted">AI availability impact</span>
              </div>
              <div className="space-y-3">
                {[78, 54, 92].map((width, index) => (
                  <div key={width} className="h-3 overflow-hidden rounded-full bg-roadcall-panel/60">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${width}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.9, delay: index * 0.12 }}
                      className="h-full rounded-full bg-gradient-to-r from-blue-400 to-orange-300"
                    />
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="relative z-10 px-4 py-16 sm:px-6 lg:py-24">
        <div className="mx-auto max-w-5xl">
          <motion.div {...fadeUp()} className="text-center">
            <p className="text-sm font-bold uppercase tracking-[0.3em] text-roadcall-orange">FAQ</p>
            <h2 className="mt-3 text-4xl font-black tracking-[-0.04em]">Built for real roadside operations.</h2>
          </motion.div>
          <div className="mt-10 grid gap-4 md:grid-cols-2">
            {FAQS.map(([question, answer], index) => (
              <motion.div key={question} {...fadeUp(index * 0.03)} className="rounded-3xl border border-roadcall-cyan/10 bg-white/[0.045] p-6 backdrop-blur-xl">
                <div className="mb-3 flex gap-3">
                  <HelpCircle className="mt-0.5 h-5 w-5 shrink-0 text-blue-300" />
                  <h3 className="font-bold text-white">{question}</h3>
                </div>
                <p className="text-sm leading-7 text-roadcall-muted">{answer}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative z-10 px-4 pb-28 pt-12 sm:px-6 lg:pb-32">
        <motion.div {...fadeUp()} className="relative mx-auto max-w-7xl overflow-hidden rounded-[2.5rem] border border-roadcall-cyan/10 bg-white/[0.055] p-8 shadow-[0_0_100px_rgba(37,99,235,0.16)] backdrop-blur-2xl sm:p-12 lg:p-14">
          <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-blue-500/20 blur-3xl" />
          <div className="absolute -bottom-24 left-1/3 h-72 w-72 rounded-full bg-roadcall-orange/15 blur-3xl" />
          <div className="relative grid gap-10 lg:grid-cols-[1fr_0.9fr] lg:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.3em] text-blue-300">Roadcall AI</p>
              <h2 className="mt-4 text-4xl font-black tracking-[-0.045em] sm:text-5xl">Modernize Your Roadside Operations With AI.</h2>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-roadcall-silver/85">Deploy an AI phone layer that answers instantly, captures high-value breakdown calls, and moves roadside work into reliable dispatch workflows.</p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href="/shops/onboarding" className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-4 text-sm font-bold text-slate-950 transition hover:-translate-y-0.5 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-300">
                  Start Free Trial <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/demo" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-roadcall-panel/45 px-6 py-4 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:border-roadcall-cyan/50 hover:bg-roadcall-cyan/10 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan">
                  Schedule Demo <CalendarClock className="h-4 w-4 text-roadcall-orange" />
                </Link>
              </div>
            </div>
            <div className="rounded-[2rem] border border-roadcall-cyan/10 bg-[#02050c]/55 p-5">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-semibold text-white">Dispatch Interface</span>
                <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">Live</span>
              </div>
              <div className="space-y-3">
                {["AI intake completed", "Fleet notified", "Mechanic matched", "ETA text queued"].map((item, index) => (
                  <div key={item} className="flex items-center justify-between rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/35 px-4 py-3 text-sm">
                    <span className="flex items-center gap-2 text-roadcall-silver/85"><Cpu className="h-4 w-4 text-blue-300" />{item}</span>
                    <span className={index < 3 ? "text-emerald-300" : "text-roadcall-orange"}>{index < 3 ? "done" : "next"}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-roadcall-cyan/10 bg-[#02050c]/90 p-3 backdrop-blur-xl md:hidden">
        <Link href="/shops/onboarding" className="flex items-center justify-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-bold text-slate-950 shadow-[0_0_35px_rgba(255,255,255,0.16)] focus:outline-none focus:ring-2 focus:ring-blue-300">
          Start Free Trial <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </main>
  );
}
