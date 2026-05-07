"use client";

import Link from "next/link";
import { Shield, Lock, Eye, MapPin, Database, Users, FileText, Layers, ArrowRight } from "lucide-react";
import { HELP_PHONE } from "@/lib/phone";

const PILLARS = [
  { icon: Shield, title: "Tenant Isolation", desc: "Each fleet organization operates in a fully isolated data context. No cross-tenant data access is possible at the query layer." },
  { icon: Users, title: "Role-Based Access Control", desc: "Dispatcher, manager, and read-only roles control who can create incidents, assign vendors, or export data." },
  { icon: FileText, title: "Audit Logs", desc: "Every incident creation, status change, and location capture is timestamped and logged to an immutable audit trail." },
  { icon: MapPin, title: "One-Time Location Links", desc: "Driver GPS links are single-use tokens with a 2-hour TTL. No persistent tracking. Location is captured once per incident and then the token expires." },
  { icon: Database, title: "Private Tenant Option", desc: "Enterprise fleets can run a dedicated Roadcall instance — completely isolated infrastructure, not shared with any other organization." },
  { icon: Layers, title: "Hybrid In-House Data Mode", desc: "Keep incident outcomes, driver records, and vehicle data in your own database. Roadcall only handles the AI call layer and vendor dispatch." },
  { icon: Lock, title: "Token Encryption", desc: "Magic-link tokens, location tokens, and API credentials are stored as hashed or encrypted values — never plaintext in the database." },
  { icon: Eye, title: "Incident-Level Data Minimization", desc: "Only the data needed to dispatch roadside help is collected. Driver PII is not retained beyond incident resolution unless you opt in." },
];

const DATA_MODES = [
  {
    name: "Hosted Multi-Tenant",
    tag: "Default",
    color: "border-blue-200 bg-blue-50",
    tagColor: "bg-blue-100 text-blue-700",
    items: [
      "Shared infrastructure, isolated data",
      "Fastest time-to-live",
      "Managed updates and uptime",
      "Best for fleets under 500 vehicles",
    ],
  },
  {
    name: "Private Tenant",
    tag: "Enterprise",
    color: "border-slate-300 bg-white",
    tagColor: "bg-slate-800 text-white",
    items: [
      "Dedicated infrastructure, your namespace",
      "No shared resources with other fleets",
      "Custom domain and branding available",
      "Best for carriers with strict compliance needs",
    ],
  },
  {
    name: "Hybrid In-House",
    tag: "Advanced",
    color: "border-cyan-200 bg-cyan-50",
    tagColor: "bg-cyan-700 text-white",
    items: [
      "Roadcall handles AI calls + vendor dispatch",
      "Incident outcomes sync to your own DB",
      "No core fleet data leaves your environment",
      "Best for enterprise carriers with existing data stacks",
    ],
  },
];

export default function FleetSecurityPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Hero */}
      <section className="bg-gradient-to-br from-slate-800 via-blue-900 to-slate-900 text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-block bg-white/20 text-sm font-medium px-4 py-1 rounded-full mb-6">
            Roadcall Fleet — Security
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            Fleet roadside automation with controlled data access
          </h1>
          <p className="text-blue-200 text-xl max-w-2xl mx-auto mb-10">
            Enterprise roadside support without forcing fleet data into a third-party CRM.
            Your data architecture. Your rules.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/fleet/onboarding"
              className="bg-white text-slate-900 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors inline-flex items-center gap-2"
            >
              Request Fleet Security Review <ArrowRight className="w-4 h-4" />
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

      {/* Security Pillars */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Eight security pillars</h2>
            <p className="text-gray-600 max-w-xl mx-auto">Built from the ground up for carriers that cannot afford data exposure during roadside events.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {PILLARS.map((p) => {
              const Icon = p.icon;
              return (
                <div key={p.title} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{p.title}</h3>
                  <p className="text-sm text-gray-600 leading-relaxed">{p.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Data Modes */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Choose your data architecture</h2>
            <p className="text-gray-600">Three deployment modes — all supported, no lock-in.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {DATA_MODES.map((m) => (
              <div key={m.name} className={`rounded-2xl border-2 p-8 ${m.color}`}>
                <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full mb-4 ${m.tagColor}`}>{m.tag}</span>
                <h3 className="font-bold text-gray-900 text-xl mb-4">{m.name}</h3>
                <ul className="space-y-3">
                  {m.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-gray-700">
                      <Shield className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Value */}
      <section className="py-20 px-4 bg-slate-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">Why security-first fleet automation matters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            {[
              { title: "For the Industry", body: "Trucking operations have historically been forced to use consumer tools or generic SaaS that weren't designed for fleet data sensitivity. Roadcall Fleet was built differently from day one." },
              { title: "For the Fleet", body: "Driver locations, vehicle movements, vendor relationships, and incident data are operationally sensitive. Roadcall protects all of it while still automating roadside support." },
              { title: "The Outcome", body: "Faster roadside response without losing data control. Your drivers get help faster. Your ops team doesn't get a security incident." },
            ].map((v) => (
              <div key={v.title} className="bg-white rounded-xl p-8 shadow-sm border border-slate-100">
                <h3 className="font-semibold text-gray-900 text-lg mb-3">{v.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{v.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-gradient-to-r from-slate-800 to-blue-900 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-2xl font-bold mb-4">Request a Fleet Security Review</h2>
          <p className="text-blue-200 mb-6">Walk through our data architecture with a Roadcall Fleet engineer before signing anything.</p>
          <Link
            href="/fleet/onboarding"
            className="bg-white text-slate-900 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors inline-flex items-center gap-2"
          >
            Start Fleet Setup <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
