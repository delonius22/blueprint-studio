---
id: TASK-15
title: 'T-15: Tickets with `to-tickets` and the review loop'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-13
references:
  - TICKETS.md
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The `to-tickets` method breaks the current PRD into tracer-bullet tickets with blocking edges and acceptance criteria, with open gaps kept out of its input. The user approves the breakdown or asks for changes in plain words until it is right. A cyclic breakdown is never shown as valid.

Delivers stories: US-32, US-33, US-34, US-35

Mirrors T-15 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The `ticket_planner` prompt is built as S9.1 defines, using `app-assets/to-tickets.md` verbatim; a graph-seam test shows the planner's input contains no gap text.
- [ ] #2 `Ticket` exists as S2.14 defines; validation and its one retry behave as S9.2 defines.
- [ ] #3 The `dag_validator` rejects unknown blockers, duplicates and cycles, naming the cycle, and renumbers valid tickets topologically (S9.3).
- [ ] #4 `review_tickets` approve and revise behave as S9.4 defines; approval sets `tickets_approved_at` and `stage` `complete`.
- [ ] #5 The ticket view shows the breakdown with blocking edges (S11.2).
<!-- AC:END -->
