---
id: TASK-4
title: 'T-04: Step confirmation gate and per-step critique'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-3
references:
  - TICKETS.md
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When the interviewer thinks a step is complete, an approval card appears summarizing it. Approving advances the session and produces a three-part critique; rejecting with a reason keeps the session on the step. A stage tracker in the header shows progress.

Delivers stories: US-15, US-16

Mirrors T-04 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `confirm_step` is a frontend tool rendered with `useHumanInTheLoop`; rejection requires text (S5.7, S11.4).
- [ ] #2 Approval and rejection update state exactly as S5.7 defines.
- [ ] #3 After each approval the `critic` stores one critique with strengths, bottlenecks and questions (S5.8, S2.8).
- [ ] #4 Routing is a pure function of state and ends the run while a gate call is unanswered (S5.1), verified through the graph seam.
- [ ] #5 The header shows the stage tracker with current and confirmed steps (S11.2).
<!-- AC:END -->
