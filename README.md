Hermes + Open WebUI GUI

What this is
- A local OpenAI-compatible adapter that turns your existing Hermes CLI setup into a backend Open WebUI can talk to.
- It reuses your existing Hermes home directory at /root/.hermes, so your current model/provider config, Discord settings, skills, memories, TTS/STT preferences, and other Hermes behavior stay in place.

What gets reused from Hermes
- ~/.hermes/config.yaml
- ~/.hermes/.env
- ~/.hermes/skills
- ~/.hermes/memory and session storage
- Your current model/provider defaults unless you change them in Hermes itself

What is new now
- Persistent Hermes session mapping keyed by Open WebUI chat id when Open WebUI forwards session headers
- Token-saving resumed chat mode: once a Hermes session is mapped, the adapter sends only the latest user turn instead of rebuilding the entire transcript every time
- Slash command support in the GUI for Hermes CLI passthrough and adapter session controls
- Windows launcher batch file

GitHub repo
- https://github.com/dangelo352/hermes-openwebui-gui

Project layout
- adapter/app.py                        FastAPI OpenAI-compatible wrapper
- requirements.txt                     Adapter dependencies
- .env.openwebui                       Open WebUI environment preconfigured for the adapter
- scripts/install_all.sh               Bootstraps the adapter environment automatically
- scripts/run_openwebui_docker.sh      Starts Open WebUI in Docker Desktop from WSL
- scripts/install_windows_wsl.sh       Syncs the project to the Windows desktop copy
- scripts/start_adapter.sh             Starts the Hermes adapter on port 8001
- scripts/start_openwebui.sh           Starts Open WebUI on port 8080
- windows-start-hermes-openwebui.bat   Windows one-click launcher
- docker-compose.yml                   Optional Docker deployment if Docker is available
- HERMES_OPENWEBUI_SETUP_COMPLETE.md   In-depth setup and architecture notes

How it works
1. Open WebUI sends normal OpenAI-style chat requests to the adapter.
2. Open WebUI can forward user/chat headers to the adapter.
3. The adapter uses the Open WebUI chat id to persist a Hermes session mapping.
4. Normal messages are routed into Hermes chat mode.
5. Slash commands are routed into Hermes CLI mode.
6. Hermes responds using your existing local Hermes configuration.
7. The adapter returns an OpenAI-compatible response back to Open WebUI.

Local setup
1. Bootstrap everything needed for the adapter:
   ./scripts/install_all.sh

2. Start the adapter:
   ./scripts/start_adapter.sh

3. Run Open WebUI in Docker with session headers forwarded:
   ./scripts/run_openwebui_docker.sh

4. Open the GUI:
   http://127.0.0.1:8080

Fastest Windows path
- Double-click:
  windows-start-hermes-openwebui.bat

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

Compatibility notes
- The adapter exposes:
  - GET /v1/models
  - POST /v1/chat/completions
  - GET /v1/session-map
- Non-streaming and basic streaming are supported.
- Conversation state can now persist across GUI turns through session mapping when the Open WebUI chat id is forwarded.

Current defaults
- Adapter URL: http://127.0.0.1:8001/v1
- Open WebUI URL: http://127.0.0.1:8080
- Model name shown in Open WebUI: hermes-gui
- OpenAI API key for Open WebUI: hermes-local

Docker recommendation
- Docker is the better way to run Open WebUI itself on this machine.
- Native Python is fine for the small adapter.
- This mixed setup is the simplest stable option here: adapter in WSL + Open WebUI in Docker Desktop.

Important limitation
- This is an adapter around Hermes CLI, not a native Hermes web app. So tool usage, memory, skills, and settings are preserved through the existing Hermes runtime, but Open WebUI conversations are translated into Hermes prompts instead of using a first-party Hermes HTTP server.

Recommended next improvements
- Add richer multimodal handling for images/files
- Add richer command metadata/help output
- Add auth for the adapter if exposing beyond localhost
- Optionally add frontend slash-command autocomplete directly into a custom Open WebUI fork
