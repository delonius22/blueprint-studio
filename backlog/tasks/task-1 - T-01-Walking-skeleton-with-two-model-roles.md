---
id: TASK-1
title: 'T-01: Walking skeleton with two model roles'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies: []
references:
  - TICKETS.md
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
One command starts the web app, the agent service and the database. The user opens the app, types a message and sees a streamed reply through the full path: browser → CopilotKit runtime route → FastAPI AG-UI endpoint → LangGraph graph → interview model. Both model roles are configured from the environment and checked at startup, and the vendored runtime assets are loaded.

Delivers stories: US-51, US-52, US-55

Mirrors T-01 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `docker compose up` with one `.env` starts `web`, `agent` and `db`; `.env.example` documents every S1.3 variable with an OpenAI-compatible block and an Anthropic block (S1.1, S1.2, S1.3).
- [ ] #2 A chat message produces a streamed reply through the runtime proxy, never a direct browser call to FastAPI (S4.1, S4.3, S4.4).
- [ ] #3 The agent refuses to start, naming the variable, for each condition in S1.4.
- [ ] #4 Every chat model comes from the one two-role factory; no other module imports a provider SDK (S1.6).
- [ ] #5 The startup check runs for both roles and refuses to start naming the role, capability, provider and model; `SKIP_MODEL_CHECK=true` skips it (S1.7).
- [ ] #6 `review_model_distinct` is computed at startup as S1.8 defines.
- [ ] #7 `app-assets/` ships as package data with the five files of S12.1, copied verbatim from this repository's `app-assets/`; the agent refuses to start, naming the file, if any is missing or empty (S12.1, S12.2).
- [ ] #8 A graph-seam test with two scripted fake models passes, proving the seam before any feature exists.
<!-- AC:END -->
