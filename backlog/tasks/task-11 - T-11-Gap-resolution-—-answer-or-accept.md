---
id: TASK-11
title: 'T-11: Gap resolution — answer or accept'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-10
references:
  - TICKETS.md
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The user goes through the gap register in a card, answering gaps or accepting them as open risks, or accepting all at once. Answers go to the interviewer, which records them as ordinary design items and marks each gap resolved. When no gap is open, the session moves to PRD drafting.

Delivers stories: US-21, US-22

Mirrors T-11 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `decide_gaps` is a frontend tool with per-gap decisions and "accept all"; answers and acceptances require text where S11.4 says so.
- [ ] #2 Accepted gaps get `status` `accepted` and the note; answered gaps are recorded through design tools and closed with `resolve_gap`, filling `resolved_by` (S6.5, S5.3).
- [ ] #3 The review does not re-run; `stage` becomes `prd_draft` when no gap is open (S6.5).
<!-- AC:END -->
