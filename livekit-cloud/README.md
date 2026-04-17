# LiveKit Cloud config in git (DigitalOcean auto-deploy)

This repo is connected to **DigitalOcean App Platform** with **auto-deploy on push** to your branch (same idea as “deploy when GitHub changes,” but **builds run on DO**, not GitHub Actions).

There is **no GitHub Actions workflow** here for LiveKit — your secrets stay in **DO App environment variables** only.

---

## Console UI vs. this repo — how they relate

LiveKit has **two different agent runtimes** and they are often confused:

| Runtime | Where it runs | Configured by | Has our custom tools? |
| --- | --- | --- | --- |
| **LiveKit Console "Agents"** (the page with *Instructions*, *Welcome*, *LLM/TTS/STT*) — e.g. `Blake-2bf…` | LiveKit Cloud (hosted) | Console UI only | **No** — can't call `find_nearby_mechanics`, `save_driver_info`, future RAG, SMS, etc. |
| **Custom Python worker** — `roadcall-agent` (in `agent/`) | Your DigitalOcean App Platform container | This repo (`agent/prompts/`, `agent/agent_worker.py`) | **Yes** |

Which runtime handles a call is decided by the **SIP dispatch rule's `roomConfig.agents[].agentName`**:

- If `agentName: "Blake-2bf…"` → LiveKit's hosted runtime answers. Console Instructions apply. No custom tools.
- If `agentName: "roadcall-agent"` → our worker answers. Prompt comes from this repo. All tools available.

For Roadcall you want **`roadcall-agent`** — otherwise the RAG / mechanic lookup / SMS / backend integrations can't run.

> The Console's *Instructions* / *Welcome* fields are **not exposed via any public API**, so the worker cannot fetch them. We solve this the other way around: we push the repo's prompt into the dispatch rule (see below).

---

## Linking the Console to the code (source of truth = repo)

The files in `agent/prompts/` are the canonical Mara prompt:

- `agent/prompts/driver_intake.md`  → system prompt
- `agent/prompts/driver_welcome.txt` → first spoken line

`agent/agent_worker.py` reads instructions in this priority order:

1. **`ctx.job.metadata`** — JSON on the agent dispatch (outbound `CreateAgentDispatch` or inbound **SIP dispatch rule** `roomConfig.agents[].metadata`). Example:

   ```json
   {
     "instructions": "Your name is Mara…",
     "welcome_message": "Thank you for calling Roadside, this is Mara…",
     "opening_instruction": "Optional; overrides first-spoken turn"
   }
   ```

2. **Room metadata** — same keys if your trunk or app sets them on the room.
3. **`LIVEKIT_CLOUD_INSTRUCTIONS`** env on the agent worker (and on the backend for outbound dispatch metadata).
4. **`agent/prompts/driver_intake.md` + `driver_welcome.txt`** — canonical committed prompt.
5. Fallback — `AGENT_DRIVER_INTAKE_*` env / built-in default in `agent/agent_worker.py`.

### One-shot: push the repo prompts into the SIP dispatch rule

Run this whenever you change `agent/prompts/*`:

```bash
# from repo root
cd agent
source .venv/bin/activate

export LIVEKIT_URL='wss://…livekit.cloud'
export LIVEKIT_API_KEY='APISAgV…'
export LIVEKIT_API_SECRET='…'

# find the dispatch rule id (the one mapped to your inbound number)
python ../livekit-cloud/list-dispatch-rules.py

# then push the prompts into it
export LIVEKIT_DISPATCH_RULE_ID='SDR_…'
export LIVEKIT_AGENT_NAME='roadcall-agent'   # must match agent/agent_worker.py
python ../livekit-cloud/sync-prompts-to-dispatch.py
```

What this does:

- Reads `agent/prompts/driver_intake.md` and `driver_welcome.txt`.
- Builds JSON `{ "instructions": …, "welcome_message": …, "opening_instruction": … }`.
- Updates the dispatch rule so `roomConfig.agents[0].metadata = <that JSON>` and `agent_name = roadcall-agent`.
- Next inbound call → LiveKit dispatches `roadcall-agent` → our worker receives the JSON as `ctx.job.metadata` → Mara speaks with the committed prompt.

**Check the dispatch rule afterwards in the Console** — you should see `roadcall-agent` listed under the rule with the prompt in its metadata.

---

## Syncing `livekit.toml` after you change something in the LiveKit Console

LiveKit does not push to GitHub for you. To get an updated `livekit.toml` into this repo so the next deploy includes it:

1. In **DigitalOcean** → your App → **Settings** → copy the LiveKit-related env vars (or use the values you already set).
2. On your machine, from the **repository root**:

   ```bash
   export LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... LIVEKIT_CLOUD_AGENT_ID=...
   bash livekit-cloud/sync-from-env.sh
   ```

3. Commit and push:

   ```bash
   git add livekit-cloud/livekit.toml
   git commit -m "chore(livekit): sync Cloud agent config"
   git push
   ```

4. **DigitalOcean** will pick up the commit and run your normal auto-deploy.

The script uses the same variable names as typical DO app env; it installs the `lk` CLI under `.livekit-cli/` (gitignored).

## What’s in `livekit.toml`

It’s the deployment metadata LiveKit exposes via `lk agent config` (project + Cloud agent id). **Agent “Instructions” from the LiveKit Console are not embedded in this file** (and cannot be, because LiveKit doesn't expose them). See the section above on how the repo prompts become the source of truth via the SIP dispatch rule.

See `LIVEKIT_CLOUD_INSTRUCTIONS` and `LIVEKIT_AGENT_DISPATCH_METADATA_EXTRA` in the root `.env.example`.
