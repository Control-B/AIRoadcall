import Link from "next/link";
import { Phone, Mail, MapPin } from "lucide-react";
import { COMPANY_PHONE, HELP_PHONE, telHref } from "@/lib/phone";

const footerLinks = {
  Product: [
    { label: "Features", href: "/features" },
    { label: "Solutions", href: "/solutions" },
    { label: "Pricing", href: "/pricing" },
    { label: "Dashboard", href: "/admin/login" },
  ],
  Solutions: [
    { label: "Roadside Assistance", href: "/solutions#roadside" },
    { label: "Mechanic Shops", href: "/solutions#shops" },
    { label: "Fleet Management", href: "/solutions#fleet" },
    { label: "Heavy Duty", href: "/solutions#heavy-duty" },
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
    <footer className="border-t border-white/[0.06] bg-[#030710]">
      {/* ── Main footer ─────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12">
          {/* Brand column */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-5">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center">
                <Phone className="h-4 w-4 text-white" />
              </div>
              <span className="text-lg font-bold tracking-tight text-white">
                Roadcall<span className="text-orange-400">.ai</span>
              </span>
            </Link>
            <p className="text-sm text-slate-500 max-w-sm leading-relaxed mb-6">
              AI-powered roadside dispatch and mechanic shop phone system.
              Built by Omniweb, LLC — AI voice agents, chat assistants, and
              workflow automation for service businesses.
            </p>
            <div className="space-y-3">
              <a
                href={telHref(COMPANY_PHONE)}
                className="flex items-center gap-2 text-sm text-slate-400 hover:text-orange-400 transition-colors"
              >
                <Phone className="h-4 w-4" />
                Company: {COMPANY_PHONE}
              </a>
              <a
                href={telHref(HELP_PHONE)}
                className="flex items-center gap-2 text-sm text-slate-400 hover:text-orange-400 transition-colors"
              >
                <Phone className="h-4 w-4" />
                Help: {HELP_PHONE}
              </a>
              <a
                href="mailto:support@roadcall.ai"
                className="flex items-center gap-2 text-sm text-slate-400 hover:text-orange-400 transition-colors"
              >
                <Mail className="h-4 w-4" />
                support@roadcall.ai
              </a>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <MapPin className="h-4 w-4" />
                All 50 US States
              </div>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">
                {title}
              </h4>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-slate-400 hover:text-white transition-colors"
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
      <div className="border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-slate-500">
            © {new Date().getFullYear()} Omniweb, LLC. All rights reserved.
          </p>
          <p className="text-sm text-slate-600">
            Roadcall.ai is a product of Omniweb, LLC
          </p>
        </div>
      </div>
    </footer>
  );
}
