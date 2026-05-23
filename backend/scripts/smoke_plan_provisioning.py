#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


PLANS = ("widget_only", "ai_telephony", "widget_voice", "enterprise", "standard", "professional", "advanced")


def build_payload(plan: str) -> dict[str, object]:
    return {
        "plan_id": plan,
        "organization_name": f"Roadcall Smoke {plan.title()}",
        "organization_slug": f"roadcall-smoke-{plan}",
        "contact_email": f"smoke+{plan}@roadcall.ai",
        "subscription_status": "active",
        "setup_fee_status": "paid",
        "onboarding_status": "not_started",
        "metadata": {"source": "smoke_plan_provisioning"},
    }


def post_json(url: str, admin_key: str, payload: dict[str, object]) -> dict[str, object]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json", "x-admin-key": admin_key},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Roadcall plan provisioning.")
    parser.add_argument("--api-base", default=os.getenv("API_BASE", "http://localhost:8000/api"))
    parser.add_argument("--admin-key", default=os.getenv("ADMIN_API_KEY", ""))
    parser.add_argument("--execute", action="store_true", help="POST to the API. Default is dry-run payload output.")
    args = parser.parse_args()

    if not args.execute:
        print(json.dumps([build_payload(plan) for plan in PLANS], indent=2))
        return 0

    for plan in PLANS:
        payload = build_payload(plan)
        if not args.admin_key:
            print("error: --execute requires ADMIN_API_KEY or --admin-key", file=sys.stderr)
            return 1
        try:
            result = post_json(f"{args.api_base.rstrip('/')}/provisioning/tenants", args.admin_key, payload)
            print(json.dumps({"plan": plan, "ok": result.get("ok"), "tenant_id": result.get("tenant", {}).get("id")}, indent=2))
        except urllib.error.HTTPError as exc:
            print(f"error provisioning {plan}: HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())