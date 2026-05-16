import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function configuredMapboxToken(value?: string): string {
  const token = (value || "").trim();
  const normalized = token.toLowerCase();
  if (!token) return "";
  if (!normalized.startsWith("pk.")) return "";
  if (normalized === "pk.xxx") return "";
  if (normalized.includes("placeholder")) return "";
  if (normalized.includes("replace_with")) return "";
  return token;
}

export async function GET() {
  const token =
    configuredMapboxToken(process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN) ||
    configuredMapboxToken(process.env.MAPBOX_ACCESS_TOKEN);

  return NextResponse.json(
    { configured: Boolean(token), token: token || null },
    { headers: { "Cache-Control": "no-store" } },
  );
}