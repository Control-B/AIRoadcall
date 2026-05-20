#!/usr/bin/env python3
"""Roadcall + GHL production readiness check.

Prints PASS/WARN/FAIL for required env vars and configuration that Roadcall
needs to operate the GHL-managed shop AI telephony lanes, the Retell-managed
Sandy/Fleet roadside lane, and the Stripe-backed GHL SaaS Pro pricing.

Never prints secret values. Only reports whether each variable is set and
basic shape checks (length, allowed prefix). Safe to run in CI.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass


GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"


@dataclass
class Check:
    name: str
    present: bool
    required: bool
    detail: str = ""


def _has(value: str | None) -> bool:
    return bool(value and value.strip())


def _len_hint(value: str | None) -> str:
    if not value:
        return "missing"
    return f"set ({len(value.strip())} chars)"


def section(title: str, checks: list[Check]) -> tuple[int, int, int]:
    fails = warns = passes = 0
    print(f"\n{CYAN}== {title} =={RESET}")
    for check in checks:
        status_color = GREEN
        status = "PASS"
        if not check.present:
            if check.required:
                status_color = RED
                status = "FAIL"
                fails += 1
            else:
                status_color = YELLOW
                status = "WARN"
                warns += 1
        else:
            passes += 1
        suffix = f" — {check.detail}" if check.detail else ""
        print(f"  {status_color}[{status}]{RESET} {check.name}{suffix}")
    return passes, warns, fails


def main() -> int:
    env = os.environ

    ghl_checks = [
        Check("GHL_API_KEY", _has(env.get("GHL_API_KEY")), True, _len_hint(env.get("GHL_API_KEY"))),
        Check("GHL_LOCATION_ID", _has(env.get("GHL_LOCATION_ID")), True, _len_hint(env.get("GHL_LOCATION_ID"))),
        Check("GHL_BASE_URL", _has(env.get("GHL_BASE_URL")), False, env.get("GHL_BASE_URL") or "defaults to services.leadconnectorhq.com"),
        Check("GHL_PROVISIONING_WEBHOOK_URL", _has(env.get("GHL_PROVISIONING_WEBHOOK_URL")), False, "needed only if Roadcall should call a GHL webhook on snapshot assignment"),
        Check("GHL_FROM_NUMBER", _has(env.get("GHL_FROM_NUMBER")), False, _len_hint(env.get("GHL_FROM_NUMBER"))),
        Check("GHL_ENCRYPTION_KEY", _has(env.get("GHL_ENCRYPTION_KEY")), False, "encrypts per-tenant GHL access/refresh tokens at rest"),
    ]

    snapshot_checks = [
        Check("GHL_STANDARD_SNAPSHOT_ID", _has(env.get("GHL_STANDARD_SNAPSHOT_ID")), False, "set after the Standard snapshot is saved in the GHL agency UI"),
        Check("GHL_PREMIUM_SNAPSHOT_ID", _has(env.get("GHL_PREMIUM_SNAPSHOT_ID")), False, "set after the Professional snapshot is saved in the GHL agency UI"),
        Check("GHL_ADVANCED_SNAPSHOT_ID", _has(env.get("GHL_ADVANCED_SNAPSHOT_ID")), False, "set after the Advanced snapshot is saved in the GHL agency UI"),
    ]

    stripe_checks = [
        Check("STRIPE_SECRET_KEY", _has(env.get("STRIPE_SECRET_KEY")), True, _len_hint(env.get("STRIPE_SECRET_KEY"))),
        Check("STRIPE_WEBHOOK_SECRET", _has(env.get("STRIPE_WEBHOOK_SECRET")), True, "required for /webhooks/stripe signature verification"),
        Check("STRIPE_STANDARD_PRICE_ID", _has(env.get("STRIPE_STANDARD_PRICE_ID")) or _has(env.get("STRIPE_STARTER_PRICE_ID")), False, "maps to Standard ($299) plan; STRIPE_STARTER_PRICE_ID remains a fallback"),
        Check("STRIPE_PREMIUM_PRICE_ID", _has(env.get("STRIPE_PREMIUM_PRICE_ID")) or _has(env.get("STRIPE_GROWTH_PRICE_ID")), False, "maps to Professional ($499) plan; STRIPE_GROWTH_PRICE_ID remains a fallback"),
        Check("STRIPE_ADVANCED_PRICE_ID", _has(env.get("STRIPE_ADVANCED_PRICE_ID")) or _has(env.get("STRIPE_PRO_PRICE_ID")), False, "maps to Advanced ($999) plan; STRIPE_PRO_PRICE_ID remains a fallback"),
    ]

    retell_checks = [
        Check("RETELL_API_KEY", _has(env.get("RETELL_API_KEY")), True, "needed for Sandy roadside + Fleet roadside + Shop receptionist agents"),
        Check("RETELL_AGENT_ID", _has(env.get("RETELL_AGENT_ID")), False, _len_hint(env.get("RETELL_AGENT_ID"))),
        Check("RETELL_CONVERSATION_FLOW_ID", _has(env.get("RETELL_CONVERSATION_FLOW_ID")), False, _len_hint(env.get("RETELL_CONVERSATION_FLOW_ID"))),
        Check("RETELL_FLEET_AGENT_ID", _has(env.get("RETELL_FLEET_AGENT_ID")), False, _len_hint(env.get("RETELL_FLEET_AGENT_ID")) or "required to fork fleet calls into RoadsideIncident"),
        Check("RETELL_SHOP_AGENT_ID", _has(env.get("RETELL_SHOP_AGENT_ID")), False, _len_hint(env.get("RETELL_SHOP_AGENT_ID")) or "third Retell agent for shop AI answering"),
        Check("RETELL_SHOP_CONVERSATION_FLOW_ID", _has(env.get("RETELL_SHOP_CONVERSATION_FLOW_ID")), False, _len_hint(env.get("RETELL_SHOP_CONVERSATION_FLOW_ID")) or "master flow for shop receptionist (run scripts/create_shop_retell_flow.py)"),
        Check("RETELL_BACKEND_WEBHOOK_TOKEN", _has(env.get("RETELL_BACKEND_WEBHOOK_TOKEN")), True, "shared secret for Retell -> Roadcall webhooks"),
    ]

    app_checks = [
        Check("APP_BASE_URL", _has(env.get("APP_BASE_URL")), True, env.get("APP_BASE_URL") or ""),
        Check("FRONTEND_URL", _has(env.get("FRONTEND_URL")), True, env.get("FRONTEND_URL") or ""),
        Check("ADMIN_API_KEY", _has(env.get("ADMIN_API_KEY")) and env.get("ADMIN_API_KEY") != "change-this-to-a-secure-admin-key", True, "must not equal the default placeholder"),
        Check("MAGIC_LINK_SECRET", _has(env.get("MAGIC_LINK_SECRET")) and env.get("MAGIC_LINK_SECRET") != "change-this-to-a-secure-random-string", True, "must not equal the default placeholder"),
        Check("MAPBOX_ACCESS_TOKEN", _has(env.get("MAPBOX_ACCESS_TOKEN")), False, "server-side; the frontend uses NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN or /api/mapbox-token"),
    ]

    frontend_public_checks = [
        Check("NEXT_PUBLIC_API_URL", _has(env.get("NEXT_PUBLIC_API_URL")), False, "frontend uses /api in production by default"),
        Check("NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN", _has(env.get("NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN")), False, "enables /search map view at build time"),
        Check("NEXT_PUBLIC_GHL_GET_STARTED_URL", _has(env.get("NEXT_PUBLIC_GHL_GET_STARTED_URL")), False, "optional: deep-link Get Started directly to GHL"),
        Check("NEXT_PUBLIC_GHL_SIGN_IN_URL", _has(env.get("NEXT_PUBLIC_GHL_SIGN_IN_URL")), False, "optional: deep-link Sign In directly to GHL"),
        Check("NEXT_PUBLIC_GHL_PROVIDER_SIGNUP", _has(env.get("NEXT_PUBLIC_GHL_PROVIDER_SIGNUP")), False, "optional: deep-link provider signup directly to GHL"),
    ]

    sms_voice_checks = [
        Check("TWILIO_ACCOUNT_SID", _has(env.get("TWILIO_ACCOUNT_SID")), False, "required only if Twilio is used for SMS/voice"),
        Check("TWILIO_AUTH_TOKEN", _has(env.get("TWILIO_AUTH_TOKEN")), False, _len_hint(env.get("TWILIO_AUTH_TOKEN"))),
        Check("TELNYX_API_KEY", _has(env.get("TELNYX_API_KEY")), False, "required only if Telnyx is used for SMS/voice"),
    ]

    totals = [0, 0, 0]
    for title, checks in [
        ("GHL SaaS connection (shop AI telephony)", ghl_checks),
        ("GHL snapshot IDs (set after official snapshots are saved)", snapshot_checks),
        ("Stripe (billing for GHL-aligned plans)", stripe_checks),
        ("Retell (Sandy roadside + Fleet roadside + Shop receptionist)", retell_checks),
        ("App / admin secrets", app_checks),
        ("Frontend public env (Next.js build)", frontend_public_checks),
        ("Optional SMS / voice providers", sms_voice_checks),
    ]:
        p, w, f = section(title, checks)
        totals[0] += p
        totals[1] += w
        totals[2] += f

    print(f"\n{CYAN}Summary:{RESET} {GREEN}{totals[0]} pass{RESET}, {YELLOW}{totals[1]} warn{RESET}, {RED}{totals[2]} fail{RESET}")
    print("\nGHL plan alignment expected by Roadcall backend:")
    print("  Standard  $299/mo + $99 setup  (canonical id: standard)")
    print("  Professional  $499/mo + $199 setup  (canonical id: premium)")
    print("  Advanced      $999/mo + $299 setup  (canonical id: advanced)")

    return 1 if totals[2] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
