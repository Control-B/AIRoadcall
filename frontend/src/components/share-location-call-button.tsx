"use client";

import { Phone } from "lucide-react";

import { HELP_PHONE, telHref } from "@/lib/phone";

export function ShareLocationCallButton({ className = "" }: { className?: string }) {
  return (
    <a
      href={telHref(HELP_PHONE)}
      aria-label={`Call Sandy at ${HELP_PHONE}`}
      className={`fixed bottom-6 left-1/2 z-[90] flex h-12 w-12 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-slate-950 shadow-2xl ring-2 ring-emerald-400/30 transition hover:scale-105 active:scale-95 sm:h-14 sm:w-14 ${className}`}
    >
      <Phone className="h-5 w-5 sm:h-6 sm:w-6" fill="currentColor" />
    </a>
  );
}
