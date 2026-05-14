export const GHL_GET_STARTED_URL =
  process.env.NEXT_PUBLIC_GHL_GET_STARTED_URL ||
  process.env.NEXT_PUBLIC_GHL_PROVIDER_SIGNUP ||
  "/provider/register";

export const GHL_SIGN_IN_URL =
  process.env.NEXT_PUBLIC_GHL_SIGN_IN_URL ||
  process.env.NEXT_PUBLIC_GHL_PROVIDER_SIGNUP ||
  "";

export function isExternalUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}
