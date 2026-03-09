#!/usr/bin/env python3
"""
Minimal local MCP server for Jira Cloud.

Implements a small subset of the MCP JSON-RPC protocol over stdio:
- initialize
- tools/list
- tools/call
"""

from __future__ import annotations

import base64
import json
import os
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


SERVER_NAME = "local-jira-mcp"
SERVER_VERSION = "0.1.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


def _stderr(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _read_message() -> Optional[Dict[str, Any]]:
    content_length = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.decode("utf-8", errors="replace").strip()
        if line == "":
            break
        if line.lower().startswith("content-length:"):
            _, value = line.split(":", 1)
            content_length = int(value.strip())
    if content_length is None:
        return None
    payload = sys.stdin.buffer.read(content_length)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def _write_message(message: Dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=True).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _error_response(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


def _jira_auth_header() -> Dict[str, str]:
    email = os.getenv("JIRA_EMAIL", "").strip()
    api_token = os.getenv("JIRA_API_TOKEN", "").strip()
    bearer = os.getenv("JIRA_BEARER_TOKEN", "").strip()

    if bearer:
        return {"Authorization": f"Bearer {bearer}"}
    if email and api_token:
        raw = f"{email}:{api_token}".encode("utf-8")
        b64 = base64.b64encode(raw).decode("ascii")
        return {"Authorization": f"Basic {b64}"}
    raise RuntimeError(
        "Missing Jira credentials. Set JIRA_BEARER_TOKEN or JIRA_EMAIL + JIRA_API_TOKEN."
    )


def _jira_base_url() -> str:
    base = os.getenv("JIRA_BASE_URL", "").strip()
    if not base:
        base = "https://sensoneosk.atlassian.net"
    return base.rstrip("/")


def _jira_request(
    method: str,
    path: str,
    query: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base_url = _jira_base_url()
    url = f"{base_url}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)

    headers = {"Accept": "application/json", **_jira_auth_header()}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, method=method.upper(), headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jira HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Jira connection error: {exc}") from exc


def _tool_jira_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    jql = str(arguments.get("jql", "")).strip()
    if not jql:
        raise RuntimeError("`jql` is required.")

    limit = int(arguments.get("limit", 10))
    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50

    response = _jira_request(
        method="GET",
        path="/rest/api/3/search/jql",
        query={
            "jql": jql,
            "maxResults": limit,
            "fields": [
                "summary",
                "status",
                "assignee",
                "priority",
                "issuetype",
                "updated",
                "created",
                "description",
            ],
        },
    )

    issues = []
    for item in response.get("issues", []):
        fields = item.get("fields", {})
        assignee = fields.get("assignee") or {}
        status = fields.get("status") or {}
        priority = fields.get("priority") or {}
        issue_type = fields.get("issuetype") or {}

        issues.append(
            {
                "key": item.get("key"),
                "summary": fields.get("summary"),
                "status": status.get("name"),
                "assignee": assignee.get("displayName"),
                "priority": priority.get("name"),
                "issueType": issue_type.get("name"),
                "updated": fields.get("updated"),
                "created": fields.get("created"),
            }
        )

    return {
        "query": jql,
        "count": len(issues),
        "issues": issues,
    }


def _tool_jira_get_issue(arguments: Dict[str, Any]) -> Dict[str, Any]:
    issue_key = str(arguments.get("issue_key", "")).strip()
    include_comments = bool(arguments.get("include_comments", True))
    comment_limit = int(arguments.get("comment_limit", 20))
    if comment_limit < 1:
        comment_limit = 1
    if comment_limit > 100:
        comment_limit = 100

    if not issue_key:
        raise RuntimeError("`issue_key` is required.")

    issue = _jira_request(
        method="GET",
        path=f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}",
        query={
            "fields": "summary,status,assignee,priority,issuetype,updated,created,description,reporter",
        },
    )

    fields = issue.get("fields", {})
    assignee = fields.get("assignee") or {}
    reporter = fields.get("reporter") or {}
    status = fields.get("status") or {}
    priority = fields.get("priority") or {}
    issue_type = fields.get("issuetype") or {}

    result = {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": status.get("name"),
        "assignee": assignee.get("displayName"),
        "reporter": reporter.get("displayName"),
        "priority": priority.get("name"),
        "issueType": issue_type.get("name"),
        "updated": fields.get("updated"),
        "created": fields.get("created"),
        "description": fields.get("description"),
    }

    if include_comments:
        comments_payload = _jira_request(
            method="GET",
            path=f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/comment",
            query={"maxResults": comment_limit, "orderBy": "-created"},
        )
        comments_out = []
        for c in comments_payload.get("comments", []):
            author = c.get("author") or {}
            comments_out.append(
                {
                    "id": c.get("id"),
                    "author": author.get("displayName"),
                    "created": c.get("created"),
                    "updated": c.get("updated"),
                    "body": c.get("body"),
                }
            )
        result["comments"] = comments_out

    return result


TOOLS = [
    {
        "name": "jira_search",
        "description": "Search Jira issues using JQL and return key fields.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string."},
                "limit": {
                    "type": "integer",
                    "description": "Max results (1-50).",
                    "default": 10,
                },
            },
            "required": ["jql"],
        },
    },
    {
        "name": "jira_get_issue",
        "description": "Get one Jira issue by key, including description and optional comments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Issue key (e.g. RET-444)."},
                "include_comments": {
                    "type": "boolean",
                    "description": "Include comments.",
                    "default": True,
                },
                "comment_limit": {
                    "type": "integer",
                    "description": "Number of latest comments (1-100).",
                    "default": 20,
                },
            },
            "required": ["issue_key"],
        },
    },
]


def _handle_request(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            if name == "jira_search":
                payload = _tool_jira_search(arguments)
            elif name == "jira_get_issue":
                payload = _tool_jira_get_issue(arguments)
            else:
                raise RuntimeError(f"Unknown tool: {name}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=True)}],
                    "structuredContent": payload,
                    "isError": False,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Tool error: {exc}"}],
                    "isError": True,
                },
            }

    if msg_id is not None:
        return _error_response(msg_id, -32601, f"Method not found: {method}")
    return None


def main() -> int:
    _stderr(f"{SERVER_NAME} started")
    while True:
        try:
            msg = _read_message()
            if msg is None:
                return 0
            response = _handle_request(msg)
            if response is not None:
                _write_message(response)
        except Exception:  # noqa: BLE001
            _stderr("Unhandled exception in MCP loop:")
            _stderr(traceback.format_exc())
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

