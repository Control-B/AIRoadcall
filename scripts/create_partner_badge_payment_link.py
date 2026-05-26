#!/usr/bin/env python3
"""Create or reuse the Stripe Payment Link for the Roadcall Partner map badge.

Required env:
  STRIPE_SECRET_KEY=sk_live_... or sk_test_...

Optional env:
    APP_BASE_URL=https://roadcall.ai
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import stripe


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


def configured(value: str | None) -> bool:
    return bool(value and value.strip() and not value.endswith("_xxx") and "xxx" not in value.lower())


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_key = key.strip()
        env_value = value.strip().strip('"').strip("'")
        if not configured(os.environ.get(env_key)):
            os.environ[env_key] = env_value


def existing_payment_link() -> stripe.PaymentLink | None:
    links = stripe.PaymentLink.list(active=True, limit=100)
    for link in links.auto_paging_iter():
        if dict(link.get("metadata") or {}).get("roadcall_product") == PRODUCT_METADATA["roadcall_product"]:
            return link
    return None


def get_or_create_price() -> stripe.Price:
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


def public_app_url() -> str:
    return (
        os.environ.get("APP_BASE_URL")
        or os.environ.get("FRONTEND_URL")
        or os.environ.get("ROADCALL_APP_URL")
        or "https://roadcall.ai"
    ).rstrip("/")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")
    load_dotenv(repo_root / "backend" / ".env")

    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not configured(secret_key):
        print("STRIPE_SECRET_KEY is not configured with a real Stripe key.", file=sys.stderr)
        print("Set STRIPE_SECRET_KEY in the environment, then rerun this script.", file=sys.stderr)
        return 2

    stripe.api_key = secret_key
    existing = existing_payment_link()
    if existing:
        payment_link = existing
    else:
        price = get_or_create_price()
        app_url = public_app_url()
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

    print("Partner badge payment link:")
    print(payment_link.url)
    print()
    print("Set this in the frontend environment:")
    print(f'NEXT_PUBLIC_PARTNER_BADGE_CHECKOUT_URL="{payment_link.url}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())