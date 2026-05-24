"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Loader2,
  Phone,
  PhoneCall,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLayout } from "@/components/page-layout";
import { FadeIn, GlassCard, SectionHeading } from "@/components/motion";

const capabilities = [
  "Roadcall AI answers calls 24/7 as your shop's service advisor",
  "Connect your existing number with call forwarding or request a Roadcall number",
  "Books appointments into your calendar and captures vehicle/job details",
  "Routes emergencies, after-hours calls, and roadside jobs to the right contact",
  "Shows missed calls recovered, appointments booked, and revenue opportunities captured",
];

const tools = [
  { name: "check_bay_availability", copy: "Confirms open repair slots before offering appointment times." },
  { name: "create_service_appointment", copy: "Creates appointment records with caller, vehicle, issue, and preferred time." },
  { name: "get_after_hours_contact", copy: "Escalates emergency or VIP calls to the right owner/dispatcher." },
  { name: "create_roadside_job", copy: "Turns mobile service calls into dispatch-ready roadside jobs." },
  { name: "estimate_eta", copy: "Gives callers a realistic callback or roadside response expectation." },
  { name: "send_location_link", copy: "Texts a location capture link when the caller needs mobile help." },
];

const metrics = [
  { icon: PhoneCall, label: "Missed calls prevented", value: "24/7" },
  { icon: CalendarClock, label: "Appointments captured", value: "Auto" },
  { icon: BarChart3, label: "Revenue opportunities", value: "Tracked" },
];

const NEW_ROADCALL_NUMBER_MODE = "roadcall_number";

const initialForm = {
  business_name: "",
  owner_name: "",
  email: "",
  phone: "",
  website: "",
  current_phone_number: "",
  phone_onboarding_mode: "existing_number",
  requested_area_code: "",
  service_area: "",
  services_offered: "",
  business_hours: "",
  current_calendar: "",
  calcom_calendar_url: "",
  wants_ai_answering: true,
  wants_booking: true,
  wants_after_hours: true,
  wants_emergency_dispatch: false,
  notes: "",
};

type TelephonyForm = typeof initialForm;

type BooleanField = {
  field: keyof Pick<
    TelephonyForm,
    "wants_ai_answering" | "wants_booking" | "wants_after_hours" | "wants_emergency_dispatch"
  >;
  label: string;
  description: string;
};

const booleanFields: BooleanField[] = [
  { field: "wants_ai_answering", label: "AI phone answering", description: "Roadcall answers and qualifies every inbound call." },
  { field: "wants_booking", label: "Calendar booking", description: "Book shop appointments during the call." },
  { field: "wants_after_hours", label: "After-hours coverage", description: "Capture jobs after closing instead of sending callers to voicemail." },
  { field: "wants_emergency_dispatch", label: "Roadside dispatch", description: "Escalate mobile/urgent jobs to a human or dispatch workflow." },
];

export default function AiTelephonyPage() {
  const [form, setForm] = useState<TelephonyForm>(initialForm);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  function setField<K extends keyof TelephonyForm>(field: K, value: TelephonyForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (!form.business_name || !form.owner_name || !form.email || !form.phone) {
      setError("Please add the shop name, owner name, email, and phone number.");
      return;
    }
    if (form.phone_onboarding_mode === NEW_ROADCALL_NUMBER_MODE && !form.requested_area_code) {
      setError("Please add the preferred area code for the new Roadcall number.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/shops/onboarding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, source: "ai-telephony-calendar" }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.detail || "Could not submit the AI telephony setup request.");
      }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit the AI telephony setup request.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageLayout>
      <section className="relative overflow-hidden border-b border-roadcall-cyan/10 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.18),transparent_35%),linear-gradient(135deg,#02050c_0%,#07101f_48%,#02050c_100%)] py-24 md:py-32">
        <div className="absolute right-[-10%] top-10 h-72 w-72 rounded-full bg-roadcall-orange/20 blur-3xl" />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/15 bg-roadcall-panel/60 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-roadcall-cyan">
              <Sparkles className="h-4 w-4 text-roadcall-orange" /> AI Telephony + Calendar
            </div>
            <h1 className="mt-8 text-5xl font-black leading-tight tracking-tight text-white md:text-7xl">
              AI service advisor for truck repair shops.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-roadcall-silver/85">
              Add Roadcall AI phone answering and appointment booking to your shop without changing Roadcall&apos;s existing dispatch, fleet, or marketplace flows.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a href="#setup">
                <Button size="lg" className="rounded-xl bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-8 font-semibold text-white hover:brightness-110">
                  Configure My AI Phone <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </a>
              <Link href="/shops/pricing">
                <Button size="lg" variant="outline" className="rounded-xl border-roadcall-cyan/20 bg-roadcall-panel/50 px-8 text-white hover:bg-roadcall-panel/70">
                  View Shop Plans
                </Button>
              </Link>
            </div>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {metrics.map((metric) => (
                <div key={metric.label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <metric.icon className="h-5 w-5 text-roadcall-orange" />
                  <div className="mt-3 text-2xl font-bold text-white">{metric.value}</div>
                  <div className="text-xs text-roadcall-muted">{metric.label}</div>
                </div>
              ))}
            </div>
          </FadeIn>

          <FadeIn delay={0.15}>
            <GlassCard className="p-6">
              <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-roadcall-orange/15 text-roadcall-orange">
                    <Phone className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm uppercase tracking-[0.2em] text-roadcall-muted">Live call flow</p>
                    <h2 className="text-xl font-bold text-white">Roadcall service advisor</h2>
                  </div>
                </div>
                <div className="mt-6 space-y-3">
                  {capabilities.map((item) => (
                    <div key={item} className="flex gap-3 rounded-xl border border-white/5 bg-white/[0.03] p-3 text-sm text-roadcall-silver/85">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-roadcall-cyan" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>
          </FadeIn>
        </div>
      </section>

      <section className="py-20 md:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <SectionHeading
            eyebrow="Built for mechanic shops"
            title="Answer, qualify, book, and escalate from one call"
            description="The new module is additive: it stores shop-specific phone, calendar, and AI advisor settings while keeping existing Roadcall dispatch and admin systems intact."
          />
          <div className="grid gap-5 md:grid-cols-3">
            {[
              { icon: PhoneCall, title: "Bring or request a number", copy: "Forward your current shop line, or request a Roadcall-provisioned number with your preferred area code." },
              { icon: CalendarClock, title: "Calendar-aware booking", copy: "Use your calendar for repair estimates, DOT inspections, fleet service, and emergency callbacks." },
              { icon: ShieldCheck, title: "Human fallback rules", copy: "Route VIP customers, after-hours jobs, and roadside emergencies to the owner or dispatcher." },
            ].map((feature, index) => (
              <FadeIn key={feature.title} delay={index * 0.05}>
                <GlassCard className="h-full p-6">
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-roadcall-blue/15 text-roadcall-cyan">
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-bold text-white">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-roadcall-muted">{feature.copy}</p>
                </GlassCard>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-roadcall-cyan/10 bg-roadcall-panel/20 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <SectionHeading eyebrow="AI tool layer" title="Service advisor actions we can wire in" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tools.map((tool) => (
              <div key={tool.name} className="rounded-2xl border border-white/5 bg-slate-950/60 p-5">
                <code className="rounded-lg bg-roadcall-cyan/10 px-2 py-1 text-xs text-roadcall-cyan">{tool.name}</code>
                <p className="mt-3 text-sm text-roadcall-muted">{tool.copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="setup" className="py-20 md:py-28">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-orange/25 bg-roadcall-orange/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-roadcall-orange">
              <Wrench className="h-4 w-4" /> Shop setup
            </div>
            <h2 className="mt-6 text-4xl font-black text-white">Tell us how to connect your phones and calendar.</h2>
            <p className="mt-4 text-roadcall-muted">
              Submit this once. We&apos;ll create the shop AI telephony profile, confirm voice settings, provision or forward the phone number, and connect calendar booking.
            </p>
            <div className="mt-6 rounded-2xl border border-white/5 bg-white/[0.03] p-5 text-sm text-roadcall-silver/80">
              <div className="flex items-center gap-2 font-semibold text-white">
                <Clock3 className="h-4 w-4 text-roadcall-cyan" /> Setup path
              </div>
              <ol className="mt-4 space-y-3 text-roadcall-muted">
                <li>1. Choose existing number forwarding or a new Roadcall number.</li>
                <li>2. Add services, hours, and calendar details.</li>
                <li>3. Roadcall configures AI voice routing and calendar booking.</li>
              </ol>
            </div>
          </div>

          <form onSubmit={submit} className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl">
            {success ? (
              <div className="py-16 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400">
                  <CheckCircle2 className="h-8 w-8" />
                </div>
                <h3 className="mt-6 text-2xl font-bold text-white">AI telephony request received.</h3>
                <p className="mx-auto mt-3 max-w-md text-roadcall-muted">
                  We&apos;ll review your number choice, calendar setup, and AI phone configuration details before activating the shop profile.
                </p>
                <Link href="/shops" className="mt-6 inline-flex items-center gap-2 text-roadcall-cyan hover:underline">
                  Back to Roadcall Shops <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Shop name" required value={form.business_name} onChange={(value) => setField("business_name", value)} placeholder="Big Rig Repair Co." />
                  <Field label="Owner name" required value={form.owner_name} onChange={(value) => setField("owner_name", value)} placeholder="John Smith" />
                  <Field label="Email" required type="email" value={form.email} onChange={(value) => setField("email", value)} placeholder="owner@shop.com" />
                  <Field label="Best phone" required type="tel" value={form.phone} onChange={(value) => setField("phone", value)} placeholder="(813) 555-0100" />
                  <Field label="Website" type="url" value={form.website} onChange={(value) => setField("website", value)} placeholder="https://shop.com" />
                  <Field label="Service area" value={form.service_area} onChange={(value) => setField("service_area", value)} placeholder="Tampa, FL — 50 miles" />
                </div>

                <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                  <label className="text-sm font-semibold text-white">Phone setup</label>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label className={`rounded-xl border p-4 ${form.phone_onboarding_mode === "existing_number" ? "border-roadcall-cyan bg-roadcall-cyan/10" : "border-white/10 bg-black/20"}`}>
                      <input type="radio" name="phone_mode" className="sr-only" checked={form.phone_onboarding_mode === "existing_number"} onChange={() => setField("phone_onboarding_mode", "existing_number")} />
                      <span className="font-semibold text-white">Use my existing number</span>
                      <span className="mt-1 block text-xs text-roadcall-muted">Forward your shop line to the Roadcall AI advisor.</span>
                    </label>
                    <label className={`rounded-xl border p-4 ${form.phone_onboarding_mode === NEW_ROADCALL_NUMBER_MODE ? "border-roadcall-orange bg-roadcall-orange/10" : "border-white/10 bg-black/20"}`}>
                      <input type="radio" name="phone_mode" className="sr-only" checked={form.phone_onboarding_mode === NEW_ROADCALL_NUMBER_MODE} onChange={() => setField("phone_onboarding_mode", NEW_ROADCALL_NUMBER_MODE)} />
                      <span className="font-semibold text-white">Request a Roadcall number</span>
                      <span className="mt-1 block text-xs text-roadcall-muted">Roadcall provisions and routes the new number.</span>
                    </label>
                  </div>
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Field label="Current shop number" type="tel" value={form.current_phone_number} onChange={(value) => setField("current_phone_number", value)} placeholder="Number to forward" />
                    <Field label="Preferred area code" value={form.requested_area_code} onChange={(value) => setField("requested_area_code", value.replace(/\D/g, "").slice(0, 3))} placeholder="813" />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Current calendar" value={form.current_calendar} onChange={(value) => setField("current_calendar", value)} placeholder="Calendar system, shop software..." />
                  <Field label="Calendar booking link" type="url" value={form.calcom_calendar_url} onChange={(value) => setField("calcom_calendar_url", value)} placeholder="https://your-booking-link.com/service" />
                  <Textarea label="Services offered" value={form.services_offered} onChange={(value) => setField("services_offered", value)} placeholder="Diagnostics, DOT inspection, tires, mobile repair..." />
                  <Textarea label="Business hours" value={form.business_hours} onChange={(value) => setField("business_hours", value)} placeholder="Mon–Fri 7am–6pm, after-hours emergency coverage..." />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {booleanFields.map((item) => (
                    <label key={item.field} className="flex cursor-pointer gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                      <input
                        type="checkbox"
                        checked={Boolean(form[item.field])}
                        onChange={(event) => setField(item.field, event.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-white/20 bg-slate-950 text-roadcall-orange"
                      />
                      <span>
                        <span className="block text-sm font-semibold text-white">{item.label}</span>
                        <span className="mt-1 block text-xs text-roadcall-muted">{item.description}</span>
                      </span>
                    </label>
                  ))}
                </div>

                <Textarea label="Notes" value={form.notes} onChange={(value) => setField("notes", value)} placeholder="Preferred AI voice, escalation contacts, shop software, appointment rules, fleet account rules..." />

                {error && <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-3 text-sm text-red-200">{error}</div>}

                <Button type="submit" disabled={loading} className="w-full rounded-xl bg-gradient-to-r from-roadcall-orange to-roadcall-blue py-6 text-base font-semibold text-white hover:brightness-110 disabled:opacity-60">
                  {loading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <ArrowRight className="mr-2 h-5 w-5" />}
                  Submit AI Telephony Setup
                </Button>
                <p className="text-center text-xs text-roadcall-muted">No payment on this form. Roadcall confirms number availability and calendar setup before activation.</p>
              </div>
            )}
          </form>
        </div>
      </section>
    </PageLayout>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  required = false,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-roadcall-silver">
        {label} {required && <span className="text-roadcall-orange">*</span>}
      </span>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none placeholder:text-roadcall-muted/60 focus:border-roadcall-cyan/60"
      />
    </label>
  );
}

function Textarea({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block sm:col-span-1">
      <span className="text-sm font-medium text-roadcall-silver">{label}</span>
      <textarea
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none placeholder:text-roadcall-muted/60 focus:border-roadcall-cyan/60"
      />
    </label>
  );
}