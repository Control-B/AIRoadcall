"use client";

import Script from "next/script";
import { Wrench, Zap } from "lucide-react";
import { PageLayout } from "@/components/page-layout";

export default function ProviderRegisterPage() {
  return (
    <PageLayout>
      <section className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center">
        <Script
          src="https://widgets.leadconnectorhq.com/loader.js"
          data-resources-url="https://widgets.leadconnectorhq.com/chat-widget/loader.js"
          data-widget-id="6a0d59ed0732dc337617ecf6"
          data-source="WEB_USER"
          strategy="afterInteractive"
        />
        <div className="inline-flex items-center gap-2 bg-emerald-500/15 border border-emerald-500/25 rounded-full px-4 py-1.5 mb-6">
          <Wrench className="h-4 w-4 text-emerald-400" />
          <span className="text-sm font-medium text-emerald-200">Provider Registration</span>
        </div>
        <h1 className="text-4xl font-black text-white mb-4">List Your Shop</h1>
        <p className="text-roadcall-muted max-w-md mb-10 leading-relaxed">
          Complete your provider registration here and we&apos;ll set up your shop profile.
        </p>
        <div className="flex items-center gap-2 text-roadcall-muted text-sm">
          <Zap className="h-4 w-4 animate-pulse text-emerald-400" /> Registration widget loading...
        </div>
      </section>
    </PageLayout>
  );
}
