---
id: TASK-13
title: 'T-13: PRD v1.1 with `to-spec`, and seam approval'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-12
references:
  - TICKETS.md
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After sign-off, the `to-spec` method extends the PRD with a solution, user stories traced to requirements and features, implementation decisions and further notes, without touching signed-off sections. The agent proposes test seams; once the user approves them, v1.1 is frozen and downloadable.

Delivers stories: US-28, US-29, US-31, US-36

Mirrors T-13 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The `spec_synthesizer` prompt and output behave as S8.1 defines, using `app-assets/to-spec.md` verbatim.
- [ ] #2 A graph-seam test shows the signed-off sections of `prd_draft` are byte-identical to v1.0 after synthesis, and every open gap appears in further notes with its ID (S8.1).
- [ ] #3 `UserStory` exists as S2.11 defines; validation and its one retry behave as S8.2 defines, including that every FR is covered by a story.
- [ ] #4 `approve_seams` approve, edit and reject behave as S8.3; approval appends v1.1 and routes as S8.4 defines.
- [ ] #5 `prd-v1.1.docx` renders as S10.4 defines and ends with the attribution line of S12.3.
<!-- AC:END -->
