---
id: TASK-11
title: 'T-11: Gap resolution — answer or accept'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:30'
labels: []
dependencies:
  - TASK-10
references:
  - TICKETS.md
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The user goes through the gap register in a card, answering gaps or accepting them as open risks, or accepting all at once. Answers go to the interviewer, which records them as ordinary design items and marks each gap resolved. When no gap is open, the session moves to PRD drafting.

Delivers stories: US-21, US-22

Mirrors T-11 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `decide_gaps` is a frontend tool with per-gap decisions and "accept all"; answers and acceptances require text where S11.4 says so.
- [x] #2 Accepted gaps get `status` `accepted` and the note; answered gaps are recorded through design tools and closed with `resolve_gap`, filling `resolved_by` (S6.5, S5.3).
- [x] #3 The review does not re-run; `stage` becomes `prd_draft` when no gap is open (S6.5).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. gap_merger emits decide_gaps(gaps) as a graph-made tool call and opens its card.
2. decide_gaps answer -> interviewer node: acceptances set status accepted + note; answered gaps go to the model (prompt section) with resolve_gap bound (S5.3); design_tools runs design tools and resolve_gap (status resolved, resolved_by).
3. Stage prd_draft when no gap is open; otherwise a new decide_gaps card for the remaining gaps; the review never re-runs.
4. Web: DecideGapsCard via useHumanInTheLoop: per-gap answer (text required) or accept (optional note), plus accept all.
5. Tests: graph seam for accept, answer+resolve, accept all, partial, no re-review; card component tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
decide_gaps is a graph-made gate: gap_merger (when gaps exist) adds an AIMessage with a decide_gaps tool call listing the open gaps and opens its card through the T-07 gate event. The answer (list of {gap_id, decision, text}) routes to the interviewer: acceptances set status accepted and note (optional); answered gaps go into an S5.2 "Gap answers to record" prompt section with resolve_gap bound (S5.3); design_tools runs design tools and resolve_gap (gap must be open, items must exist; sets resolved + resolved_by) and sets stage prd_draft when none is open. If the interviewer finishes with gaps still open, a new decide_gaps card lists them. Gate tool names are known server-side (gates.GATES). Model input closes unanswered tool calls with a placeholder result (a user may type instead of answering a card). Web: DecideGapsCard (answer needs text, accept note optional, accept all). Also fixed the T-08 scorecard chat message markdown (advice was rendered inside the quote).
Validation: agent pytest 144 passed; web vitest 49 passed; browser: full interview via canvas edits and five confirmations -> scorecard -> parallel review -> gap card -> accept with note -> register shows accepted, stage PRD draft.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The gap register comes to the user as a decide_gaps card: each gap is answered (text required) or accepted as an open risk with an optional note, or all are accepted at once; acceptances update the gap, answers are recorded by the interviewer as ordinary design items and closed with resolve_gap, gaps left open come back in a new card, and the session moves to PRD drafting when none is open, without re-running the review. Verified with graph-seam tests, card tests and a full browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
