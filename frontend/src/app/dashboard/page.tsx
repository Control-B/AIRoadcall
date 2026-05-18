import Link from "next/link";
import { ArrowRight, Bot, LifeBuoy, PlayCircle, Truck, Wrench } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";

const cards = [
  {
    title: "Configure AI agent",
    body: "Set instructions, welcome message, phone rules, voice, and test-call controls.",
    href: "/agents/dashboard",
    cta: "Open agent setup",
    icon: Bot,
    accent: "text-roadcall-cyan",
  },
  {
    title: "Try Mechanics AI Profile",
    body: "Preview the mechanic profile with sample shop details, services, and activation controls.",
    href: "/mechanic/dashboard?demo=1",
    cta: "Open Mechanics AI Profile",
    icon: Wrench,
    accent: "text-roadcall-orange",
  },
  {
    title: "Try fleet demo",
    body: "Preview the fleet dispatch console with incidents, assets, drivers, and vendor coverage.",
    href: "/fleet/dashboard?demo=1",
    cta: "Open fleet demo",
    icon: Truck,
    accent: "text-blue-300",
  },
];

export default function DashboardPage() {
  return (
    <PageLayout>
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/25 bg-roadcall-cyan/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-roadcall-cyan">
              <Bot className="h-4 w-4" /> Roadcall dashboard
            </div>
            <h1 className="mt-5 text-4xl font-black tracking-tight text-white sm:text-5xl">
              Open your Roadcall AI workspace
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-roadcall-muted">
              Configure your agent, preview the shop or fleet experience, or request a fresh private dashboard link from Roadcall support.
            </p>
          </div>

          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {cards.map((card) => {
              const Icon = card.icon;
              return (
                <Link
                  key={card.href}
                  href={card.href}
                  className="group flex min-h-[260px] flex-col justify-between rounded-2xl border border-white/10 bg-slate-950/65 p-6 shadow-2xl shadow-black/20 transition hover:-translate-y-1 hover:border-roadcall-cyan/35 hover:bg-slate-950/85"
                >
                  <div>
                    <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10">
                      <Icon className={`h-6 w-6 ${card.accent}`} />
                    </span>
                    <h2 className="mt-5 text-xl font-black text-white">{card.title}</h2>
                    <p className="mt-3 text-sm leading-6 text-roadcall-muted">{card.body}</p>
                  </div>
                  <span className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-roadcall-cyan">
                    {card.cta} <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="mt-8 rounded-2xl border border-roadcall-orange/25 bg-roadcall-orange/10 p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex items-start gap-3">
                <LifeBuoy className="mt-1 h-5 w-5 text-roadcall-orange" />
                <div>
                  <p className="font-bold text-white">Already subscribed?</p>
                  <p className="mt-1 text-sm leading-6 text-roadcall-muted">
                    Customer dashboards use secure private links. Ask support to resend yours if you do not have it handy.
                  </p>
                </div>
              </div>
              <Button asChild variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10">
                <a href="mailto:support@roadcall.ai?subject=Please%20resend%20my%20Roadcall%20dashboard%20link">
                  Email support
                </a>
              </Button>
            </div>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild className="rounded-xl">
              <Link href="/mechanic/dashboard?demo=1">
                <PlayCircle className="mr-2 h-4 w-4" /> Try Mechanics AI Profile
              </Link>
            </Button>
            <Button asChild variant="outline" className="rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10">
              <Link href="/get-started">View plans</Link>
            </Button>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
