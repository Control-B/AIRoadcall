"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Bot, LogIn, PlayCircle, Truck, Wrench } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { getApiBase } from "@/lib/api-client";
import { GHL_SIGN_IN_URL, isExternalUrl } from "@/lib/ghl-links";
import { supportMailtoHref } from "@/lib/support-email";

const FLEET_SETUP_REQUEST_HREF = supportMailtoHref("Roadcall fleet setup request", { source: "sign_in_fleet_track" });

type Role = "shop" | "fleet";

const ROLES: { id: Role; label: string; icon: typeof Wrench; tagline: string }[] = [
  { id: "shop", label: "Shop / Mechanic", icon: Wrench, tagline: "AI service advisor that answers, qualifies, and books." },
  { id: "fleet", label: "Fleet Manager", icon: Truck, tagline: "AI roadside dispatch for trucks, trailers, and drivers." },
];

const GHL_DASHBOARD_HREF = GHL_SIGN_IN_URL || "/pricing";
const GHL_DASHBOARD_EXTERNAL = isExternalUrl(GHL_DASHBOARD_HREF);

export default function SignInPage() {
  const [role, setRole] = useState<Role>("shop");

  return (
    <PageLayout>
      <section className="min-h-[85vh] px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-orange/25 bg-roadcall-orange/10 px-4 py-1.5 mb-6">
              <LogIn className="h-4 w-4 text-roadcall-orange" />
              <span className="text-sm font-medium text-orange-100">Sign In</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-black text-white mb-4">Create or access your Roadcall account</h1>
            <p className="text-roadcall-muted max-w-xl mx-auto leading-relaxed">
              New customers can choose a plan and create an account. Returning subscribers can continue to the GHL dashboard.
            </p>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2">
            {ROLES.map((option) => {
              const Icon = option.icon;
              const active = role === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setRole(option.id)}
                  className={`rounded-2xl border p-5 text-left transition ${
                    active
                      ? "border-roadcall-orange/60 bg-roadcall-orange/10"
                      : "border-slate-700/60 bg-roadcall-panel/40 hover:border-roadcall-cyan/40"
                  }`}
                >
                  <Icon className={`h-6 w-6 ${active ? "text-roadcall-orange" : "text-roadcall-cyan"}`} />
                  <p className="mt-3 font-bold text-white">{option.label}</p>
                  <p className="mt-1 text-sm text-roadcall-muted">{option.tagline}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-10 rounded-[2rem] border border-white/10 bg-white/[0.03] p-8 shadow-2xl">
            {role === "shop" && <ShopTrack />}
            {role === "fleet" && <FleetTrack />}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}

function ShopTrack() {
  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <div className="flex items-center gap-2 text-roadcall-orange">
          <Wrench className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Shop / Mechanic</span>
        </div>
        <h2 className="mt-3 text-2xl font-bold text-white">Subscribe, set up, go live.</h2>
        <p className="mt-3 text-roadcall-muted">
          Secure billing activates your account. Once paid, Roadcall seeds your shop profile,
          provisions your AI advisor, and connects your customer dashboard.
        </p>
        <div className="mt-6 space-y-3">
          <Link href="/pricing" className="block">
            <Button className="w-full bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold rounded-xl py-6">
              <ArrowRight className="h-4 w-4 mr-2" /> View plans &amp; create account
            </Button>
          </Link>
          <ReturningSubscriberButton />
          <Link href="/mechanic/dashboard?demo=1" className="block">
            <Button variant="outline" className="w-full border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl py-6">
              <PlayCircle className="h-4 w-4 mr-2" /> Try the Mechanics AI Profile
            </Button>
          </Link>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-black/30 p-6">
        <div className="flex items-center gap-2 text-roadcall-cyan">
          <Bot className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Returning customer</span>
        </div>
        <h3 className="mt-3 text-lg font-bold text-white">Need your dashboard link?</h3>
        <p className="mt-2 text-sm text-roadcall-muted">
          Existing subscribers can open the GHL dashboard directly or request a fresh sign-in link by email.
        </p>
        <ReturningSubscriberButton compact />
        <ResendLinkForm vertical="shop" />
      </div>
    </div>
  );
}

function FleetTrack() {
  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <div className="flex items-center gap-2 text-roadcall-cyan">
          <Truck className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Fleet Manager</span>
        </div>
        <h2 className="mt-3 text-2xl font-bold text-white">Tell us about your fleet.</h2>
        <p className="mt-3 text-roadcall-muted">
          Fleet onboarding is concierge — share fleet size, assets, and data mode,
          and our team configures your AI roadside dispatch. Fleet demo dashboard
          is coming next.
        </p>
        <div className="mt-6 space-y-3">
          <a href={FLEET_SETUP_REQUEST_HREF} className="block">
            <Button className="w-full bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold rounded-xl py-6">
              <ArrowRight className="h-4 w-4 mr-2" /> Start fleet onboarding
            </Button>
          </a>
          <ReturningSubscriberButton />
          <Link href="/fleet/dashboard?demo=1" className="block">
            <Button variant="outline" className="w-full border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl py-6">
              <PlayCircle className="h-4 w-4 mr-2" /> Try the fleet demo dashboard
            </Button>
          </Link>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-black/30 p-6">
        <div className="flex items-center gap-2 text-roadcall-cyan">
          <Bot className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em]">Returning customer</span>
        </div>
        <h3 className="mt-3 text-lg font-bold text-white">Need your fleet console link?</h3>
        <p className="mt-2 text-sm text-roadcall-muted">
          Existing subscribers can open the GHL dashboard directly or request a fresh sign-in link.
        </p>
        <ReturningSubscriberButton compact />
        <ResendLinkForm vertical="fleet" />
      </div>
    </div>
  );
}

function ReturningSubscriberButton({ compact = false }: { compact?: boolean }) {
  const className = compact ? "mt-4 block" : "block";
  const rel = GHL_DASHBOARD_EXTERNAL ? "noopener noreferrer" : undefined;
  const target = GHL_DASHBOARD_EXTERNAL ? "_blank" : undefined;

  return (
    <Link href={GHL_DASHBOARD_HREF} target={target} rel={rel} className={className}>
      <Button variant="outline" className="w-full border-roadcall-cyan/35 text-roadcall-silver/90 hover:bg-roadcall-panel rounded-xl py-6">
        <LogIn className="h-4 w-4 mr-2" /> Already subscribed? Continue to GHL dashboard
      </Button>
    </Link>
  );
}

function ResendLinkForm({ vertical }: { vertical: "shop" | "fleet" }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!email.includes("@")) {
      setStatus("error");
      return;
    }
    setStatus("sending");
    try {
      const res = await fetch(`${getApiBase()}/billing/resend-dashboard-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, vertical }),
      });
      // Backend always returns 200 with a generic message to avoid leaking
      // account existence; treat any 2xx as success.
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus("sent");
    } catch {
      // Fall back to optimistic confirmation — we never want to disclose
      // whether a given email maps to an account.
      setStatus("sent");
    }
  }

  return (
    <form onSubmit={submit} className="mt-4 space-y-3">
      <input
        type="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        placeholder={vertical === "shop" ? "you@yourshop.com" : "dispatch@yourfleet.com"}
        className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none focus:border-roadcall-cyan"
      />
      <Button
        type="submit"
        variant="outline"
        disabled={status === "sending"}
        className="w-full border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl"
      >
        {status === "sending" ? "Sending…" : "Send my sign-in link"}
      </Button>
      {status === "sent" && (
        <p className="text-xs text-emerald-300">
          If an account exists for {email}, a sign-in link is on the way. Check your inbox.
        </p>
      )}
      {status === "error" && (
        <p className="text-xs text-red-300">Please enter a valid email address.</p>
      )}
    </form>
  );
}
