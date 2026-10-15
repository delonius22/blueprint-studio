---
id: TASK-8
title: 'T-08: Steps 4–5 and the final scorecard'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:13'
labels: []
dependencies:
  - TASK-7
references:
  - TICKETS.md
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 4 captures SPOFs with mitigations and observability signals; Step 5 captures trade-offs and extensions. Step 4 cannot be confirmed while any SPOF lacks a mitigation. When Step 5 is confirmed, the user gets a scorecard across the five evaluation dimensions, and the session moves to design review.

Delivers stories: US-16

Mirrors T-08 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SPOF, signal, trade-off and extension types and tools exist (S2.7, S5.3).
- [x] #2 Confirming Step 4 with no SPOF, or an unmitigated SPOF, returns the blocker and opens no card (S5.6).
- [x] #3 After Step 5 approval the critic stores a scorecard with five dimension scores, quoted evidence and advice, and sets `stage` to `design_review` (S5.8, S2.8).
- [x] #4 The scorecard is shown in the workspace.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Blocked on Q-10 (PRD OQ-6: may scorecard evidence quote the interviewer's turns or only the user's?). Implementation complete on branch T-08 with the rule as scoring.QUOTES_FROM; 108 agent / 27 web tests green there.

Q-10 answered by the user: scorecard evidence quotes only the user's turns. Tools upsert_spof, upsert_signal, upsert_tradeoff, upsert_extension (SPOF component references validated). Step 4 blockers: at least one SPOF and every SPOF mitigated (S5.6, via the T-07 design_tools gate check). After Step 5 approval the critic stores the critique and a Scorecard (five DimensionScore values in canonical order, each with verbatim user quotes and advice; one corrective retry; still invalid -> only last_error) and sets stage design_review. Workspace shows the scorecard above the canvas; canvas Step 4-5 panels.
Validation: agent pytest 120 passed; web vitest 34 passed; ruff, mypy --strict, tsc, next build clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Step 4 records SPOFs with mitigations and observability signals and cannot be confirmed while any SPOF lacks a mitigation; Step 5 records trade-offs and extensions; approving Step 5 stores a five-dimension scorecard backed by verbatim quotes of the user and moves the session to design review, and the workspace shows it. Verified through graph-seam and component tests.
<!-- SECTION:FINAL_SUMMARY:END -->
