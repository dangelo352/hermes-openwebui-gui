# Hermes + Open WebUI Setup Complete Guide

## Short answer to the Docker question

Yes: Docker is the better place to run Open WebUI on this machine.

Best setup here:
- Open WebUI in Docker Desktop on Windows
- Hermes adapter in WSL/Linux Python
- Hermes itself stays in your existing WSL Hermes install

Why this is better:
- Open WebUI is a big app with a lot of dependencies and startup behavior, and Docker keeps that isolated and repeatable.
- The Hermes adapter is small and simple, so keeping it native in WSL is easier and faster.
- This mixed setup gives you the easiest maintenance and the least dependency pain.

In one line:
- Docker is better for Open WebUI.
- Native WSL is better for the small Hermes bridge.

## What this project is

This project creates a GUI for your existing Hermes setup by placing Open WebUI in front of Hermes through a small OpenAI-compatible adapter.

Instead of replacing Hermes, it reuses your real Hermes installation and current settings.

Architecture:
- Open WebUI -> Hermes adapter -> Hermes CLI -> your real Hermes config

## What was built

A project folder was created at:
- `/root/hermes-openwebui-gui`

A Windows-accessible copy was also created at:
- `C:\Users\DAngelo\Desktop\hermes-openwebui-gui`

That project contains:
- `adapter/app.py`
  - FastAPI app that exposes OpenAI-compatible endpoints for Open WebUI
- `requirements.txt`
  - Python dependencies for the adapter
- `workspace/hermes_control_tool.py`
  - Workspace > Tools asset that exposes Hermes control actions inside Open WebUI
- `.env.openwebui`
  - Open WebUI environment values pointing it to the adapter
- `scripts/install_all.sh`
  - Bootstraps the adapter environment automatically
- `scripts/run_openwebui_docker.sh`
  - Starts Open WebUI in Docker Desktop from WSL
- `scripts/install_windows_wsl.sh`
  - Syncs the repo to the Windows desktop copy
- `scripts/start_adapter.sh`
  - Starts the adapter locally on port 8001
- `scripts/start_openwebui.sh`
  - Starts Open WebUI from a Python venv if desired
- `docker-compose.yml`
  - Optional Docker deployment for adapter + Open WebUI
- `windows-start-hermes-openwebui.bat`
  - Windows one-click launcher for Docker Desktop + adapter + Open WebUI container
- `README.md`
  - Short project overview
- `.gitignore`
  - Prevents venv/data/cache/state junk from being committed
- `hermes-openwebui-gui.bundle`
  - Portable git bundle of the repository
- `HERMES_OPENWEBUI_SETUP_COMPLETE.md`
  - This full write-up

## What Hermes settings are reused

The bridge uses your existing Hermes installation and existing Hermes home directory.

Reused Hermes paths:
- `/root/.hermes/config.yaml`
- `/root/.hermes/.env`
- `/root/.hermes/skills`
- `/root/.hermes/sessions`
- `/root/.hermes` memory/profile/config state generally

That means this GUI is using your existing Hermes behavior, including things like:
- default model and provider settings
- tool configuration
- skills
- memory
- user profile behavior
- messaging/gateway-related Hermes setup that already exists in that environment

## What the adapter does

The adapter is a small FastAPI service that exposes these endpoints:
- `GET /health`
- `GET /v1/models`
- `GET /v1/session-map`
- `POST /v1/chat/completions`

### Adapter behavior

1. Open WebUI sends a normal OpenAI-style chat request.
2. The adapter reads the message list.
3. It detects Open WebUI session/user headers when available.
4. For normal messages, it converts the conversation history into a plain-text prompt.
5. It calls Hermes CLI in quiet mode.
6. It captures the Hermes response and Hermes session id.
7. It stores a mapping between the Open WebUI chat id and the Hermes session id.
8. It returns an OpenAI-compatible response back to Open WebUI.

## Persistent Hermes session mapping

This was added so Open WebUI chats can continue using the same Hermes session.

### Why this matters

Without mapping:
- every request is just prompt reconstruction
- continuity is approximate
- token usage is higher because the full transcript keeps getting rebuilt

With mapping:
- the adapter can resume the same Hermes session for the same Open WebUI chat
- chat continuity feels much more like real Hermes
- after the first mapped turn, the adapter can send only the newest user turn instead of the whole transcript, which keeps token overhead much lower

### How it works

Open WebUI can forward these headers when enabled:
- `X-OpenWebUI-Chat-Id`
- `X-OpenWebUI-User-Id`
- `X-OpenWebUI-Message-Id`

The adapter reads those and stores session mappings in:
- `/root/hermes-openwebui-gui/state/session_map.json`

Mapping key shape:
- `user_id:chat_id`

### Open WebUI setting needed for this

Open WebUI must run with:
- `ENABLE_FORWARD_USER_INFO_HEADERS=True`

That was added to the environment/config for this bridge.

## Slash command support added

Slash command support was added inside the adapter.

### Adapter-managed slash commands
- `/help`
- `/session`
- `/new`
- `/resume <hermes_session_id>`
- `/hermes <args>`

### Hermes CLI passthrough examples
- `/sessions list`
- `/gateway status`
- `/gateway restart`
- `/skills list`
- `/cron list`
- `/doctor`
- `/tools`
- `/config`

### Important note on slash commands

The adapter supports many non-interactive Hermes CLI commands through slash passthrough.

But not every command can be fully guaranteed in a GUI bridge because some Hermes commands are interactive by nature.

Examples of commands that may need special handling or non-interactive flags:
- interactive `chat`
- setup/login flows
- editor-driven commands
- anything expecting a TTY session

So the practical rule is:
- normal GUI messages -> Hermes chat mode
- slash commands -> Hermes CLI passthrough when non-interactive

## Hermes command called by the adapter for chat

The adapter runs Hermes chat like this:
- `/root/.hermes/hermes-agent/venv/bin/hermes chat -Q --source tool -q "...prompt..."`

If a session is already mapped, it resumes that Hermes session by adding:
- `--resume <session_id>`

That is why it is really using your Hermes.

## Workspace integration added

A Workspace-compatible integration was added without needing a custom sidebar.

Open WebUI now gets a Workspace > Tools asset named:
- `Hermes Control`

That tool is installed automatically after Open WebUI starts and gives you Workspace-visible Hermes controls for:
- adapter health
- session map
- gateway status
- gateway restart / start / stop
- sessions list
- skills list
- cron list
- config summary
- doctor
- tool summary
- memory help
- current session mapping actions
- arbitrary Hermes slash-command execution
- arbitrary Hermes CLI passthrough

This follows your preference to keep extra functionality under existing Open WebUI workspace areas instead of building a whole custom sidebar.

## Current runtime status

### Hermes adapter
Running locally at:
- `http://127.0.0.1:8001`

Health check:
- `http://127.0.0.1:8001/health`

### Open WebUI GUI
Running in Docker on Windows Docker Desktop and exposed locally at:
- `http://127.0.0.1:8080`

Container name:
- `hermes-open-webui`

## How Open WebUI was started

Docker Desktop on Windows was launched from WSL using:
- `cmd.exe /c start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"`

Then Open WebUI was started in Docker using:
- `cmd.exe /c docker run -d -p 8080:8080 -e ENABLE_OPENAI_API=True -e ENABLE_FORWARD_USER_INFO_HEADERS=True -e OPENAI_API_BASE_URL=http://host.docker.internal:8001/v1 -e OPENAI_API_KEY=hermes-local -e WEBUI_AUTH=False -v hermes-open-webui-data:/app/backend/data --name hermes-open-webui --restart unless-stopped ghcr.io/open-webui/open-webui:main`

Important detail:
- `host.docker.internal:8001` lets the Windows Docker container talk back to the Hermes adapter running inside WSL/Linux.

## How the adapter was started

A Python venv was created for the adapter and dependencies installed.

Commands used:
- `uv venv --python 3.11 .venv`
- `. .venv/bin/activate`
- `uv pip install -r requirements.txt`

Then the adapter was started with:
- `./scripts/start_adapter.sh`

That script runs uvicorn and serves `adapter.app:app` on port 8001.

## Windows launcher added

A one-click Windows batch launcher was created:
- `C:\Users\DAngelo\Desktop\hermes-openwebui-gui\windows-start-hermes-openwebui.bat`

What it does:
1. Starts Docker Desktop
2. Waits for Docker to be ready
3. Starts the Hermes adapter inside WSL
4. Recreates the Open WebUI container with the correct environment variables
5. Leaves you with the GUI available at `http://127.0.0.1:8080`

## Git repository that was created

A git repository was initialized in:
- `/root/hermes-openwebui-gui`

Current branch:
- `main`

Initial commit:
- `2f113e47b8cf7a45ebfddd59b9f7c46cb40df7af`

Portable git bundle:
- `/root/hermes-openwebui-gui/hermes-openwebui-gui.bundle`

## GitHub status

The project is now in a real GitHub repo:
- https://github.com/dangelo352/hermes-openwebui-gui

Local repo still exists at:
- `/root/hermes-openwebui-gui`

## Windows copy created

The project was copied to your Windows filesystem so you can access it directly from your main PC.

Windows-accessible folder:
- `C:\Users\DAngelo\Desktop\hermes-openwebui-gui`

This folder is the one you can open in Windows Explorer, copy, edit, zip, back up, or push to GitHub from your normal Windows apps.

## Important limitations of the current bridge

This is a bridge, not a native full Hermes web server.

So right now:
- Open WebUI works as the GUI
- Hermes still provides the intelligence/config/behavior
- but not every Hermes-native command or UI concept is exposed directly in Open WebUI

### What works well now
- GUI access through browser
- OpenAI-compatible chat endpoint
- reuse of Hermes config and environment
- basic streaming
- persistent session mapping using Open WebUI chat ids when forwarded
- slash command passthrough for many Hermes CLI commands

### What is not fully implemented yet
- true first-party Hermes web UI semantics
- native display of all Hermes tool calls/events inside the UI
- rich file/image/tool bridging beyond basic text conversion
- guaranteed support for every interactive Hermes CLI command in GUI form
- first-class control for switching Hermes runtime settings from the GUI itself

## Best next upgrades if you want it to feel even more like full Hermes

### 1. Richer command registry
Add explicit pretty handling for more Hermes commands instead of generic passthrough text.

### 2. Better file/image support
Map Open WebUI uploads into Hermes file/tool workflows more directly.

### 3. Auth/security
Right now Open WebUI auth was disabled in the Docker run command:
- `WEBUI_AUTH=False`

That is convenient for local testing, but if you want LAN exposure or remote access, auth should be turned on.

### 4. GitHub publishing
Push this repo to a real GitHub remote once working GitHub auth and target repo details are confirmed.

## Exact files that were created/changed

### In `/root/hermes-openwebui-gui`
- `.env.openwebui`
- `.gitignore`
- `README.md`
- `adapter/app.py`
- `docker-compose.yml`
- `requirements.txt`
- `scripts/start_adapter.sh`
- `scripts/start_openwebui.sh`
- `windows-start-hermes-openwebui.bat`
- `HERMES_OPENWEBUI_SETUP_COMPLETE.md`

## How to use it from Windows

### Open the GUI
Open your browser on Windows and go to:
- `http://127.0.0.1:8080`

### Open the project folder on Windows
Go to:
- `C:\Users\DAngelo\Desktop\hermes-openwebui-gui`

### Open the full in-depth markdown file
Open:
- `C:\Users\DAngelo\Desktop\hermes-openwebui-gui\HERMES_OPENWEBUI_SETUP_COMPLETE.md`

## Useful commands to remember

### Check adapter health from WSL/Linux
- `curl http://127.0.0.1:8001/health`

### Check session map
- `curl http://127.0.0.1:8001/v1/session-map`

### Check Open WebUI container status from WSL via Windows Docker Desktop
- `cmd.exe /c docker ps --filter name=hermes-open-webui`

### View Open WebUI logs
- `cmd.exe /c docker logs --tail 100 hermes-open-webui`

### Stop Open WebUI
- `cmd.exe /c docker stop hermes-open-webui`

### Start Open WebUI again if container already exists
- `cmd.exe /c docker start hermes-open-webui`

### Remove Open WebUI container
- `cmd.exe /c docker rm -f hermes-open-webui`

### Start adapter manually
- `cd /root/hermes-openwebui-gui`
- `./scripts/start_adapter.sh`

### Re-clone the project from local Linux repo
- `git clone /root/hermes-openwebui-gui my-hermes-webui`

### Re-clone the project from the bundle
- `git clone /root/hermes-openwebui-gui/hermes-openwebui-gui.bundle my-hermes-webui`

## How to recreate this setup from scratch

### Step 1: ensure Hermes exists and works
You need a working Hermes installation at:
- `/root/.hermes/hermes-agent`

And a working Hermes home at:
- `/root/.hermes`

### Step 2: create project folder
- `mkdir -p /root/hermes-openwebui-gui/adapter /root/hermes-openwebui-gui/scripts /root/hermes-openwebui-gui/open-webui-data`

### Step 3: create adapter files
Create:
- `adapter/app.py`
- `requirements.txt`
- `.env.openwebui`
- helper scripts and README

### Step 4: bootstrap the adapter environment automatically
- `cd /root/hermes-openwebui-gui`
- `./scripts/install_all.sh`

### Step 5: start adapter
- `./scripts/start_adapter.sh`

### Step 6: launch Open WebUI in Docker
- `./scripts/run_openwebui_docker.sh`

### Step 7: open browser
- `http://127.0.0.1:8080`

## How to remember this setup later

If you forget how it works, remember this simple mental model:

- Hermes is still the brain.
- Open WebUI is the face.
- The adapter is the translator.
- Session mapping is the memory bridge between GUI chats and Hermes sessions.
- Slash commands are the control bridge into Hermes CLI.

In one line:
- Open WebUI -> adapter -> Hermes CLI -> your real Hermes config

## Repair/rebuild flow added

The repo now includes a repeatable way to fix/rebuild everything after future updates.

Use one of these:
- Windows: `scripts\\fix_all.bat`
- macOS/Linux: `./scripts/fix_all.sh`
- CLI: `python launcher.py rebuild-webui && python launcher.py start`

That flow is intended to:
- rebuild the patched Open WebUI image
- restart the live GUI container
- restart the adapter if needed
- reinstall the Hermes Workspace assets

## Summary

You now have:
- a Windows-accessible copy of the project
- a local git repo with the changes committed
- a real GitHub repo at `https://github.com/dangelo352/hermes-openwebui-gui`
- a working Open WebUI GUI at `http://127.0.0.1:8080`
- a Hermes-backed adapter at `http://127.0.0.1:8001`
- persistent session mapping support
- slash command support
- a Windows launcher batch file
- packaged Open WebUI frontend patch files
- a rebuild/redeploy path for patched live Open WebUI
- a full documentation file you can reopen later

If you continue improving this, the best next changes are richer file/image support, better command UX, and more live coding-event rendering in the patched frontend.
