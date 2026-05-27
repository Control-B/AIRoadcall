"use client";

import { useState } from "react";
import { CheckCircle2, ArrowRight, Loader2 } from "lucide-react";
import { SUPPORT_EMAIL, submitSupportRequest } from "@/lib/support-email";

interface ShopsFormData {
  business_name: string;
  owner_name: string;
  email: string;
  phone: string;
  website: string;
  service_area: string;
  services_offered: string;
  business_hours: string;
  current_phone_number: string;
  wants_ai_answering: boolean;
  wants_booking: boolean;
  wants_reviews: boolean;
  notes: string;
}

const INITIAL: ShopsFormData = {
  business_name: "",
  owner_name: "",
  email: "",
  phone: "",
  website: "",
  service_area: "",
  services_offered: "",
  business_hours: "",
  current_phone_number: "",
  wants_ai_answering: true,
  wants_booking: true,
  wants_reviews: false,
  notes: "",
};

export default function ShopsOnboardingPage() {
  const [form, setForm] = useState<ShopsFormData>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const set = (field: keyof ShopsFormData, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.business_name || !form.owner_name || !form.email || !form.phone) {
      setError("Please fill in all required fields.");
      return;
    }
    setLoading(true);
    try {
      await submitSupportRequest("shops", "Roadcall shop listing request", { ...form, source: "shops_onboarding" });
      setSuccess(true);
    } catch {
      setError(`Could not prepare the support email. Please email ${SUPPORT_EMAIL}.`);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <main className="min-h-screen bg-roadcall-void flex items-center justify-center px-4 text-white">
        <div className="max-w-md w-full text-center bg-roadcall-panel/40 rounded-2xl shadow-2xl shadow-black/30 border border-roadcall-cyan/10 p-12">
          <div className="w-16 h-16 bg-emerald-500/15 border border-emerald-400/25 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-8 h-8 text-emerald-300" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-3">Shop profile received!</h1>
          <p className="text-roadcall-muted mb-6">
            Your request was sent to Roadcall support, or an email draft opened with your completed shop profile.
          </p>
          <a
            href="/shops"
            className="inline-flex items-center gap-2 bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white font-semibold px-6 py-3 rounded-lg hover:brightness-110 transition-colors"
          >
            Back to Roadcall Shops <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-roadcall-void py-16 px-4 text-white">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <span className="inline-block bg-roadcall-orange/10 text-roadcall-orange border border-roadcall-orange/20 text-sm font-medium px-4 py-1 rounded-full mb-4">
            Roadcall Shops Onboarding
          </span>
          <h1 className="text-3xl font-bold text-white mb-2">Create your shop profile</h1>
          <p className="text-roadcall-muted">Takes about 3 minutes. We&apos;ll handle the rest during setup.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-roadcall-panel/40 rounded-2xl shadow-2xl shadow-black/30 border border-roadcall-cyan/10 p-8 space-y-6">
          {/* Business Info */}
          <div>
            <h2 className="font-semibold text-white text-lg mb-4 pb-2 border-b border-roadcall-cyan/10">Shop information</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Business name <span className="text-roadcall-orange">*</span></label>
                <input
                  type="text" required value={form.business_name}
                  onChange={(e) => set("business_name", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="Big Rig Repair Co."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Owner name <span className="text-roadcall-orange">*</span></label>
                <input
                  type="text" required value={form.owner_name}
                  onChange={(e) => set("owner_name", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="John Smith"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Email <span className="text-roadcall-orange">*</span></label>
                <input
                  type="email" required value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="john@bigrigrepair.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Phone <span className="text-roadcall-orange">*</span></label>
                <input
                  type="tel" required value={form.phone}
                  onChange={(e) => set("phone", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="(813) 555-0100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Website</label>
                <input
                  type="url" value={form.website}
                  onChange={(e) => set("website", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="https://bigrigrepair.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Current phone number to port/forward</label>
                <input
                  type="tel" value={form.current_phone_number}
                  onChange={(e) => set("current_phone_number", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="(813) 555-0199"
                />
              </div>
            </div>
          </div>

          {/* Operations */}
          <div>
            <h2 className="font-semibold text-white text-lg mb-4 pb-2 border-b border-roadcall-cyan/10">Operations</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Service area (city/state or region)</label>
                <input
                  type="text" value={form.service_area}
                  onChange={(e) => set("service_area", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="Tampa, FL — 50 mile radius"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Business hours</label>
                <input
                  type="text" value={form.business_hours}
                  onChange={(e) => set("business_hours", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="Mon–Fri 7am–6pm, Sat 8am–2pm"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-roadcall-silver mb-1">Services offered</label>
                <textarea
                  rows={2} value={form.services_offered}
                  onChange={(e) => set("services_offered", e.target.value)}
                  className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
                  placeholder="Engine repair, brakes, tires, DOT inspections, mobile service..."
                />
              </div>
            </div>
          </div>

          {/* Feature flags */}
          <div>
            <h2 className="font-semibold text-white text-lg mb-4 pb-2 border-b border-roadcall-cyan/10">Features wanted</h2>
            <div className="space-y-3">
              {([
                { field: "wants_ai_answering" as keyof ShopsFormData, label: "AI call answering (answer every call automatically)" },
                { field: "wants_booking" as keyof ShopsFormData, label: "Appointment booking via AI" },
                { field: "wants_reviews" as keyof ShopsFormData, label: "Post-job customer follow-up after completed jobs" },
              ] as { field: keyof ShopsFormData; label: string }[]).map(({ field, label }) => (
                <label key={field} className="flex items-center gap-3 cursor-pointer rounded-lg border border-roadcall-cyan/10 bg-roadcall-ink/35 p-3">
                  <input
                    type="checkbox"
                    checked={form[field] as boolean}
                    onChange={(e) => set(field, e.target.checked)}
                    className="w-4 h-4 text-roadcall-orange border-roadcall-cyan/20 rounded"
                  />
                  <span className="text-sm text-roadcall-silver">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-roadcall-silver mb-1">Anything else we should know?</label>
            <textarea
              rows={3} value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              className="w-full border border-roadcall-cyan/15 bg-roadcall-ink/70 rounded-lg px-3 py-2 text-sm text-white placeholder:text-roadcall-muted/55 focus:outline-none focus:ring-2 focus:ring-roadcall-cyan/60"
              placeholder="Special setup requests, existing software, questions..."
            />
          </div>

          {error && <p className="text-red-200 text-sm bg-red-500/10 border border-red-500/25 rounded-lg p-3">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-roadcall-blue to-roadcall-cyan text-white font-semibold py-3 rounded-lg hover:brightness-110 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><ArrowRight className="w-4 h-4" /> Create Shop Profile</>}
          </button>
          <p className="text-center text-xs text-roadcall-muted">No payment required. A specialist will contact you within 1 business day.</p>
        </form>
      </div>
    </main>
  );
}
