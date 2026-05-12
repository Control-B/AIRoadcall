"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { login } from "@/lib/admin-auth";
import { BrandMark } from "@/components/BrandMark";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const result = await login(username, password);

    if (result.success) {
      router.push("/admin");
    } else {
      setError(result.error || "Login failed");
    }
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-roadcall-void flex items-center justify-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(234,88,12,0.12),transparent_60%)] pointer-events-none" />
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-3">
            <BrandMark width={230} height={92} priority />
          </div>
          <p className="text-roadcall-muted text-sm">Admin Dashboard</p>
        </div>

        {/* Login Card */}
        <div className="bg-roadcall-panel/35 backdrop-blur-sm rounded-2xl border border-roadcall-cyan/10 p-6 shadow-xl">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-roadcall-silver/85 mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                className="w-full px-3 py-2.5 bg-roadcall-panel/45 border border-roadcall-cyan/15 rounded-xl text-white placeholder:text-roadcall-muted/70 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-colors text-sm"
                placeholder="Enter username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-roadcall-silver/85 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2.5 bg-roadcall-panel/45 border border-roadcall-cyan/15 rounded-xl text-white placeholder:text-roadcall-muted/70 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-colors text-sm"
                placeholder="Enter password"
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-gradient-to-r from-roadcall-orange to-roadcall-blue hover:from-roadcall-orange hover:to-roadcall-blue disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-xl font-medium text-sm transition-all shadow-lg shadow-roadcall-orange/20 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-roadcall-muted/55 text-xs mt-6">
          Roadcall.ai by Omniweb, LLC &middot; Admin Access Only
        </p>
      </div>
    </div>
  );
}
