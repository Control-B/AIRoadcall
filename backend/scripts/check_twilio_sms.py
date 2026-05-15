#!/usr/bin/env python3
"""Check whether Roadcall's configured Twilio SMS sender is ready.

Dry-run by default. To send a live test SMS, pass both `--to` and `--send`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.sms_service import SMSService  # noqa: E402


def mask(value: str, keep: int = 4) -> str:
    value = value or ""
    if not value:
        return "missing"
    if len(value) <= keep:
        return "set"
    return f"{value[:keep]}…{value[-keep:]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Twilio SMS configuration and optionally send a test SMS.")
    parser.add_argument("--to", help="Destination phone number in E.164 format, e.g. +15551234567")
    parser.add_argument("--body", default="Roadcall.ai SMS test. Reply STOP to opt out, HELP for help.")
    parser.add_argument("--from-number", help="Override TWILIO_FROM_NUMBER for this check/test")
    parser.add_argument("--send", action="store_true", help="Actually send a live SMS. Without this, only configuration is checked.")
    args = parser.parse_args()

    settings = get_settings()
    from_number = args.from_number or settings.TWILIO_FROM_NUMBER
    has_sid = bool(settings.TWILIO_ACCOUNT_SID and not settings.TWILIO_ACCOUNT_SID.startswith("AC_placeholder"))
    has_token = bool(settings.TWILIO_AUTH_TOKEN)
    has_from = bool(from_number or settings.TWILIO_MESSAGING_SERVICE_SID)

    print("Twilio SMS readiness")
    print(f"  account_sid: {mask(settings.TWILIO_ACCOUNT_SID)}")
    print(f"  auth_token: {'set' if has_token else 'missing'}")
    print(f"  from_number: {from_number or 'missing'}{' (override)' if args.from_number else ''}")
    print(f"  messaging_service_sid: {mask(settings.TWILIO_MESSAGING_SERVICE_SID)}")
    print(f"  studio_flow_sid: {mask(settings.TWILIO_STUDIO_FLOW_SID)}")

    if not has_sid or not has_token or not has_from:
        print("\nResult: not ready — configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID.")
        return 2

    if not args.send:
        print("\nResult: config looks ready. Dry-run only; pass --to +15551234567 --send to send a live SMS.")
        return 0

    if not args.to:
        print("\nResult: missing --to. Refusing to send without an explicit destination number.")
        return 2

    original_from_number = settings.TWILIO_FROM_NUMBER
    settings.TWILIO_FROM_NUMBER = from_number
    try:
        sent = SMSService._send_via_twilio(args.to, args.body)
    finally:
        settings.TWILIO_FROM_NUMBER = original_from_number
    if sent:
        print("\nResult: Twilio accepted the SMS request. Check Twilio message logs for carrier delivery status.")
        return 0

    print("\nResult: Twilio send failed. Check backend logs/Twilio error for A2P, sender, or destination issues.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
