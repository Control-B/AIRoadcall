"use client";

/**
 * Lightweight CSS / SVG rotating "dotted globe" background.
 * No Three.js dependency — uses radial gradients + an SVG dot grid
 * masked to a sphere and slowly rotated. Visually similar to the
 * Omniweb dotted globe but a fraction of the bundle cost.
 */
export function RotatingGlobeBackground({ className = "" }: { className?: string }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      {/* Deep space background */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,#06122a_0%,#020715_70%,#01030a_100%)]" />

      {/* Star field */}
      <div
        className="absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            "radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.7) 50%, transparent 51%)," +
            "radial-gradient(1px 1px at 70% 80%, rgba(255,255,255,0.5) 50%, transparent 51%)," +
            "radial-gradient(1.5px 1.5px at 40% 60%, rgba(180,210,255,0.55) 50%, transparent 51%)," +
            "radial-gradient(1px 1px at 85% 25%, rgba(255,255,255,0.6) 50%, transparent 51%)," +
            "radial-gradient(1px 1px at 15% 85%, rgba(255,255,255,0.5) 50%, transparent 51%)," +
            "radial-gradient(1.5px 1.5px at 60% 15%, rgba(200,220,255,0.5) 50%, transparent 51%)," +
            "radial-gradient(1px 1px at 92% 65%, rgba(255,255,255,0.6) 50%, transparent 51%)",
          backgroundSize: "100% 100%",
        }}
      />

      {/* Globe — perfectly centered */}
      <div className="absolute left-1/2 top-1/2 h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 sm:h-[40rem] sm:w-[40rem] lg:h-[46rem] lg:w-[46rem]">
        {/* Outer atmospheric glow */}
        <div className="absolute inset-[-12%] rounded-full bg-[radial-gradient(circle,rgba(96,165,250,0.18),rgba(34,211,238,0.10)_45%,transparent_70%)] blur-2xl" />

        {/* Sphere shadow / dark side */}
        <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_30%_30%,#0b1a36_0%,#050b1c_55%,#01030a_100%)] shadow-[inset_-40px_-40px_120px_rgba(0,0,0,0.7),inset_40px_40px_120px_rgba(34,211,238,0.05)]" />

        {/* Rotating dotted layer (in front) */}
        <div className="absolute inset-0 animate-spin-slow rounded-full overflow-hidden [mask-image:radial-gradient(circle,black_60%,transparent_75%)]">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "radial-gradient(rgba(147,197,253,0.55) 1px, transparent 1.4px)",
              backgroundSize: "16px 16px",
            }}
          />
        </div>

        {/* Counter-rotating slower dotted layer (depth) */}
        <div className="absolute inset-0 animate-spin-slower rounded-full overflow-hidden opacity-50 [mask-image:radial-gradient(circle,black_55%,transparent_70%)]">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "radial-gradient(rgba(34,211,238,0.45) 1px, transparent 1.4px)",
              backgroundSize: "22px 22px",
              transform: "rotate(35deg)",
            }}
          />
        </div>

        {/* Specular highlight */}
        <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_28%_25%,rgba(191,219,254,0.18),transparent_45%)]" />

        {/* Orbital ring */}
        <div className="absolute inset-[-8%] rounded-full border border-cyan-300/15 [transform:rotateX(70deg)]" />
        <div className="absolute inset-[-14%] rounded-full border border-dashed border-cyan-300/10 [transform:rotateX(70deg)]" />
      </div>

      {/* Vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,transparent_30%,rgba(2,7,21,0.5)_80%,rgba(2,7,21,0.85)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(34,211,238,0.10),transparent_22%),radial-gradient(circle_at_70%_30%,rgba(139,92,246,0.10),transparent_24%),radial-gradient(circle_at_35%_72%,rgba(255,138,0,0.08),transparent_22%)]" />
    </div>
  );
}
