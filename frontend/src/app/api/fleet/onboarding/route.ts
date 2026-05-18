import { NextResponse } from "next/server";
import { forwardIntake, validateIntake } from "@/lib/server/onboarding-intake";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ detail: "Invalid fleet onboarding payload." }, { status: 400 });
  }

  const payload = body as Record<string, unknown>;
  const validationError = validateIntake(payload, ["company_name", "contact_name"]);
  if (validationError) {
    return NextResponse.json({ detail: validationError }, { status: 400 });
  }

  try {
    const delivery = await forwardIntake("fleet", payload);
    return NextResponse.json({ ok: true, message: "Fleet onboarding request received.", delivery });
  } catch (error) {
    console.error("Fleet onboarding forward failed", error);
    return NextResponse.json(
      { detail: "We could not deliver this fleet profile. Please call Roadcall or try again in a moment." },
      { status: 503 },
    );
  }
}
