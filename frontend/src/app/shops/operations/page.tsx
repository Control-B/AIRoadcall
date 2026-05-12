import {
  BarChart3,
  Bot,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Megaphone,
  MessageSquareText,
  PhoneCall,
  Radar,
  Route,
  Share2,
  ShieldCheck,
  Sparkles,
  Star,
  TrendingUp,
  Video,
  Wrench,
} from "lucide-react";

const workflows = [
  {
    icon: PhoneCall,
    title: "AI receptionist + missed-call text back",
    detail: "Capture every call, classify intent, ask only the operational questions that matter, and push qualified jobs into dispatch.",
    status: "Live workflow",
  },
  {
    icon: Route,
    title: "Roadside lead queue",
    detail: "Prioritized local dispatch opportunities scored by fit, radius, issue type, and expected close probability.",
    status: "Dispatch-ready",
  },
  {
    icon: Megaphone,
    title: "AI customer acquisition",
    detail: "Turn reviews, specialties, service areas, and photos into SEO pages, social posts, and follow-up campaigns.",
    status: "Growth engine",
  },
  {
    icon: Star,
    title: "Reputation intelligence",
    detail: "Spot review gaps, generate review requests, and surface trust indicators that improve marketplace ranking.",
    status: "Trust score",
  },
];

const stats = [
  ["Answer rate", "96%", "+18% vs baseline", PhoneCall],
  ["Dispatch fit", "88", "weighted provider score", Radar],
  ["Avg response", "24m", "route + availability estimate", Clock3],
  ["Growth score", "72", "SEO/reviews/profile health", TrendingUp],
];

const timeline = [
  ["AI call intake", "Caller says: blown tire on I-4, box truck, Spanish preferred.", Bot],
  ["Deterministic ranking", "Roadcall filters radius, roadside capability, truck support, 24/7 signal, and trust score.", Radar],
  ["Provider contact", "AI texts/calls best-fit providers, collects ETA, and tracks accept/decline.", MessageSquareText],
  ["Customer updates", "Driver receives ETA, provider status, and live dispatch progress.", Route],
  ["Growth loop", "Completed job triggers review request, lead attribution, and provider quality score update.", Share2],
];

export default function ShopOperationsPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="relative overflow-hidden border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(59,130,246,0.34),transparent_34%),radial-gradient(circle_at_80%_0%,rgba(249,115,22,0.18),transparent_28%)]" />
        <div className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-orange-300/30 bg-orange-300/10 px-3 py-1 text-sm text-orange-100">
              <Wrench className="h-4 w-4" /> Provider operations + growth center
            </div>
            <h1 className="mt-6 text-4xl font-black tracking-tight sm:text-6xl">
              Run your roadside business like an AI-powered dispatch operation.
            </h1>
            <p className="mt-5 max-w-3xl text-lg text-slate-300">
              Roadcall turns provider profiles into a workflow: AI receptionist, dispatch leads,
              response intelligence, reputation growth, local SEO, social content, and conversion analytics.
            </p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-4">
            {stats.map(([label, value, detail, Icon]) => (
              <div key={label as string} className="rounded-3xl border border-white/10 bg-white/[0.07] p-5 backdrop-blur">
                <Icon className="mb-4 h-6 w-6 text-orange-200" />
                <p className="text-3xl font-black">{value as string}</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{label as string}</p>
                <p className="mt-2 text-xs text-slate-400">{detail as string}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:px-8">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-blue-200">Operations layer</p>
          <h2 className="mt-3 text-3xl font-bold">From missed call to completed job</h2>
          <p className="mt-4 text-slate-300">
            The provider dashboard should not feel like a static profile editor. It should show what is happening now,
            what needs attention, and what actions will grow dispatch volume.
          </p>

          <div className="mt-6 space-y-3">
            {timeline.map(([title, detail, Icon], index) => (
              <div key={title as string} className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.05] p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-500/20 text-blue-100">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Step {index + 1}</p>
                  <h3 className="font-semibold">{title as string}</h3>
                  <p className="mt-1 text-sm text-slate-400">{detail as string}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {workflows.map((item) => (
            <div key={item.title} className="rounded-3xl border border-white/10 bg-white/[0.07] p-5 shadow-xl">
              <div className="mb-5 flex items-center justify-between">
                <div className="rounded-2xl bg-orange-500/20 p-3 text-orange-100">
                  <item.icon className="h-6 w-6" />
                </div>
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-xs font-semibold text-emerald-200">
                  {item.status}
                </span>
              </div>
              <h3 className="text-lg font-bold">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">{item.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8">
        <div className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-blue-600/20 to-orange-500/10 p-6 md:p-8">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <p className="text-sm uppercase tracking-[0.25em] text-cyan-200">Provider growth loop</p>
              <h2 className="mt-3 text-3xl font-bold">Every dispatch improves the next ranking.</h2>
              <p className="mt-3 text-slate-300">
                Roadcall can use completed jobs, accepted ETAs, customer updates, and review outcomes to improve provider
                quality scores and unlock better leads — without using expensive LLMs for routine decisions.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <LoopItem icon={ClipboardList} label="Dispatch analytics" detail="Acceptance, completion, ETA accuracy, repeat jobs." />
              <LoopItem icon={Video} label="AI marketing" detail="Social posts, service pages, and short video scripts." />
              <LoopItem icon={ShieldCheck} label="Trust indicators" detail="Verified, enriched, review depth, response confidence." />
              <LoopItem icon={CalendarClock} label="Follow-up automation" detail="Review requests, reactivation, fleet touchpoints." />
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function LoopItem({ icon: Icon, label, detail }: { icon: React.ElementType; label: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
      <div className="mb-3 flex items-center gap-2 text-blue-100">
        <Icon className="h-4 w-4" />
        <span className="font-semibold">{label}</span>
      </div>
      <p className="text-sm text-slate-400">{detail}</p>
      <div className="mt-3 flex items-center gap-2 text-xs text-emerald-200">
        <CheckCircle2 className="h-3.5 w-3.5" /> Workflow-ready
      </div>
    </div>
  );
}
