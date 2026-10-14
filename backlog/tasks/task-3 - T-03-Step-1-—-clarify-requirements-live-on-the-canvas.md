---
id: TASK-3
title: 'T-03: Step 1 — clarify requirements, live on the canvas'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 23:02'
labels: []
dependencies:
  - TASK-2
references:
  - TICKETS.md
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The interviewer, prompted from the vendored instructions and course context, runs Step 1. It asks for users, use cases, read/write ratio, latency, availability and out-of-scope items, and records each answer as a structured item that appears on the canvas during the conversation. During Step 1 it cannot record architecture, even if asked.

Delivers stories: US-5, US-6, US-7, US-10, US-12

Mirrors T-03 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The design record and its Step 1 item types exist as S2.4, S2.5, S2.6, S2.7 and S2.15 define.
- [x] #2 The interviewer's system prompt is assembled as S5.2 defines, from `app-assets/` files.
- [x] #3 Backend tools record requirements, NFR targets, out-of-scope notes and estimates with IDs that are never reused, executed by the `design_tools` node (S5.1, S5.3).
- [x] #4 A graph-seam test shows that asking to "add a Redis cache" during Step 1 records nothing architectural (S5.4).
- [x] #5 Estimates keep their formula as well as their result (S2.7).
- [x] #6 The canvas shows Step 1 panels with item IDs, updating live (S11.2, S11.3).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. blueprint.design: ID issuance (S2.5), S2.15 validation, backend tool registry with Step 1 tools (upsert_requirement/nfr/out_of_scope/estimate, delete_item), S5.4 step gating.
2. blueprint.prompts: S5.2 system prompt from app-assets + stage/step + ID-labelled design summary + edit note slot.
3. Graph: interviewer binds step tools + frontend actions; design_tools node executes backend calls and returns to interviewer; pure routing.
4. Web: canvas with Step 1 panels showing IDs, fed live by agent state.
5. Tests: graph seam (records with IDs never reused, Redis cache at step 1 records nothing, estimates keep formula), prompt assembly, validation, canvas component.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented blueprint.design (ID issuance, S2.15 violations, generic upsert tool registry with Step 1 tools, S5.4 gating), blueprint.prompts (S5.2 assembly with ID-labelled design summary and an edit-note slot), graph nodes interviewer + design_tools with pure routing (frontend tool calls end the run; backend calls go to design_tools). SessionDetail.state is now typed (SessionState) so the frontend's S2 types are generated from OpenAPI too. Canvas panels for Step 1 read the agent's live state.
Validation: agent pytest 84 passed, ruff + mypy --strict clean; web vitest 12 passed, tsc clean, build OK; browser via docker compose with a scripted OpenAI-compatible fake: FR/NFR/OOS appeared on the canvas with IDs during the conversation; 'Add a Redis cache' in Step 1 recorded nothing.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Step 1 runs on the S5.2 prompt built from the vendored assets; backend tools executed by the design_tools node record requirements, NFR targets, out-of-scope notes and estimates (with formula and result) under never-reused IDs; architecture tools are unbound in Step 1; the canvas shows the Step 1 panels with IDs, updating live. Verified with graph-seam tests, validation tests, canvas component tests and a browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
