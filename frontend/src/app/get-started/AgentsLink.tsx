"use client";

import Link from "next/link";

export default function AgentsLink() {
  return (
    <div className="mt-8 text-center">
      <Link href="/agents/dashboard" className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition">
        Go to Agent Dashboard
      </Link>
    </div>
  );
}
