#!/usr/bin/env python3
"""Publish a generated report into a Jira issue description."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from project_config import get_publish_settings, load_project_config

DEFAULT_PROJECT_CONFIG_PATH = Path(os.getenv("APPDATA", "")) / "SensoneoAI" / "project_report_config.json"


def get_auth_context() -> tuple[str, str]:
    base_url = os.getenv("JIRA_BASE_URL", "").strip()
    email = os.getenv("JIRA_EMAIL", "").strip()
    token = os.getenv("JIRA_API_TOKEN", "").strip()
    if not base_url or not email or not token:
        raise RuntimeError("Missing JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN environment variables.")

    raw = f"{email}:{token}".encode("utf-8")
    auth_header = "Basic " + base64.b64encode(raw).decode("ascii")
    return base_url.rstrip("/"), auth_header


def text_node(text: str) -> dict:
    return {"type": "text", "text": text}


def paragraph_node(text: str) -> dict:
    return {"type": "paragraph", "content": [text_node(text)]}


def heading_node(level: int, text: str) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [text_node(text)]}


def bullet_list_node(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [{"type": "paragraph", "content": [text_node(item)]}],
            }
            for item in items
        ],
    }


def markdown_to_adf(markdown: str) -> dict:
    blocks: list[dict] = []
    bullet_buffer: list[str] = []

    def flush_bullets() -> None:
        nonlocal bullet_buffer
        if bullet_buffer:
            blocks.append(bullet_list_node(bullet_buffer))
            bullet_buffer = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_bullets()
            continue

        bullet_match = re.match(r"^-\s+(.*)$", stripped)
        if bullet_match:
            bullet_buffer.append(bullet_match.group(1).strip())
            continue

        flush_bullets()

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = min(len(heading_match.group(1)), 6)
            blocks.append(heading_node(level, heading_match.group(2).strip()))
            continue

        blocks.append(paragraph_node(stripped))

    flush_bullets()
    return {"version": 1, "type": "doc", "content": blocks}


def update_issue_description(base_url: str, auth_header: str, issue_key: str, description_doc: dict) -> None:
    payload = json.dumps({"fields": {"description": description_doc}}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/rest/api/3/issue/{issue_key}",
        data=payload,
        headers={
            "Authorization": auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"Unexpected Jira response status: {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a generated PM report to a Jira issue.")
    parser.add_argument("--report-type", required=True, choices=["daily", "weekly", "steering"])
    parser.add_argument("--report-file", type=Path, required=True)
    parser.add_argument("--project-config", type=Path, default=DEFAULT_PROJECT_CONFIG_PATH)
    parser.add_argument("--issue-key", default="")
    args = parser.parse_args()

    report_text = args.report_file.read_text(encoding="utf-8")
    config = load_project_config(args.project_config)
    publish_settings = get_publish_settings(config, args.report_type)

    issue_key = (args.issue_key or str(publish_settings.get("jira_issue_key") or "")).strip()
    enabled = bool(publish_settings.get("enabled")) or bool(args.issue_key)
    mode = str(publish_settings.get("mode") or "overwrite_description").strip()

    if not enabled:
        print(f"SKIP: publishing disabled for {args.report_type}")
        return 0
    if not issue_key:
        raise SystemExit(f"Missing jira_issue_key for {args.report_type} publishing.")
    if mode != "overwrite_description":
        raise SystemExit(f"Unsupported publish mode: {mode}")

    base_url, auth_header = get_auth_context()
    description_doc = markdown_to_adf(report_text)
    try:
        update_issue_description(base_url, auth_header, issue_key, description_doc)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Failed to update Jira issue {issue_key}: HTTP {exc.code} {body}") from exc

    print(f"OK: updated Jira issue {issue_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
