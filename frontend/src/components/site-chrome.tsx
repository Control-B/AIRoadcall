"use client";

import Script from "next/script";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
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

const LEADCONNECTOR_WIDGET_SELECTORS = [
  "script[src*='widgets.leadconnectorhq.com/loader.js']",
  "script[src*='leadconnectorhq.com/chat-widget/loader.js']",
  "script[data-widget-id='6a0d59ed0732dc337617ecf6']",
  "iframe[src*='widgets.leadconnectorhq.com']",
  "iframe[src*='leadconnectorhq.com']",
  "iframe[src*='msgsndr.com']",
  "div[id*='lc_chat']",
  "div[id*='chat-widget']",
  "div[class*='lc-chat']",
  "div[class*='chat-widget']",
  "div[class*='hl-app']",
];

function purgeLeadConnectorWidgetArtifacts() {
  if (typeof document === "undefined") return;
  LEADCONNECTOR_WIDGET_SELECTORS.forEach((selector) => {
    document.querySelectorAll(selector).forEach((element) => element.remove());
  });
}

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
  if (!pathname) return false;
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
  const showWidget = useShowLeadConnectorChatWidget();

  useEffect(() => {
    if (showWidget || typeof document === "undefined") {
      return;
    }

    // Remove immediately, then keep pruning in case the third-party loader
    // re-injects after route changes.
    purgeLeadConnectorWidgetArtifacts();

    const observer = new MutationObserver(() => {
      purgeLeadConnectorWidgetArtifacts();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    const interval = window.setInterval(() => {
      purgeLeadConnectorWidgetArtifacts();
    }, 1200);

    return () => {
      observer.disconnect();
      window.clearInterval(interval);
    };
  }, [showWidget]);

  if (!showWidget) {
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
