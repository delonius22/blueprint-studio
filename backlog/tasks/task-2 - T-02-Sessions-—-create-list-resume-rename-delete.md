---
id: TASK-2
title: 'T-02: Sessions — create, list, resume, rename, delete'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 22:56'
labels: []
dependencies:
  - TASK-1
references:
  - TICKETS.md
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The user lands on a session list, creates a named session, works in it, closes the browser or restarts the stack, and finds the session exactly as left. Sessions can be renamed and deleted. The REST API is fully described by the generated OpenAPI document.

Delivers stories: US-1, US-2, US-3, US-4

Mirrors T-02 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Session routes behave as S3.1–S3.5, including `422`, `404` and idempotent delete; every error uses the S3.6 shape.
- [x] #2 `DesignState` extends `CopilotKitState` with the stages of S2.3; a new session's state has every S2.2 field with the initial values of S3.1 (S2.1).
- [x] #3 The list page shows sessions newest first with name and stage, paginated by keyset cursor (S3.2, S11.1).
- [x] #4 State is checkpointed in Postgres with thread ID equal to session ID and survives an `agent` restart (S4.2, NFR-3).
- [x] #5 `/openapi.json` describes every route with typed models and error shapes; the frontend's REST types are generated from it (S3.7).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. S2 domain models + DesignState with all S2.2 fields and initial values.
2. sessions table store + REST routes S3.1-S3.6 with typed OpenAPI (S3.7), AsyncPostgresSaver thread=session.
3. SessionAgent wrapper: refuse unknown sessions, refresh session row after runs.
4. Web: REST proxy, generated types, session list (/), workspace (/s/[id]) with history restore.
5. Tests: API over Postgres incl. restart; contract tests; list component tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions: Q-7 (/agent excluded from the REST OpenAPI document), Q-8 (empty thread after a web restart is re-synced with a no-message run; graph START route ends at once, snapshots come from the checkpoint), Q-9 (openapi-typescript runs from web/tools/openapi with TS 5.9.3; the app stays on TS 7.0.2). All S2 shapes defined in blueprint.domain; graph state stores them as JSON. Session rows (sessions table) are refreshed after every agent run by the SessionAgent wrapper; runs on unknown sessions get RUN_ERROR.
Validation: agent ruff + mypy --strict clean, pytest 75 passed (Postgres via throwaway container); web tsc clean, vitest 8 passed, next build OK; browser: list page, create -> workspace, chat history restored after a verified web container restart.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Sessions end to end: REST API (create/list/get/rename/delete with S3.6 errors, keyset cursor, typed OpenAPI 3.1), DesignState with every S2.2 field and S3.1 initial values, Postgres checkpoints with thread ID = session ID, session list page and workspace page wired to the session's thread. Verified by API tests over a real Postgres (including a restart test), contract tests for openapi.json and the generated TS types, component tests for the list, and a browser run through docker compose.
<!-- SECTION:FINAL_SUMMARY:END -->
