import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Roadcall.ai — AI-Powered Roadside Dispatch",
    template: "%s | Roadcall.ai",
  },
  icons: {
    icon: [{ url: "/favicon.svg?v=2", type: "image/svg+xml" }],
    shortcut: "/favicon.svg?v=2",
    apple: "/favicon.svg?v=2",
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
        <link rel="icon" href="/favicon.svg?v=2" type="image/svg+xml" />
        <link rel="shortcut icon" href="/favicon.svg?v=2" />
        <link
          href="https://api.mapbox.com/mapbox-gl-js/v3.9.3/mapbox-gl.css"
          rel="stylesheet"
        />
      </head>
      <body className={inter.className}>
        <main className="min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
