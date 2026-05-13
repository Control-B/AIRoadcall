"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global error boundary caught:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-roadcall-void text-roadcall-silver">
        <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center justify-center px-6 text-center">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-roadcall-cyan">
            Roadcall Platform
          </p>
          <h1 className="mb-3 text-3xl font-bold text-white sm:text-4xl">Temporary client error</h1>
          <p className="mb-8 max-w-xl text-sm text-roadcall-muted sm:text-base">
            This page crashed unexpectedly. Please retry, or return home while we keep systems running.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={reset}
              className="rounded-xl bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-6 py-3 text-sm font-semibold text-white hover:brightness-110"
            >
              Retry page
            </button>
            <Link
              href="/"
              className="rounded-xl border border-roadcall-cyan/30 bg-roadcall-panel/40 px-6 py-3 text-sm font-semibold text-roadcall-silver hover:bg-roadcall-panel/70"
            >
              Return home
            </Link>
          </div>
        </main>
      </body>
    </html>
  );
}
