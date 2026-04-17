# Agent prompts — source of truth

LiveKit Cloud does **not** expose the Console → Agents "Instructions" text over a public API, so this folder is the canonical version that our Python worker uses.

Files
- `driver_intake.md` — system prompt for inbound driver intake calls.
- `driver_welcome.txt` — first spoken line after the caller connects (adapted on the fly).

## Load order (driver intake)

The worker resolves the system prompt in this order:

1. `ctx.job.metadata.instructions` (JSON from `CreateAgentDispatch` / SIP dispatch rule `roomConfig.agents[].metadata`).
2. Room metadata `instructions` (same keys).
3. `LIVEKIT_CLOUD_INSTRUCTIONS` environment variable.
4. `AGENT_DRIVER_INTAKE_PROMPT` / `AGENT_DRIVER_INTAKE_PROMPT_FILE`.
5. **`agent/prompts/driver_intake.md`** (this folder) — default canonical prompt.
6. Built-in string fallback in `agent_worker.py`.

When the prompt comes from 1–3 or 5, the worker appends a short **Roadcall tools appendix** (`find_nearby_mechanics`, `save_driver_info`) so behavior remains app-aware.

Opening (welcome) line:

1. `welcome_message` / `opening_instruction` in job or room metadata.
2. `AGENT_DRIVER_OPENING_INSTRUCTION` environment variable.
3. **`agent/prompts/driver_welcome.txt`** (this folder).
4. Built-in string fallback.

## Keeping LiveKit Console in sync

The Console UI is useful for live preview in LiveKit's hosted playground. For production calls routed to our Python worker, edit the files here and commit. On push, DigitalOcean redeploys the `livekit-agent` worker and behavior updates.

If you edit the Console instead, copy the text back into `driver_intake.md` (and `driver_welcome.txt`) so git stays authoritative.
