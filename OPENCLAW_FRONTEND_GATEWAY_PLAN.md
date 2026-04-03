# OpenClaw-Inspired Hermes Gateway UI Plan

## Goal

Evolve this project from a backend bridge into a more complete Hermes control-plane UI inspired by OpenClaw's gateway experience while still using Open WebUI as the base shell.

## Research summary

OpenClaw's control UI patterns worth copying:
- dark control-plane layout
- left sidebar with grouped nav sections
- gateway/admin-oriented pages: Overview, Channels, Instances, Sessions, Usage, Cron Jobs, Skills, Config, Debug, Logs, Docs
- top header with session selector and quick actions
- chat as an intervention console, not just a consumer messenger
- better event/log/status surfacing around sessions and gateway state

## Current project state

Already implemented here:
- Hermes adapter with OpenAI-compatible chat endpoint
- persistent session mapping
- slash command passthrough
- token-saving resumed session mode
- installer scripts
- Docker launch flow
- Windows launcher

Still missing for a true OpenClaw-like UX:
- frontend command palette and slash autocomplete
- sidebar control-plane navigation inside the GUI
- structured gateway pages
- richer tool/event timeline rendering
- command-specific UI affordances

## Constraints

This repo currently wraps Open WebUI and Hermes. It does not ship a full custom Open WebUI frontend fork yet.

To fully match the OpenClaw UX, the next implementation should likely do one of these:
1. fork Open WebUI frontend and add Hermes-specific screens/components
2. build a separate Hermes control frontend that talks to the adapter and/or Hermes gateway APIs

## Recommended next implementation phases

### Phase 1: Chat input UX improvements
- Add slash command autocomplete in frontend
- Add command descriptions/argument hints
- Render slash command responses in terminal-style cards
- Surface mapped Hermes session in the chat header

### Phase 2: Gateway control sidebar
- Add a Hermes navigation shell inspired by OpenClaw:
  - Chat
  - Overview
  - Channels
  - Instances
  - Sessions
  - Usage
  - Cron Jobs
  - Skills
  - Config
  - Debug
  - Logs
  - Docs
- Route these pages to adapter/gateway-backed data sources

### Phase 3: Status and event timeline
- Add live status badges
- Add command run history
- Add session timeline / tool timeline
- Add gateway health cards
- Add logs tail panel

### Phase 4: Structured actions
- Quick actions in header:
  - refresh
  - new session
  - resume session
  - gateway status
  - logs
  - config
- session selector dropdown
- approval/task action drawer if needed

## Suggested architecture for the frontend work

### Option A: Open WebUI fork inside this repo
- Add an `openwebui-fork/` or patch workflow
- Maintain a small patchset against upstream Open WebUI
- Inject Hermes-specific navigation and pages

### Option B: Separate frontend app
- Add a `frontend/` app (React/Vite or similar)
- Use adapter endpoints plus future Hermes gateway endpoints
- Keep Open WebUI for chat, and use the custom frontend as control UI

## Immediate practical next step

If continuing implementation, the highest-value next milestone is:
- add frontend slash-command autocomplete
- add command help UI
- add a Hermes gateway sidebar shell with placeholder pages wired to real data incrementally

## Why this plan matters

This preserves what already works:
- robust Hermes backend integration
- token efficiency
- command support
- easy install

while creating a path to the advanced OpenClaw-style operator UX the user wants.
