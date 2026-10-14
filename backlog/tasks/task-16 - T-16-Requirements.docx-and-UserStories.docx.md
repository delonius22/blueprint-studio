---
id: TASK-16
title: 'T-16: Requirements.docx and UserStories.docx'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-15
references:
  - TICKETS.md
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Once tickets are approved, the user can download a requirements document with coverage and a gap appendix, and a user-stories document with stories by feature, tickets with acceptance criteria, and build waves.

Delivers stories: US-37, US-38, US-53

Mirrors T-16 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `requirements.docx` renders as S10.5 defines from the current PRD.
- [ ] #2 `user-stories.docx` renders as S10.6 defines, with build waves computed from the blocking edges.
- [ ] #3 Both are `409` before `stage` is `complete` (S10.3).
- [ ] #4 Both open without repair prompts in Word 365, LibreOffice 24+ and Google Docs (NFR-11).
<!-- AC:END -->
