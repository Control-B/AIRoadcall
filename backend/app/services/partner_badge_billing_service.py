from __future__ import annotations

import stripe

from app.core.config import Settings


PRODUCT_NAME = "Roadcall Partner Map Badge"
PRICE_LOOKUP_KEY = "roadcall_partner_map_badge_monthly_1999"
PRODUCT_METADATA = {"roadcall_product": "partner_map_badge"}
MONTHLY_AMOUNT_CENTS = 1999
CHECKOUT_CUSTOM_FIELDS = [
    {
        "key": "business_name",
        "label": {"type": "custom", "custom": "Business name"},
        "type": "text",
        "optional": False,
    },
    {
        "key": "service_area",
        "label": {"type": "custom", "custom": "Primary city / service area"},
        "type": "text",
        "optional": False,
    },
    {
        "key": "listing_url",
        "label": {"type": "custom", "custom": "Roadcall listing URL or website"},
        "type": "text",
        "optional": True,
    },
]


def _configured(value: str | None) -> bool:
    return bool(value and value.strip() and not value.endswith("_xxx") and "xxx" not in value.lower())


class PartnerBadgeBillingService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_or_reuse_payment_link(self) -> dict[str, object]:
        if not _configured(self.settings.STRIPE_SECRET_KEY):
            raise ValueError("STRIPE_SECRET_KEY is not configured with a real Stripe key")

        stripe.api_key = self.settings.STRIPE_SECRET_KEY
        existing_link = self._existing_payment_link()
        if existing_link:
            price_id = self._line_item_price_id(existing_link)
            return self._response(existing_link, reused=True, price_id=price_id)

        price = self._get_or_create_price()
        app_url = self.settings.public_app_base_url.rstrip("/") or "https://roadcall.ai"
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            metadata=PRODUCT_METADATA,
            phone_number_collection={"enabled": True},
            custom_fields=CHECKOUT_CUSTOM_FIELDS,
            custom_text={
                "submit": {
                    "message": "After payment, Roadcall will verify your listing and enable the partner badge on eligible map pins."
                }
            },
            after_completion={
                "type": "redirect",
                "redirect": {"url": f"{app_url}/shops/onboarding?upgrade=map-partner-badge&checkout=success"},
            },
        )
        return self._response(payment_link, reused=False, price_id=price.id)

    def _existing_payment_link(self):
        links = stripe.PaymentLink.list(active=True, limit=100)
        for link in links.auto_paging_iter():
            if dict(link.get("metadata") or {}).get("roadcall_product") == PRODUCT_METADATA["roadcall_product"]:
                return link
        return None

    def _get_or_create_price(self):
        prices = stripe.Price.list(active=True, lookup_keys=[PRICE_LOOKUP_KEY], limit=1)
        if prices.data:
            return prices.data[0]

        product = stripe.Product.create(
            name=PRODUCT_NAME,
            description="Monthly paid visibility upgrade for Roadcall provider map pins.",
            metadata=PRODUCT_METADATA,
        )
        return stripe.Price.create(
            product=product.id,
            currency="usd",
            unit_amount=MONTHLY_AMOUNT_CENTS,
            recurring={"interval": "month"},
            lookup_key=PRICE_LOOKUP_KEY,
            metadata=PRODUCT_METADATA,
        )

    def _line_item_price_id(self, payment_link) -> str | None:
        line_items = stripe.PaymentLink.list_line_items(payment_link.id, limit=1)
        if not line_items.data:
            return None
        price = line_items.data[0].get("price")
        return price.get("id") if price else None

    def _response(self, payment_link, *, reused: bool, price_id: str | None) -> dict[str, object]:
        return {
            "payment_link_id": payment_link.id,
            "payment_link_url": payment_link.url,
            "price_id": price_id,
            "reused": reused,
            "frontend_env": f'NEXT_PUBLIC_PARTNER_BADGE_CHECKOUT_URL="{payment_link.url}"',
        }