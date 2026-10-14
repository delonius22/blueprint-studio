---
id: TASK-3
title: 'T-03: Step 1 — clarify requirements, live on the canvas'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
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
- [ ] #1 The design record and its Step 1 item types exist as S2.4, S2.5, S2.6, S2.7 and S2.15 define.
- [ ] #2 The interviewer's system prompt is assembled as S5.2 defines, from `app-assets/` files.
- [ ] #3 Backend tools record requirements, NFR targets, out-of-scope notes and estimates with IDs that are never reused, executed by the `design_tools` node (S5.1, S5.3).
- [ ] #4 A graph-seam test shows that asking to "add a Redis cache" during Step 1 records nothing architectural (S5.4).
- [ ] #5 Estimates keep their formula as well as their result (S2.7).
- [ ] #6 The canvas shows Step 1 panels with item IDs, updating live (S11.2, S11.3).
<!-- AC:END -->
