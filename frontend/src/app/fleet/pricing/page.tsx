"use client";

import Link from "next/link";
import { CheckCircle2, ArrowRight, HelpCircle, PauseCircle } from "lucide-react";

const FLEET_FOCUS = [
  { label: "AI roadside support", desc: "Continue validating caller location, triage, outbound calls, and mechanic matching before selling fleet subscriptions." },
  { label: "Mechanic shop growth", desc: "Prioritize mechanic shop plans and provider onboarding while the fleet package stays private." },
  { label: "Fleet product stays intact", desc: "Fleet demos, onboarding, dashboards, and backend workflows remain available for testing and future rollout." },
];

const FAQS = [
  { q: "Do we need to move our data into Roadcall?", a: "No. Roadcall Fleet supports a hybrid in-house mode where only the AI call layer and dispatch actions touch Roadcall infrastructure. Your core fleet data stays in your own database." },
  { q: "Can Roadcall use our tracker data?", a: "Yes. Roadcall can integrate with fleet tracking systems to pull vehicle location into incidents automatically when a driver calls." },
  { q: "Can we keep our internal roadside process?", a: "Yes. Roadcall Fleet is designed to augment your existing process — not replace your dispatcher. The AI handles first contact and data capture; your team takes over at any point." },
  { q: "Can this work with approved vendors only?", a: "Yes. Enterprise plans support an approved vendor list. The geo-match engine will only surface and dispatch to vendors you have pre-approved." },
];

export default function FleetPricingPage() {
  return (
    <main className="roadcall-page min-h-screen text-roadcall-silver">
      {/* Hero */}
      <section className="bg-gradient-to-br from-slate-800 via-blue-900 to-cyan-900 text-white py-16 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <span className="inline-block bg-white/20 text-sm font-medium px-4 py-1 rounded-full mb-6">Roadcall Fleet — On Hold</span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">Fleet subscriptions are paused.</h1>
          <p className="text-blue-200 text-lg">Roadcall is focusing on AI roadside support performance and mechanic shop growth before opening fleet pricing.</p>
        </div>
      </section>

      {/* Hold Notice */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto rounded-2xl border border-roadcall-cyan/20 bg-slate-950/70 p-8 text-center">
          <PauseCircle className="mx-auto h-10 w-10 text-roadcall-cyan" />
          <h2 className="mt-5 text-2xl font-bold text-white">No public fleet pricing right now</h2>
          <p className="mx-auto mt-3 max-w-2xl text-roadcall-muted">
            The fleet product remains available internally for demos and validation, but Roadcall is not selling fleet subscriptions until roadside support performance is proven at the level we want.
          </p>
          <div className="mt-8 grid gap-4 text-left md:grid-cols-3">
            {FLEET_FOCUS.map((item) => (
              <div key={item.label} className="rounded-xl border border-white/10 bg-black/25 p-4">
                <CheckCircle2 className="mb-4 h-5 w-5 text-roadcall-cyan" />
                <p className="font-semibold text-white">{item.label}</p>
                <p className="mt-2 text-sm leading-6 text-roadcall-muted">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Current Focus */}
      <section className="py-16 px-4 bg-slate-950/35 border-y border-white/10">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">What Roadcall is prioritizing first</h2>
          <div className="space-y-4">
            {FLEET_FOCUS.map((item) => (
              <div key={item.label} className="flex gap-4 p-4 bg-slate-950/70 rounded-xl border border-white/10">
                <CheckCircle2 className="w-5 h-5 text-roadcall-cyan flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">{item.label}</span>
                  <span className="text-roadcall-muted"> — {item.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">Frequently asked questions</h2>
          <div className="space-y-6">
            {FAQS.map((faq) => (
              <div key={faq.q} className="border border-white/10 bg-slate-950/55 rounded-xl p-6">
                <div className="flex gap-3 mb-2">
                  <HelpCircle className="w-5 h-5 text-roadcall-cyan flex-shrink-0 mt-0.5" />
                  <p className="font-semibold text-white">{faq.q}</p>
                </div>
                <p className="text-roadcall-muted text-sm ml-8">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-gradient-to-r from-slate-800 to-blue-900 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-2xl font-bold mb-4">Fleet access is waitlist-only</h2>
          <p className="text-blue-200 mb-6">Fleet pages and demos stay available while subscriptions are paused.</p>
          <Link
            href="/fleet/onboarding"
            className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white font-semibold px-8 py-3 rounded-lg hover:brightness-110 transition-colors inline-flex items-center gap-2"
          >
            Request Fleet Review <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
