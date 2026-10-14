---
id: TASK-1
title: 'T-01: Walking skeleton with two model roles'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 22:40'
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
- [x] #1 `docker compose up` with one `.env` starts `web`, `agent` and `db`; `.env.example` documents every S1.3 variable with an OpenAI-compatible block and an Anthropic block (S1.1, S1.2, S1.3).
- [x] #2 A chat message produces a streamed reply through the runtime proxy, never a direct browser call to FastAPI (S4.1, S4.3, S4.4).
- [x] #3 The agent refuses to start, naming the variable, for each condition in S1.4.
- [x] #4 Every chat model comes from the one two-role factory; no other module imports a provider SDK (S1.6).
- [x] #5 The startup check runs for both roles and refuses to start naming the role, capability, provider and model; `SKIP_MODEL_CHECK=true` skips it (S1.7).
- [x] #6 `review_model_distinct` is computed at startup as S1.8 defines.
- [x] #7 `app-assets/` ships as package data with the five files of S12.1, copied verbatim from this repository's `app-assets/`; the agent refuses to start, naming the file, if any is missing or empty (S12.1, S12.2).
- [x] #8 A graph-seam test with two scripted fake models passes, proving the seam before any feature exists.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Log D13/API/source conflicts in QUESTIONS.md (Q-1..Q-6).
2. agent/: uv project (Python 3.14, pinned D13), src/blueprint: settings (S1.3/S1.4 per MODEL-CONNECTION), two-role factory via init_chat_model(model_provider=openai) (S1.6), review_model_distinct (S1.8), startup capability check (S1.7), app-assets as package data copied at build (S12.1/S12.2), minimal DesignState(CopilotKitState) + interviewer graph, FastAPI /agent via add_langgraph_fastapi_endpoint + LangGraphAGUIAgent 'blueprint' (S4.1), AsyncPostgresSaver.
3. Tests: graph seam with two scripted fake models; AG-UI endpoint test settling OQ-2 (frontend tool reaches hand-built StateGraph node, run ends on unanswered call, result returns); startup refusal per condition; factory import scan; asset verbatim check.
4. web/: Next 16.4.1 + TS 7.0.2, CopilotKit v2 provider + CopilotChat, /api/copilotkit runtime route with HttpAgent -> AGENT_URL/agent (S4.3/S4.4); vitest proxy test.
5. docker-compose.yml (web, agent, db), .env.example with OpenAI-compatible and Anthropic blocks.
6. Verify: ruff, mypy --strict, pytest, tsc, vitest, docker compose up, real-model streamed reply.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions: Q-1..Q-6 in QUESTIONS.md (no langchain-anthropic; Anthropic via OpenAI-compatible endpoint; base URL stands in for provider; all seven app-assets shipped and checked; CopilotKit v2 API differences; OQ-2 settled: frontend tools reach hand-built StateGraph nodes via state['copilotkit']['actions']). app-assets copied into the package by agent/hatch_build.py on every build. Startup check has a 60 s per-call limit so an unreachable endpoint refuses instead of hanging.
Validation: agent ruff + mypy --strict clean, pytest 58 passed; web tsc (TS 7.0.2) clean, vitest 3 passed, next build OK; docker compose up (web, agent, db) healthy; image app_assets sha256-identical to repo; Playwright drive of localhost:3000 showed a streamed reply via /api/copilotkit only, against a containerised OpenAI-compatible fake model (startup check made real HTTP tool-call and json_schema calls for both roles). Real-model run pending the user's .env.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Walking skeleton: docker compose starts web (Next 16.4.1, CopilotKit 1.79 v2 runtime proxy), agent (FastAPI AG-UI /agent, LangGraph, AsyncPostgresSaver) and db (Postgres 16). Both model roles come from one init_chat_model factory configured by base URL/key/name, pass a startup tool-call and structured-output check, and review_model_distinct is computed. Vendored app-assets ship verbatim as package data. Verified by 58 agent tests (graph seam with two scripted fakes, AG-UI endpoint incl. OQ-2 proof, startup refusals), 3 web tests, lint/type checks, and a browser run through the full stack.
<!-- SECTION:FINAL_SUMMARY:END -->
