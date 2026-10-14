---
id: TASK-2
title: 'T-02: Sessions — create, list, resume, rename, delete'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
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
- [ ] #1 Session routes behave as S3.1–S3.5, including `422`, `404` and idempotent delete; every error uses the S3.6 shape.
- [ ] #2 `DesignState` extends `CopilotKitState` with the stages of S2.3; a new session's state has every S2.2 field with the initial values of S3.1 (S2.1).
- [ ] #3 The list page shows sessions newest first with name and stage, paginated by keyset cursor (S3.2, S11.1).
- [ ] #4 State is checkpointed in Postgres with thread ID equal to session ID and survives an `agent` restart (S4.2, NFR-3).
- [ ] #5 `/openapi.json` describes every route with typed models and error shapes; the frontend's REST types are generated from it (S3.7).
<!-- AC:END -->
