#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "workspace" / "hermes_control_tool.py"
OPENWEBUI_BASE = "http://127.0.0.1:8080"
SIGNIN_PATH = "/api/v1/auths/signin"
TOOLS_LIST_PATH = "/api/v1/tools/list"
TOOLS_CREATE_PATH = "/api/v1/tools/create"
TOOLS_UPDATE_TMPL = "/api/v1/tools/id/{id}/update"

TOOL_ID = "hermes_control"
TOOL_NAME = "Hermes Control"
TOOL_META = {
    "description": "Workspace toolkit for Hermes gateway/session controls through the Hermes Open WebUI adapter.",
}


def sign_in() -> str:
    res = requests.post(
        f"{OPENWEBUI_BASE}{SIGNIN_PATH}",
        json={"email": "admin@localhost", "password": "admin"},
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    token = data.get("token")
    if not token:
        raise RuntimeError("Open WebUI signin succeeded but no token was returned")
    return token


def headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def load_tool_content() -> str:
    return TOOL_PATH.read_text()


def main() -> int:
    token = sign_in()
    content = load_tool_content()
    payload = {
        "id": TOOL_ID,
        "name": TOOL_NAME,
        "content": content,
        "meta": TOOL_META,
        "access_grants": [],
    }

    current = requests.get(f"{OPENWEBUI_BASE}{TOOLS_LIST_PATH}", headers=headers(token), timeout=30)
    current.raise_for_status()
    tools = current.json()
    exists = any(tool.get("id") == TOOL_ID for tool in tools)

    if exists:
        res = requests.post(
            f"{OPENWEBUI_BASE}{TOOLS_UPDATE_TMPL.format(id=TOOL_ID)}",
            headers=headers(token),
            json=payload,
            timeout=30,
        )
        res.raise_for_status()
        print(f"Updated Open WebUI workspace tool: {TOOL_ID}")
    else:
        res = requests.post(
            f"{OPENWEBUI_BASE}{TOOLS_CREATE_PATH}",
            headers=headers(token),
            json=payload,
            timeout=30,
        )
        res.raise_for_status()
        print(f"Created Open WebUI workspace tool: {TOOL_ID}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
