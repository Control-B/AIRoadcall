import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import CookieConsent from "@/components/CookieConsent";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Roadcall.ai — AI-Powered Roadside Dispatch",
    template: "%s | Roadcall.ai",
  },
  icons: {
    icon: [
      { url: "/favicon.ico?v=4", type: "image/x-icon" },
      { url: "/favicon-32x32.png?v=4", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png?v=4", sizes: "16x16", type: "image/png" },
    ],
    shortcut: "/favicon.ico?v=4",
    apple: "/apple-touch-icon.png?v=4",
  },
  description:
    "AI dispatcher that picks up every call, finds the closest mechanic, and gets help on the way in under 90 seconds. 35,000+ mechanics across all 50 states.",
  keywords: [
    "roadside assistance",
    "AI dispatch",
    "mechanic finder",
    "roadside help",
    "tow truck",
    "flat tire",
    "breakdown",
    "heavy duty",
  ],
  openGraph: {
    title: "Roadcall.ai — AI-Powered Roadside Dispatch",
    description:
      "Call our AI dispatcher. Share your location with one tap. We find the closest, best-rated mechanic and send them straight to you.",
    siteName: "Roadcall.ai",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Roadcall.ai — AI-Powered Roadside Dispatch",
    description:
      "AI dispatcher that picks up every call, finds the closest mechanic, and gets help on the way in under 90 seconds.",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico?v=4" sizes="any" />
        <link rel="icon" href="/favicon-32x32.png?v=4" type="image/png" sizes="32x32" />
        <link rel="icon" href="/favicon-16x16.png?v=4" type="image/png" sizes="16x16" />
        <link rel="shortcut icon" href="/favicon.ico?v=4" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png?v=4" />
        <link
          href="https://api.mapbox.com/mapbox-gl-js/v3.9.3/mapbox-gl.css"
          rel="stylesheet"
        />
      </head>
      <body className={`${inter.className} bg-roadcall-void text-roadcall-silver`}>
        <SiteHeader />
        <main className="min-h-screen">
          {children}
        </main>
        <SiteFooter />
        <CookieConsent />
      </body>
    </html>
  );
}
