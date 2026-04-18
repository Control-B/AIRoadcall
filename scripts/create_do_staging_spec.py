#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import os
import sys

import yaml


PLACEHOLDER_KEYS = {
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
    "NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN",
    "TAVILY_API_KEY",
    "DO_AI_API_KEY",
    "DO_AI_MODEL",
    "DO_AI_ENDPOINT",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "APIFY_API_TOKEN",
    "MAGIC_LINK_SECRET",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "ADMIN_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "DEMO_PHONE_NUMBER",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "LIVEKIT_URL",
    "LIVEKIT_SIP_TRUNK_ID",
    "LIVEKIT_OUTBOUND_AGENT_ID",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "DEEPGRAM_API_KEY",
}


def load_env(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a DO staging app spec with local .env secrets injected")
    parser.add_argument("--base-spec", default="/root/AIRoadcall/.do/app.staging.yaml")
    parser.add_argument("--env-file", default="/root/AIRoadcall/.env")
    parser.add_argument("--output", default="-", help="Output path or - for stdout")
    args = parser.parse_args()

    base_spec = Path(args.base_spec)
    env_file = Path(args.env_file)
    env_values = load_env(env_file)
    spec = yaml.safe_load(base_spec.read_text())

    for group in ("services", "workers", "jobs", "static_sites"):
        for component in spec.get(group, []) or []:
            for env in component.get("envs", []) or []:
                key = env.get("key")
                if key in env_values and (key in PLACEHOLDER_KEYS or str(env.get("value", "")).startswith("EV[") or env.get("value") == "placeholder"):
                    env["value"] = env_values[key]

    output_text = yaml.safe_dump(spec, sort_keys=False)
    if args.output == "-":
        sys.stdout.write(output_text)
    else:
        Path(args.output).write_text(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
