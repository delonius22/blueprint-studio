---
id: TASK-19
title: 'T-19: Resilience, token budget and structured logs'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-4
references:
  - TICKETS.md
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When a provider throttles, errors or times out, the app retries quietly; only if retries fail does the user see an alert with a retry button, and state is never half-written. A token meter shows use per model role and warns at 80 %; at 100 % no further model calls are made. Logs are structured JSON with per-node, per-role latency and tokens, and never contain secrets.

Delivers stories: US-45, US-46, US-47, US-48, US-50

Mirrors T-19 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Model calls retry as S13.1 defines; after exhausted retries only `last_error` changes (S13.2), proven through the graph seam with a failing fake model.
- [ ] #2 Token accounting per role, the budget stop and the usage estimate behave as S13.3 defines.
- [ ] #3 Structured output falls back from JSON-schema mode to tool calling as S13.4 defines.
- [ ] #4 The error alert, Retry action and per-role token meter behave as S11.6 defines.
- [ ] #5 Logs follow S13.5, including `role`, `ttft_ms` and `export_ms`; LangSmith tracing toggles by variable.
- [ ] #6 A test scans log output, the web bundle and every download kind for both configured key values and finds none (S1.5, NFR-6).
<!-- AC:END -->
