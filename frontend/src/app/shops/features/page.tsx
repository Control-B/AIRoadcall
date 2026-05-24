"use client";

import Link from "next/link";
import Image from "next/image";
import {
  Phone,
  MessageSquare,
  Calendar,
  Users,
  Star,
  MapPin,
  FileText,
  Bell,
  ArrowRight,
  CheckCircle2,
  Zap,
  TrendingUp,
} from "lucide-react";
import { HELP_PHONE } from "@/lib/phone";

const FEATURES = [
  {
    icon: Phone,
    title: "AI Call Answering",
    desc: "A trained AI receptionist picks up every call, 24/7. Captures lead info, explains services, and books appointments — even at 2 AM.",
  },
  {
    icon: MessageSquare,
    title: "Missed-Call Text-Back",
    desc: "When a call goes unanswered, an automated text fires within seconds so you never lose a lead to voicemail.",
  },
  {
    icon: Calendar,
    title: "Appointment Booking",
    desc: "Callers can book a drop-off or mobile service call directly during the AI conversation — no web form required.",
  },
  {
    icon: Users,
    title: "CRM Pipeline",
    desc: "Every customer and lead lands in a structured pipeline so you can see open jobs, follow-ups, and long-term customers at a glance.",
  },
  {
    icon: Bell,
    title: "Customer Follow-Up",
    desc: "Automated SMS & email sequences keep customers informed on repair status, invoices, and ready-for-pickup alerts.",
  },
  {
    icon: Star,
    title: "Review Requests",
    desc: "After a job is complete the system sends a polite review request, building your public rating automatically.",
  },
  {
    icon: MapPin,
    title: "Service-Area Routing",
    desc: "Calls outside your service area are politely declined or forwarded so your team focuses on jobs you can actually take.",
  },
  {
    icon: FileText,
    title: "Call Summaries",
    desc: "Every call generates a structured summary — caller name, vehicle, issue, and any info given — saved to the CRM automatically.",
  },
];

const STEPS = [
  { title: "Customer Calls", desc: "Your shop number rings. The AI answers instantly — no hold music, no voicemail." },
  { title: "AI Qualifies the Call", desc: "The AI collects name, vehicle type, issue, and preferred service time in a natural conversation." },
  { title: "Lead is Captured", desc: "Contact info, vehicle details, and call summary are pushed into the CRM automatically." },
  { title: "Job or Appointment Created", desc: "If ready to book, an appointment is created. If not, the lead sits in the pipeline for follow-up." },
  { title: "Automation Takes Over", desc: "Follow-up texts, reminders, status updates, and review requests run on autopilot from there." },
];

export default function ShopsFeaturesPage() {
  return (
    <main className="min-h-screen bg-roadcall-void text-white">
      {/* Hero */}
      <section className="relative min-h-[65vh] flex flex-col justify-end overflow-hidden">
        <Image
          src="https://images.unsplash.com/photo-1530046339160-ce3e530c7d2f?w=1920&q=80"
          alt="Mechanic working in a truck repair shop"
          fill
          priority
          className="object-cover object-center"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/90 z-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-transparent to-black/20 z-10" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(234,88,12,0.2),transparent_70%)] z-10" />
        <div className="relative z-20 max-w-4xl mx-auto px-4 sm:px-6 w-full pb-16 pt-28 text-center">
          <span className="inline-flex items-center gap-2 bg-roadcall-panel/60 border border-roadcall-cyan/20 backdrop-blur-sm text-sm font-medium px-4 py-1.5 rounded-full mb-8 text-roadcall-silver">
            Roadcall Shops — Features
          </span>
          <h1 className="text-5xl md:text-6xl font-black leading-[0.95] mb-6 text-white">
            Never miss another<br />
            <span className="bg-gradient-to-r from-roadcall-orange to-roadcall-cyan bg-clip-text text-transparent">repair call</span>
          </h1>
          <p className="text-lg text-roadcall-silver/85 max-w-2xl mx-auto mb-10 leading-relaxed">
            Roadcall Shops gives truck mechanics a full AI phone and CRM stack —
            answering calls, booking jobs, and following up automatically.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/shops/onboarding"
              className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-semibold px-8 py-3 rounded-xl transition-colors inline-flex items-center gap-2"
            >
              Start AI Phones for Your Shop <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href={`tel:${HELP_PHONE}`}
              className="border border-roadcall-cyan/30 bg-roadcall-panel/45 backdrop-blur-sm text-white font-semibold px-8 py-3 rounded-xl hover:bg-roadcall-panel/60 transition-colors"
            >
              Call {HELP_PHONE}
            </a>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="border-t border-roadcall-cyan/10 bg-roadcall-void px-4 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Everything your front desk should be doing
            </h2>
            <p className="text-roadcall-muted max-w-2xl mx-auto text-lg">
              Eight core capabilities designed for truck repair shops — running around the clock.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="rounded-xl border border-roadcall-cyan/10 bg-roadcall-panel/35 p-6 shadow-xl shadow-black/10 transition-colors hover:border-roadcall-cyan/25 hover:bg-roadcall-panel/45">
                  <div className="w-10 h-10 bg-roadcall-orange/10 border border-roadcall-orange/20 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-roadcall-orange" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="border-t border-roadcall-cyan/10 px-4 py-20">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-white mb-4">From ring to booked job — automated</h2>
            <p className="text-roadcall-muted">Five steps, fully automated after a 30-minute setup.</p>
          </div>
          <div className="space-y-6">
            {STEPS.map((s, i) => (
              <div key={s.title} className="flex gap-6 items-start p-6 bg-roadcall-panel/35 rounded-xl border border-roadcall-cyan/10">
                <div className="flex-shrink-0 w-12 h-12 bg-roadcall-orange text-white rounded-full flex items-center justify-center font-bold text-lg">
                  {i + 1}
                </div>
                <div>
                  <h3 className="font-semibold text-white text-lg mb-1">{s.title}</h3>
                  <p className="text-roadcall-muted">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Value */}
      <section className="border-t border-roadcall-cyan/10 bg-roadcall-panel/20 px-4 py-20">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-12 text-center">Why it matters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: TrendingUp, title: "For the Industry", body: "Truck mechanics are often one- or two-person shops running on a single cell number. Roadcall gives them the phone infrastructure franchise shops pay tens of thousands for." },
              { icon: Zap, title: "For the Shop Owner", body: "One missed call on a $3,000 engine job pays for a year of Roadcall Shops. No front-desk hire needed." },
              { icon: CheckCircle2, title: "The Outcome", body: "Fewer missed calls, more booked repairs, a CRM that fills itself, and review ratings that grow without asking manually." },
            ].map((v) => {
              const Icon = v.icon;
              return (
                <div key={v.title} className="rounded-xl border border-roadcall-orange/15 bg-roadcall-panel/35 p-8 text-center shadow-xl shadow-black/10">
                  <div className="w-12 h-12 bg-roadcall-orange/10 border border-roadcall-orange/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon className="w-6 h-6 text-roadcall-orange" />
                  </div>
                  <h3 className="font-semibold text-white text-lg mb-3">{v.title}</h3>
                  <p className="text-roadcall-muted text-sm leading-relaxed">{v.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 bg-gradient-to-r from-roadcall-orange to-roadcall-blue text-white text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-4">Ready to start AI Phones for your shop?</h2>
          <p className="text-white/85 mb-8 text-lg">Setup takes under 30 minutes. No long-term contracts on entry plans.</p>
          <Link
            href="/shops/onboarding"
            className="bg-white text-roadcall-orange font-semibold px-10 py-4 rounded-lg hover:bg-roadcall-silver transition-colors inline-flex items-center gap-2 text-lg"
          >
            Start AI Phones for Your Shop <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </main>
  );
}
