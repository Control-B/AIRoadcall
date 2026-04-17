#!/usr/bin/env python3
"""List all SIP dispatch rules on the LiveKit project so you can grab an ID.

Usage:
    cd agent && .venv/bin/python ../livekit-cloud/list-dispatch-rules.py

Required env:
    LIVEKIT_URL
    LIVEKIT_API_KEY
    LIVEKIT_API_SECRET
"""

from __future__ import annotations

import asyncio
import os
import sys

from livekit import api
from livekit.protocol.sip import ListSIPDispatchRuleRequest


def _require(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        print(f"error: {name} is not set", file=sys.stderr)
        sys.exit(1)
    return v


async def main() -> None:
    url = _require("LIVEKIT_URL")
    _require("LIVEKIT_API_KEY")
    _require("LIVEKIT_API_SECRET")

    async with api.LiveKitAPI(url=url) as lkapi:
        resp = await lkapi.sip.list_sip_dispatch_rule(ListSIPDispatchRuleRequest())

    if not resp.items:
        print("(no SIP dispatch rules configured)")
        return

    for r in resp.items:
        print(f"- id:        {r.sip_dispatch_rule_id}")
        print(f"  name:      {r.name or '(unnamed)'}")
        print(f"  trunks:    {list(r.trunk_ids)}")
        print(f"  numbers:   {list(r.inbound_numbers)}")
        print(f"  agents:    {[a.agent_name for a in r.room_config.agents]}")
        for a in r.room_config.agents:
            meta = a.metadata or ""
            if meta:
                preview = meta[:120].replace("\n", " ")
                suffix = "…" if len(meta) > 120 else ""
                print(f"    - {a.agent_name!r} metadata[{len(meta)}]: {preview}{suffix}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
