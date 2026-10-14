---
id: TASK-14
title: 'T-14: Proposed changes and PRD v1.2'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-13
references:
  - TICKETS.md
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When synthesis proposed changes to signed-off content, the user reviews each one in a card, approving or rejecting it, or accepting all. Approved changes produce PRD v1.2, with a table of what changed; rejected ones are dropped. With no proposals, this stage is skipped.

Delivers stories: US-30, US-36

Mirrors T-14 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `ProposedChange` exists as S2.13 defines.
- [ ] #2 `review_changes` and the `change_applier` behave as S8.5 defines; no v1.2 is created when every change is rejected.
- [ ] #3 A graph-seam test shows v1.0 and v1.1 are unchanged after v1.2 is created, and later stages read v1.2 as the current PRD (S2.12, S8.6).
- [ ] #4 `prd-v1.2.docx` renders with its "Changes from v1.1" table (S10.4).
<!-- AC:END -->
