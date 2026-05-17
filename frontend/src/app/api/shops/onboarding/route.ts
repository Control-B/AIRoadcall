import { NextResponse } from "next/server";
import { forwardIntake, validateIntake } from "@/lib/server/onboarding-intake";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ detail: "Invalid shop onboarding payload." }, { status: 400 });
  }

  const payload = body as Record<string, unknown>;
  const validationError = validateIntake(payload, ["business_name", "owner_name"]);
  if (validationError) {
    return NextResponse.json({ detail: validationError }, { status: 400 });
  }

  try {
    await forwardIntake("shops", payload);
  } catch (error) {
    console.error("Shop onboarding forward failed", error);
  }

  return NextResponse.json({ ok: true, message: "Shop onboarding request received." });
}
