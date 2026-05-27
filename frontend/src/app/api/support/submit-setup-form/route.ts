import { NextResponse } from "next/server";
import { forwardIntake } from "@/lib/server/onboarding-intake";

export const dynamic = "force-dynamic";

const allowedRoles = new Set([
  "mechanic",
  "shops",
  "fleet",
  "vendor",
  "trucking_company",
  "marketplace_listing",
  "marketplace_claim",
  "marketplace_update",
  "ai_phone",
  "map_badge",
]);

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ detail: "Invalid setup payload." }, { status: 400 });
  }

  const payload = body as { role?: unknown; data?: unknown };
  const role = typeof payload.role === "string" ? payload.role : "mechanic";
  if (!allowedRoles.has(role)) {
    return NextResponse.json({ detail: "Unsupported setup role." }, { status: 400 });
  }
  if (!payload.data || typeof payload.data !== "object") {
    return NextResponse.json({ detail: "Missing setup form data." }, { status: 400 });
  }

  try {
    const delivery = await forwardIntake(role as Parameters<typeof forwardIntake>[0], payload.data as Record<string, unknown>);
    return NextResponse.json({ ok: true, delivery });
  } catch (error) {
    console.error("Support setup forward failed", error);
    return NextResponse.json(
      { detail: "We could not submit this setup form. Please try again or contact support@roadcall.ai." },
      { status: 503 },
    );
  }
}