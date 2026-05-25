"use client";

import Link from "next/link";

export default function AgentsLink({ className = "" }: { className?: string }) {
  return (
    <div className={`text-center ${className}`}>
      <Link
        href="/agents/dashboard"
        className="inline-flex min-h-14 w-full max-w-md items-center justify-center rounded-2xl bg-blue-600 px-6 py-4 text-center text-lg font-black text-white shadow-2xl shadow-blue-600/20 transition hover:bg-blue-700 sm:text-xl"
      >
        Go to Agent Configuration
      </Link>
    </div>
  );
}
