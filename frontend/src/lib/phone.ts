export const HELP_PHONE =
  process.env.NEXT_PUBLIC_HELP_PHONE ||
  process.env.NEXT_PUBLIC_DEMO_PHONE ||
  "(866) 818-3060";

export const COMPANY_PHONE =
  process.env.NEXT_PUBLIC_COMPANY_PHONE || "(866) 623-3331";

export const telHref = (phone: string) => {
  const raw = phone.replace(/[^+\d]/g, "");
  const digits = raw.replace(/\D/g, "");
  if (raw.startsWith("+")) return `tel:${raw}`;
  if (digits.length === 10) return `tel:+1${digits}`;
  if (digits.length === 11 && digits.startsWith("1")) return `tel:+${digits}`;
  return `tel:${raw}`;
};
