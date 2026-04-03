from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


DEFAULT_HERMES_BIN = "/root/.hermes/hermes-agent/venv/bin/hermes"
DEFAULT_HERMES_WORKDIR = "/root/.hermes/hermes-agent"
DEFAULT_MODEL_NAME = "hermes-gui"

HERMS_BIN = os.getenv("HERMES_BIN", DEFAULT_HERMES_BIN)
HERMES_WORKDIR = os.getenv("HERMES_WORKDIR", DEFAULT_HERMES_WORKDIR)
MODEL_NAME = os.getenv("HERMES_OPENAI_MODEL", DEFAULT_MODEL_NAME)
API_KEY = os.getenv("HERMES_OPENAI_API_KEY", "hermes-local")
DEFAULT_SOURCE = os.getenv("HERMES_SOURCE", "tool")

app = FastAPI(title="Hermes OpenAI Adapter", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: Any
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, alias="max_completion_tokens")


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "hermes"


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
                if item_type == "text":
                    parts.append(str(item.get("text", "")))
                elif item_type == "input_text":
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
        if msg.name:
            lines.append(f"{role} ({msg.name}):")
        else:
            lines.append(f"{role}:")
        lines.append(content)
        lines.append("")
    lines.append("Respond as the assistant to the latest user message.")
    return "\n".join(lines).strip()


def _extract_text(stdout: str) -> str:
    text = stdout.strip()
    text = re.sub(r"^╭─ .*?╮\n", "", text, count=1, flags=re.DOTALL)
    text = re.sub(r"\n*session_id:\s*[^\n]+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _run_hermes(prompt: str) -> str:
    cmd = [HERMS_BIN, "chat", "-Q", "--source", DEFAULT_SOURCE, "-q", prompt]
    try:
        result = subprocess.run(
            cmd,
            cwd=HERMES_WORKDIR,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("HERMES_TIMEOUT_SECONDS", "600")),
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Hermes binary not found: {HERMS_BIN}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Hermes request timed out") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Hermes command failed").strip()
        raise HTTPException(status_code=500, detail=detail)

    text = _extract_text(result.stdout)
    if not text:
        raise HTTPException(status_code=500, detail="Hermes returned an empty response")
    return text


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.get("/v1/models")
def models() -> dict[str, list[dict[str, Any]]]:
    return {"data": [ModelCard(id=MODEL_NAME).model_dump()]}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages is required")

    prompt = _build_prompt(request.messages)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = request.model or MODEL_NAME

    text = await asyncio.to_thread(_run_hermes, prompt)

    if request.stream:
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

    return JSONResponse(
        {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hermes OpenAI adapter is running", "model": MODEL_NAME}
