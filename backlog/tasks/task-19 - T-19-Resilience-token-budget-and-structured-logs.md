---
id: TASK-19
title: 'T-19: Resilience, token budget and structured logs'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 23:29'
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
- [x] #1 Model calls retry as S13.1 defines; after exhausted retries only `last_error` changes (S13.2), proven through the graph seam with a failing fake model.
- [x] #2 Token accounting per role, the budget stop and the usage estimate behave as S13.3 defines.
- [x] #3 Structured output falls back from JSON-schema mode to tool calling as S13.4 defines.
- [x] #4 The error alert, Retry action and per-role token meter behave as S11.6 defines.
- [x] #5 Logs follow S13.5, including `role`, `ttft_ms` and `export_ms`; LangSmith tracing toggles by variable.
- [x] #6 A test scans log output, the web bundle and every download kind for both configured key values and finds none (S1.5, NFR-6).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. llm.ModelGateway: budget check (S13.3), retries on 429/5xx/timeouts with full-jitter backoff and Retry-After (S13.1), usage accounting per role with estimate fallback, structured output JSON-schema then tool calling cached per model (S13.4); factory sets max_retries=0 so this policy governs.
2. Nodes write state only after success; failures set only last_error (S13.2); routing ends while last_error is set.
3. JSON-line logging (S13.5) with role, latency_ms, tokens, ttft_ms, export_ms (download middleware); key redaction filter; uvicorn logs in JSON; LANGSMITH_TRACING applied.
4. Web: error alert with Retry (clears last_error, re-runs the last user turn) and dismiss; per-role token meter warning at 80%.
5. Tests: failing fake model through the graph seam, budget stop, estimates, fallback cache, logs, key scan of logs and web bundle.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.llm.ModelGateway: budget check before each call (budget_exhausted, not retryable); retries on 429/5xx/timeouts (classified by shape, no provider SDK import) with full-jitter backoff from 1 s and at least Retry-After, up to 3 retries; per-role token accounting from usage_metadata or the chars/4 estimate (logged usage_estimated); structured output JSON-schema then tool calling on provider rejection, mode cached per model; interviewer replies are streamed and assembled so ttft_ms is measured. Factory sets max_retries=0 and a 120 s request timeout so S13.1 is the only retry policy. Nodes write only last_error on failure; every route ends while last_error is set. last_error carries only role and HTTP status (provider text can quote a key; it stays in the redacted log). blueprint.log: JSON lines, uvicorn logs included, RedactSecrets filter; DownloadTimer logs export_ms for /api/sessions/{id}/downloads/{kind}; LANGSMITH_TRACING applied at startup. Web: ErrorAlert (Retry clears last_error and re-runs the last user turn; Dismiss), onRunInitialized clears last_error when the user sends a new message, TokenMeter per role with 80 % warning. Key scan: logs (agent test) and the web build (vitest builds with sentinel keys); download kinds join the scan as T-12+ add them.
Validation: agent pytest 112 passed; web vitest 32 passed; browser: 4 injected 503s -> 3 logged retries -> alert; reload made no model call; Retry recovered; a new message after an error was answered.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Provider failures are retried with backoff and, once retries are exhausted, only last_error changes and the user gets an alert with Retry; every model call is budgeted and counted per role, with a header meter warning at 80 % and a hard stop at 100 %; structured output falls back to tool calling; logs are structured JSON with per-node, per-role latency and tokens, and keys are redacted. Verified through graph-seam tests with failing fake models, gateway and logging tests, web component tests, a bundle key scan and a browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
