"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { getApiBase } from "@/lib/api-client";

const PLANS = {
  ai_chat: {
    name: "AI Chat",
    price: "$49/mo",
    setup: "No setup fee",
    features: ["AI website widget", "FAQ assistant", "Appointment capture", "Lead capture", "No SaaS Mode provisioning"],
  },
  widget_voice: {
    name: "Widget + Voice",
    price: "$149/mo",
    setup: "No setup fee",
    features: ["Everything in AI Chat", "AI phone answering", "AI intake", "Missed-call text-back", "No SaaS Mode provisioning"],
  },
  driver_pro: {
    name: "Driver Pro",
    price: "$9.99/mo",
    setup: "No setup fee",
    features: ["Saved truck profile", "Roadside intake", "Preferred providers", "Dispatch tracking", "No SaaS Mode provisioning"],
  },
  professional: {
    name: "Professional",
    price: "$297/mo",
    setup: "$199 setup",
    features: ["AI website", "CRM and pipelines", "Workflows", "Calendars", "GHL SaaS Mode snapshot"],
  },
  premium: {
    name: "Premium",
    price: "$497/mo",
    setup: "$299 setup",
    features: ["Everything in Professional", "Mobile app", "Customer portal", "Fleet dashboard", "Advanced reporting"],
  },
  enterprise: {
    name: "Enterprise",
    price: "$997/mo",
    setup: "$499 setup",
    features: ["Everything in Premium", "Social media marketing", "Funnels and campaigns", "Content automation", "Priority support"],
  },
} as const;

type PlanId = keyof typeof PLANS;

function MechanicCheckoutContent() {
  const params = useSearchParams();
  const rawPlan = params.get("plan") || "widget_voice";
  const initialPlan = ({ starter: "ai_chat", standard: "widget_voice", growth: "professional", pro: "premium", advanced: "enterprise" } as Record<string, PlanId>)[rawPlan] || rawPlan as PlanId;
  const [planId, setPlanId] = useState<PlanId>(PLANS[initialPlan] ? initialPlan : "widget_voice");
  const [businessName, setBusinessName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = useMemo(() => PLANS[planId], [planId]);

  async function startCheckout(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${getApiBase()}/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_id: planId,
          business_name: businessName,
          owner_name: ownerName || undefined,
          email,
          phone: phone || undefined,
          website: website || undefined,
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail || body.message || "Checkout failed");
      }
      window.location.href = body.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#02050c] px-4 py-24 text-white">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8 shadow-2xl">
          <Link href="/pricing" className="text-sm font-semibold text-blue-300 hover:text-blue-200">← Back to pricing</Link>
          <h1 className="mt-8 text-4xl font-black tracking-tight">Start your Roadcall AI advisor.</h1>
          <p className="mt-4 text-slate-300">Subscribe, complete your profile, then Roadcall activates the right AI service or full business OS workspace for your plan.</p>
          <div className="mt-8 space-y-3">
            {["Secure billing activates your subscription", "Lightweight plans skip GHL SaaS Mode provisioning", "Full OS plans create the Roadcall/GHL workspace", "Your profile is completed after checkout"].map((item) => (
              <div key={item} className="flex items-center gap-3 text-sm text-slate-300"><CheckCircle2 className="h-4 w-4 text-emerald-300" /> {item}</div>
            ))}
          </div>
          <div className="mt-8 rounded-2xl border border-blue-400/20 bg-blue-400/10 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-100"><ShieldCheck className="h-4 w-4" /> Secure activation flow</div>
            <p className="mt-2 text-sm text-slate-300">Activation starts after checkout confirms the plan and your profile details are ready.</p>
          </div>
        </section>

        <form onSubmit={startCheckout} className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-6 shadow-2xl">
          <div className="grid gap-3">
            {(Object.keys(PLANS) as PlanId[]).map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setPlanId(id)}
                className={`rounded-2xl border p-4 text-left transition ${planId === id ? "border-orange-300 bg-orange-400/10" : "border-white/10 bg-white/[0.03] hover:border-blue-300/40"}`}
              >
                <p className="font-bold">{PLANS[id].name}</p>
                <p className="mt-1 text-2xl font-black">{PLANS[id].price}</p>
                <p className="mt-1 text-xs text-slate-400">{PLANS[id].setup}</p>
                <p className="mt-2 text-xs leading-5 text-slate-300">{PLANS[id].features.join(" · ")}</p>
              </button>
            ))}
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-sm text-slate-300">Shop name<input required value={businessName} onChange={(event) => setBusinessName(event.target.value)} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
            <label className="space-y-2 text-sm text-slate-300">Owner name<input value={ownerName} onChange={(event) => setOwnerName(event.target.value)} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
            <label className="space-y-2 text-sm text-slate-300">Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
            <label className="space-y-2 text-sm text-slate-300">Phone<input value={phone} onChange={(event) => setPhone(event.target.value)} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
            <label className="space-y-2 text-sm text-slate-300 sm:col-span-2">Website<input value={website} onChange={(event) => setWebsite(event.target.value)} className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-blue-300" /></label>
          </div>

          {error && <div className="mt-5 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</div>}

          <button disabled={loading} className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-full bg-white px-6 py-4 font-bold text-slate-950 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-70">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            Continue to secure checkout for {selectedPlan.name}
          </button>
          <p className="mt-4 text-center text-xs text-slate-500">You’ll manage billing through a secure customer portal after checkout.</p>
        </form>
      </div>
    </main>
  );
}

export default function MechanicCheckoutPage() {
  return (
    <Suspense fallback={<main className="grid min-h-screen place-items-center bg-[#02050c] text-white">Loading checkout…</main>}>
      <MechanicCheckoutContent />
    </Suspense>
  );
}
