"use client";

import { useEffect } from "react";
import { Wrench, Zap } from "lucide-react";
import { PageLayout } from "@/components/page-layout";

// When GHL is configured, set this env var to your GHL embed/calendar/form URL
const GHL_FORM_URL = process.env.NEXT_PUBLIC_GHL_PROVIDER_SIGNUP;

export default function ProviderRegisterPage() {
  useEffect(() => {
    if (GHL_FORM_URL && GHL_FORM_URL.startsWith("http")) {
      window.location.replace(GHL_FORM_URL);
    }
  }, []);

  return (
    <PageLayout>
      <section className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center">
        <div className="inline-flex items-center gap-2 bg-emerald-500/15 border border-emerald-500/25 rounded-full px-4 py-1.5 mb-6">
          <Wrench className="h-4 w-4 text-emerald-400" />
          <span className="text-sm font-medium text-emerald-200">Provider Registration</span>
        </div>
        <h1 className="text-4xl font-black text-white mb-4">List Your Shop</h1>
        <p className="text-roadcall-muted max-w-md mb-10 leading-relaxed">
          {GHL_FORM_URL
            ? "Redirecting you to our provider registration portal…"
            : "Provider registration is coming soon. In the meantime, call us and we'll set up your profile manually."}
        </p>
        {GHL_FORM_URL ? (
          <div className="flex items-center gap-2 text-roadcall-muted text-sm">
            <Zap className="h-4 w-4 animate-pulse text-emerald-400" /> Redirecting…
          </div>
        ) : (
          <a
            href="tel:+18668183060"
            className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-bold px-8 py-4 rounded-2xl transition-all text-sm"
          >
            Call to Get Listed
          </a>
        )}
      </section>
    </PageLayout>
  );
}
