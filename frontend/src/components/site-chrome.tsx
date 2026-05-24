"use client";

import Script from "next/script";
import { usePathname } from "next/navigation";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

const CHAT_WIDGET_EXCLUDED_PATHS = [
  "/admin",
  "/go",
  "/locate",
  "/mechanic-offer",
  "/mechanic-track",
  "/search",
  "/support",
  "/template",
];

/**
 * Public website chrome.
 * Admin routes have their own dashboard shell and must not inherit the public
 * navbar/footer because that breaks the database dashboard layout.
 */
function useShowPublicChrome() {
  const pathname = usePathname();
  return !pathname?.startsWith("/admin");
}

function useShowLeadConnectorChatWidget() {
  const pathname = usePathname();
  return !CHAT_WIDGET_EXCLUDED_PATHS.some((path) => pathname === path || pathname?.startsWith(`${path}/`));
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

export function LeadConnectorChatWidget() {
  if (!useShowLeadConnectorChatWidget()) {
    return null;
  }

  return (
    <Script
      src="https://widgets.leadconnectorhq.com/loader.js"
      data-resources-url="https://widgets.leadconnectorhq.com/chat-widget/loader.js"
      data-widget-id="6a0d59ed0732dc337617ecf6"
      data-source="WEB_USER"
      strategy="afterInteractive"
    />
  );
}
