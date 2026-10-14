---
id: TASK-9
title: 'T-09: Direct canvas edits the interviewer notices'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-8
references:
  - TICKETS.md
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The user can add, edit and delete any item on any canvas panel. Invalid edits are rejected with a visible reason and the old value is kept. On its next turn the interviewer acknowledges the edits by item ID.

Delivers stories: US-13

Mirrors T-09 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every canvas panel supports add, edit and delete through `agent.setState` (S11.3).
- [ ] #2 Writes are validated as S2.15 defines; an invalid write keeps the old state and sets `last_error`.
- [ ] #3 New items get IDs per S2.5; deleted IDs are never reused.
- [ ] #4 A graph-seam test shows the next interviewer call receives a note naming the edited IDs, and that `agent_design` tracks the interviewer's own writes (S5.9).
<!-- AC:END -->
