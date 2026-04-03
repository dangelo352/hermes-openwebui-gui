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

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.valves.adapter_api_key}",
            "Content-Type": "application/json",
        }

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
            headers=self._headers(),
            json=payload,
            timeout=self.valves.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def hermes_help(self) -> str:
        """Show Hermes slash-command help for the Open WebUI bridge."""
        return self._post_chat("/help")

    def hermes_adapter_health(self) -> str:
        """Check Hermes adapter health and model info."""
        response = requests.get(
            f"{self.valves.adapter_base_url}/health",
            headers={"Authorization": f"Bearer {self.valves.adapter_api_key}"},
            timeout=self.valves.timeout_seconds,
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)

    def hermes_session_map(self) -> str:
        """Show the Hermes adapter's Open WebUI chat-to-session map."""
        response = requests.get(
            f"{self.valves.adapter_base_url}/v1/session-map",
            headers={"Authorization": f"Bearer {self.valves.adapter_api_key}"},
            timeout=self.valves.timeout_seconds,
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)

    def gateway_status(self) -> str:
        """Run `hermes gateway status` through the adapter."""
        return self._post_chat("/gateway status")

    def list_sessions(self) -> str:
        """Run `hermes sessions list` through the adapter."""
        return self._post_chat("/sessions list")

    def list_skills(self) -> str:
        """Run `hermes skills list` through the adapter."""
        return self._post_chat("/skills list")

    def list_cron_jobs(self) -> str:
        """Run `hermes cron list` through the adapter."""
        return self._post_chat("/cron list")

    def run_slash_command(
        self,
        command: str = Field(
            ..., description="A Hermes slash command such as `/gateway status` or `/sessions list`."
        ),
    ) -> str:
        """Run a Hermes slash command through the adapter."""
        command = command.strip()
        if not command.startswith("/"):
            command = f"/{command}"
        return self._post_chat(command)
