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

Project layout
- adapter/app.py                FastAPI OpenAI-compatible wrapper
- requirements.txt             Adapter dependencies
- .env.openwebui               Open WebUI environment preconfigured for the adapter
- scripts/start_adapter.sh     Starts the Hermes adapter on port 8001
- scripts/start_openwebui.sh   Starts Open WebUI on port 8080
- docker-compose.yml           Optional Docker deployment if Docker is available

How it works
1. Open WebUI sends normal OpenAI-style chat requests to the adapter.
2. The adapter converts the message history into a prompt.
3. The adapter calls Hermes CLI in quiet mode.
4. Hermes responds using your existing local Hermes configuration.
5. The adapter returns an OpenAI-compatible response back to Open WebUI.

Local setup
1. Create the adapter venv and install deps:
   uv venv --python 3.11 .venv
   . .venv/bin/activate
   uv pip install -r requirements.txt

2. Create an Open WebUI venv and install Open WebUI:
   uv venv --python 3.11 .open-webui-venv
   . .open-webui-venv/bin/activate
   uv pip install open-webui

3. Start the adapter:
   ./scripts/start_adapter.sh

4. In a second terminal, start Open WebUI:
   ./scripts/start_openwebui.sh

5. Open the GUI:
   http://127.0.0.1:8080

Compatibility notes
- The adapter exposes:
  - GET /v1/models
  - POST /v1/chat/completions
- Non-streaming and basic streaming are supported.
- Conversation state is passed from Open WebUI on each request, then Hermes is invoked with your full message history.

Current defaults
- Adapter URL: http://127.0.0.1:8001/v1
- Open WebUI URL: http://127.0.0.1:8080
- Model name shown in Open WebUI: hermes-gui
- OpenAI API key for Open WebUI: hermes-local

Docker option
- If Docker becomes available, run:
  docker compose up
- Open WebUI will be on http://127.0.0.1:3000

Important limitation
- This is an adapter around Hermes CLI, not a native Hermes web app. So tool usage, memory, skills, and settings are preserved through the existing Hermes runtime, but Open WebUI conversations are translated into Hermes prompts instead of using a first-party Hermes HTTP server.

Recommended next improvements
- Add request authentication to the adapter
- Add better session mapping between Open WebUI chat IDs and Hermes session IDs
- Add richer multimodal handling for images/files
- Add explicit model switching support
