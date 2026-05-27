"use client";

import Link from "next/link";

export default function AgentsLink({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 text-center sm:flex-row ${className}`}>
      <Link
        href="/agents/dashboard"
        className="inline-flex min-h-14 w-full max-w-md items-center justify-center rounded-2xl bg-blue-600 px-6 py-4 text-center text-lg font-black text-white shadow-2xl shadow-blue-600/20 transition hover:bg-blue-700 sm:w-auto sm:min-w-[360px] sm:text-xl"
      >
        Go to Agent Configuration
      </Link>
      <Link
        href="/mechanic/dashboard?trial=3days"
        className="inline-flex min-h-14 w-full max-w-md items-center justify-center rounded-2xl border border-roadcall-orange/60 bg-roadcall-orange/15 px-6 py-4 text-center text-lg font-black text-orange-100 shadow-2xl shadow-roadcall-orange/10 transition hover:bg-roadcall-orange/25 sm:w-auto sm:min-w-[360px] sm:text-xl"
      >
        Request A Three Days Free Trial
      </Link>
    </div>
  );
}
