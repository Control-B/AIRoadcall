export const HELP_PHONE =
  process.env.NEXT_PUBLIC_HELP_PHONE ||
  process.env.NEXT_PUBLIC_DEMO_PHONE ||
  "(866) 613-5299";

export const COMPANY_PHONE =
  process.env.NEXT_PUBLIC_COMPANY_PHONE || "(866) 415-9494";

export const telHref = (phone: string) =>
  `tel:${phone.replace(/[^+\d]/g, "")}`;
