"use client";

import Link from "next/link";
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
    desc: "After a job is complete the system sends a polite review request, building your Google and Facebook rating automatically.",
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
    <main className="min-h-screen bg-white">
      {/* Hero */}
      <section className="bg-gradient-to-br from-orange-600 via-red-600 to-orange-700 text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-block bg-white/20 text-sm font-medium px-4 py-1 rounded-full mb-6">
            Roadcall Shops — Features
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            Never miss another repair call
          </h1>
          <p className="text-xl text-orange-100 max-w-2xl mx-auto mb-10">
            Roadcall Shops gives truck mechanics a full AI phone and CRM stack —
            answering calls, booking jobs, and following up automatically.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/shops/onboarding"
              className="bg-white text-orange-600 font-semibold px-8 py-3 rounded-lg hover:bg-orange-50 transition-colors inline-flex items-center gap-2"
            >
              Start AI Phones for Your Shop <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href={`tel:${HELP_PHONE}`}
              className="border border-white/40 text-white font-semibold px-8 py-3 rounded-lg hover:bg-white/10 transition-colors"
            >
              Call {HELP_PHONE}
            </a>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Everything your front desk should be doing
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto text-lg">
              Eight core capabilities designed for truck repair shops — running around the clock.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-orange-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">From ring to booked job — automated</h2>
            <p className="text-gray-600">Five steps, fully automated after a 30-minute setup.</p>
          </div>
          <div className="space-y-6">
            {STEPS.map((s, i) => (
              <div key={s.title} className="flex gap-6 items-start p-6 bg-gray-50 rounded-xl border border-gray-100">
                <div className="flex-shrink-0 w-12 h-12 bg-orange-600 text-white rounded-full flex items-center justify-center font-bold text-lg">
                  {i + 1}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 text-lg mb-1">{s.title}</h3>
                  <p className="text-gray-600">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Value */}
      <section className="py-20 px-4 bg-orange-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">Why it matters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: TrendingUp, title: "For the Industry", body: "Truck mechanics are often one- or two-person shops running on a single cell number. Roadcall gives them the phone infrastructure franchise shops pay tens of thousands for." },
              { icon: Zap, title: "For the Shop Owner", body: "One missed call on a $3,000 engine job pays for a year of Roadcall Shops. No front-desk hire needed." },
              { icon: CheckCircle2, title: "The Outcome", body: "Fewer missed calls, more booked repairs, a CRM that fills itself, and review ratings that grow without asking manually." },
            ].map((v) => {
              const Icon = v.icon;
              return (
                <div key={v.title} className="bg-white rounded-xl p-8 shadow-sm border border-orange-100 text-center">
                  <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon className="w-6 h-6 text-orange-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 text-lg mb-3">{v.title}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">{v.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 bg-gradient-to-r from-orange-600 to-red-600 text-white text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-4">Ready to start AI Phones for your shop?</h2>
          <p className="text-orange-100 mb-8 text-lg">Setup takes under 30 minutes. No long-term contracts on entry plans.</p>
          <Link
            href="/shops/onboarding"
            className="bg-white text-orange-600 font-semibold px-10 py-4 rounded-lg hover:bg-orange-50 transition-colors inline-flex items-center gap-2 text-lg"
          >
            Start AI Phones for Your Shop <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </main>
  );
}
