#!/usr/bin/env python3
"""Create or update a SIP dispatch rule for the self-hosted `roadcall-agent`.

This is the clean bootstrap step for a brand-new LiveKit project when you want
the phone number to route directly to the repo-backed worker instead of a hosted
Console agent.

Required env:
    LIVEKIT_URL
    LIVEKIT_API_KEY
    LIVEKIT_API_SECRET

One of:
    LIVEKIT_SIP_TRUNK_ID
    LIVEKIT_INBOUND_NUMBER

Optional env:
    LIVEKIT_AGENT_NAME              defaults to "roadcall-agent"
    LIVEKIT_DISPATCH_RULE_NAME      defaults to "Roadcall"
    LIVEKIT_ROOM_PREFIX             defaults to "roadcall"
    LIVEKIT_DISPATCH_RULE_ID        update this exact rule if provided
    LIVEKIT_DISPATCH_EXTRA_JSON     merged into dispatch metadata JSON
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from livekit import api
from livekit.protocol.agent_dispatch import RoomAgentDispatch
from livekit.protocol.room import RoomConfiguration
from livekit.protocol.sip import (
    CreateSIPDispatchRuleRequest,
    ListSIPDispatchRuleRequest,
    SIPDispatchRule,
    SIPDispatchRuleCallee,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
INTAKE_FILE = REPO_ROOT / "agent" / "prompts" / "driver_intake.md"
WELCOME_FILE = REPO_ROOT / "agent" / "prompts" / "driver_welcome.txt"


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"error: required env var {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value


def _load_text(path: Path) -> str:
    if not path.exists():
        print(f"error: missing prompt file: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding="utf-8").strip()


def _dispatch_metadata() -> str:
    payload: dict[str, object] = {
        "instructions": _load_text(INTAKE_FILE),
        "welcome_message": _load_text(WELCOME_FILE),
        "opening_instruction": _load_text(WELCOME_FILE),
    }
    extra_raw = os.getenv("LIVEKIT_DISPATCH_EXTRA_JSON", "").strip()
    if extra_raw:
        try:
            extra = json.loads(extra_raw)
        except json.JSONDecodeError as exc:
            print(f"warn: ignoring invalid LIVEKIT_DISPATCH_EXTRA_JSON ({exc})", file=sys.stderr)
        else:
            if isinstance(extra, dict):
                payload.update(extra)
            else:
                print("warn: LIVEKIT_DISPATCH_EXTRA_JSON is not a JSON object; ignoring", file=sys.stderr)
    return json.dumps(payload)


def _matching_rule(rules: list, *, rule_id: str | None, rule_name: str):
    if rule_id:
        return next((rule for rule in rules if rule.sip_dispatch_rule_id == rule_id), None)
    return next((rule for rule in rules if (rule.name or "") == rule_name), None)


async def main() -> None:
    url = _require_env("LIVEKIT_URL")
    api_key = _require_env("LIVEKIT_API_KEY")
    api_secret = _require_env("LIVEKIT_API_SECRET")

    trunk_id = os.getenv("LIVEKIT_SIP_TRUNK_ID", "").strip()
    inbound_number = os.getenv("LIVEKIT_INBOUND_NUMBER", "").strip()
    if not trunk_id and not inbound_number:
        print(
            "error: set LIVEKIT_SIP_TRUNK_ID or LIVEKIT_INBOUND_NUMBER for the inbound route",
            file=sys.stderr,
        )
        sys.exit(1)

    agent_name = os.getenv("LIVEKIT_AGENT_NAME", "roadcall-agent").strip() or "roadcall-agent"
    rule_name = os.getenv("LIVEKIT_DISPATCH_RULE_NAME", "Roadcall").strip() or "Roadcall"
    room_prefix = os.getenv("LIVEKIT_ROOM_PREFIX", "roadcall").strip() or "roadcall"
    explicit_rule_id = os.getenv("LIVEKIT_DISPATCH_RULE_ID", "").strip() or None
    metadata = _dispatch_metadata()

    room_config = RoomConfiguration(
        agents=[RoomAgentDispatch(agent_name=agent_name, metadata=metadata)]
    )
    dispatch_rule = SIPDispatchRule(
        dispatch_rule_callee=SIPDispatchRuleCallee(room_prefix=room_prefix, randomize=True)
    )

    async with api.LiveKitAPI(url=url, api_key=api_key, api_secret=api_secret) as lkapi:
        listing = await lkapi.sip.list_dispatch_rule(ListSIPDispatchRuleRequest())
        existing = _matching_rule(list(listing.items), rule_id=explicit_rule_id, rule_name=rule_name)

        if existing is None:
            created = await lkapi.sip.create_dispatch_rule(
                CreateSIPDispatchRuleRequest(
                    name=rule_name,
                    trunk_ids=[trunk_id] if trunk_id else [],
                    inbound_numbers=[inbound_number] if inbound_number else [],
                    rule=dispatch_rule,
                    room_config=room_config,
                )
            )
            print(f"created dispatch rule {created.sip_dispatch_rule_id}")
            print(f"  name:      {created.name or '(unnamed)'}")
            print(f"  trunks:    {list(created.trunk_ids)}")
            print(f"  numbers:   {list(created.inbound_numbers)}")
            print(f"  agents:    {[a.agent_name for a in created.room_config.agents]}")
            return

        replacement = type(existing)()
        replacement.CopyFrom(existing)
        replacement.name = rule_name
        replacement.rule.CopyFrom(dispatch_rule)
        del replacement.room_config.agents[:]
        replacement.room_config.agents.extend(room_config.agents)
        del replacement.trunk_ids[:]
        if trunk_id:
            replacement.trunk_ids.extend([trunk_id])
        del replacement.inbound_numbers[:]
        if inbound_number:
            replacement.inbound_numbers.extend([inbound_number])

        updated = await lkapi.sip.update_dispatch_rule(existing.sip_dispatch_rule_id, replacement)
        print(f"updated dispatch rule {updated.sip_dispatch_rule_id}")
        print(f"  name:      {updated.name or '(unnamed)'}")
        print(f"  trunks:    {list(updated.trunk_ids)}")
        print(f"  numbers:   {list(updated.inbound_numbers)}")
        print(f"  agents:    {[a.agent_name for a in updated.room_config.agents]}")


if __name__ == "__main__":
    asyncio.run(main())