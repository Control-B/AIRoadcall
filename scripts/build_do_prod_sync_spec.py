#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import yaml


CRITICAL_WORKER_ENVS = {
    'LIVEKIT_AGENT_NAME': 'roadcall-agent',
    'LIVEKIT_DRIVER_PROMPT_SOURCE': 'repo',
    'AGENT_ENABLE_EXTENDED_DRIVER_TOOLS': 'false',
    'AGENT_NUM_IDLE_PROCESSES': '2',
    'LIVEKIT_INFERENCE_TTS': 'elevenlabs/eleven_multilingual_v2',
    'LIVEKIT_INFERENCE_TTS_VOICE': 'nf4MCGNSdM0hxM95ZBQR',
    'LIVEKIT_INFERENCE_STT': 'deepgram/nova-3-general',
    'ELEVENLABS_VOICE_ID': 'nf4MCGNSdM0hxM95ZBQR',
    'BACKEND_URL': '${backend.PRIVATE_URL}',
}


def upsert_env(envs: list[dict], key: str, value: str, scope: str = 'RUN_TIME', secret: bool = False) -> None:
    for env in envs:
        if env.get('key') == key:
            env['value'] = value
            env['scope'] = scope
            if secret:
                env['type'] = 'SECRET'
            return
    entry = {'key': key, 'value': value, 'scope': scope}
    if secret:
        entry['type'] = 'SECRET'
    envs.append(entry)


def main() -> int:
    parser = argparse.ArgumentParser(description='Normalize a live DO production app spec to the stable Roadcall worker config')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    spec = yaml.safe_load(Path(args.input).read_text())
    workers = spec.get('workers') or []
    if not workers:
        raise SystemExit('No workers found in app spec')

    worker = workers[0]
    worker['name'] = 'livekit-agent'
    worker['dockerfile_path'] = 'Dockerfile'
    worker['source_dir'] = 'agent'
    envs = worker.setdefault('envs', [])
    for key, value in CRITICAL_WORKER_ENVS.items():
        upsert_env(envs, key, value)
    upsert_env(envs, 'ADMIN_API_KEY', next((env.get('value') for env in envs if env.get('key') == 'ADMIN_API_KEY' and env.get('value')), 'placeholder'), secret=True)
    upsert_env(envs, 'LIVEKIT_API_KEY', next((env.get('value') for env in envs if env.get('key') == 'LIVEKIT_API_KEY' and env.get('value')), ''), secret=any(env.get('type') == 'SECRET' for env in envs if env.get('key') == 'LIVEKIT_API_KEY'))

    Path(args.output).write_text(yaml.safe_dump(spec, sort_keys=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
