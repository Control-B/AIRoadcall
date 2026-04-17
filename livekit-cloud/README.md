# LiveKit Cloud ↔ GitHub sync

LiveKit **does not** send webhooks to GitHub when you save changes in the Cloud Console. This folder holds the pulled deployment file and helpers so you can commit it and trigger deploys (e.g. DigitalOcean on push to `main`).

## Secrets live on DigitalOcean — GitHub Actions cannot see them

**GitHub Actions runs on GitHub’s servers.** It has **no access** to [DigitalOcean App Platform environment variables](https://docs.digitalocean.com/products/app-platform/how-to/use-environment-variables/). Those values only exist inside your DO runtime.

You can do **one** of the following:

### Option A — Copy the same values into GitHub (recommended for the sync workflow)

Use the **same names and values** as in DO App → **Settings → App-Level Environment Variables** (or your component env):

| GitHub Actions secret | Typical DO env name |
|----------------------|---------------------|
| `LIVEKIT_URL` | `LIVEKIT_URL` |
| `LIVEKIT_API_KEY` | `LIVEKIT_API_KEY` |
| `LIVEKIT_API_SECRET` | `LIVEKIT_API_SECRET` |
| `LIVEKIT_CLOUD_AGENT_ID` | `LIVEKIT_CLOUD_AGENT_ID` (or add this in DO if missing) |

Add them under **Repo → Settings → Secrets and variables → Actions**. This is not a second “source of truth” — it is the **same credentials** GitHub needs to run `lk` for you.

Then run **Actions → Sync LiveKit Cloud config → Run workflow**.

### Option B — Sync from your machine (no GitHub secrets)

Export the same variables (copy from the DO dashboard or from your local `.env`), then from the **repo root**:

```bash
export LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... LIVEKIT_CLOUD_AGENT_ID=...
bash livekit-cloud/sync-from-env.sh
git add livekit-cloud/livekit.toml && git commit -m "chore(livekit): sync Cloud config" && git push
```

The script installs the `lk` CLI under `.livekit-cli/` (gitignored) on macOS or Linux.

### Option B2 — Run inside DO (advanced)

If you add a **one-off Job**, **Worker**, or SSH Droplet that has those env vars, you can run `sync-from-env.sh` there and push with a **deploy key** or **PAT** stored only on DO. That keeps secrets solely on DO but requires extra plumbing; most teams use Option A for the GitHub workflow.

---

## What gets synced

The workflow / script runs `lk agent config --id <AGENT_ID>` and writes **`livekit-cloud/livekit.toml`** (project + Cloud agent id for CLI use).

Some **Console-only** fields (certain Agent Builder UI) may not appear in that file. Prompts for your **Python worker** stay in `agent/agent_worker.py` / env.

## Disable the GitHub workflow

Set repo variable **`LIVEKIT_SYNC_DISABLED`** = `true` if you only sync manually.
