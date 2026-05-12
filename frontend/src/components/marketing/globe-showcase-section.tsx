"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { RotatingGlobeBackground } from "./rotating-globe-background";

const orbitPoints = [
  {
    title: "AI Roadside Phone Agent",
    description:
      "Sandy answers every breakdown call 24/7 — capturing vehicle, location, and incident details in under 90 seconds, day or night.",
    accent: "from-cyan-400/30 via-sky-400/20 to-blue-500/25",
    border: "border-cyan-300/30",
    glow: "shadow-[0_24px_80px_rgba(34,211,238,0.18)]",
    position: "left-[4%] top-[12%]",
  },
  {
    title: "AI Mechanic Dispatcher",
    description:
      "Scores 35,000+ verified vendors by distance, truck class, specialty, and availability — then routes the right shop in seconds.",
    accent: "from-orange-400/30 via-amber-400/18 to-rose-500/22",
    border: "border-orange-300/30",
    glow: "shadow-[0_24px_80px_rgba(255,138,0,0.18)]",
    position: "right-[4%] top-[16%]",
  },
  {
    title: "AI Lead Capture for Shops",
    description:
      "Missed-call text-back, instant booking, and CRM follow-up so truck mechanic shops never lose a customer to a slow phone again.",
    accent: "from-emerald-400/28 via-cyan-300/16 to-teal-400/24",
    border: "border-emerald-300/30",
    glow: "shadow-[0_24px_80px_rgba(16,185,129,0.18)]",
    position: "left-1/2 top-[62%] -translate-x-1/2",
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
      className="relative -mt-px flex min-h-[88vh] items-center justify-center overflow-hidden border-y border-roadcall-line/30 bg-roadcall-void"
    >
      <RotatingGlobeBackground className="z-0" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col items-center px-6 py-14 lg:px-8 lg:pt-14 lg:pb-6">
        {/* Copy — centered at top */}
        <motion.div style={{ y: copyY }} className="w-full max-w-3xl text-center">
          <div className="inline-flex items-center rounded-full border border-cyan-300/35 bg-cyan-400/10 px-4 py-1.5 text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-200 backdrop-blur-md shadow-[0_18px_60px_rgba(34,211,238,0.18)]">
            Roadcall Orbit
          </div>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-white lg:text-4xl">
            Put AI specialists around every roadside call.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-roadcall-silver/70 lg:text-base">
            One platform answers the phones, dispatches the mechanic, and follows up with the
            customer — so fleets, drivers, and shops never miss a beat.
          </p>
        </motion.div>

        {/* Desktop orbit cards — pushed into bottom portion */}
        <div className="relative mx-auto mt-4 hidden h-[36rem] w-full max-w-6xl lg:block">
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-[29rem] w-[29rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/10" />
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-[38rem] w-[38rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-300/10 border-dashed opacity-70" />

          {orbitPoints.map((point, index) => (
            <motion.div
              key={point.title}
              initial={{ opacity: 0, y: 24, scale: 0.96 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              animate={{ y: [0, index % 2 === 0 ? -10 : 10, 0] }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{
                opacity: { duration: 0.45, delay: index * 0.12 },
                y: { duration: 7 + index, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
                scale: { duration: 0.45, delay: index * 0.12 },
              }}
              className={`absolute w-[18rem] overflow-hidden rounded-[1.75rem] border bg-[linear-gradient(180deg,rgba(255,255,255,0.18),rgba(255,255,255,0.06))] px-6 py-6 text-left backdrop-blur-2xl ${point.border} ${point.glow} ${point.position}`}
            >
              <div className={`absolute inset-0 rounded-[1.75rem] bg-gradient-to-br ${point.accent} opacity-90`} />
              <div className="relative z-10">
                <div className="inline-flex rounded-full border border-white/20 bg-black/20 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-white/80">
                  Roadcall AI
                </div>
                <h3 className="mt-4 text-xl font-semibold leading-tight text-white">{point.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-100/88">{point.description}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mobile stacked cards */}
        <div className="mt-12 grid gap-4 text-left lg:hidden">
          {orbitPoints.map((point, index) => (
            <motion.div
              key={`${point.title}-mobile`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
              className={`relative overflow-hidden rounded-[1.5rem] border px-5 py-5 text-left backdrop-blur-xl ${point.border} ${point.glow}`}
              style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.06))" }}
            >
              <div className={`absolute inset-0 rounded-[1.5rem] bg-gradient-to-br ${point.accent} opacity-80`} />
              <div className="relative z-10">
                <div className="inline-flex rounded-full border border-white/20 bg-black/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.26em] text-white/80">
                  Roadcall AI
                </div>
                <h3 className="mt-4 text-lg font-semibold text-white">{point.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-100/88">{point.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
