---
id: TASK-16
title: 'T-16: Requirements.docx and UserStories.docx'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:58'
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
- [x] #1 `requirements.docx` renders as S10.5 defines from the current PRD.
- [x] #2 `user-stories.docx` renders as S10.6 defines, with build waves computed from the blocking edges.
- [x] #3 Both are `409` before `stage` is `complete` (S10.3).
- [x] #4 Both open without repair prompts in Word 365, LibreOffice 24+ and Google Docs (NFR-11).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.exports.delivery_docx: render_requirements (FR table ID/Feature/Requirement/Covering stories, NFR table ID/Category/Requirement/Covering stories, appendix of open gaps and accepted risks) and render_user_stories (stories under feature headings with sentence, requirement IDs, delivering tickets and acceptance criteria; every ticket in ID order with what to build, blocking edges, delivered stories and a ☐ checklist; build-waves table wave/tickets/blocked by computed from the edges), both from the current PRD and stamped with tickets_approved_at. Registered in downloads; 409 before complete via the S10.3 rule. tests/fixtures.complete_state is the shared completed-session fixture; the key scan now covers PRD v1.0, v1.1, Requirements and UserStories.
Validation: agent pytest 174 passed (incl. LibreOffice opening both documents, REST 409/200 with S10.2 file names, determinism).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Once tickets are approved, Requirements.docx (requirements with covering stories and a gap appendix) and UserStories.docx (stories by feature, tickets with acceptance criteria as a checklist, build waves from the blocking edges) are downloadable; both are 409 before completion and open in LibreOffice. Verified through the export seam and REST tests.
<!-- SECTION:FINAL_SUMMARY:END -->
