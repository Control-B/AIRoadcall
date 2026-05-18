type IntakeKind = "shops" | "fleet" | "mechanic";
type IntakeBody = Record<string, unknown>;

type DeliveryResult = {
  delivered: boolean;
  channel: "webhook" | "backend_support";
  status: number;
};

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

function configured(value?: string): string {
  const trimmed = (value || "").trim();
  if (!trimmed) return "";
  if (trimmed.includes("example.")) return "";
  if (trimmed.includes("placeholder")) return "";
  return trimmed;
}

function supportEndpointFromApiBase(value?: string): string {
  const apiBase = configured(value).replace(/\/+$/, "");
  if (!apiBase) return "";
  const base = apiBase.endsWith("/api") ? apiBase : `${apiBase}/api`;
  return `${base}/support/submit-setup-form`;
}

async function postJson(url: string, body: unknown): Promise<Response> {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function forwardIntake(kind: IntakeKind, body: IntakeBody): Promise<DeliveryResult> {
  const webhookUrl = configured(process.env.ROADCALL_ONBOARDING_WEBHOOK_URL);
  const backendSupportUrl = supportEndpointFromApiBase(
    process.env.ROADCALL_BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL,
  );

  const submission = { kind, submitted_at: new Date().toISOString(), ...body };
  const failures: string[] = [];

  if (webhookUrl) {
    try {
      const response = await postJson(webhookUrl, submission);
      if (response.ok) {
        return { delivered: true, channel: "webhook", status: response.status };
      }
      failures.push(`webhook:${response.status}`);
    } catch (error) {
      failures.push(`webhook:${error instanceof Error ? error.message : "request_failed"}`);
    }
  }

  if (backendSupportUrl) {
    try {
      const response = await postJson(backendSupportUrl, { role: kind, data: body });
      if (response.ok) {
        return { delivered: true, channel: "backend_support", status: response.status };
      }
      failures.push(`backend_support:${response.status}`);
    } catch (error) {
      failures.push(`backend_support:${error instanceof Error ? error.message : "request_failed"}`);
    }
  }

  const detail = failures.length
    ? failures.join(", ")
    : "no ROADCALL_ONBOARDING_WEBHOOK_URL or ROADCALL_BACKEND_API_URL/NEXT_PUBLIC_API_URL configured";
  throw new Error(`Onboarding delivery failed: ${detail}`);
}
