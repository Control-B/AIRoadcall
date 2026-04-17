# LiveKit Cloud config in git (DigitalOcean auto-deploy)

This repo is connected to **DigitalOcean App Platform** with **auto-deploy on push** to your branch (same idea as “deploy when GitHub changes,” but **builds run on DO**, not GitHub Actions).

There is **no GitHub Actions workflow** here for LiveKit — your secrets stay in **DO App environment variables** only.

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

It’s the deployment metadata LiveKit exposes via `lk agent config` (project + Cloud agent id). Some Console-only UI fields may not appear in this file; worker prompts in `agent/agent_worker.py` remain your code source of truth.
