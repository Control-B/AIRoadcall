type IntakeBody = Record<string, unknown>;

const REQUIRED_FIELDS = ["email", "phone"];

function valueAsString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function validateIntake(body: IntakeBody, extraRequired: string[] = []) {
  const missing = [...REQUIRED_FIELDS, ...extraRequired].filter((field) => !valueAsString(body[field]));
  if (missing.length > 0) {
    return `Missing required fields: ${missing.join(", ")}`;
  }
  return null;
}

export async function forwardIntake(kind: "shops" | "fleet", body: IntakeBody) {
  const webhookUrl = process.env.ROADCALL_ONBOARDING_WEBHOOK_URL;
  if (!webhookUrl) return;

  await fetch(webhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, submitted_at: new Date().toISOString(), ...body }),
  });
}
