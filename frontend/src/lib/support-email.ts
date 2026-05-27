export const SUPPORT_EMAIL = "support@roadcall.ai";

type SupportValue = string | number | boolean | null | undefined | string[] | Record<string, unknown>;

function stringifySupportValue(value: SupportValue): string {
  if (Array.isArray(value)) return value.filter(Boolean).join(", ");
  if (value && typeof value === "object") return JSON.stringify(value, null, 2);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value ?? "").trim();
}

export function supportMailtoHref(subject: string, fields: Record<string, SupportValue> = {}) {
  const body = Object.entries(fields)
    .map(([key, value]) => [key, stringifySupportValue(value)] as const)
    .filter(([, value]) => value.length > 0)
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`)
    .join("\n");

  const params = new URLSearchParams({ subject });
  if (body) params.set("body", body);
  return `mailto:${SUPPORT_EMAIL}?${params.toString()}`;
}

export async function submitSupportRequest(role: string, subject: string, data: Record<string, SupportValue>) {
  const payload = { ...data, request_subject: subject };
  try {
    const response = await fetch("/api/support/submit-setup-form", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, data: payload }),
    });
    if (response.ok) return "submitted" as const;
  } catch {
    // Fall through to mailto so request buttons never fail silently.
  }

  if (typeof window !== "undefined") {
    window.location.href = supportMailtoHref(subject, payload);
  }
  return "email_draft" as const;
}
