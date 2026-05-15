#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "ghl" / "roadcall-plan-snapshots.json"
DEFAULT_OUTPUT_DIR = ROOT / "ghl" / "generated"
DEFAULT_BASE_URL = "https://services.leadconnectorhq.com"


class SnapshotBuilderError(RuntimeError):
    pass


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data.get("plans"), list):
        raise SnapshotBuilderError("Config must contain a plans array")
    return data


def merge_plan(plans_by_id: dict[str, dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    parent_id = plan.get("inherits")
    if not parent_id:
        return dict(plan)
    if parent_id not in plans_by_id:
        raise SnapshotBuilderError(f"Plan {plan['id']} inherits unknown plan {parent_id}")
    parent = merge_plan(plans_by_id, plans_by_id[parent_id])
    merged = dict(parent)
    for key, value in plan.items():
        if isinstance(value, list):
            merged[key] = [*parent.get(key, []), *value]
        elif isinstance(value, dict) and isinstance(parent.get(key), dict):
            merged[key] = {**parent[key], **value}
        else:
            merged[key] = value
    return merged


def unique_items(items: list[Any], key_name: str | None = None) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for item in items:
        marker = item.get(key_name) if key_name and isinstance(item, dict) else json.dumps(item, sort_keys=True)
        marker = str(marker)
        if marker in seen:
            continue
        seen.add(marker)
        output.append(item)
    return output


def normalize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(plan)
    normalized["tags"] = unique_items(normalized.get("tags", []))
    normalized["customFields"] = unique_items(normalized.get("customFields", []), "key")
    normalized["pipelines"] = unique_items(normalized.get("pipelines", []), "name")
    normalized["workflows"] = unique_items(normalized.get("workflows", []), "name")
    normalized["emailTemplates"] = unique_items(normalized.get("emailTemplates", []), "name")
    normalized["smsTemplates"] = unique_items(normalized.get("smsTemplates", []), "name")
    normalized["calendars"] = unique_items(normalized.get("calendars", []), "name")
    return normalized


def selected_plans(config: dict[str, Any], selected: str) -> list[dict[str, Any]]:
    plans_by_id = {plan["id"]: plan for plan in config["plans"]}
    if selected == "all":
        plans = config["plans"]
    else:
        if selected not in plans_by_id:
            raise SnapshotBuilderError(f"Unknown plan {selected}. Choose one of: {', '.join(plans_by_id)}")
        plans = [plans_by_id[selected]]
    return [normalize_plan(merge_plan(plans_by_id, plan)) for plan in plans]


def write_artifacts(plan: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    plan_dir = output_dir / slugify(plan["id"])
    plan_dir.mkdir(parents=True, exist_ok=True)
    json_path = plan_dir / "snapshot-blueprint.json"
    markdown_path = plan_dir / "build-guide.md"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)
        file.write("\n")

    lines = [
        f"# {plan['snapshotName']}",
        "",
        f"Plan: {plan['displayName']} (${plan['pricing']['monthly']}/mo + ${plan['pricing']['setup']} setup)",
        "",
        plan.get("target", ""),
        "",
        "## Tags",
        *[f"- `{tag}`" for tag in plan.get("tags", [])],
        "",
        "## Custom Fields",
        *[f"- `{field['key']}` — {field['name']} ({field['type']})" for field in plan.get("customFields", [])],
        "",
        "## Pipelines",
    ]
    for pipeline in plan.get("pipelines", []):
        lines.append(f"- {pipeline['name']}: {', '.join(pipeline.get('stages', []))}")
    lines.extend(["", "## Workflows"])
    for workflow in plan.get("workflows", []):
        lines.append(f"- {workflow['name']} — {workflow['trigger']}")
        for action in workflow.get("actions", []):
            lines.append(f"  - {action}")
    lines.extend(["", "## Templates"])
    for template in plan.get("emailTemplates", []):
        lines.append(f"- Email: {template['name']} — {template['subject']}")
    for template in plan.get("smsTemplates", []):
        lines.append(f"- SMS: {template['name']}")
    lines.extend([
        "",
        "## Snapshot Step",
        "Build or apply these assets to a clean source sub-account, verify the checklist, then save that source sub-account as an official GHL Snapshot from the agency UI.",
    ])

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


class LeadConnectorClient:
    def __init__(self, *, api_key: str, base_url: str, location_id: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.location_id = location_id

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}{endpoint}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28",
            },
        )
        try:
            with request.urlopen(http_request, timeout=20) as response:
                text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")[:500]
            raise SnapshotBuilderError(f"LeadConnector HTTP {exc.code} for {endpoint}: {message}") from exc
        return json.loads(text) if text else {"ok": True}

    def create_tag(self, tag: str) -> dict[str, Any]:
        return self.post(f"/locations/{self.location_id}/tags", {"name": tag, "locationId": self.location_id})

    def create_custom_field(self, field: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "locationId": self.location_id,
            "name": field["name"],
            "fieldKey": field["key"],
            "dataType": field["type"],
        }
        if field.get("options"):
            payload["options"] = field["options"]
        return self.post(f"/locations/{self.location_id}/customFields", payload)


def apply_supported_assets(plan: dict[str, Any], client: LeadConnectorClient) -> None:
    for tag in plan.get("tags", []):
        print(f"Applying tag: {tag}")
        client.create_tag(tag)
    for field in plan.get("customFields", []):
        print(f"Applying custom field: {field['key']}")
        client.create_custom_field(field)


def print_summary(plan: dict[str, Any], *, apply: bool) -> None:
    print(f"\n{plan['snapshotName']}")
    print(f"  Plan: {plan['displayName']} (${plan['pricing']['monthly']}/mo + ${plan['pricing']['setup']} setup)")
    print(f"  Tags: {len(plan.get('tags', []))}")
    print(f"  Custom fields: {len(plan.get('customFields', []))}")
    print(f"  Pipelines: {len(plan.get('pipelines', []))}")
    print(f"  Workflows: {len(plan.get('workflows', []))}")
    print(f"  Email templates: {len(plan.get('emailTemplates', []))}")
    print(f"  SMS templates: {len(plan.get('smsTemplates', []))}")
    print(f"  Mode: {'apply supported assets' if apply else 'dry run'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Roadcall GHL plan snapshot blueprints.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--plan", default="all", help="Plan id to build, or all")
    parser.add_argument("--apply", action="store_true", help="Apply supported assets to a GHL location. Dry run by default.")
    parser.add_argument("--location-id", default=os.getenv("GHL_LOCATION_ID", ""), help="GHL location/sub-account id. Defaults to GHL_LOCATION_ID.")
    parser.add_argument("--api-key-env", default="GHL_API_KEY", help="Environment variable containing the GHL API key.")
    parser.add_argument("--base-url", default=os.getenv("GHL_BASE_URL", DEFAULT_BASE_URL))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        plans = selected_plans(config, args.plan)
        client: LeadConnectorClient | None = None
        if args.apply:
            api_key = os.getenv(args.api_key_env, "")
            if not api_key:
                raise SnapshotBuilderError(f"--apply requires {args.api_key_env} to be set")
            if not args.location_id:
                raise SnapshotBuilderError("--apply requires --location-id or GHL_LOCATION_ID")
            client = LeadConnectorClient(api_key=api_key, base_url=args.base_url, location_id=args.location_id)

        for plan in plans:
            print_summary(plan, apply=args.apply)
            json_path, markdown_path = write_artifacts(plan, args.output_dir)
            print(f"  Wrote: {json_path.relative_to(ROOT)}")
            print(f"  Wrote: {markdown_path.relative_to(ROOT)}")
            if client:
                apply_supported_assets(plan, client)
                print("  Applied supported assets: tags and custom fields")

        print("\nOfficial GHL snapshot creation: configure a clean source sub-account with these assets, then save it as a Snapshot in the GHL agency UI.")
        return 0
    except SnapshotBuilderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())