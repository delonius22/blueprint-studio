---
id: TASK-12
title: 'T-12: PRD v1.0 — draft, sign-off and first download'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-11
references:
  - TICKETS.md
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The agent drafts a full PRD from the design record and gap register: problem, goals, users, features grouping the requirements, requirements copied verbatim, scope, and open gaps with their features. The user reviews it in a PRD viewer and signs it off, or rejects it with a reason until it is right. Once signed off, v1.0 is frozen and downloadable as Word.

Delivers stories: US-24, US-25, US-26, US-27, US-36

Mirrors T-12 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `PrdDoc`, `Feature`, `PrdRequirement`, `PrdNfr` and `PrdVersion` exist as S2.10 and S2.12 define.
- [ ] #2 The `prd_drafter` behaves as S7.1 defines; a graph-seam test shows FR and NFR statements in the draft are byte-identical to the design record.
- [ ] #3 Validation and its one retry behave as S7.2 defines.
- [ ] #4 `sign_off_prd` approval and rejection behave as S7.3 and S7.4 define; a signed-off version is never modified.
- [ ] #5 The PRD viewer shows the draft and every version with a version switcher (S11.2).
- [ ] #6 The download listing and file routes of S10.3 exist, backed by pure renderers (S10.1); `prd-v1.0.docx` renders as S10.4 defines and is `409` before sign-off.
- [ ] #7 The file opens without a repair prompt in Word 365, LibreOffice 24+ and Google Docs (NFR-11).
<!-- AC:END -->
