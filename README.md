Hermes + Open WebUI GUI

What this is
- A cross-platform launcher for running Open WebUI against your existing Hermes CLI install.
- Works on macOS, Windows, and Linux from one repo.
- One command or double-click starts the adapter, boots Docker if needed, launches Open WebUI, and opens the browser.

What gets reused from Hermes
- ~/.hermes/config.yaml
- ~/.hermes/.env
- ~/.hermes/skills
- ~/.hermes/memory and session storage
- Your current model/provider defaults unless you change them in Hermes itself

What is new now
- Cross-platform Python launcher: launcher.py
- Windows double-click starter: start-hermes-openwebui.bat
- Linux shell starter: start-hermes-openwebui.sh
- macOS double-click starter: start-hermes-openwebui.command
- Windows easy update/rebuild starter: update-webui-easy.bat
- Windows compatibility update/rebuild starter: update-hermes-openwebui.bat
- Linux update/rebuild starter: update-hermes-openwebui.sh
- macOS update/rebuild starter: update-hermes-openwebui.command
- Automatic adapter venv bootstrap and dependency install
- Automatic Hermes CLI path detection on macOS, Windows, Linux, and WSL
- Automatic Docker Desktop startup on macOS, Windows, and WSL when available
- Open WebUI container startup with host routing that also works on Linux
- Persistent Hermes session mapping keyed by Open WebUI chat id
- Slash command support in the GUI for Hermes CLI passthrough and adapter session controls
- Patched Open WebUI frontend image is now the default so `/` opens a Hermes command overlay instead of the stock weird slash token UX
- Automatic Open WebUI source clone/patch/build flow for the patched GUI image

GitHub repo
- https://github.com/dangelo352/hermes-openwebui-gui

High-context maintainer guide
- MAINTAINER_GUIDE.md

Project layout
- adapter/app.py                                   FastAPI OpenAI-compatible wrapper
- workspace/hermes_control_tool.py                 Hermes Workspace tool for Open WebUI
- openwebui-patches/...                            Source patches for Open WebUI chat slash overlay UI
- launcher.py                                      Cross-platform all-in-one launcher
- requirements.txt                                 Adapter dependencies
- start-hermes-openwebui.bat                       Windows one-click launcher
- start-hermes-openwebui.sh                        Linux shell launcher
- start-hermes-openwebui.command                   macOS double-click launcher
- update-webui-easy.bat                            Windows easy git-pull/rebuild/start launcher
- update-hermes-openwebui.bat                      Windows compatibility git-pull/rebuild/start launcher
- update-hermes-openwebui.sh                       Linux git-pull/rebuild/start launcher
- update-hermes-openwebui.command                  macOS git-pull/rebuild/start launcher
- scripts/install_openwebui_workspace_assets.py    Creates/updates the Hermes Control tool in Workspace
- scripts/run_openwebui_docker.sh                  Starts Open WebUI and installs workspace assets
- scripts/apply_openwebui_chat_patches.sh          Applies chat UI patches to an Open WebUI source checkout
- scripts/apply_openwebui_chat_patches.bat         Windows helper for applying chat UI patches
- scripts/                                         Helper scripts and compatibility utilities
- docker-compose.yml                               Optional Docker deployment
- HERMES_OPENWEBUI_SETUP_COMPLETE.md               Original setup notes
- OPENCLAW_FRONTEND_GATEWAY_PLAN.md                OpenClaw-inspired UX notes

Quick start
- Windows: double-click start-hermes-openwebui.bat
- Linux: run ./start-hermes-openwebui.sh
- macOS: double-click start-hermes-openwebui.command
- CLI on any OS: python launcher.py start

Update after pulling latest changes
- Windows: double-click update-webui-easy.bat
- Windows compatibility launcher: double-click update-hermes-openwebui.bat
- Linux: run ./update-hermes-openwebui.sh
- macOS: double-click update-hermes-openwebui.command
- CLI on any OS: python launcher.py update

Repair / rebuild everything after updates
- Windows: double-click fix-hermes-openwebui.bat
- Windows compatibility script: scripts\fix_all.bat
- macOS/Linux: ./scripts/fix_all.sh
- CLI: python launcher.py update --skip-git-pull

What the launcher does automatically
1. Creates .venv if needed
2. Installs/updates adapter dependencies
3. Detects your Hermes CLI path automatically
4. Builds/uses the patched Open WebUI image when enabled
5. Starts the Hermes adapter on port 8001
6. Starts Docker Desktop when possible
7. Runs Open WebUI in Docker on port 8080
8. Installs/updates the Hermes Control workspace tool in Open WebUI
9. Opens http://127.0.0.1:8080

Requirements
- Python 3
- Docker Desktop or Docker Engine
- Hermes CLI already installed locally

Useful commands
- python launcher.py prepare
- python launcher.py start
- python launcher.py stop
- python launcher.py restart
- python launcher.py status
- python launcher.py start-adapter
- python launcher.py start-webui
- python launcher.py install-workspace-assets
- python launcher.py build-webui
- python launcher.py rebuild-webui
- python launcher.py update
- python launcher.py update --skip-git-pull
- python launcher.py start --no-browser

Environment overrides
- HERMES_BIN                    Explicit path to the Hermes executable
- HERMES_WORKDIR                Explicit Hermes working directory
- HERMES_OPENAI_MODEL           Model name shown in Open WebUI, default: hermes-gui
- HERMES_OPENAI_API_KEY         API key used by Open WebUI, default: hermes-local
- HERMES_ADAPTER_PORT           Adapter port, default: 8001
- HERMES_WEBUI_PORT             Open WebUI port, default: 8080
- HERMES_WEBUI_CONTAINER        Docker container name, default: hermes-open-webui
- HERMES_WEBUI_IMAGE            Open WebUI image, default: ghcr.io/open-webui/open-webui:main

Compatibility notes
- Adapter endpoints:
  - GET /health
  - GET /v1/models
  - POST /v1/chat/completions
  - GET /v1/session-map
- Non-streaming and basic streaming are supported.
- Conversation state persists across GUI turns through session mapping when Open WebUI forwards the chat id.
- On Linux, the launcher automatically adds host.docker.internal -> host-gateway for the container.
- On Windows, the adapter now forces Hermes subprocesses into a more non-interactive/CI-style mode to avoid prompt_toolkit console errors in launcher-driven or background runs.

Windows troubleshooting
- Preferred updater/rebuilder: `update-webui-easy.bat`
- Preferred repair entrypoint: `fix-hermes-openwebui.bat`
- If a user sees `prompt_toolkit.output.win32.NoConsoleScreenBufferError`, they are hitting a non-console Windows execution path. Update to the latest repo and re-run one of the preferred batch files above.

Slash commands in Open WebUI
- /help
- /session
- /new
- /resume <session_id>
- /hermes <args>
- /sessions list
- /gateway status
- /skills list
- and many other non-interactive Hermes CLI commands

Workspace integration
- Open WebUI Workspace > Tools will automatically get a tool named `Hermes Control`
- That tool gives you clickable/LLM-callable helpers for:
  - adapter health
  - session map
  - gateway status / restart / start / stop
  - sessions list
  - skills list
  - cron list
  - config summary
  - doctor
  - tool summary
  - memory help
  - session mapping actions
  - arbitrary Hermes slash-command execution
  - arbitrary Hermes CLI passthrough via `/hermes ...`

Chat UI integration
- The repo now also contains source patches for Open WebUI chat input and response rendering
- These patches replace the default `/` prompt menu with a Hermes command overlay
- They also add a custom coding-response block for Hermes tool activity traces
- By default the launcher now builds and runs a patched image named `hermes-openwebui-patched:<ref>`
- Manual patching is still available if you want to work on an Open WebUI source checkout directly:
  - macOS/Linux: `./scripts/apply_openwebui_chat_patches.sh /path/to/open-webui`
  - Windows: `scripts\apply_openwebui_chat_patches.bat C:\path\to\open-webui`

Notes
- "No setup needed" here means the launcher bootstraps the adapter environment automatically from this folder.
- Hermes itself still needs to exist on the machine because this GUI is an adapter around your real Hermes runtime.
- If Hermes is in a non-standard location, set HERMES_BIN and optionally HERMES_WORKDIR.
