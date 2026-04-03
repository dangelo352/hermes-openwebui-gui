# Hermes Open WebUI GUI Maintainer Guide

This file is the high-context maintainer document for this repo.

It is written for:
- future AI agents
- future human maintainers
- the project owner

Read this before making major changes.

---

# 1. What this repo is

This repo turns an existing Hermes CLI installation into a GUI experience using Open WebUI.

Architecture:

```text
Open WebUI (patched frontend)
  -> Hermes OpenAI-compatible adapter
    -> Hermes CLI
      -> real Hermes config, skills, sessions, memory, tools
```

This repo is not a replacement Hermes runtime.
It is a bridge + GUI layer around the real Hermes installation.

---

# 2. Main goals of this repo

The repo is intended to provide:
- a usable GUI for Hermes
- lower token overhead than naive transcript replay
- persistent Hermes session mapping per GUI chat when possible
- slash-command support from GUI chat
- Workspace-based Hermes controls
- patched Open WebUI frontend behavior for Hermes-specific UX
- rebuild/redeploy automation so updates are repeatable

User preferences for this project:
- keep the repo proactively updated whenever requested changes are made
- keep the Windows desktop copy in sync
- prefer polished, robust implementations
- prefer cleaner formatting and markdown code fences where helpful
- for coding tasks, show tool activity, file activity, and progress when possible

---

# 3. Important live paths

## Linux / WSL repo path

```text
/root/hermes-openwebui-gui
```

## Windows synced copy

```text
C:\Users\DAngelo\Desktop\hermes-openwebui-gui
```

## Open WebUI source checkout used for local patch/build work

```text
/root/open-webui
```

## Real Hermes installation used by the adapter

Typical path on this machine:

```text
/root/.hermes/hermes-agent/venv/bin/hermes
```

## Real Hermes home/config reused by the bridge

```text
/root/.hermes
```

---

# 4. Important URLs and runtime endpoints

## GUI

```text
http://127.0.0.1:8080
```

## Adapter

```text
http://127.0.0.1:8001
```

## Adapter health

```text
http://127.0.0.1:8001/health
```

## Session map

```text
http://127.0.0.1:8001/v1/session-map
```

---

# 5. Core repo components

## 5.1 Adapter

Main file:

```text
adapter/app.py
```

What it does:
- exposes OpenAI-compatible endpoints for Open WebUI
- routes chat requests into Hermes CLI
- supports slash-command passthrough
- supports persistent session mapping
- reduces token waste for resumed sessions
- formats command output into markdown-friendly blocks
- attempts to surface coding-task tool traces more cleanly

Key endpoints:
- `GET /health`
- `GET /v1/models`
- `GET /v1/session-map`
- `POST /v1/chat/completions`

## 5.2 Workspace Hermes controls

Main file:

```text
workspace/hermes_control_tool.py
```

This installs into Open WebUI Workspace > Tools as:

```text
Hermes Control
```

It provides actions like:
- adapter health
- session map
- gateway status/restart/start/stop
- sessions list
- skills list
- cron list
- config summary
- doctor
- tool summary
- memory help
- session mapping actions
- generic slash-command execution
- generic Hermes CLI passthrough

## 5.3 Open WebUI patch overlay files

Patch root:

```text
openwebui-patches/src/
```

These are source overlay files copied onto an Open WebUI source tree before building the patched image.

Current important frontend patches include:
- Hermes slash overlay components for chat input
- custom response rendering blocks for Hermes coding/tool activity

## 5.4 Launcher

Main file:

```text
launcher.py
```

The launcher is intended to be the cross-platform entrypoint.

It handles:
- adapter venv setup
- dependency install
- Hermes detection
- patched Open WebUI image build/use
- container start/restart
- workspace asset install

## 5.5 Rebuild / fix scripts

Important scripts:

```text
scripts/fix_all.sh
scripts/fix_all.bat
scripts/rebuild_live_patched_openwebui.py
scripts/rebuild_live_patched_openwebui.sh
scripts/rebuild_live_patched_openwebui.bat
scripts/install_openwebui_workspace_assets.py
scripts/apply_openwebui_chat_patches.sh
scripts/apply_openwebui_chat_patches.bat
```

---

# 6. How the adapter works

## 6.1 Chat flow

Normal chat flow:

```text
Open WebUI -> /v1/chat/completions -> adapter builds prompt -> Hermes CLI chat -> result returned to Open WebUI
```

## 6.2 Session mapping

If the Open WebUI chat/user metadata is available, the adapter maps:

```text
Open WebUI chat id + user id -> Hermes session id
```

Stored in:

```text
state/session_map.json
```

When mapped:
- future turns can resume the Hermes session
- token overhead is lower
- continuity is better than replaying the whole transcript every time

## 6.3 Token-saving behavior

Current intent:
- first turn may use larger reconstructed prompt/history
- resumed mapped sessions should prefer sending only the latest user turn when safe

This is an important design goal. Do not regress it casually.

## 6.4 Slash commands

The adapter supports slash commands in chat.

Examples:

```text
/session
/new
/resume <id>
/gateway status
/gateway restart
/sessions list
/skills list
/cron list
/config
/doctor
/hermes <args>
```

The adapter formats command results using markdown blocks so they render better in the GUI.

---

# 7. Open WebUI frontend patch strategy

This repo does not permanently fork all of Open WebUI into the repo.
Instead, it stores an overlay patch tree and rebuild process.

Flow:

```text
Open WebUI source checkout
  + repo patch overlay
  -> patched build tree
  -> patched Docker image
  -> running patched Open WebUI container
```

This makes updates easier than manually editing random files without documentation.

## 7.1 Current patched frontend areas

### Chat slash overlay

The repo replaces or augments the default `/` suggestion behavior with Hermes command suggestions.

Key patched source areas include files under:

```text
src/lib/components/chat/MessageInput/
```

### Coding activity rendering

The repo also patches message rendering for Hermes coding activity blocks.

Key patched source areas include files under:

```text
src/lib/components/chat/Messages/
```

The goal is better rendering for:
- tool activity
- files referenced
- clearer result separation

---

# 8. How to start the system

## 8.1 Recommended quick start

### Windows

```bat
start-hermes-openwebui.bat
```

### macOS/Linux

```bash
./start-hermes-openwebui.command
```

### CLI

```bash
python launcher.py start
```

---

# 9. How to rebuild/fix everything after updates

This is critical.

If changes are made to:
- adapter
- frontend patch overlay
- launcher logic
- workspace tool logic
- rebuild scripts

then use the repair flow.

## 9.1 Windows

```bat
scripts\fix_all.bat
```

## 9.2 macOS/Linux

```bash
./scripts/fix_all.sh
```

## 9.3 Direct CLI equivalent

```bash
python launcher.py rebuild-webui
python launcher.py start
```

Intended effect:
- rebuild patched Open WebUI image
- redeploy Open WebUI container
- restart adapter if needed
- reinstall Workspace Hermes tool

---

# 10. How to rebuild only the live patched Open WebUI

If only the frontend overlay changed:

## Windows

```bat
scripts\rebuild_live_patched_openwebui.bat
```

## macOS/Linux

```bash
./scripts/rebuild_live_patched_openwebui.sh
```

## Python direct

```bash
python scripts/rebuild_live_patched_openwebui.py
```

Then restart/redeploy via launcher if needed:

```bash
python launcher.py restart
```

---

# 11. How Workspace assets are installed

Workspace tool install script:

```text
scripts/install_openwebui_workspace_assets.py
```

This script creates or updates the `Hermes Control` tool inside Open WebUI.

The launcher also calls this after starting Open WebUI.

If Workspace controls seem missing:

```bash
python scripts/install_openwebui_workspace_assets.py
```

---

# 12. How to patch an arbitrary Open WebUI source checkout

This is for users who want to patch their own Open WebUI source tree one-to-one.

## macOS/Linux

```bash
./scripts/apply_openwebui_chat_patches.sh /path/to/open-webui
```

## Windows

```bat
scripts\apply_openwebui_chat_patches.bat C:\path\to\open-webui
```

This applies the repo’s frontend patch overlay files into that source checkout.

---

# 13. Git / repo maintenance rules

These rules matter.

## 13.1 Always update the repo when user-requested changes are made

The user explicitly wants:
- the GitHub repo kept updated to reflect requested changes
- the Windows desktop copy kept in sync

So after meaningful work:
1. commit changes
2. push to GitHub
3. sync Windows copy

## 13.2 Repo URL

```text
https://github.com/dangelo352/hermes-openwebui-gui
```

## 13.3 Typical sync command already used in this project

The repo often syncs to Windows via the helper script:

```bash
./scripts/install_windows_wsl.sh
```

## 13.4 Do not leave important changes only in the local Open WebUI source tree

If you patch `/root/open-webui/...` directly, make sure the equivalent change is also copied into:

```text
openwebui-patches/src/...
```

Otherwise future rebuilds may lose the change.

This is a very important maintainer rule.

---

# 14. Formatting expectations

The user asked for:
- cleaner list formatting when helpful
- markdown code fences for code/commands
- concise by default
- better coding-task visibility

So outputs should prefer:

```md
- lists
- fenced code blocks
- headings where useful
```

For slash command/system output, prefer markdown rendering like:

```md
Command
```bash
$ gateway status
```

Exit code: `0`

Stdout
```text
...
```
```

Do not dump ugly plain text when markdown improves readability.

---

# 15. Current known limitations

Even after the current work, some limitations remain.

## 15.1 True live tool streaming is still incomplete

The current bridge/frontend improvements are better than before, but not yet a perfect live dev-console timeline.

Still needed for a fully ideal coding UX:
- richer live progress events while tool calls are in flight
- stronger file edit detection
- better mapping of tool calls to structured chat cards
- stronger inline rendering during streaming rather than mostly after completion

## 15.2 Raw chain-of-thought should not be exposed

Do not expose private chain-of-thought.

Allowed alternatives:
- concise reasoning summaries
- tool activity
- file activity
- progress/status steps

## 15.3 Interactive CLI commands may not work well via slash passthrough

The adapter is better for non-interactive commands.
Some interactive terminal-native commands may still need a real terminal session.

---

# 16. Good maintainer workflow for future changes

When changing the project, follow this order:

1. inspect current repo files
2. make the code change
3. if frontend change touches local `/root/open-webui`, mirror it into `openwebui-patches/src`
4. rebuild live patched Open WebUI if frontend changed
5. reinstall Workspace assets if needed
6. test the actual running flow
7. update docs
8. commit + push repo
9. sync Windows copy

---

# 17. Recommended future improvement areas

High-value next work:
- richer live coding event rendering
- more slash overlay metadata and categories
- GUI session views for Hermes/Codex/Claude if implemented later
- more Workspace pages/panels for gateway/admin/session data
- better file edit cards
- better progress visualization during long tasks

---

# 18. Quick command cheatsheet

## Start everything

```bash
python launcher.py start
```

## Stop everything

```bash
python launcher.py stop
```

## Restart everything

```bash
python launcher.py restart
```

## Show status

```bash
python launcher.py status
```

## Rebuild patched Open WebUI image

```bash
python launcher.py rebuild-webui
```

## Full repair flow

```bash
./scripts/fix_all.sh
```

## Reinstall Workspace Hermes tool

```bash
python scripts/install_openwebui_workspace_assets.py
```

---

# 19. If you are an AI reading this

You should assume:
- the repo should be kept current
- the Windows copy should be synced
- user wants polished UX, not half-finished roughness
- frontend changes must be preserved in the patch overlay, not only local source
- rebuild/redeploy is part of the job, not optional, when frontend patches change

If you make meaningful changes, do all of these unless blocked:
- test them
- commit them
- push them
- sync the Windows copy
- update docs if behavior changed

---

# 20. Bottom line

This repo is the maintained bridge between:
- real Hermes CLI
- patched Open WebUI GUI
- Workspace-based Hermes controls
- future richer dev/operator UX

Preserve these invariants:
- real Hermes remains the backend brain
- Open WebUI is the GUI shell
- repo patch files are the source of truth for frontend customizations
- rebuild scripts must keep the live app aligned with repo changes
