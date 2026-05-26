export const SHOP_CHECKOUT_LINKS = {
  standard: "https://buy.stripe.com/8x24gB4NWbRI9fc1jU1sQ0r",
  professional: "https://buy.stripe.com/28EaEZ2FO6xo6305Aa1sQ0s",
  advanced: "https://buy.stripe.com/00w7sNa8g6xofDAfaK1sQ0t",
  partnerBadge: process.env.NEXT_PUBLIC_PARTNER_BADGE_CHECKOUT_URL || "/shops/onboarding?upgrade=map-partner-badge",
} as const;