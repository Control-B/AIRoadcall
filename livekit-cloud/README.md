# LiveKit Cloud ↔ GitHub sync

LiveKit **does not** send webhooks to GitHub when you save changes in the Cloud Console. To keep deployment metadata in git (so pushes can trigger DigitalOcean or other CI), this repo includes a workflow that **pulls** the official deployment file from LiveKit using the CLI.

## What gets synced

The workflow runs `lk agent config --id <AGENT_ID>` and commits `livekit-cloud/livekit.toml`. That file links your LiveKit **project** and **Cloud agent ID** for CLI operations (`lk agent deploy`, `lk agent status`, etc.).

Dashboard-only fields (e.g. some Agent Builder prompts, voice UI) may be stored in LiveKit separately; they are **not** guaranteed to appear in `livekit.toml`. For prompts that must be version-controlled with your code, keep them in the Python worker (`agent/agent_worker.py`) or env-driven text files in this repository.

## One-time: GitHub secrets

In the repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Description |
|--------|-------------|
| `LIVEKIT_URL` | WebSocket URL, e.g. `wss://your-subdomain.livekit.cloud` |
| `LIVEKIT_API_KEY` | Project API key |
| `LIVEKIT_API_SECRET` | Project API secret |
| `LIVEKIT_CLOUD_AGENT_ID` | Cloud agent id (often `CA_…`). From local CLI: `lk agent list` after `lk cloud auth` or `lk project add`. |

Optional repo **variable** `LIVEKIT_SYNC_DISABLED` = `true` disables the workflow job if you are not using this integration.

## How to run

- **Automatic:** workflow `.github/workflows/sync-livekit-cloud-config.yml` runs on a schedule (every 6 hours) and only commits when `livekit.toml` changes.
- **Manual:** **Actions → Sync LiveKit Cloud config → Run workflow**.

After a successful run, a commit on `main` will trigger your usual DO deploy (if configured for that branch).

## Local pull (same as CI)

```bash
# Install CLI: https://docs.livekit.io/reference/developer-tools/livekit-cli/
lk project add myproj --url "$LIVEKIT_URL" --api-key "$LIVEKIT_API_KEY" --api-secret "$LIVEKIT_API_SECRET" --default
mkdir -p livekit-cloud && cd livekit-cloud
lk agent config --id "$LIVEKIT_CLOUD_AGENT_ID"
```
