"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { getJobByCode } from "@/lib/api-client";

export default function GoCodePage() {
  const params = useParams();
  const router = useRouter();
  const code = (params.code as string)?.toUpperCase();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) return;

    async function lookupCode() {
      try {
        const data = await getJobByCode(code);
        // Redirect to the full support page with the magic link token
        router.replace(`/support/${data.magic_link_token}`);
      } catch (err: any) {
        const message = err?.message || "Unable to connect. Please check your internet and try again.";
        if (message.toLowerCase().includes("not found")) {
          setError("We couldn't find a case with that code. Please double-check and try again.");
        } else {
          setError(message);
        }
        setLoading(false);
      }
    }

    lookupCode();
  }, [code, router]);

  return (
    <div className="roadcall-page min-h-screen flex items-center justify-center p-4 text-roadcall-silver">
      <div className="roadcall-surface max-w-md w-full rounded-2xl p-8 text-center">
        <div className="mb-6">
          <div className="w-16 h-16 bg-roadcall-cyan/15 rounded-full flex items-center justify-center mx-auto mb-4 ring-1 ring-roadcall-cyan/25">
            <svg className="w-8 h-8 text-roadcall-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Roadside Assist</h1>
          {loading && !error ? (
            <>
              <p className="text-roadcall-muted mb-4">Looking up case <span className="font-mono font-bold text-white">{code}</span>...</p>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-roadcall-cyan mx-auto"></div>
            </>
          ) : error ? (
            <>
              <p className="text-red-200 mb-4">{error}</p>
              <p className="text-sm text-roadcall-muted">
                Your code should look like <span className="font-mono">RC-XXXXXXXX</span>
              </p>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
