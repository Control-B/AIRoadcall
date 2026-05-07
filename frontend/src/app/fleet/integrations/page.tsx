"use client";

import Link from "next/link";
import { ArrowRight, Plug, Truck, Map, Wrench, Radio, Network, MessageSquare } from "lucide-react";
import { HELP_PHONE } from "@/lib/phone";

const CATEGORIES = [
  {
    icon: Truck,
    title: "Vehicle Database",
    desc: "Sync your unit numbers, VINs, and vehicle types so the AI knows your fleet during every call.",
    providers: ["CSV Import", "Manual Entry", "REST API"],
  },
  {
    icon: Map,
    title: "GPS / Telematics",
    desc: "Pull real-time vehicle location into incidents automatically when a driver calls.",
    providers: ["Samsara", "Geotab", "Motive", "Custom API"],
  },
  {
    icon: Radio,
    title: "ELD Systems",
    desc: "Cross-reference HOS data when logging incidents for compliance documentation.",
    providers: ["Motive (KeepTruckin)", "Geotab Drive", "Custom ELD"],
  },
  {
    icon: Wrench,
    title: "Maintenance Systems",
    desc: "Create work orders automatically from roadside incidents.",
    providers: ["Fleetio", "RTA", "Dossier", "Custom API"],
  },
  {
    icon: Network,
    title: "Dispatch / TMS",
    desc: "Notify your TMS when a load is delayed due to a breakdown and trigger re-routing.",
    providers: ["McLeod", "TMW", "Custom TMS"],
  },
  {
    icon: Plug,
    title: "Vendor / Mechanic Network",
    desc: "Bring your approved vendor list into Roadcall for geo-matched dispatch.",
    providers: ["CSV Import", "Manual Entry", "REST API"],
  },
  {
    icon: MessageSquare,
    title: "SMS / Voice Providers",
    desc: "Route driver and vendor communications through your preferred telecom layer.",
    providers: ["Twilio", "Telnyx", "Retell AI"],
  },
];

const STEPS = [
  { step: "01", title: "Connect your fleet data source", desc: "Link your vehicle database, GPS provider, or upload a CSV to seed unit and driver records." },
  { step: "02", title: "Map vehicle and unit fields", desc: "Tell Roadcall which field is your unit number, which is your VIN, and what vehicle types you run." },
  { step: "03", title: "Configure roadside rules", desc: "Set approved vendor networks, dispatch radius, after-hours escalation paths, and data-mode preference." },
  { step: "04", title: "Activate AI support", desc: "Go live. The Retell AI agent answers roadside calls and creates structured incidents automatically." },
  { step: "05", title: "Sync incident outcomes", desc: "Resolved incidents push back to your maintenance system, TMS, or webhook endpoint of choice." },
];

export default function FleetIntegrationsPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-700 via-cyan-700 to-blue-800 text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-block bg-white/20 text-sm font-medium px-4 py-1 rounded-full mb-6">
            Roadcall Fleet — Integrations
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            Connect Roadcall to your fleet systems
          </h1>
          <p className="text-blue-100 text-xl max-w-2xl mx-auto mb-10">
            Roadcall Fleet plugs into your existing GPS, ELD, maintenance, and dispatch stack —
            so you automate roadside support without replacing what's already working.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/fleet/onboarding"
              className="bg-white text-blue-700 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors inline-flex items-center gap-2"
            >
              Plan Fleet Integration <ArrowRight className="w-4 h-4" />
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

      {/* Categories */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Integration categories</h2>
            <p className="text-gray-600 max-w-xl mx-auto">Seven categories covering the full fleet operations stack. Native connectors and open REST API for anything else.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {CATEGORIES.map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.title} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{c.title}</h3>
                  <p className="text-sm text-gray-600 mb-4">{c.desc}</p>
                  <div className="flex flex-wrap gap-2">
                    {c.providers.map((p) => (
                      <span key={p} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full border border-blue-100">{p}</span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Integration Flow */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">How integration works</h2>
            <p className="text-gray-600">Five steps from data connection to live roadside AI support.</p>
          </div>
          <div className="space-y-6">
            {STEPS.map((s, i) => (
              <div key={s.title} className="flex gap-6 items-start p-6 bg-gray-50 rounded-xl border border-gray-100">
                <div className="flex-shrink-0 w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg">
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

      {/* Open API note */}
      <section className="py-16 px-4 bg-blue-50 border-y border-blue-100">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Not on the list? Use the open API.</h2>
          <p className="text-gray-600 mb-6">
            Every Roadcall Fleet endpoint is accessible via REST. Bring your own integration, your own scheduler,
            your own data pipeline — we publish and version our API so your team can build confidently.
          </p>
          <Link
            href="/fleet/onboarding"
            className="bg-blue-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
          >
            Plan Fleet Integration <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-gradient-to-r from-blue-700 to-cyan-700 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-2xl font-bold mb-4">Ready to connect your fleet stack?</h2>
          <p className="text-blue-100 mb-6">Book a call with the Roadcall Fleet team to map your integration path.</p>
          <Link
            href="/fleet/onboarding"
            className="bg-white text-blue-700 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors inline-flex items-center gap-2"
          >
            Start Fleet Setup <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
