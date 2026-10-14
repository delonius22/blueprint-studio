---
id: TASK-18
title: 'T-18: Completion view, zip and deterministic downloads'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
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
- [ ] #1 The completion view renders from the S10.3 listing (S11.5), and the `completer` posts the downloads message (S9.4).
- [ ] #2 `bundle.zip` contains every available kind except itself, with the file names of S10.2 (S10.8).
- [ ] #3 Rendering every kind twice from the same state yields byte-identical files, Word documents and zip included (S10.9, FR-28).
- [ ] #4 With a 50-ticket fixture, generating `bundle.zip` takes at most 10 s at p95 over 20 runs, and each download logs `export_ms` (NFR-2, S13.5).
<!-- AC:END -->
