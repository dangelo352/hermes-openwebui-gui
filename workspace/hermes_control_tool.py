from __future__ import annotations

import json
from typing import Any

import requests
from pydantic import BaseModel, Field


class Valves(BaseModel):
    adapter_base_url: str = Field(
        default="http://host.docker.internal:8001",
        description="Base URL for the Hermes adapter reachable from Open WebUI.",
    )
    adapter_api_key: str = Field(
        default="hermes-local",
        description="API key expected by the Hermes adapter.",
    )
    timeout_seconds: int = Field(
        default=60,
        description="HTTP timeout for adapter requests.",
    )


class Tools:
    def __init__(self):
        self.valves = Valves()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.valves.adapter_api_key}"}

    def _json_headers(self) -> dict[str, str]:
        return {**self._auth_headers(), "Content-Type": "application/json"}

    def _get(self, path: str) -> str:
        response = requests.get(
            f"{self.valves.adapter_base_url}{path}",
            headers=self._auth_headers(),
            timeout=self.valves.timeout_seconds,
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)

    def _post_chat(self, message: str, metadata: dict[str, Any] | None = None) -> str:
        payload = {
            "model": "hermes-gui",
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        }
        if metadata:
            payload["metadata"] = metadata

        response = requests.post(
            f"{self.valves.adapter_base_url}/v1/chat/completions",
            headers=self._json_headers(),
            json=payload,
            timeout=self.valves.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _normalize_command(self, command: str) -> str:
        command = command.strip()
        if not command:
            raise ValueError("Command cannot be empty")
        if not command.startswith("/"):
            command = f"/{command}"
        return command

    def hermes_help(self) -> str:
        """Show Hermes slash-command help for the Open WebUI bridge."""
        return self._post_chat("/help")

    def hermes_adapter_health(self) -> str:
        """Check Hermes adapter health and model info."""
        return self._get("/health")

    def hermes_session_map(self) -> str:
        """Show the Hermes adapter's Open WebUI chat-to-session map."""
        return self._get("/v1/session-map")

    def gateway_status(self) -> str:
        """Run `hermes gateway status` through the adapter."""
        return self._post_chat("/gateway status")

    def gateway_restart(self) -> str:
        """Run `hermes gateway restart` through the adapter."""
        return self._post_chat("/gateway restart")

    def gateway_start(self) -> str:
        """Run `hermes gateway start` through the adapter."""
        return self._post_chat("/gateway start")

    def gateway_stop(self) -> str:
        """Run `hermes gateway stop` through the adapter."""
        return self._post_chat("/gateway stop")

    def list_sessions(self) -> str:
        """Run `hermes sessions list` through the adapter."""
        return self._post_chat("/sessions list")

    def list_recent_sessions(self) -> str:
        """Alias for listing Hermes sessions."""
        return self._post_chat("/sessions list")

    def list_skills(self) -> str:
        """Run `hermes skills list` through the adapter."""
        return self._post_chat("/skills list")

    def list_cron_jobs(self) -> str:
        """Run `hermes cron list` through the adapter."""
        return self._post_chat("/cron list")

    def doctor(self) -> str:
        """Run `hermes doctor` through the adapter."""
        return self._post_chat("/doctor")

    def config_summary(self) -> str:
        """Run `hermes config` through the adapter."""
        return self._post_chat("/config")

    def tool_summary(self) -> str:
        """Run `hermes tools` through the adapter."""
        return self._post_chat("/tools")

    def memory_help(self) -> str:
        """Run `hermes memory --help` through the adapter."""
        return self._post_chat("/memory --help")

    def gateway_logs_hint(self) -> str:
        """Show quick guidance for reaching gateway logs and status commands."""
        return "\n".join(
            [
                "Useful Hermes gateway commands:",
                "- /gateway status",
                "- /gateway restart",
                "- /gateway stop",
                "- /doctor",
                "- /config",
                "- /sessions list",
                "Use run_slash_command for anything more specific.",
            ]
        )

    def resume_chat_session(
        self,
        session_id: str = Field(..., description="Hermes session id to map to the current Open WebUI chat."),
    ) -> str:
        """Map the current Open WebUI chat to an existing Hermes session id."""
        return self._post_chat(f"/resume {session_id}")

    def clear_chat_session(self) -> str:
        """Clear the mapped Hermes session for the current Open WebUI chat."""
        return self._post_chat("/new")

    def show_chat_session(self) -> str:
        """Show the currently mapped Hermes session for the current Open WebUI chat."""
        return self._post_chat("/session")

    def run_slash_command(
        self,
        command: str = Field(
            ..., description="A Hermes slash command such as `/gateway status` or `/sessions list`."
        ),
    ) -> str:
        """Run any Hermes slash command through the adapter."""
        return self._post_chat(self._normalize_command(command))

    def run_hermes_cli(
        self,
        args: str = Field(
            ..., description="Hermes CLI args without the leading `hermes`, e.g. `gateway status` or `skills list`."
        ),
    ) -> str:
        """Run Hermes CLI args through `/hermes ...` on the adapter."""
        args = args.strip()
        if not args:
            raise ValueError("args cannot be empty")
        return self._post_chat(f"/hermes {args}")

    def command_presets(self) -> str:
        """Show a curated list of useful Hermes commands for Workspace users."""
        return "\n".join(
            [
                "Hermes command presets:",
                "- /gateway status",
                "- /gateway restart",
                "- /sessions list",
                "- /skills list",
                "- /cron list",
                "- /doctor",
                "- /config",
                "- /tools",
                "- /memory --help",
                "- /session",
                "- /new",
                "- /resume <session_id>",
            ]
        )
