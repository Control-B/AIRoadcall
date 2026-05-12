"use client";

/* ── 10 colorful Roadcall marketing message cards ── */
const marqueeCards = [
  {
    label: "Revenue",
    title: "More booked jobs",
    body: "AI handles first response, dispatch, and follow-up so shops and fleets close more work without lifting a phone.",
    gradient: "from-cyan-500/30 to-blue-600/20",
    border: "border-cyan-400/30",
    labelColor: "text-cyan-300",
  },
  {
    label: "Pipeline",
    title: "Every missed call recovered",
    body: "Missed-call text-back and instant booking turn after-hours rings into next-morning revenue.",
    gradient: "from-violet-500/30 to-fuchsia-500/20",
    border: "border-violet-400/30",
    labelColor: "text-violet-300",
  },
  {
    label: "Efficiency",
    title: "Less manual dispatch",
    body: "Automation replaces phone-tag and spreadsheets across intake, routing, and ETA updates.",
    gradient: "from-emerald-500/30 to-teal-500/20",
    border: "border-emerald-400/30",
    labelColor: "text-emerald-300",
  },
  {
    label: "Speed",
    title: "Sub-90s incident intake",
    body: "Driver calls in stranded — vehicle, location, and incident are captured in under a minute and a half.",
    gradient: "from-amber-500/30 to-orange-500/20",
    border: "border-amber-400/30",
    labelColor: "text-amber-300",
  },
  {
    label: "Coverage",
    title: "24/7 AI dispatch",
    body: "Sandy never sleeps — fleets get answered at 3am on a Sunday the same way they do on Monday at noon.",
    gradient: "from-rose-500/30 to-pink-500/20",
    border: "border-rose-400/30",
    labelColor: "text-rose-300",
  },
  {
    label: "Network",
    title: "35,000+ verified mechanics",
    body: "Heavy-duty truck specialists, mobile techs, and tow operators scored by class, distance, and availability.",
    gradient: "from-sky-500/30 to-indigo-500/20",
    border: "border-sky-400/30",
    labelColor: "text-sky-300",
  },
  {
    label: "Reach",
    title: "All 50 states covered",
    body: "From Atlanta to Anchorage, every interstate corridor has a verified mechanic ready to roll.",
    gradient: "from-fuchsia-500/30 to-purple-600/20",
    border: "border-fuchsia-400/30",
    labelColor: "text-fuchsia-300",
  },
  {
    label: "Visibility",
    title: "Live driver + mechanic GPS",
    body: "One-tap secure SMS link — no app download. Dispatch sees both pins on a single ops board.",
    gradient: "from-teal-500/30 to-cyan-600/20",
    border: "border-teal-400/30",
    labelColor: "text-teal-300",
  },
  {
    label: "Reliability",
    title: "Heavy-duty specialists",
    body: "Class 7 & 8 trucks, refrigerated trailers, and reefers — matched to mechanics with the right gear.",
    gradient: "from-lime-500/30 to-green-500/20",
    border: "border-lime-400/30",
    labelColor: "text-lime-300",
  },
  {
    label: "Insight",
    title: "Full incident audit trail",
    body: "Every call, dispatch, and ETA logged — giving fleets the data to negotiate better with insurers and shippers.",
    gradient: "from-indigo-500/30 to-blue-500/20",
    border: "border-indigo-400/30",
    labelColor: "text-indigo-300",
  },
];

function MarqueeCard({ card }: { card: (typeof marqueeCards)[number] }) {
  return (
    <div
      className={`relative w-[min(20rem,calc(100vw-2rem))] flex-shrink-0 overflow-hidden rounded-[1.6rem] border ${card.border} bg-white/[0.05] px-5 py-5 backdrop-blur-sm sm:px-6 sm:py-6`}
    >
      <div className={`absolute inset-0 rounded-[1.6rem] bg-gradient-to-br ${card.gradient} opacity-80`} />
      <div className="relative z-10">
        <p className={`text-[11px] font-semibold uppercase tracking-[0.24em] ${card.labelColor}`}>{card.label}</p>
        <h3 className="mt-3 text-xl font-semibold text-white">{card.title}</h3>
        <p className="mt-3 text-sm leading-7 text-slate-200/90">{card.body}</p>
      </div>
    </div>
  );
}

export function ScrollingMarqueeSection() {
  return (
    <section className="relative overflow-hidden border-y border-white/10 bg-white/[0.02] py-12 lg:py-14">
      {/* Fade edges */}
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-roadcall-void to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-roadcall-void to-transparent" />

      {/* Scrolling track — render cards twice for a seamless loop */}
      <div className="flex w-max animate-marquee gap-5">
        {[...marqueeCards, ...marqueeCards].map((card, i) => (
          <MarqueeCard key={`${card.title}-${i}`} card={card} />
        ))}
      </div>
    </section>
  );
}
