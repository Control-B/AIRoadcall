import Link from "next/link";
import { Phone, Mail, MapPin } from "lucide-react";
import { COMPANY_PHONE, HELP_PHONE, telHref } from "@/lib/phone";
import { BrandMark } from "@/components/BrandMark";

const footerLinks = {
  "Find Service": [
    { label: "Search Providers", href: "/search" },
    { label: "Driver Help", href: "/driver" },
    { label: "AI Marketplace", href: "/marketplace" },
    { label: "All 50 States", href: "/search" },
  ],
  Providers: [
    { label: "List Your Shop", href: "/provider" },
    { label: "Get Verified", href: "/provider#verified" },
    { label: "AI Phone (Shops)", href: "/shops" },
    { label: "Fleet Solutions", href: "/fleet" },
  ],
  Platform: [
    { label: "Features", href: "/features" },
    { label: "Pricing", href: "/pricing" },
    { label: "Solutions", href: "/solutions" },
    { label: "Dashboard", href: "/admin/login" },
  ],
  Company: [
    { label: "About", href: "/company#about" },
    { label: "Contact", href: "/company#contact" },
    { label: "SMS Consent Policy", href: "/sms-consent" },
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
  ],
};

export function SiteFooter() {
  return (
    <footer className="border-t border-roadcall-cyan/10 bg-[linear-gradient(180deg,rgba(3,12,30,0.96),rgba(2,7,21,0.98))]">
      {/* ── Main footer ─────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12">
          {/* Brand column */}
          <div className="lg:col-span-2">
            <Link href="/" className="mb-5 inline-block">
              <BrandMark width={250} height={82} />
            </Link>
            <p className="text-sm text-roadcall-muted max-w-sm leading-relaxed mb-6">
              AI-powered roadside dispatch and mechanic shop phone system.
              Built by Omniweb, LLC — AI voice agents, chat assistants, and
              workflow automation for service businesses.
            </p>
            <div className="space-y-3">
              <a
                href={telHref(COMPANY_PHONE)}
                className="flex items-center gap-2 text-sm text-roadcall-muted hover:text-roadcall-cyan transition-colors"
              >
                <Phone className="h-4 w-4" />
                Company: {COMPANY_PHONE}
              </a>
              <a
                href={telHref(HELP_PHONE)}
                className="flex items-center gap-2 text-sm text-roadcall-muted hover:text-roadcall-cyan transition-colors"
              >
                <Phone className="h-4 w-4" />
                Help: {HELP_PHONE}
              </a>
              <a
                href="mailto:support@roadcall.ai"
                className="flex items-center gap-2 text-sm text-roadcall-muted hover:text-roadcall-cyan transition-colors"
              >
                <Mail className="h-4 w-4" />
                support@roadcall.ai
              </a>
              <div className="flex items-center gap-2 text-sm text-roadcall-muted">
                <MapPin className="h-4 w-4" />
                All 50 US States
              </div>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h4 className="text-xs font-semibold uppercase tracking-widest text-roadcall-cyan/70 mb-4">
                {title}
              </h4>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-roadcall-muted hover:text-white transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* ── Bottom bar ──────────────────────────────── */}
      <div className="border-t border-roadcall-cyan/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-roadcall-muted/80">
            © {new Date().getFullYear()} Omniweb, LLC. All rights reserved.
          </p>
          <p className="text-sm text-roadcall-muted/70">
            Roadcall.ai is a product of Omniweb, LLC
          </p>
        </div>
      </div>
    </footer>
  );
}
