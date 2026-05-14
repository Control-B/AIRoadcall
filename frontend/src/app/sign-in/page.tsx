"use client";

import { useEffect } from "react";
import Link from "next/link";
import { LogIn, Wrench, Shield } from "lucide-react";
import { PageLayout } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { GHL_SIGN_IN_URL, isExternalUrl } from "@/lib/ghl-links";

export default function SignInPage() {
  const hasGhlSignIn = Boolean(GHL_SIGN_IN_URL);
  const external = hasGhlSignIn && isExternalUrl(GHL_SIGN_IN_URL);

  useEffect(() => {
    if (external) {
      window.location.replace(GHL_SIGN_IN_URL);
    }
  }, [external]);

  return (
    <PageLayout>
      <section className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-roadcall-orange/25 bg-roadcall-orange/10 px-4 py-1.5 mb-6">
          <LogIn className="h-4 w-4 text-roadcall-orange" />
          <span className="text-sm font-medium text-orange-100">Sign In</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-black text-white mb-4">Sign in to Roadcall</h1>
        <p className="text-roadcall-muted max-w-xl mb-10 leading-relaxed">
          {external
            ? "Redirecting you to the Roadcall customer portal…"
            : "Customer and provider sign-in will route through GHL once the portal link is configured. Internal Roadcall admins can use the admin dashboard."}
        </p>
        {external ? (
          <div className="text-sm text-roadcall-muted">Redirecting…</div>
        ) : (
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            {hasGhlSignIn ? (
              <Link href={GHL_SIGN_IN_URL}>
                <Button className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold rounded-xl px-7">
                  <Wrench className="h-4 w-4 mr-2" /> Continue to Portal
                </Button>
              </Link>
            ) : (
              <Link href="/get-started">
                <Button className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 text-white font-bold rounded-xl px-7">
                  <Wrench className="h-4 w-4 mr-2" /> Get Started
                </Button>
              </Link>
            )}
            <Link href="/admin/login">
              <Button variant="outline" className="border-slate-600 text-roadcall-silver/85 hover:bg-roadcall-panel rounded-xl px-7">
                <Shield className="h-4 w-4 mr-2" /> Admin Login
              </Button>
            </Link>
          </div>
        )}
      </section>
    </PageLayout>
  );
}
