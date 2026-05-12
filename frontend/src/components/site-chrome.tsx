"use client";

import { usePathname } from "next/navigation";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

/**
 * Public website chrome.
 * Admin routes have their own dashboard shell and must not inherit the public
 * navbar/footer because that breaks the database dashboard layout.
 */
function useShowPublicChrome() {
  const pathname = usePathname();
  return !pathname?.startsWith("/admin");
}

export function SiteHeaderChrome() {
  if (!useShowPublicChrome()) {
    return null;
  }

  return <SiteHeader />;
}

export function SiteFooterChrome() {
  if (!useShowPublicChrome()) {
    return null;
  }

  return <SiteFooter />;
}
