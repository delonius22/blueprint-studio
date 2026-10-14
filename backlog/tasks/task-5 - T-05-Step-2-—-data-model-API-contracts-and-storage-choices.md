---
id: TASK-5
title: 'T-05: Step 2 — data model, API contracts and storage choices'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
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
- [ ] #1 Entity, relationship, endpoint and storage-choice types and tools exist as S2.7 and S5.3 define.
- [ ] #2 A graph-seam test shows "I'll use Cassandra" alone leaves the choice `proposed` and prompts a justification question; a justification naming a valid basis makes it `decided` (S5.5).
- [ ] #3 Rejected alternatives are recorded with the choice (S2.7).
- [ ] #4 The canvas shows Step 2 panels with item IDs (S11.3).
<!-- AC:END -->
