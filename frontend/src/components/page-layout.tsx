"use client";

export function PageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="roadcall-page min-h-screen text-roadcall-silver relative overflow-hidden">
      {/* ── Background effects (Omniweb-style) ─────── */}
      <div className="pointer-events-none fixed inset-0 z-0">
        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
        {/* Radial glow top */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[120vw] h-[60vh] bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(20,216,255,0.16),transparent_60%)]" />
        {/* Radial glow right */}
        <div className="absolute top-1/3 right-0 w-[60vw] h-[60vh] bg-[radial-gradient(ellipse_50%_50%_at_80%_50%,rgba(255,138,0,0.10),transparent_50%)]" />
      </div>

      {/* ── Content ────────────────────────────────── */}
      <main className="relative z-10">{children}</main>
    </div>
  );
}
