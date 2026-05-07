"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { Phone, Menu, X, ChevronDown, ArrowRight } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { HELP_PHONE, telHref } from "@/lib/phone";

/* ── Navigation structure (Omniweb-style mega-dropdown) ──── */
interface NavSubItem {
  label: string;
  description: string;
  href: string;
}

interface NavItem {
  label: string;
  href: string;
  children?: NavSubItem[];
}

const navItems: NavItem[] = [
  {
    label: "Features",
    href: "/features",
    children: [
      {
        label: "AI Dispatch Agent",
        description: "24/7 AI phone agent that handles every call",
        href: "/features#ai-dispatch",
      },
      {
        label: "SMS Magic Link",
        description: "One-tap location sharing & payment authorization",
        href: "/features#magic-link",
      },
      {
        label: "Smart Mechanic Matching",
        description: "Score & rank 35,000+ mechanics instantly",
        href: "/features#matching",
      },
      {
        label: "Live Tracking",
        description: "Real-time map with ETA updates for every job",
        href: "/features#tracking",
      },
      {
        label: "Admin Dashboard",
        description: "Call logs, analytics, and job management",
        href: "/features#dashboard",
      },
    ],
  },
  {
    label: "Solutions",
    href: "/solutions",
    children: [
      {
        label: "Roadside Assistance",
        description: "AI-powered dispatch for stranded drivers",
        href: "/solutions#roadside",
      },
      {
        label: "Mechanic Shops",
        description: "Never miss another after-hours call",
        href: "/solutions#shops",
      },
      {
        label: "Fleet Management",
        description: "Centralized dispatch for fleet breakdowns",
        href: "/solutions#fleet",
      },
      {
        label: "Heavy Duty & Trucking",
        description: "Specialized support for Class 7-8 vehicles",
        href: "/solutions#heavy-duty",
      },
    ],
  },
  {
    label: "Pricing",
    href: "/pricing",
  },
  {
    label: "Company",
    href: "/company",
    children: [
      {
        label: "About Us",
        description: "Our mission to reinvent roadside rescue",
        href: "/company#about",
      },
      {
        label: "Contact",
        description: "Get in touch with our team",
        href: "/company#contact",
      },
      {
        label: "SMS Consent Policy",
        description: "How SMS opt-in, HELP, STOP, and service texting work",
        href: "/sms-consent",
      },
      {
        label: "Privacy Policy",
        description: "How Roadcall.ai collects, uses, and protects data",
        href: "/privacy",
      },
      {
        label: "Terms of Use",
        description: "Service rules, limitations, disclaimers, and obligations",
        href: "/terms",
      },
    ],
  },
];

/* ── Header component ────────────────────────────────────── */
export function SiteHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMobileMenuOpen(false);
    setOpenDropdown(null);
  }, [pathname]);

  const handleMouseEnter = (label: string) => {
    clearTimeout(timeoutRef.current);
    setOpenDropdown(label);
  };

  const handleMouseLeave = () => {
    timeoutRef.current = setTimeout(() => setOpenDropdown(null), 150);
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#050a14]/90 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/20"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* ── Logo ──────────────────────────────────────── */}
        <Link href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg shadow-orange-500/20 group-hover:shadow-orange-500/40 transition-shadow">
            <Phone className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">
            Roadcall
            <span className="text-orange-400">.ai</span>
          </span>
        </Link>

        {/* ── Desktop nav ───────────────────────────────── */}
        <nav
          className="hidden lg:flex items-center gap-1"
          ref={dropdownRef}
        >
          {navItems.map((item) => (
            <div
              key={item.label}
              className="relative"
              onMouseEnter={() =>
                item.children && handleMouseEnter(item.label)
              }
              onMouseLeave={handleMouseLeave}
            >
              <Link
                href={item.href}
                className={`flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  pathname === item.href
                    ? "text-white bg-white/10"
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                {item.label}
                {item.children && (
                  <ChevronDown
                    className={`h-3.5 w-3.5 transition-transform ${
                      openDropdown === item.label ? "rotate-180" : ""
                    }`}
                  />
                )}
              </Link>

              {/* Mega dropdown */}
              <AnimatePresence>
                {item.children && openDropdown === item.label && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    transition={{ duration: 0.15 }}
                    className="absolute top-full left-0 mt-2 w-80 rounded-2xl border border-white/10 bg-[#0a1020]/95 backdrop-blur-xl shadow-2xl shadow-black/40 p-2 overflow-hidden"
                    onMouseEnter={() => handleMouseEnter(item.label)}
                    onMouseLeave={handleMouseLeave}
                  >
                    {item.children.map((child) => (
                      <Link
                        key={child.label}
                        href={child.href}
                        className="flex flex-col gap-0.5 px-4 py-3 rounded-xl hover:bg-white/[0.06] transition-colors group/item"
                      >
                        <span className="text-sm font-medium text-white group-hover/item:text-orange-300 transition-colors">
                          {child.label}
                        </span>
                        <span className="text-xs text-slate-500">
                          {child.description}
                        </span>
                      </Link>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </nav>

        {/* ── Desktop CTA ───────────────────────────────── */}
        <div className="hidden lg:flex items-center gap-3 shrink-0">
          <a href={telHref(HELP_PHONE)}>
            <Button
              size="sm"
              className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white rounded-full px-5 shadow-lg shadow-orange-600/20"
            >
              <Phone className="h-3.5 w-3.5 mr-1.5" />
              Call for Help
            </Button>
          </a>
        </div>

        {/* ── Mobile hamburger ──────────────────────────── */}
        <button
          className="lg:hidden p-2 text-slate-300 hover:text-white transition-colors"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <Menu className="h-6 w-6" />
          )}
        </button>
      </div>

      {/* ── Mobile menu ─────────────────────────────────── */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="lg:hidden overflow-hidden bg-[#0a1020] border-t border-white/10"
          >
            <div className="px-4 py-4 space-y-1 max-h-[80vh] overflow-y-auto">
              {navItems.map((item) => (
                <div key={item.label}>
                  <Link
                    href={item.href}
                    className={`flex items-center justify-between px-4 py-3 text-sm font-medium rounded-lg ${
                      pathname === item.href
                        ? "text-white bg-white/10"
                        : "text-slate-300 hover:text-white hover:bg-white/5"
                    }`}
                  >
                    {item.label}
                    {item.children && (
                      <ArrowRight className="h-4 w-4 text-slate-500" />
                    )}
                  </Link>
                  {item.children && (
                    <div className="pl-4 space-y-0.5 mt-1 mb-2">
                      {item.children.map((child) => (
                        <Link
                          key={child.label}
                          href={child.href}
                          className="block px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-lg"
                        >
                          {child.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              <div className="pt-3 border-t border-white/10 space-y-2">
                <a href={telHref(HELP_PHONE)}>
                  <Button className="w-full bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 shadow-lg">
                    <Phone className="h-4 w-4 mr-2" />
                    Call for Help: {HELP_PHONE}
                  </Button>
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
