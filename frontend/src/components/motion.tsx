"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

interface FadeInProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "down" | "left" | "right";
  once?: boolean;
}

export function FadeIn({
  children,
  className,
  delay = 0,
  direction = "up",
  once = true,
}: FadeInProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once, margin: "-80px" });

  const directionMap = {
    up: { y: 30, x: 0 },
    down: { y: -30, x: 0 },
    left: { x: 30, y: 0 },
    right: { x: -30, y: 0 },
  };

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, ...directionMap[direction] }}
      animate={isInView ? { opacity: 1, x: 0, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: [0.21, 0.47, 0.32, 0.98] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ── Section Heading ─────────────────────────────────────── */
interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  description?: string;
  eyebrowColor?: string;
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  eyebrowColor = "text-roadcall-cyan",
}: SectionHeadingProps) {
  return (
    <FadeIn className="text-center mb-16 md:mb-20">
      {eyebrow && (
        <p
          className={`text-sm font-semibold uppercase tracking-[0.25em] ${eyebrowColor} mb-4`}
        >
          {eyebrow}
        </p>
      )}
      <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-5">
        {title}
      </h2>
      {description && (
        <p className="text-lg text-roadcall-muted max-w-2xl mx-auto leading-relaxed">
          {description}
        </p>
      )}
    </FadeIn>
  );
}

/* ── Glass Card ──────────────────────────────────────────── */
interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export function GlassCard({
  children,
  className = "",
  hover = false,
}: GlassCardProps) {
  return (
    <div
      className={`rounded-2xl border border-roadcall-cyan/10 bg-roadcall-panel/35 backdrop-blur-sm ${
        hover
          ? "transition-all hover:border-roadcall-cyan/30 hover:bg-roadcall-cyan/[0.04]"
          : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}
