# Self-hosted `roadcall-agent`

This folder contains the single-runtime LiveKit worker for Roadcall.

## Source of truth

- `agent/agent_worker.py` — agent runtime and backend tool wiring
- `agent/prompts/driver_intake.md` — main driver prompt
- `agent/prompts/driver_welcome.txt` — first spoken greeting

For the cleanest setup, route inbound calls directly to `roadcall-agent` and do
not depend on a separate hosted Console agent for production behavior.

## Required environment

Set these values for a new LiveKit project:

```bash
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_AGENT_NAME=roadcall-agent

BACKEND_URL=https://roadcall.ai
ADMIN_API_KEY=...

LIVEKIT_INFERENCE_LLM=openai/gpt-4o-mini
LIVEKIT_INFERENCE_STT=deepgram/nova-2-phonecall
LIVEKIT_INFERENCE_TTS=elevenlabs/eleven_multilingual_v2
LIVEKIT_INFERENCE_TTS_VOICE=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_API_KEY=...
```

The worker currently uses the direct ElevenLabs plugin for speech, so the
`ELEVENLABS_API_KEY` secret must be present anywhere the agent runs.

## Local start

```bash
cd agent
uv sync
uv run python agent_worker.py start
```

## New project bootstrap

After you create the new LiveKit project and inbound SIP trunk, bootstrap the
dispatch rule so inbound calls route to `roadcall-agent` with the committed
prompt metadata:

```bash
cd agent
source .venv/bin/activate

export LIVEKIT_URL=wss://your-project.livekit.cloud
export LIVEKIT_API_KEY=...
export LIVEKIT_API_SECRET=...
export LIVEKIT_AGENT_NAME=roadcall-agent

# choose one of these depending on what you have handy
export LIVEKIT_SIP_TRUNK_ID=ST_...
# or
export LIVEKIT_INBOUND_NUMBER=+1866...

python ../livekit-cloud/bootstrap-roadcall-dispatch.py
```

If you later edit `driver_intake.md` or `driver_welcome.txt`, re-sync the prompt
payload into the dispatch rule:

```bash
export LIVEKIT_DISPATCH_RULE_ID=SDR_...
python ../livekit-cloud/sync-prompts-to-dispatch.py
```

To inspect live rules:

```bash
python ../livekit-cloud/list-dispatch-rules.py
```

## Production note

The DigitalOcean worker must use the same new project values for:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_AGENT_NAME=roadcall-agent`

If those values still point at an old or deleted project, the worker cannot
register and inbound calls will not answer.