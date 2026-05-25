export const HELP_PHONE =
  process.env.NEXT_PUBLIC_HELP_PHONE ||
  process.env.NEXT_PUBLIC_DEMO_PHONE ||
  "(866) 818-3060";

export const COMPANY_PHONE =
  process.env.NEXT_PUBLIC_COMPANY_PHONE || "(866) 623-3331";

export const telHref = (phone: string) =>
  `tel:${phone.replace(/[^+\d]/g, "")}`;
