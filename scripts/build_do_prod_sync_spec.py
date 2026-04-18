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

def load_env(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def is_localhost_url(value: str | None) -> bool:
    normalized = (value or '').strip().rstrip('/').lower()
    return normalized in {'', 'http://localhost:3000', 'http://127.0.0.1:3000'}


def resolve_public_base_url(spec: dict, env_values: dict[str, str]) -> str | None:
    app_base_url = env_values.get('APP_BASE_URL', '').strip().rstrip('/')
    frontend_url = env_values.get('FRONTEND_URL', '').strip().rstrip('/')

    if not is_localhost_url(app_base_url):
        return app_base_url
    if not is_localhost_url(frontend_url):
        return frontend_url

    for domain in spec.get('domains', []) or []:
        domain_name = (domain.get('domain') or '').strip()
        if domain_name:
            return f'https://{domain_name}'

    default_ingress = (spec.get('default_ingress') or '').strip().rstrip('/')
    if default_ingress:
        return default_ingress

    return None


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
    parser.add_argument('--env-file', default='/root/AIRoadcall/.env')
    args = parser.parse_args()

    spec = yaml.safe_load(Path(args.input).read_text())
    env_values: dict[str, str] = {}
    env_file = Path(args.env_file)
    if env_file.exists():
        env_values = load_env(env_file)

    public_base_url = resolve_public_base_url(spec, env_values)

    backend = next((service for service in spec.get('services', []) if service.get('name') == 'backend'), None)
    if backend is not None:
        backend_envs = backend.setdefault('envs', [])
        if public_base_url:
            upsert_env(backend_envs, 'APP_BASE_URL', public_base_url)
            upsert_env(backend_envs, 'FRONTEND_URL', public_base_url)
        if env_values.get('ADMIN_API_KEY'):
            upsert_env(backend_envs, 'ADMIN_API_KEY', env_values['ADMIN_API_KEY'], secret=True)

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
    worker_admin_api_key = env_values.get(
        'ADMIN_API_KEY',
        next((env.get('value') for env in envs if env.get('key') == 'ADMIN_API_KEY' and env.get('value')), 'placeholder'),
    )
    upsert_env(envs, 'ADMIN_API_KEY', worker_admin_api_key, secret=True)
    upsert_env(envs, 'LIVEKIT_API_KEY', next((env.get('value') for env in envs if env.get('key') == 'LIVEKIT_API_KEY' and env.get('value')), ''), secret=any(env.get('type') == 'SECRET' for env in envs if env.get('key') == 'LIVEKIT_API_KEY'))

    Path(args.output).write_text(yaml.safe_dump(spec, sort_keys=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
