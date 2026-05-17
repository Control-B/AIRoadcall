"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import Link from "next/link";
import { useRef } from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { RotatingGlobeBackground } from "./rotating-globe-background";

type AudienceCard = {
  href: string;
  eyebrow: string;
  eyebrowClass: string;
  title: string;
  audience: string;
  audienceClass: string;
  bullets: string[];
  ctaLabel: string;
  ctaClass: string;
  border: string;
  hoverBorder: string;
  accentGradient: string;
  glow: string;
  iconClass: string;
  desktopPosition: string;
};

const audienceCards: AudienceCard[] = [
  {
    href: "/fleet/features",
    eyebrow: "Lane 1 · AI Dispatch",
    eyebrowClass: "text-blue-400",
    title: "Roadside Matching",
    audience: "for Fleets & Drivers",
    audienceClass: "text-blue-300",
    bullets: ["Location-First Intake", "Problem Classification", "Mechanic Matching", "Dispatch & Tracking"],
    ctaLabel: "Explore Dispatch",
    ctaClass: "bg-blue-600 text-white group-hover:bg-blue-500",
    border: "border-blue-500/30",
    hoverBorder: "hover:border-blue-500/60",
    accentGradient: "from-blue-500/15 via-transparent to-transparent",
    glow: "shadow-[0_24px_80px_rgba(59,130,246,0.22)]",
    iconClass: "text-blue-400",
    desktopPosition: "left-[2%] top-[6%]",
  },
  {
    href: "/ai-telephony",
    eyebrow: "Lane 2 · AI Telephony",
    eyebrowClass: "text-roadcall-orange",
    title: "AI Service Advisor",
    audience: "for Mechanic Shops",
    audienceClass: "text-roadcall-orange",
    bullets: ["Retell AI Phone", "Missed-Call Text Back", "Appointment Booking", "Call Summaries"],
    ctaLabel: "Explore AI Phone",
    ctaClass: "bg-roadcall-orange text-white group-hover:brightness-110",
    border: "border-orange-500/30",
    hoverBorder: "hover:border-orange-500/60",
    accentGradient: "from-roadcall-orange/15 via-transparent to-transparent",
    glow: "shadow-[0_24px_80px_rgba(234,88,12,0.22)]",
    iconClass: "text-roadcall-orange",
    desktopPosition: "right-[2%] top-[6%]",
  },
  {
    href: "/lead-generation",
    eyebrow: "Lane 3 · AI Lead Gen",
    eyebrowClass: "text-emerald-300",
    title: "Provider Growth",
    audience: "for Shops & Roadside Operators",
    audienceClass: "text-emerald-200",
    bullets: ["Inbound Lead Capture", "Email Enrichment", "Campaign Follow-Up", "Plan-Based Quotas"],
    ctaLabel: "Explore Leads",
    ctaClass: "bg-emerald-400 text-slate-950 group-hover:bg-emerald-300",
    border: "border-emerald-400/30",
    hoverBorder: "hover:border-emerald-400/60",
    accentGradient: "from-emerald-400/15 via-transparent to-transparent",
    glow: "shadow-[0_24px_80px_rgba(52,211,153,0.2)]",
    iconClass: "text-emerald-300",
    desktopPosition: "left-[2%] bottom-[6%]",
  },
  {
    href: "/search",
    eyebrow: "Lane 4 · Search",
    eyebrowClass: "text-cyan-300",
    title: "Truck Service Directory",
    audience: "for Drivers & Dispatchers",
    audienceClass: "text-cyan-200",
    bullets: ["Find Truck Service", "Search by Location", "Roadside & Towing", "Protected Contact Data"],
    ctaLabel: "Search Providers",
    ctaClass: "bg-cyan-500 text-slate-950 group-hover:bg-cyan-300",
    border: "border-cyan-400/30",
    hoverBorder: "hover:border-cyan-400/60",
    accentGradient: "from-cyan-400/15 via-transparent to-transparent",
    glow: "shadow-[0_24px_80px_rgba(34,211,238,0.22)]",
    iconClass: "text-cyan-300",
    desktopPosition: "right-[2%] bottom-[6%]",
  },
];

export function GlobeShowcaseSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start 80%", "end 20%"],
  });
  const copyY = useTransform(scrollYProgress, [0, 1], [20, -10]);

  return (
    <section
      ref={sectionRef}
      className="relative -mt-px flex min-h-[100vh] items-center justify-center overflow-hidden border-y border-roadcall-line/30 bg-roadcall-void"
    >
      <RotatingGlobeBackground className="z-0" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col items-center px-6 py-14 lg:px-8 lg:pt-14 lg:pb-10">
        {/* Copy — centered at top, with soft glass backdrop for readability over the globe */}
        <motion.div
          style={{ y: copyY }}
          className="relative w-full max-w-3xl rounded-3xl bg-roadcall-void/55 px-6 py-6 text-center backdrop-blur-md ring-1 ring-white/5 shadow-[0_30px_80px_rgba(2,5,12,0.55)]"
        >
          <div className="inline-flex items-center rounded-full border border-cyan-300/35 bg-cyan-400/10 px-4 py-1.5 text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-200 backdrop-blur-md shadow-[0_18px_60px_rgba(34,211,238,0.18)]">
            Choose your Roadcall path
          </div>
          <h2 className="mt-4 bg-gradient-to-b from-white via-cyan-50 to-cyan-200 bg-clip-text text-3xl font-bold tracking-tight text-transparent drop-shadow-[0_4px_24px_rgba(8,12,28,0.85)] lg:text-4xl">
            One platform. Four clear lanes for truck service.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-cyan-100/90 drop-shadow-[0_2px_12px_rgba(8,12,28,0.85)] lg:text-base">
            Choose AI dispatch, AI telephony, AI lead generation, or general
            truck service search — each lane has its own job.
          </p>
        </motion.div>

        {/* Desktop orbit cards */}
        <div className="relative mx-auto mt-6 hidden h-[40rem] w-full max-w-6xl lg:block">
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-[32rem] w-[32rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/10" />
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-[42rem] w-[42rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-300/10 border-dashed opacity-70" />

          {audienceCards.map((card, index) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 24, scale: 0.96 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              animate={{ y: [0, index % 2 === 0 ? -10 : 10, 0] }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{
                opacity: { duration: 0.45, delay: index * 0.12 },
                y: { duration: 7 + index, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
                scale: { duration: 0.45, delay: index * 0.12 },
              }}
              className={`absolute w-[19rem] ${card.desktopPosition}`}
            >
              <Link
                href={card.href}
                className={`group relative block overflow-hidden rounded-[1.75rem] border bg-[#080b12]/65 px-6 py-6 text-left backdrop-blur-2xl transition-all duration-200 ${card.border} ${card.hoverBorder} ${card.glow}`}
              >
                <div className={`absolute inset-0 rounded-[1.75rem] bg-gradient-to-br ${card.accentGradient} opacity-90`} />
                <div className="relative z-10">
                  <div className={`text-[10px] font-bold uppercase tracking-[0.24em] mb-2 ${card.eyebrowClass}`}>
                    {card.eyebrow}
                  </div>
                  <h3 className="text-lg font-bold leading-tight text-white">{card.title}</h3>
                  <p className={`text-[11px] font-medium mt-1 mb-3 ${card.audienceClass}`}>{card.audience}</p>
                  <ul className="grid gap-1.5 mb-4">
                    {card.bullets.map((b) => (
                      <li key={b} className="flex items-center gap-2 text-[12px] text-roadcall-silver/90">
                        <CheckCircle2 className={`h-3.5 w-3.5 shrink-0 ${card.iconClass}`} />
                        {b}
                      </li>
                    ))}
                  </ul>
                  <div className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[11px] font-semibold transition-all ${card.ctaClass}`}>
                    {card.ctaLabel} <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Mobile / tablet stacked cards */}
        <div className="mt-10 grid w-full gap-4 text-left lg:hidden">
          {audienceCards.map((card, index) => (
            <motion.div
              key={`${card.title}-mobile`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              <Link
                href={card.href}
                className={`group relative block overflow-hidden rounded-[1.5rem] border bg-[#080b12]/70 px-5 py-5 text-left backdrop-blur-xl transition-all duration-200 ${card.border} ${card.hoverBorder} ${card.glow}`}
              >
                <div className={`absolute inset-0 rounded-[1.5rem] bg-gradient-to-br ${card.accentGradient} opacity-90`} />
                <div className="relative z-10">
                  <div className={`text-[10px] font-bold uppercase tracking-[0.24em] mb-2 ${card.eyebrowClass}`}>
                    {card.eyebrow}
                  </div>
                  <h3 className="text-lg font-bold text-white">{card.title}</h3>
                  <p className={`text-[11px] font-medium mt-1 mb-3 ${card.audienceClass}`}>{card.audience}</p>
                  <ul className="grid gap-1.5 mb-4">
                    {card.bullets.map((b) => (
                      <li key={b} className="flex items-center gap-2 text-[12px] text-roadcall-silver/90">
                        <CheckCircle2 className={`h-3.5 w-3.5 shrink-0 ${card.iconClass}`} />
                        {b}
                      </li>
                    ))}
                  </ul>
                  <div className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[11px] font-semibold transition-all ${card.ctaClass}`}>
                    {card.ctaLabel} <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
