import { supportMailtoHref } from "@/lib/support-email";

export const GHL_GET_STARTED_URL =
  process.env.NEXT_PUBLIC_GHL_GET_STARTED_URL ||
  process.env.NEXT_PUBLIC_GHL_PROVIDER_SIGNUP ||
  supportMailtoHref("Roadcall setup request", { source: "ghl_get_started_fallback" });

export const GHL_SIGN_IN_URL =
  process.env.NEXT_PUBLIC_GHL_SIGN_IN_URL ||
  process.env.NEXT_PUBLIC_GHL_PROVIDER_SIGNUP ||
  "";

export function isExternalUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}
