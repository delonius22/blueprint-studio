---
id: TASK-13
title: 'T-13: PRD v1.1 with `to-spec`, and seam approval'
status: Done
assignee: []
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:50'
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
- [x] #1 The `spec_synthesizer` prompt and output behave as S8.1 defines, using `app-assets/to-spec.md` verbatim.
- [x] #2 A graph-seam test shows the signed-off sections of `prd_draft` are byte-identical to v1.0 after synthesis, and every open gap appears in further notes with its ID (S8.1).
- [x] #3 `UserStory` exists as S2.11 defines; validation and its one retry behave as S8.2 defines, including that every FR is covered by a story.
- [x] #4 `approve_seams` approve, edit and reject behave as S8.3; approval appends v1.1 and routes as S8.4 defines.
- [x] #5 `prd-v1.1.docx` renders as S10.4 defines and ends with the attribution line of S12.3.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.spec: spec_synthesizer prompt = app framing (synthesize without questions, PRD v1.1 instead of a tracker, seams separate, never change signed-off sections; propose changes instead) + to-spec.md verbatim incl. its attribution comment; input = signed-off v1.0, design record, transcript. Output (solution, user_stories, implementation_decisions, further_notes, proposed_changes) validated per S8.2 with one corrective retry; the draft copies v1.0's signed-off sections untouched (deep copy) and appends every open gap to further_notes as "GAP-n: risk Decision needed: ... Note: ..."; US- and CHG- IDs issued by the app. seam_proposer: to-spec step 2 only, SEAM- IDs, emits approve_seams; approval (seams possibly edited: known IDs kept, new ones issued) copies seams into testing_decisions, appends PrdVersion 1.1, stage change_review if proposed changes else ticket_breakdown; rejection re-proposes with the feedback. A page-load re-sync never proposes twice. prd-v1.1.docx adds the extension sections and ends with the to-spec attribution (S12.3). Web: ApproveSeamsCard (edit/add/remove, feedback required to reject); viewer shows extension sections.
Validation: agent pytest 157 passed; web vitest 57 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
After sign-off, to-spec (vendored verbatim) extends the PRD with a solution, traced user stories, implementation decisions and further notes (open gaps verbatim with IDs) without touching the signed-off sections; the result is validated with one retry; the agent proposes test seams, and the user's approval (with edits) freezes v1.1, downloadable as Word with the to-spec attribution. Verified with graph-seam tests, an export test and card tests.
<!-- SECTION:FINAL_SUMMARY:END -->
