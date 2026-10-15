---
id: TASK-18
title: 'T-18: Completion view, zip and deterministic downloads'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 11:38'
labels: []
dependencies:
  - TASK-14
  - TASK-16
  - TASK-17
references:
  - TICKETS.md
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When the session completes, a completion view lists every document with a "Download all (.zip)" action. Every download is byte-identical across renders of the same state, and generating all of them is fast.

Delivers stories: US-43, US-44, US-45

Mirrors T-18 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The completion view renders from the S10.3 listing (S11.5), and the `completer` posts the downloads message (S9.4).
- [x] #2 `bundle.zip` contains every available kind except itself, with the file names of S10.2 (S10.8).
- [x] #3 Rendering every kind twice from the same state yields byte-identical files, Word documents and zip included (S10.9, FR-28).
- [x] #4 With a 50-ticket fixture, generating `bundle.zip` takes at most 10 s at p95 over 20 runs, and each download logs `export_ms` (NFR-2, S13.5).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.exports.bundle_zip + downloads._bundle: bundle.zip holds every available kind except itself under its S10.2 file name, in the fixed kind order, each entry stamped with tickets_approved_at and fixed attributes. Determinism (S10.9) is tested by rendering every kind twice and by rendering in two processes with different PYTHONHASHSEED and wall-clock seconds (identical SHA-256 per kind). Performance: 50-ticket fixture, bundle.zip p95 105 ms over 20 runs (limit 10 s). export_ms is logged for real download requests (409 and 200). Web: CompletionView (from the S10.3 listing: available documents by file name and "Download all (.zip)") leads the main panel at stage complete, with the approved tickets below; the completer's downloads message is covered by the T-15 tests.
Validation: agent pytest 191 passed; web vitest 63 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
At completion the workspace lists every available document and offers a deterministic bundle.zip with the S10.2 file names; every download kind renders byte-identically from the same state, including across processes, a 50-ticket bundle renders in about 0.1 s at p95, and each download logs export_ms. Verified with export-seam, REST and component tests.
<!-- SECTION:FINAL_SUMMARY:END -->
