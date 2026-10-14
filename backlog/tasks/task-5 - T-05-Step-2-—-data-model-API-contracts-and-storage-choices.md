---
id: TASK-5
title: 'T-05: Step 2 — data model, API contracts and storage choices'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 23:10'
labels: []
dependencies:
  - TASK-4
references:
  - TICKETS.md
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In Step 2 the interviewer captures entities, relationships, keys, endpoints and storage choices on the canvas. Every storage choice starts as "proposed" and becomes "decided" only after the user justifies it with workload facts.

Delivers stories: US-8, US-11

Mirrors T-05 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Entity, relationship, endpoint and storage-choice types and tools exist as S2.7 and S5.3 define.
- [x] #2 A graph-seam test shows "I'll use Cassandra" alone leaves the choice `proposed` and prompts a justification question; a justification naming a valid basis makes it `decided` (S5.5).
- [x] #3 Rejected alternatives are recorded with the choice (S2.7).
- [x] #4 The canvas shows Step 2 panels with item IDs (S11.3).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tools: upsert_entity, upsert_relationship, upsert_endpoint, upsert_storage_choice (always proposed, with rejected alternatives), decide_storage_choice (basis must name read_write_ratio/consistency/latency/throughput).
2. Tool results steer the interviewer to ask for a justification while a choice is proposed.
3. Canvas Step 2 panels with IDs.
4. Tests through the graph seam (Cassandra proposed -> decided), validation, panels.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added upsert_entity, upsert_relationship, upsert_endpoint, upsert_storage_choice (status fixed to proposed by the app, not an argument; its tool result tells the interviewer to ask for a workload justification) and decide_storage_choice (basis must name read_write_ratio, consistency, latency or throughput; sets decided and the justification). FK/relationship references validated per S2.15. Canvas Step 2 panels: entities, relationships, API endpoints, storage choices (status badge, why, rejected alternatives).
Validation: agent pytest 93 passed (Cassandra proposed -> decided through the graph seam), ruff/mypy clean; web vitest 18 passed, tsc, build OK.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Step 2 records entities, relationships, endpoints and storage choices as structured items with IDs; a named technology stays proposed until decide_storage_choice records a justification grounded in read/write ratio, consistency, latency or throughput, with rejected alternatives kept. The canvas shows the Step 2 panels. Verified through graph-seam and component tests.
<!-- SECTION:FINAL_SUMMARY:END -->
