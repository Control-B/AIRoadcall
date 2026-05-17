"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ArrowRight, CalendarClock, Phone } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { GHL_GET_STARTED_URL, isExternalUrl } from "@/lib/ghl-links";
import { HELP_PHONE, telHref } from "@/lib/phone";

export default function GetStartedPage() {
  const external = isExternalUrl(GHL_GET_STARTED_URL);

  useEffect(() => {
    if (external) {
      window.location.replace(GHL_GET_STARTED_URL);
    }
  }, [external]);

  return (
    <PageLayout>
      <section className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-cyan/25 bg-roadcall-cyan/10 px-4 py-1.5 mb-6">
          <CalendarClock className="h-4 w-4 text-roadcall-cyan" />
          <span className="text-sm font-medium text-cyan-100">Get Started</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-black text-white mb-4">Start with Roadcall</h1>
        <p className="text-roadcall-muted max-w-xl mb-10 leading-relaxed">
          {external
            ? "Redirecting you to Roadcall onboarding…"
            : "Choose the best starting point for your team. We will route signups through Roadcall onboarding once your link is configured."}
        </p>
        {external ? (
          <div className="text-sm text-roadcall-muted">Redirecting…</div>
        ) : (
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href={GHL_GET_STARTED_URL}>
              <Button className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold rounded-xl px-7">
                Continue <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
            <a href={telHref(HELP_PHONE)}>
              <Button variant="outline" className="border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl px-7">
                <Phone className="h-4 w-4 mr-2" /> Call {HELP_PHONE}
              </Button>
            </a>
          </div>
        )}
      </section>
    </PageLayout>
  );
}
