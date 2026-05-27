"use client";

import Link from "next/link";
import Image from "next/image";
import { Shield, Lock, Eye, MapPin, Database, Users, FileText, Layers, ArrowRight } from "lucide-react";
import { HELP_PHONE } from "@/lib/phone";
import { supportMailtoHref } from "@/lib/support-email";

const FLEET_SECURITY_REQUEST_HREF = supportMailtoHref("Roadcall fleet security review request", { source: "fleet_security" });

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
    color: "border-roadcall-cyan/35 bg-roadcall-cyan/10",
    tagColor: "bg-roadcall-cyan/15 text-roadcall-cyan",
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
    color: "border-white/10 bg-slate-950/70",
    tagColor: "bg-roadcall-panel text-white",
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
    color: "border-cyan-300/30 bg-cyan-400/10",
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
    <main className="roadcall-page min-h-screen text-roadcall-silver">
      {/* Hero */}
      <section className="relative min-h-[65vh] flex flex-col justify-end overflow-hidden">
        <Image
          src="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1920&q=80"
          alt="Secure data center server infrastructure"
          fill
          priority
          className="object-cover object-center"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-black/90 z-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-transparent to-black/30 z-10" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(59,130,246,0.22),transparent_70%)] z-10" />
        <div className="relative z-20 max-w-4xl mx-auto px-4 sm:px-6 w-full pb-16 pt-28 text-center">
          <span className="inline-flex items-center gap-2 bg-roadcall-panel/60 border border-roadcall-cyan/20 backdrop-blur-sm text-sm font-medium px-4 py-1.5 rounded-full mb-8 text-roadcall-silver">
            Roadcall Fleet — Security
          </span>
          <h1 className="text-5xl md:text-6xl font-black leading-[0.95] mb-6 text-white">
            Fleet roadside automation<br />
            <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">with controlled data access</span>
          </h1>
          <p className="text-lg text-roadcall-silver/85 max-w-2xl mx-auto mb-10 leading-relaxed">
            Enterprise roadside support without forcing fleet data into an outside CRM.
            Your data architecture. Your rules.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href={FLEET_SECURITY_REQUEST_HREF}
              className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-semibold px-8 py-3 rounded-xl transition-colors inline-flex items-center gap-2"
            >
              Request Fleet Security Review <ArrowRight className="w-4 h-4" />
            </a>
            <a
              href={`tel:${HELP_PHONE}`}
              className="border border-roadcall-cyan/30 bg-roadcall-panel/45 backdrop-blur-sm text-white font-semibold px-8 py-3 rounded-xl hover:bg-roadcall-panel/60 transition-colors"
            >
              Call {HELP_PHONE}
            </a>
          </div>
        </div>
      </section>

      {/* Security Pillars */}
      <section className="py-20 px-4 bg-slate-950/35 border-y border-white/10">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-white mb-4">Eight security pillars</h2>
            <p className="text-roadcall-muted max-w-xl mx-auto">Built from the ground up for carriers that cannot afford data exposure during roadside events.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {PILLARS.map((p) => {
              const Icon = p.icon;
              return (
                <div key={p.title} className="bg-slate-950/70 rounded-xl p-6 border border-white/10 hover:border-roadcall-cyan/35 transition-colors">
                  <div className="w-10 h-10 bg-roadcall-cyan/15 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-roadcall-cyan" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">{p.title}</h3>
                  <p className="text-sm text-roadcall-muted leading-relaxed">{p.desc}</p>
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
            <h2 className="text-3xl font-bold text-white mb-4">Choose your data architecture</h2>
            <p className="text-roadcall-muted">Three deployment modes — all supported, no lock-in.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {DATA_MODES.map((m) => (
              <div key={m.name} className={`rounded-2xl border-2 p-8 ${m.color}`}>
                <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full mb-4 ${m.tagColor}`}>{m.tag}</span>
                <h3 className="font-bold text-white text-xl mb-4">{m.name}</h3>
                <ul className="space-y-3">
                  {m.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-slate-300">
                      <Shield className="w-4 h-4 text-roadcall-cyan flex-shrink-0 mt-0.5" />
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
      <section className="py-20 px-4 bg-slate-950/35 border-y border-white/10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-12 text-center">Why security-first fleet automation matters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            {[
              { title: "For the Industry", body: "Trucking operations have historically been forced to use consumer tools or generic SaaS that weren't designed for fleet data sensitivity. Roadcall Fleet was built differently from day one." },
              { title: "For the Fleet", body: "Driver locations, vehicle movements, vendor relationships, and incident data are operationally sensitive. Roadcall protects all of it while still automating roadside support." },
              { title: "The Outcome", body: "Faster roadside response without losing data control. Your drivers get help faster. Your ops team doesn't get a security incident." },
            ].map((v) => (
              <div key={v.title} className="bg-slate-950/70 rounded-xl p-8 border border-white/10">
                <h3 className="font-semibold text-white text-lg mb-3">{v.title}</h3>
                <p className="text-roadcall-muted text-sm leading-relaxed">{v.body}</p>
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
          <a
            href={FLEET_SECURITY_REQUEST_HREF}
            className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white font-semibold px-8 py-3 rounded-lg hover:brightness-110 transition-colors inline-flex items-center gap-2"
          >
            Start Fleet Setup <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </section>
    </main>
  );
}
