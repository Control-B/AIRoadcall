"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

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
        const res = await fetch(`${API_URL}/jobs/by-code/${encodeURIComponent(code)}`);
        if (!res.ok) {
          if (res.status === 404) {
            setError("We couldn't find a case with that code. Please double-check and try again.");
          } else {
            setError("Something went wrong. Please try again in a moment.");
          }
          setLoading(false);
          return;
        }
        const data = await res.json();
        // Redirect to the full support page with the magic link token
        router.replace(`/support/${data.magic_link_token}`);
      } catch {
        setError("Unable to connect. Please check your internet and try again.");
        setLoading(false);
      }
    }

    lookupCode();
  }, [code, router]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
        <div className="mb-6">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Roadside Assist</h1>
          {loading && !error ? (
            <>
              <p className="text-gray-600 mb-4">Looking up case <span className="font-mono font-bold">{code}</span>…</p>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            </>
          ) : error ? (
            <>
              <p className="text-red-600 mb-4">{error}</p>
              <p className="text-sm text-gray-500">
                Your code should look like <span className="font-mono">RC-XXXXXXXX</span>
              </p>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
