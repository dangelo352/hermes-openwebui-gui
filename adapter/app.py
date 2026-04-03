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


def _extract_text(stdout: str) -> str:
    text = stdout.strip()
    text = re.sub(r"^↻ Resumed session [^\n]+\n\n", "", text)
    text = re.sub(r"\n*session_id:\s*[^\n]+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _extract_session_id(stdout: str) -> str | None:
    match = re.search(r"session_id:\s*([^\s]+)", stdout)
    return match.group(1) if match else None


def _run_subprocess(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=HERMES_WORKDIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Hermes binary not found: {HERMES_BIN}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"Command timed out after {timeout}s") from exc


def _run_hermes_chat(prompt: str, resume_session: str | None = None) -> tuple[str, str | None]:
    cmd = [HERMES_BIN, "chat", "-Q", "--source", HERMES_SOURCE]
    if resume_session:
        cmd.extend(["--resume", resume_session])
    cmd.extend(["-q", prompt])
    result = _run_subprocess(cmd, CHAT_TIMEOUT_SECONDS)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Hermes chat failed").strip()
        raise HTTPException(status_code=500, detail=detail)
    text = _extract_text(result.stdout)
    if not text:
        raise HTTPException(status_code=500, detail="Hermes returned an empty response")
    return text, _extract_session_id(result.stdout)


def _format_command_result(result: subprocess.CompletedProcess[str], cmd: list[str]) -> str:
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    parts = [f"$ {' '.join(shlex.quote(part) for part in cmd[1:])}", f"exit_code: {result.returncode}"]
    if out:
        parts.append("stdout:")
        parts.append(out)
    if err:
        parts.append("stderr:")
        parts.append(err)
    return "\n".join(parts).strip()


def _slash_help() -> str:
    return """Hermes slash commands in Open WebUI

Adapter-managed:
- /help
- /session            Show mapped Hermes session for this Open WebUI chat
- /new                Clear the mapped Hermes session for this chat
- /resume <session>   Attach this Open WebUI chat to an existing Hermes session
- /hermes <args>      Run any non-interactive Hermes CLI command

Direct passthrough examples:
- /sessions list
- /sessions browse
- /gateway status
- /gateway restart
- /skills list
- /memory --help
- /config
- /cron list
- /doctor
- /tools

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
        return _slash_help()

    command = parts[0]
    args = parts[1:]
    chat_id = context.get("chat_id")
    user_id = context.get("user_id")

    if command == "help":
        return _slash_help()
    if command == "session":
        session_id = _get_mapped_session(chat_id, user_id)
        return f"Mapped Hermes session for this chat: {session_id}" if session_id else "No Hermes session is currently mapped to this Open WebUI chat."
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

    cmd = [HERMES_BIN, command, *args]
    result = _run_subprocess(cmd, COMMAND_TIMEOUT_SECONDS)
    return _format_command_result(result, cmd)


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

        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

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
    text, session_id = await asyncio.to_thread(_run_hermes_chat, prompt, mapped_session)

    if session_id and context.get("chat_id"):
        _set_mapped_session(context.get("chat_id"), context.get("user_id"), session_id)

    return _build_streaming_response(text, completion_id, created, model) if payload.stream else _build_openai_response(text, completion_id, created, model)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Hermes OpenAI adapter is running",
        "model": MODEL_NAME,
        "session_map": str(SESSION_MAP_PATH),
    }
