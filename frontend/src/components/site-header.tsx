"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { Menu, X, ArrowRight, Phone } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { HELP_PHONE, telHref } from "@/lib/phone";
import { BrandMark } from "@/components/BrandMark";
import { GHL_SIGN_IN_URL } from "@/lib/ghl-links";

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
      label: "Template",
      href: "https://preview-1779364005181565636.vibepreview.com",
    },
  {
    label: "AI Services",
    href: "/solutions",
    children: [
      {
        label: "AI Roadside Support",
        description: "Driver-side agent for breakdown intake and help routing",
        href: "/driver",
      },
      {
        label: "AI Telephony for Mechanics",
        description: "Attach a shop number and configure an AI service advisor",
        href: "/ai-telephony",
      },
      {
        label: "AI Fleet Roadside",
        description: "AI roadside department connected to fleet assets and vendors",
        href: "/fleet",
      },
      {
        label: "General Search Directory",
        description: "Search Truck Service public directory for providers",
        href: "/search",
      },
      {
        label: "Security & Data",
        description: "Private tenant isolation, RBAC, and audit logs",
        href: "/fleet/security",
      },
    ],
  },
  {
    label: "Directory",
    href: "/search",
    children: [
      {
        label: "Search Truck Service",
        description: "Browse 35,000+ mechanics, tow trucks & repair shops",
        href: "/search",
      },
      {
        label: "AI Marketplace",
        description: "AI-ranked providers matched to your exact problem",
        href: "/marketplace",
      },
      {
        label: "Trucking Companies",
        description: "Limited public trucking company directory",
        href: "/directories/trucking-companies",
      },
      {
        label: "National Vendors",
        description: "Limited public national service provider directory",
        href: "/directories/national-vendors",
      },
      {
        label: "List Your Shop",
        description: "Add or claim your mechanic profile — free",
        href: "/provider",
      },
      {
        label: "Get Verified & Dispatched",
        description: "Receive AI-routed leads and grow your revenue",
        href: "/provider#verified",
      },
    ],
  },
  {
    label: "Resources",
    href: "/privacy",
    children: [
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
      {
        label: "SMS Consent Policy",
        description: "How SMS opt-in, HELP, STOP, and service texting work",
        href: "/sms-consent",
      },
      {
        label: "Contact",
        description: "Get in touch with our team",
        href: "/company#contact",
      },
      {
        label: "About Us",
        description: "Our mission to reinvent roadside rescue",
        href: "/company#about",
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
        label: "Roadcall Shops (AI Phone)",
        description: "AI call answering, CRM, and booking for your shop",
        href: "/shops",
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
  const getStartedHref = "/get-started";
  const signInHref = GHL_SIGN_IN_URL ? "/sign-in" : "/admin/login";

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
          ? "bg-roadcall-void/90 backdrop-blur-xl border-b border-roadcall-cyan/15 shadow-lg shadow-blue-950/30"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-20 flex items-center justify-between">
        {/* ── Logo ──────────────────────────────────────── */}
        <Link href="/" aria-label="Roadcall.ai home" className="shrink-0 group flex items-center">
          <BrandMark width={220} height={72} priority className="flex items-center transition-opacity group-hover:opacity-90" />
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
                    ? "text-white bg-roadcall-blue/15 border border-roadcall-cyan/20"
                    : "text-roadcall-muted hover:text-white hover:bg-roadcall-cyan/10"
                }`}
              >
                {item.label}
              </Link>

              {/* Mega dropdown */}
              <AnimatePresence>
                {item.children && openDropdown === item.label && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    transition={{ duration: 0.15 }}
                    className="absolute top-full left-0 mt-2 w-80 rounded-2xl border border-roadcall-cyan/15 bg-roadcall-panel/95 backdrop-blur-xl shadow-2xl shadow-black/40 p-2 overflow-hidden"
                    onMouseEnter={() => handleMouseEnter(item.label)}
                    onMouseLeave={handleMouseLeave}
                  >
                    {item.children.map((child) => (
                      <Link
                        key={child.label}
                        href={child.href}
                        className="flex flex-col gap-0.5 px-4 py-3 rounded-xl hover:bg-roadcall-cyan/[0.08] transition-colors group/item"
                      >
                        <span className="text-sm font-medium text-white group-hover/item:text-roadcall-cyan transition-colors">
                          {child.label}
                        </span>
                        <span className="text-xs text-roadcall-muted">
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

        {/* ── Desktop CTA cluster ───────────────────────── */}
        <div className="hidden lg:flex items-center gap-1.5 shrink-0 -mr-6 xl:-mr-12 2xl:-mr-20">
          <Link
            href={signInHref}
            className="inline-flex h-8 items-center rounded-full border border-white/10 bg-roadcall-panel/30 px-3 text-xs font-semibold text-roadcall-muted hover:border-roadcall-cyan/35 hover:text-white transition-colors"
          >
            Sign In
          </Link>
          <Link
            href={getStartedHref}
            className="inline-flex h-8 items-center gap-1 rounded-full bg-gradient-to-r from-roadcall-blue to-roadcall-cyan px-3 text-xs font-bold text-white shadow-lg shadow-cyan-950/30 hover:brightness-110 transition-all"
          >
            Get Started <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <a
            href={telHref(HELP_PHONE)}
            className="inline-flex h-8 items-center gap-1.5 rounded-full border border-roadcall-cyan/25 bg-roadcall-panel/40 px-2.5 text-xs font-semibold text-roadcall-silver hover:border-roadcall-cyan/50 hover:text-white transition-colors"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full border border-roadcall-cyan/25 bg-roadcall-void/60">
              <Phone className="h-3 w-3 text-white" />
            </span>
            <span className="hidden xl:inline">Call</span>
            <span className="text-white">{HELP_PHONE}</span>
          </a>
        </div>

        {/* ── Mobile hamburger ──────────────────────────── */}
        <button
          className="lg:hidden p-2 text-roadcall-muted hover:text-white transition-colors"
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
            className="lg:hidden overflow-hidden bg-roadcall-panel/98 border-t border-roadcall-cyan/15"
          >
            <div className="px-4 py-4 space-y-1 max-h-[80vh] overflow-y-auto">
              {navItems.map((item) => (
                <div key={item.label}>
                  <Link
                    href={item.href}
                    className={`flex items-center justify-between px-4 py-3 text-sm font-medium rounded-lg ${
                      pathname === item.href
                        ? "text-white bg-roadcall-blue/15"
                        : "text-roadcall-muted hover:text-white hover:bg-roadcall-cyan/10"
                    }`}
                  >
                    {item.label}
                    {item.children && (
                      <ArrowRight className="h-4 w-4 text-roadcall-muted" />
                    )}
                  </Link>
                  {item.children && (
                    <div className="pl-4 space-y-0.5 mt-1 mb-2">
                      {item.children.map((child) => (
                        <Link
                          key={child.label}
                          href={child.href}
                          className="block px-4 py-2 text-sm text-roadcall-muted hover:text-white hover:bg-roadcall-cyan/10 rounded-lg"
                        >
                          {child.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              <div className="pt-3 border-t border-roadcall-cyan/15 space-y-2">
                <Link href={getStartedHref}>
                  <Button className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 w-full">
                    Get Started
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </Link>
                <Link href={signInHref}>
                  <Button variant="outline" className="border-roadcall-cyan/25 bg-roadcall-panel/40 text-roadcall-silver hover:bg-roadcall-cyan/10 w-full">
                    Sign In
                  </Button>
                </Link>
                <a href={telHref(HELP_PHONE)}>
                  <Button className="bg-gradient-to-r from-roadcall-blue to-roadcall-cyan hover:brightness-110 w-full">
                    <Phone className="h-4 w-4 mr-2" />
                    Call {HELP_PHONE}
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
