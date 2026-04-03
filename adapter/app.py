from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any
from collections import deque

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MODEL_NAME = "hermes-gui"
DEFAULT_API_KEY = "hermes-local"
DEFAULT_SOURCE = "tool"
DEFAULT_CHAT_TIMEOUT = 600
DEFAULT_COMMAND_TIMEOUT = 180
HEADER_CHAT_ID = "X-OpenWebUI-Chat-Id"
HEADER_MESSAGE_ID = "X-OpenWebUI-Message-Id"
HEADER_USER_ID = "X-OpenWebUI-User-Id"


def _default_hermes_candidates() -> list[Path]:
    home = Path.home()
    candidates = [
        home / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        home / ".hermes" / "hermes-agent" / "venv" / "Scripts" / "hermes.exe",
        home / ".hermes" / "bin" / "hermes",
        home / ".local" / "bin" / "hermes",
    ]
    found = shutil.which("hermes")
    if found:
        candidates.insert(0, Path(found))
    return candidates


def _resolve_hermes_bin() -> str:
    override = os.getenv("HERMES_BIN")
    if override:
        return override
    for candidate in _default_hermes_candidates():
        if candidate.exists():
            return str(candidate)
    return "hermes"


def _resolve_hermes_workdir(hermes_bin: str) -> str:
    override = os.getenv("HERMES_WORKDIR")
    if override:
        return override
    bin_path = Path(hermes_bin).expanduser()
    for parent in [bin_path.parent, *bin_path.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return str(parent)
    default_home = Path.home() / ".hermes" / "hermes-agent"
    return str(default_home if default_home.exists() else Path.cwd())


HERMES_BIN = _resolve_hermes_bin()
HERMES_WORKDIR = _resolve_hermes_workdir(HERMES_BIN)
MODEL_NAME = os.getenv("HERMES_OPENAI_MODEL", DEFAULT_MODEL_NAME)
API_KEY = os.getenv("HERMES_OPENAI_API_KEY", DEFAULT_API_KEY)
HERMES_SOURCE = os.getenv("HERMES_SOURCE", DEFAULT_SOURCE)
CHAT_TIMEOUT_SECONDS = int(os.getenv("HERMES_TIMEOUT_SECONDS", str(DEFAULT_CHAT_TIMEOUT)))
COMMAND_TIMEOUT_SECONDS = int(os.getenv("HERMES_COMMAND_TIMEOUT_SECONDS", str(DEFAULT_COMMAND_TIMEOUT)))
STATE_DIR = Path(os.getenv("HERMES_ADAPTER_STATE_DIR", str(Path(__file__).resolve().parents[1] / "state")))
SESSION_MAP_PATH = STATE_DIR / "session_map.json"
UPDATE_REBUILD_LOG_PATH = STATE_DIR / "update-rebuild.log"
UPDATE_REBUILD_PID_PATH = STATE_DIR / "update-rebuild.pid"
UPDATE_REBUILD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_from_git_and_rebuild.sh"
HERMES_HOME = Path.home() / ".hermes"
HERMES_ENV_PATH = HERMES_HOME / ".env"
HERMES_CONFIG_PATH = HERMES_HOME / "config.yaml"
CHANNEL_DIRECTORY_PATH = HERMES_HOME / "channel_directory.json"
GATEWAY_LOG_PATH = HERMES_HOME / "logs" / "gateway.log"

app = FastAPI(title="Hermes OpenAI Adapter", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATE_LOCK = threading.Lock()


class ChatMessage(BaseModel):
    role: str
    content: Any
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    model: str | None = None
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    user: str | None = None
    metadata: dict[str, Any] | None = None
    chat_id: str | None = None
    session_id: str | None = None
    max_tokens: int | None = Field(default=None, alias="max_completion_tokens")


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "hermes"


class HermesCommandRequest(BaseModel):
    command: str


class HermesEnvUpdateRequest(BaseModel):
    key: str
    value: str


class HermesConfigUpdateRequest(BaseModel):
    path: str
    value: Any


class UpdateRebuildRequest(BaseModel):
    git_pull: bool = True


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _load_session_map() -> dict[str, Any]:
    _ensure_state_dir()
    if not SESSION_MAP_PATH.exists():
        return {}
    try:
        return json.loads(SESSION_MAP_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_session_map(data: dict[str, Any]) -> None:
    _ensure_state_dir()
    SESSION_MAP_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_env_text(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _mask_secret(key: str, value: str) -> str:
    secret_markers = ("TOKEN", "KEY", "PASSWORD", "SECRET", "URL", "ACCOUNT")
    if not value:
        return ""
    if any(marker in key.upper() for marker in secret_markers):
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + ("*" * max(4, len(value) - 8)) + value[-4:]
    return value


def _read_env_payload() -> dict[str, Any]:
    raw = _read_text_file(HERMES_ENV_PATH)
    env = _parse_env_text(raw)
    return {
        "path": str(HERMES_ENV_PATH),
        "raw": raw,
        "values": env,
        "masked": {key: _mask_secret(key, value) for key, value in env.items()},
    }


def _read_config_payload() -> dict[str, Any]:
    raw = _read_text_file(HERMES_CONFIG_PATH)
    parsed = yaml.safe_load(raw) if raw.strip() else {}
    return {
        "path": str(HERMES_CONFIG_PATH),
        "raw": raw,
        "values": parsed or {},
    }


def _set_dotted_path(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    target = data
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise HTTPException(status_code=400, detail="Config path cannot be empty")
    for part in parts[:-1]:
        current = target.get(part)
        if not isinstance(current, dict):
            current = {}
            target[part] = current
        target = current
    target[parts[-1]] = value
    return data


def _write_env_key(key: str, value: str) -> None:
    existing = _read_text_file(HERMES_ENV_PATH)
    lines = existing.splitlines()
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        new_lines.append(f"{key}={value}")
    HERMES_ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    HERMES_ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _write_config_path(path: str, value: Any) -> None:
    payload = _read_config_payload()["values"]
    if not isinstance(payload, dict):
        payload = {}
    updated = _set_dotted_path(payload, path, value)
    HERMES_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    HERMES_CONFIG_PATH.write_text(yaml.safe_dump(updated, sort_keys=False), encoding="utf-8")


def _read_gateway_files_payload() -> dict[str, Any]:
    return {
        "env": _read_env_payload(),
        "config": _read_config_payload(),
        "channel_directory": json.loads(_read_text_file(CHANNEL_DIRECTORY_PATH) or "{}"),
        "gateway_log_tail": "\n".join(_read_text_file(GATEWAY_LOG_PATH).splitlines()[-200:]),
    }


def _session_key(chat_id: str | None, user_id: str | None) -> str | None:
    if not chat_id:
        return None
    return f"{user_id or 'anonymous'}:{chat_id}"


def _get_mapped_session(chat_id: str | None, user_id: str | None) -> str | None:
    key = _session_key(chat_id, user_id)
    if not key:
        return None
    with _STATE_LOCK:
        data = _load_session_map()
        item = data.get(key) or {}
        return item.get("session_id")


def _set_mapped_session(chat_id: str | None, user_id: str | None, session_id: str) -> None:
    key = _session_key(chat_id, user_id)
    if not key:
        return
    with _STATE_LOCK:
        data = _load_session_map()
        data[key] = {
            "session_id": session_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "updated_at": int(time.time()),
        }
        _save_session_map(data)


def _clear_mapped_session(chat_id: str | None, user_id: str | None) -> bool:
    key = _session_key(chat_id, user_id)
    if not key:
        return False
    with _STATE_LOCK:
        data = _load_session_map()
        existed = key in data
        if existed:
            del data[key]
            _save_session_map(data)
        return existed


def _normalize_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                item_type = item.get("type")
                if item_type in {"text", "input_text"}:
                    parts.append(str(item.get("text", "")))
                elif item_type == "image_url":
                    image = item.get("image_url") or {}
                    url = image.get("url", "") if isinstance(image, dict) else str(image)
                    parts.append(f"[image: {url}]")
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _build_prompt(messages: list[ChatMessage]) -> str:
    lines: list[str] = [
        "You are Hermes Agent running behind an OpenAI-compatible adapter for Open WebUI.",
        "Use the conversation history below to answer the final user request naturally.",
        "Keep continuity with the previous assistant replies when relevant.",
        "",
        "Conversation:",
    ]
    for msg in messages:
        role = msg.role.upper()
        content = _normalize_content(msg.content).strip()
        if not content:
            continue
        lines.append(f"{role}{f' ({msg.name})' if msg.name else ''}:")
        lines.append(content)
        lines.append("")
    lines.append("Respond as the assistant to the latest user message.")
    return "\n".join(lines).strip()


def _get_last_user_message(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return _normalize_content(msg.content).strip()
    return ""


def _build_incremental_prompt(messages: list[ChatMessage]) -> str:
    latest_user = _get_last_user_message(messages)
    if latest_user:
        return latest_user
    for msg in reversed(messages):
        content = _normalize_content(msg.content).strip()
        if content:
            return content
    raise HTTPException(status_code=400, detail="No usable message content found")

def _extract_box_content(stdout: str) -> str | None:
    normalized = stdout.replace("\r\n", "\n").replace("\r", "\n")
    matches = re.findall(r"╭─ ⚕ Hermes [^\n]*╮\n(.*?)\n╰[^\n]*╯", normalized, re.DOTALL)
    return matches[-1].strip() if matches else None


def _extract_tool_trace(stdout: str) -> list[str]:
    content = _extract_box_content(stdout)
    source = content.splitlines() if content else stdout.splitlines()
    traces: list[str] = []
    for line in source:
        stripped = line.strip()
        if not stripped:
            continue
        if (
            stripped.startswith("📞 Tool")
            or stripped.startswith("✅ Tool")
            or stripped.startswith("Args:")
            or stripped.startswith("Result:")
        ):
            traces.append(stripped)
    return traces


def _extract_text(stdout: str) -> str:
    content = _extract_box_content(stdout)
    if content:
        filtered: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("📞 Tool") or stripped.startswith("✅ Tool") or stripped.startswith("Result:"):
                continue
            if stripped.startswith("🎉 Conversation completed"):
                continue
            filtered.append(stripped)
        return "\n".join(filtered).strip()

    text = stdout.strip()
    text = re.sub(r"^↻ Resumed session [^\n]+\n\n", "", text)
    text = re.sub(r"^╭─ .*?╮\n", "", text, count=1, flags=re.DOTALL)
    text = re.sub(r"\n*session_id:\s*[^\n]+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _extract_session_id(stdout: str) -> str | None:
    match = re.search(r"session_id:\s*([^\s]+)", stdout)
    return match.group(1) if match else None


def _extract_error_text(stdout: str) -> str:
    normalized = stdout.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.splitlines()]
    filtered: list[str] = []
    skip_prefixes = (
        "Query:",
        "Available Tools",
        "Available Skills",
        "gpt-",
        "Session:",
        "⚠",
    )
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("┌", "│", "└", "╭", "╰")):
            continue
        if stripped.startswith(skip_prefixes):
            continue
        filtered.append(stripped)

    if not filtered:
        return "Hermes chat failed"

    joined = "\n".join(filtered)
    if "NoConsoleScreenBufferError" in joined:
        return (
            "Windows non-console terminal detection failure while launching Hermes chat. "
            "The adapter now forces non-interactive mode for SSH/background sessions; update/restart the adapter on the host and retry.\n\n"
            + "\n".join(filtered[-12:])
        )

    return "\n".join(filtered[-20:])


def _sanitize_stream_line(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    safe_prefixes = (
        "↻ Resumed session",
        "┊",
        "📞 Tool",
        "✅ Tool",
        "Args:",
        "Result:",
    )
    if stripped.startswith(safe_prefixes):
        return text.replace('\r', '')
    return None


def _should_show_trace(prompt: str) -> bool:
    lowered = prompt.lower()
    coding_markers = [
        "```",
        "code",
        "coding",
        "implement",
        "fix",
        "refactor",
        "bug",
        "test",
        "write a file",
        "edit",
        "patch",
        "function",
        "class",
    ]
    return any(marker in lowered for marker in coding_markers)


def _hermes_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CI", "1")
    env.setdefault("NO_COLOR", "1")
    env.setdefault("TERM", "dumb")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PROMPT_TOOLKIT_COLOR_DEPTH", "DEPTH_1_BIT")
    return env


def _run_subprocess(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=HERMES_WORKDIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_hermes_subprocess_env(),
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Hermes binary not found: {HERMES_BIN}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"Command timed out after {timeout}s") from exc


def _build_hermes_chat_cmd(prompt: str, resume_session: str | None = None, force_verbose: bool = False) -> tuple[list[str], bool]:
    show_trace = force_verbose or _should_show_trace(prompt)
    cmd = [HERMES_BIN, "chat", "--source", HERMES_SOURCE]
    cmd.append("-v" if show_trace else "-Q")
    if resume_session:
        cmd.extend(["--resume", resume_session])
    cmd.extend(["-q", prompt])
    return cmd, show_trace


def _run_hermes_chat(prompt: str, resume_session: str | None = None) -> tuple[str, str | None]:
    cmd, show_trace = _build_hermes_chat_cmd(prompt, resume_session)
    result = _run_subprocess(cmd, CHAT_TIMEOUT_SECONDS)
    if result.returncode != 0:
        detail_source = (result.stderr or result.stdout or "Hermes chat failed").strip()
        raise HTTPException(status_code=500, detail=_extract_error_text(detail_source))
    text = _extract_text(result.stdout)
    if not text:
        raise HTTPException(status_code=500, detail="Hermes returned an empty response")
    if show_trace:
        trace_lines = _extract_tool_trace(result.stdout)
        if trace_lines:
            text = "Tool activity:\n" + "\n".join(trace_lines) + "\n\nResult:\n" + text
    return text, _extract_session_id(result.stdout)


def _format_command_result(result: subprocess.CompletedProcess[str], cmd: list[str]) -> str:
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    rendered_cmd = ' '.join(shlex.quote(part) for part in cmd[1:])

    parts = [
        "Command",
        "```bash",
        f"$ {rendered_cmd}",
        "```",
        f"Exit code: `{result.returncode}`",
    ]

    if out:
        parts.extend(
            [
                "",
                "Stdout",
                "```text",
                out,
                "```",
            ]
        )

    if err:
        parts.extend(
            [
                "",
                "Stderr",
                "```text",
                err,
                "```",
            ]
        )

    return "\n".join(parts).strip()

def _slash_help(compact: bool = False) -> str:
    if compact:
        return "\n".join(
            [
                "Hermes commands:",
                "/session  /new  /resume <id>",
                "/gateway status  /sessions list  /skills list",
                "/cron list  /config  /doctor",
                "/hermes <args>",
                "Use /help for the full list.",
            ]
        )

    return """Hermes slash commands in Open WebUI

Adapter-managed:
- /help               Full command help
- /session            Show mapped Hermes session for this Open WebUI chat
- /new                Clear the mapped Hermes session for this chat
- /resume <session>   Attach this Open WebUI chat to an existing Hermes session
- /hermes <args>      Run any non-interactive Hermes CLI command

Common commands:
- /gateway status
- /gateway restart
- /sessions list
- /skills list
- /cron list
- /config
- /doctor
- /memory --help

Notes:
- Normal messages still go through Hermes chat mode.
- Slash commands run Hermes CLI directly.
- Interactive commands may not work from the GUI unless they support non-interactive flags.
- Persistent session mapping uses the Open WebUI chat id when it is forwarded by Open WebUI."""


def _extract_context(request: Request, payload: ChatCompletionRequest) -> dict[str, str | None]:
    metadata = payload.metadata or {}
    chat_id = (
        request.headers.get(HEADER_CHAT_ID)
        or metadata.get("chat_id")
        or payload.chat_id
        or metadata.get("conversation_id")
    )
    message_id = request.headers.get(HEADER_MESSAGE_ID) or metadata.get("message_id")
    user_id = request.headers.get(HEADER_USER_ID) or metadata.get("user_id") or payload.user
    return {"chat_id": chat_id, "message_id": message_id, "user_id": user_id}


def _run_slash_command(command_text: str, context: dict[str, str | None]) -> str:
    if not command_text.startswith("/"):
        raise HTTPException(status_code=400, detail="Slash command must start with '/'")
    try:
        parts = shlex.split(command_text[1:])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid slash command: {exc}") from exc
    if not parts:
        return _slash_help(compact=True)

    command = parts[0]
    args = parts[1:]
    chat_id = context.get("chat_id")
    user_id = context.get("user_id")

    if command in {"help", "commands"}:
        if args and args[0] == "full":
            return _slash_help(compact=False)
        return _slash_help(compact=(command == "commands"))
    if command == "session":
        session_id = _get_mapped_session(chat_id, user_id)
        if session_id:
            return (
                f"Mapped Hermes session for this chat: `{session_id}`\n\n"
                f"GUI model alias: `{MODEL_NAME}`\n"
                "Follow-up turns can reuse this Hermes session, which is better for continuity and usually wastes fewer tokens."
            )
        return (
            "No Hermes session is currently mapped to this Open WebUI chat.\n\n"
            "What this means:\n"
            "- slash commands still work\n"
            "- follow-up chat still works\n"
            "- but until a Hermes session gets mapped, normal follow-ups may need more prompt replay and can cost more tokens\n\n"
            "How to fix it:\n"
            "- send a normal chat message to create/map a Hermes session\n"
            "- or use `/resume <session_id>` to attach an existing Hermes session"
        )
    if command == "new":
        cleared = _clear_mapped_session(chat_id, user_id)
        return "Cleared the Hermes session mapping for this Open WebUI chat." if cleared else "There was no mapped Hermes session for this Open WebUI chat."
    if command == "resume":
        if not args:
            raise HTTPException(status_code=400, detail="Usage: /resume <hermes_session_id>")
        session_id = args[0]
        _set_mapped_session(chat_id, user_id, session_id)
        return f"Mapped this Open WebUI chat to Hermes session: {session_id}"
    if command == "hermes":
        if not args:
            raise HTTPException(status_code=400, detail="Usage: /hermes <args>")
        command = args[0]
        args = args[1:]

    if command == "chat" and not any(flag in args for flag in ["-q", "--query"]):
        raise HTTPException(
            status_code=400,
            detail="Interactive `chat` is not supported through slash passthrough. Use normal chat messages or `/chat -q \"your prompt\"`.",
        )

    known_commands = {
        "chat", "gateway", "sessions", "skills", "cron", "doctor", "config", "memory", "tools", "model",
        "webhook", "pairing", "plugins", "mcp", "status", "insights", "auth", "login", "logout", "setup",
        "whatsapp", "profile", "version", "update", "completion",
    }
    if command not in known_commands:
        return (
            f"Unknown Hermes slash command: /{command}\n\n"
            + _slash_help(compact=True)
        )

    cmd = [HERMES_BIN, command, *args]
    result = _run_subprocess(cmd, COMMAND_TIMEOUT_SECONDS)
    return _format_command_result(result, cmd)


def _tail_lines(path: Path, max_lines: int = 80) -> list[str]:
    if not path.exists():
        return []
    return list(deque(path.read_text(encoding="utf-8", errors="replace").splitlines(), maxlen=max_lines))


def _update_rebuild_status() -> dict[str, Any]:
    pid = None
    running = False
    if UPDATE_REBUILD_PID_PATH.exists():
        try:
            pid = int(UPDATE_REBUILD_PID_PATH.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            running = True
        except Exception:
            running = False
    return {
        "running": running,
        "pid": pid,
        "log_path": str(UPDATE_REBUILD_LOG_PATH),
        "tail": _tail_lines(UPDATE_REBUILD_LOG_PATH),
    }


def _launch_update_rebuild(git_pull: bool = True) -> dict[str, Any]:
    _ensure_state_dir()
    if not UPDATE_REBUILD_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"Missing update script: {UPDATE_REBUILD_SCRIPT}")
    status = _update_rebuild_status()
    if status.get("running"):
        return status

    env = os.environ.copy()
    env["HERMES_GUI_GIT_PULL"] = "1" if git_pull else "0"
    log_handle = open(UPDATE_REBUILD_LOG_PATH, "a", encoding="utf-8")
    process = subprocess.Popen(
        ["bash", str(UPDATE_REBUILD_SCRIPT)],
        cwd=str(Path(__file__).resolve().parents[1]),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    UPDATE_REBUILD_PID_PATH.write_text(str(process.pid), encoding="utf-8")
    return _update_rebuild_status()


def _build_openai_response(text: str, completion_id: str, created: int, model: str) -> JSONResponse:
    return JSONResponse(
        {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )


def _run_hermes_cli_command(command_text: str) -> dict[str, Any]:
    parts = shlex.split(command_text.strip())
    if not parts:
        raise HTTPException(status_code=400, detail="Hermes command cannot be empty")
    if parts[0].startswith("/"):
        parts[0] = parts[0][1:]
    cmd = [HERMES_BIN, *parts]
    result = _run_subprocess(cmd, COMMAND_TIMEOUT_SECONDS)
    return {
        "command": command_text,
        "argv": parts,
        "exit_code": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
        "rendered": _format_command_result(result, cmd),
    }


def _gateway_overview() -> dict[str, Any]:
    gateway = _run_hermes_cli_command("gateway status")
    sessions = _run_hermes_cli_command("sessions list")
    cron = _run_hermes_cli_command("cron list")
    config = _run_hermes_cli_command("config")
    doctor = _run_hermes_cli_command("doctor")
    profiles = _run_hermes_cli_command("profile list")
    auth = _run_hermes_cli_command("auth list")
    pairing = _run_hermes_cli_command("pairing list")
    webhooks = _run_hermes_cli_command("webhook list")
    plugins = _run_hermes_cli_command("plugins list")
    tools = _run_hermes_cli_command("tools list --platform discord")
    with _STATE_LOCK:
        session_map = _load_session_map()
    return {
        "health": {"status": "ok", "model": MODEL_NAME, "hermes_bin": HERMES_BIN, "hermes_workdir": HERMES_WORKDIR},
        "gateway": gateway,
        "sessions": sessions,
        "cron": cron,
        "config": config,
        "doctor": doctor,
        "profiles": profiles,
        "auth": auth,
        "pairing": pairing,
        "webhooks": webhooks,
        "plugins": plugins,
        "tools": tools,
        "session_map": session_map,
        "session_map_count": len(session_map),
        "supported_channels": [
            {"id": "discord", "name": "Discord", "setup_command": "gateway setup", "docs_slug": "discord"},
            {"id": "telegram", "name": "Telegram", "setup_command": "gateway setup", "docs_slug": "telegram"},
            {"id": "slack", "name": "Slack", "setup_command": "gateway setup", "docs_slug": "slack"},
            {"id": "whatsapp", "name": "WhatsApp", "setup_command": "gateway setup", "docs_slug": "whatsapp"},
            {"id": "signal", "name": "Signal", "setup_command": "gateway setup", "docs_slug": "signal"},
            {"id": "matrix", "name": "Matrix", "setup_command": "gateway setup", "docs_slug": "matrix"},
            {"id": "email", "name": "Email", "setup_command": "gateway setup", "docs_slug": "email"},
            {"id": "mattermost", "name": "Mattermost", "setup_command": "gateway setup", "docs_slug": "mattermost"},
            {"id": "open-webui", "name": "Open WebUI", "setup_command": "gateway setup", "docs_slug": "open-webui"},
        ],
    }


def _build_streaming_response(text: str, completion_id: str, created: int, model: str) -> StreamingResponse:
    async def event_stream():
        first = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(first, ensure_ascii=False)}\n\n"

        for piece in _chunk_text_for_stream(text):
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)

        end = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(end, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_chunk(completion_id: str, created: int, model: str, content: str | None = None, *, role: str | None = None, finish_reason: str | None = None) -> str:
    delta: dict[str, Any] = {}
    if role is not None:
        delta["role"] = role
    if content:
        delta["content"] = content
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_text_for_stream(text: str, chunk_size: int = 120) -> list[str]:
    if not text:
        return []
    normalized = text.replace("\r\n", "\n")
    chunks: list[str] = []
    buffer = ""
    for token in re.split(r"(\s+)", normalized):
        if not token:
            continue
        if len(buffer) + len(token) > chunk_size and buffer:
            chunks.append(buffer)
            buffer = token
        else:
            buffer += token
    if buffer:
        chunks.append(buffer)
    return chunks


def _build_live_chat_streaming_response(
    prompt: str,
    resume_session: str | None,
    context: dict[str, str | None],
    completion_id: str,
    created: int,
    model: str,
) -> StreamingResponse:
    async def event_stream():
        yield _sse_chunk(completion_id, created, model, role="assistant")

        cmd, show_trace = _build_hermes_chat_cmd(prompt, resume_session, force_verbose=False)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=HERMES_WORKDIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=_hermes_subprocess_env(),
        )

        session_id: str | None = None
        collected: list[str] = []
        assert process.stdout is not None

        try:
            while True:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=CHAT_TIMEOUT_SECONDS)
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                collected.append(text)
                if not session_id:
                    session_id = _extract_session_id(text)
                if show_trace:
                    clean = _sanitize_stream_line(text)
                    if clean:
                        yield _sse_chunk(completion_id, created, model, content=clean)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            yield _sse_chunk(completion_id, created, model, content="\n[adapter] Hermes request timed out.\n", finish_reason="stop")
            yield "data: [DONE]\n\n"
            return

        return_code = await process.wait()
        full_output = "".join(collected)
        if not session_id:
            session_id = _extract_session_id(full_output)
        if return_code != 0:
            detail = _extract_error_text(full_output.strip() or "Hermes chat failed")
            yield _sse_chunk(completion_id, created, model, content=f"\n[adapter] Error:\n{detail}\n")
        else:
            final_text = _extract_text(full_output)
            if show_trace:
                trace_lines = _extract_tool_trace(full_output)
                if trace_lines:
                    tool_header = "Tool activity:\n" + "\n".join(trace_lines) + "\n\nResult:\n"
                    final_text = tool_header + final_text if final_text else tool_header.rstrip()
            if final_text:
                prefix = "\n\n" if collected and show_trace else ""
                suffix = "\n"
                pieces = _chunk_text_for_stream(prefix + final_text + suffix)
                for piece in pieces:
                    yield _sse_chunk(completion_id, created, model, content=piece)
                    await asyncio.sleep(0.01)
            if session_id and context.get("chat_id"):
                _set_mapped_session(context.get("chat_id"), context.get("user_id"), session_id)

        yield _sse_chunk(completion_id, created, model, finish_reason="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME, "hermes_bin": HERMES_BIN, "hermes_workdir": HERMES_WORKDIR}


@app.get("/v1/models")
def models() -> dict[str, list[dict[str, Any]]]:
    return {"data": [ModelCard(id=MODEL_NAME).model_dump()]}


@app.get("/v1/session-map")
def session_map() -> dict[str, Any]:
    with _STATE_LOCK:
        return {"data": _load_session_map()}


@app.get("/v1/hermes/overview")
def hermes_overview() -> dict[str, Any]:
    return _gateway_overview()


@app.get("/v1/hermes/config-files")
def hermes_config_files() -> dict[str, Any]:
    return _read_gateway_files_payload()


@app.post("/v1/hermes/config-files/env")
def hermes_update_env(payload: HermesEnvUpdateRequest) -> dict[str, Any]:
    if not payload.key.strip():
        raise HTTPException(status_code=400, detail="Env key cannot be empty")
    _write_env_key(payload.key.strip(), str(payload.value))
    return _read_gateway_files_payload()


@app.post("/v1/hermes/config-files/config")
def hermes_update_config(payload: HermesConfigUpdateRequest) -> dict[str, Any]:
    _write_config_path(payload.path.strip(), payload.value)
    return _read_gateway_files_payload()


@app.post("/v1/hermes/command")
def hermes_command(payload: HermesCommandRequest) -> dict[str, Any]:
    normalized = payload.command.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    if normalized.startswith("/"):
        rendered = _run_slash_command(normalized, {"chat_id": None, "message_id": None, "user_id": None})
        return {"command": normalized, "mode": "slash", "rendered": rendered}
    result = _run_hermes_cli_command(normalized)
    result["mode"] = "cli"
    return result


@app.get("/v1/admin/update-rebuild")
def update_rebuild_status() -> dict[str, Any]:
    return _update_rebuild_status()


@app.post("/v1/admin/update-rebuild")
def update_rebuild_start(payload: UpdateRebuildRequest) -> dict[str, Any]:
    return _launch_update_rebuild(git_pull=payload.git_pull)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, payload: ChatCompletionRequest):
    if request.headers.get("Authorization") not in {None, "", f"Bearer {API_KEY}"}:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages is required")

    context = _extract_context(request, payload)
    latest_user_message = _get_last_user_message(payload.messages)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = payload.model or MODEL_NAME

    if latest_user_message.startswith("/"):
        text = await asyncio.to_thread(_run_slash_command, latest_user_message, context)
        return _build_streaming_response(text, completion_id, created, model) if payload.stream else _build_openai_response(text, completion_id, created, model)

    mapped_session = _get_mapped_session(context.get("chat_id"), context.get("user_id"))
    prompt = _build_incremental_prompt(payload.messages) if mapped_session else _build_prompt(payload.messages)

    if payload.stream:
        return _build_live_chat_streaming_response(prompt, mapped_session, context, completion_id, created, model)

    text, session_id = await asyncio.to_thread(_run_hermes_chat, prompt, mapped_session)

    if session_id and context.get("chat_id"):
        _set_mapped_session(context.get("chat_id"), context.get("user_id"), session_id)

    return _build_openai_response(text, completion_id, created, model)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Hermes OpenAI adapter is running",
        "model": MODEL_NAME,
        "session_map": str(SESSION_MAP_PATH),
    }
