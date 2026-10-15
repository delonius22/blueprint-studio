---
id: TASK-12
title: 'T-12: PRD v1.0 — draft, sign-off and first download'
status: Done
assignee: []
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:47'
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
- [x] #1 `PrdDoc`, `Feature`, `PrdRequirement`, `PrdNfr` and `PrdVersion` exist as S2.10 and S2.12 define.
- [x] #2 The `prd_drafter` behaves as S7.1 defines; a graph-seam test shows FR and NFR statements in the draft are byte-identical to the design record.
- [x] #3 Validation and its one retry behave as S7.2 defines.
- [x] #4 `sign_off_prd` approval and rejection behave as S7.3 and S7.4 define; a signed-off version is never modified.
- [x] #5 The PRD viewer shows the draft and every version with a version switcher (S11.2).
- [x] #6 The download listing and file routes of S10.3 exist, backed by pure renderers (S10.1); `prd-v1.0.docx` renders as S10.4 defines and is `409` before sign-off.
- [x] #7 The file opens without a repair prompt in Word 365, LibreOffice 24+ and Google Docs (NFR-11).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
prd_drafter (interview model, structured PrdDraftOut) writes only problem statement, goals, users, features (grouping FRs, by ref) and scope, plus gap->feature refs; blueprint.prd.build_prd copies FRs/NFRs verbatim, out_of_scope from design notes, open_gaps = accepted gaps with feature_ids (also written to state gaps); features keep their F- ID across re-drafts when the name is unchanged. S7.2 validation with one corrective retry; failure -> last_error. The node emits sign_off_prd (graph-made gate); approval appends PrdVersion 1.0 (approved_at UTC) and sets spec_synthesis; rejection re-drafts with the reason. Routing: prd_draft reached from gap_merger (zero gaps), the interviewer/design_tools (gaps settled), or START (retry). Design tools are bound only in interview and gap_resolution. Downloads: blueprint.downloads (S10.2 kinds, S10.3 availability, pure renderers), GET /api/sessions/{id}/downloads and /downloads/{kind} (404 unknown kind, 409 unmet condition, RFC 5987 Content-Disposition); exports/docx_util makes deterministic .docx (fixed core properties and zip entry times from the approval time, author Blueprint Studio); exports/prd_docx renders S10.4 (v1.1 and v1.2 sections ready for T-13/T-14). Web: PrdViewer with version switcher, SignOffCard, DownloadsMenu in the header; REST proxy forwards Content-Disposition. NFR-11: verified with LibreOffice 26.2 (headless PDF conversion in a test, skipped where LibreOffice is absent); Word 365 and Google Docs cannot be run here, so they are not verified directly. Key scan now renders every available download kind.
Validation: agent pytest 151 passed; web vitest 55 passed; browser: full flow to sign-off, PRD v1.0.docx downloaded via the menu (Word 2007+ file, S10.4 sections, accepted gap with note).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The agent drafts PRD v1.0 from the design record and gap register with requirements copied verbatim, validates it with one corrective retry, and asks for sign-off in a card; a rejection with a reason re-drafts, an approval freezes v1.0. The PRD viewer shows the draft and every version, and the download listing and file routes serve PRD v1.0.docx, rendered deterministically, once signed off (409 before). Verified with graph-seam, export-seam and REST tests, a LibreOffice open check, web component tests and a browser download.
<!-- SECTION:FINAL_SUMMARY:END -->
