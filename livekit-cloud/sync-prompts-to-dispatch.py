#!/usr/bin/env python3
"""Push committed Mara prompts into the LiveKit SIP dispatch rule.

The LiveKit *Console* "Agents" UI (Instructions / Welcome / models) only
configures LiveKit's hosted agent runtime. Those fields are not exposed via
any public API, so our self-hosted Python worker (``agent/agent_worker.py``)
cannot read them directly.

What *is* scriptable is the **SIP dispatch rule**. It has a
``roomConfig.agents[].metadata`` string that LiveKit passes to whichever
agent handles the call as ``ctx.job.metadata``. Our worker already parses
that JSON and extracts ``instructions`` / ``welcome_message`` /
``opening_instruction``.

So the "link" between the Console and our code is:

    agent/prompts/driver_intake.md   ->  dispatch rule roomConfig.agents[].metadata.instructions
    agent/prompts/driver_welcome.txt ->  dispatch rule roomConfig.agents[].metadata.welcome_message

Run this script whenever you change those files.

Usage
-----
    # from repo root
    cd agent && .venv/bin/python ../livekit-cloud/sync-prompts-to-dispatch.py

Required env:
    LIVEKIT_URL
    LIVEKIT_API_KEY
    LIVEKIT_API_SECRET
    LIVEKIT_DISPATCH_RULE_ID        (run list-dispatch-rules.py to find it)

Optional env:
    LIVEKIT_AGENT_NAME              (defaults to "roadcall-agent")
    LIVEKIT_DISPATCH_EXTRA_JSON     (extra JSON merged into metadata)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from livekit import api
from livekit.protocol.agent_dispatch import RoomAgentDispatch
from livekit.protocol.sip import ListSIPDispatchRuleRequest


REPO_ROOT = Path(__file__).resolve().parent.parent
INTAKE_FILE = REPO_ROOT / "agent" / "prompts" / "driver_intake.md"
WELCOME_FILE = REPO_ROOT / "agent" / "prompts" / "driver_welcome.txt"


def _require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"error: required env var {name} is not set", file=sys.stderr)
        sys.exit(1)
    return val


def _load_text(path: Path) -> str:
    if not path.exists():
        print(f"error: missing prompt file: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding="utf-8").strip()


async def main() -> None:
    lk_url = _require_env("LIVEKIT_URL")
    api_key = _require_env("LIVEKIT_API_KEY")
    api_secret = _require_env("LIVEKIT_API_SECRET")
    rule_id = _require_env("LIVEKIT_DISPATCH_RULE_ID")
    agent_name = os.getenv("LIVEKIT_AGENT_NAME", "roadcall-agent").strip()

    instructions = _load_text(INTAKE_FILE)
    welcome = _load_text(WELCOME_FILE)

    payload: dict[str, object] = {
        "instructions": instructions,
        "welcome_message": welcome,
        "opening_instruction": welcome,
    }

    extra_raw = os.getenv("LIVEKIT_DISPATCH_EXTRA_JSON", "").strip()
    if extra_raw:
        try:
            extra = json.loads(extra_raw)
            if isinstance(extra, dict):
                payload.update(extra)
            else:
                print(
                    "warn: LIVEKIT_DISPATCH_EXTRA_JSON is not a JSON object; ignoring",
                    file=sys.stderr,
                )
        except json.JSONDecodeError as e:
            print(f"warn: LIVEKIT_DISPATCH_EXTRA_JSON invalid JSON ({e}); ignoring", file=sys.stderr)

    job_metadata = json.dumps(payload)

    async with api.LiveKitAPI(url=lk_url, api_key=api_key, api_secret=api_secret) as lkapi:
        listing = await lkapi.sip.list_dispatch_rule(ListSIPDispatchRuleRequest())
        rule = next(
            (r for r in listing.items if r.sip_dispatch_rule_id == rule_id),
            None,
        )
        if rule is None:
            print(f"error: dispatch rule {rule_id} not found on this project", file=sys.stderr)
            print("hint: run livekit-cloud/list-dispatch-rules.py", file=sys.stderr)
            sys.exit(2)

        # Build replacement SIPDispatchRuleInfo based on the existing one
        replacement = type(rule)()
        replacement.CopyFrom(rule)

        agents = list(replacement.room_config.agents)
        found = False
        for a in agents:
            if a.agent_name == agent_name:
                a.metadata = job_metadata
                found = True
                break
        if not found:
            agents.append(RoomAgentDispatch(agent_name=agent_name, metadata=job_metadata))

        del replacement.room_config.agents[:]
        replacement.room_config.agents.extend(agents)
        updated = await lkapi.sip.update_dispatch_rule(rule_id, replacement)

    print(f"updated dispatch rule {rule_id}")
    print(f"  name:        {updated.name or '(unnamed)'}")
    print(f"  trunk_ids:   {list(updated.trunk_ids)}")
    for a in updated.room_config.agents:
        print(
            f"  agent:       name={a.agent_name}  "
            f"metadata_chars={len(a.metadata)}"
        )
    print()
    print("Next inbound call will carry these instructions via ctx.job.metadata.")


if __name__ == "__main__":
    asyncio.run(main())
