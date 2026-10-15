---
id: TASK-14
title: 'T-14: Proposed changes and PRD v1.2'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 11:36'
labels: []
dependencies:
  - TASK-13
references:
  - TICKETS.md
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When synthesis proposed changes to signed-off content, the user reviews each one in a card, approving or rejecting it, or accepting all. Approved changes produce PRD v1.2, with a table of what changed; rejected ones are dropped. With no proposals, this stage is skipped.

Delivers stories: US-30, US-36

Mirrors T-14 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `ProposedChange` exists as S2.13 defines.
- [x] #2 `review_changes` and the `change_applier` behave as S8.5 defines; no v1.2 is created when every change is rejected.
- [x] #3 A graph-seam test shows v1.0 and v1.1 are unchanged after v1.2 is created, and later stages read v1.2 as the current PRD (S2.12, S8.6).
- [x] #4 `prd-v1.2.docx` renders with its "Changes from v1.1" table (S10.4).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Blocked on Q-11 (S8.5 does not define how an approved proposed change is applied to structured sections). Implementation in progress on branch T-14 with reading (a).

Q-11 answered (a). change_applier (no model) emits review_changes listing the pending changes (graph-made gate); the answer is a decision per change ID (rejections carry a reason in the card); approved changes are applied to a copy of the current PRD by blueprint.changes.apply_changes (reading (a): exact edits; FR/NFR adds issue new IDs, an FR goes into the feature named by target_id; features lose their FRs only by removal) and PRD v1.2 is appended only if at least one was approved; rejected ones are recorded as rejected and not applied; stage ticket_breakdown, and the ticket planner runs in the same run on the current PRD (prd.current_prd, S8.6). S8.2 rejects proposals the rules cannot apply (open gaps unchangeable, no standalone feature adds, FR adds need a target feature, list edits must quote an existing entry). A run that adds nothing never re-opens a waiting gate. PRD v1.2.docx adds the "Changes from v1.1" table. Web: ReviewChangesCard (per change, reason required to reject, accept all).
Validation: agent pytest 186 passed (incl. v1.0 and v1.1 unchanged after v1.2, the planner reading v1.2); web vitest tests for the card.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
When synthesis proposes changes to signed-off content, the user approves or rejects each one (or accepts all) in a card; approved changes produce PRD v1.2 as exact edits, rejected ones are dropped, no v1.2 is made when all are rejected, earlier versions never change, and later stages read v1.2 as the current PRD. PRD v1.2.docx lists the changes. Verified through graph-seam, export and card tests.
<!-- SECTION:FINAL_SUMMARY:END -->
