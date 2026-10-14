---
id: TASK-10
title: 'T-10: Design review on the review model'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-8
references:
  - TICKETS.md
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After Step 5, three reviewers on the separate review model check the design in parallel for security, efficiency and maintainability. A merge step produces the gap register, shown in its own panel with each gap's lens, severity, affected items, risk and decision needed. When the review model equals the interview model, a persistent warning says the cross-model check is not active.

Delivers stories: US-18, US-19, US-20, US-23

Mirrors T-10 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The `Gap` type exists as S2.9 defines.
- [ ] #2 The three reviewer nodes run in parallel on the review-role model with the inputs of S6.1, the checklists of S6.2 and the rules and severity definitions of S6.3.
- [ ] #3 The `gap_merger` drops findings that cite no existing item, combines duplicates keeping the higher severity, and issues `GAP` IDs (S6.4).
- [ ] #4 A graph-seam test with a scripted review model shows a finding that proposes a new component produces no design item and no requirement (S6.3, G3).
- [ ] #5 Zero gaps sends the session to `prd_draft`; otherwise to `gap_resolution` (S6.4).
- [ ] #6 Tokens are counted under the `review` role (S13.3).
- [ ] #7 The gap register panel and the same-model warning render as S11.2 and S6.6 define.
<!-- AC:END -->
