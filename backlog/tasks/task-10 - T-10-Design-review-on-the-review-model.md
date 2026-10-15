---
id: TASK-10
title: 'T-10: Design review on the review model'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:23'
labels: []
dependencies:
  - TASK-8
references:
  - TICKETS.md
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After Step 5, three reviewers on the separate review model check the design in parallel for security, efficiency and maintainability. A merge step produces the gap register, shown in its own panel with each gap's lens, severity, affected items, risk and decision needed. When the review model equals the interview model, a persistent warning says the cross-model check is not active.

Delivers stories: US-18, US-19, US-20, US-23

Mirrors T-10 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The `Gap` type exists as S2.9 defines.
- [x] #2 The three reviewer nodes run in parallel on the review-role model with the inputs of S6.1, the checklists of S6.2 and the rules and severity definitions of S6.3.
- [x] #3 The `gap_merger` drops findings that cite no existing item, combines duplicates keeping the higher severity, and issues `GAP` IDs (S6.4).
- [x] #4 A graph-seam test with a scripted review model shows a finding that proposes a new component produces no design item and no requirement (S6.3, G3).
- [x] #5 Zero gaps sends the session to `prd_draft`; otherwise to `gap_resolution` (S6.4).
- [x] #6 Tokens are counted under the `review` role (S13.3).
- [x] #7 The gap register panel and the same-model warning render as S11.2 and S6.6 define.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. blueprint.review: reviewer prompt from design-judge-reviewer.md with {lens}; input = design record (no transcript); structured findings; merge rules (drop uncited/unknown items, never add, combine duplicates keeping higher severity, GAP IDs).
2. Graph: critic (step 5) and START route fan out to review_security/efficiency/maintainability in parallel (private review channel keyed by lens: findings, tokens, error) -> gap_merger (review model, design-judge-merge.md) -> gaps, stage prd_draft or gap_resolution, tokens_used[review], last_error on failure.
3. Web: gap register panel in design_review/gap_resolution; persistent same-model warning (S6.6, S11.6).
4. Tests: graph seam with scripted review model (parallel, review tokens, proposals never become design items or requirements, zero gaps -> prd_draft), merge rule unit tests, panel tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.review: reviewer prompt = design-judge-reviewer.md with {lens} replaced; reviewer input = the design record as JSON (FR/NFR included), never the transcript; merger prompt = design-judge-merge.md. Graph: critic (step 5, stage design_review) and START (stage design_review, e.g. a retry) fan out to review_security/efficiency/maintainability in parallel; each writes findings, review tokens or an error to a graph-internal ReviewChannel keyed by lens (not a session field; absent from state snapshots); gap_merger sums review tokens into tokens_used["review"], sets last_error if any reviewer failed, pre-filters findings to existing IDs, merges on the review model, then holds the result to S6.4 in code (cited items only, each gap backed by an input finding of the same lens, duplicates combined keeping the higher severity, ordered by severity) and issues GAP IDs; zero gaps -> prd_draft (no merger call), else gap_resolution; posts a summary message. Web: main panel switches by stage (canvas in interview; gap register in design_review/gap_resolution), scorecard above; ReviewModelWarning persistent banner while review_model_distinct is false.
Validation: agent pytest 139 passed (incl. AG-UI run of the parallel review); web vitest 46 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
After Step 5 three reviewers on the review model check the design record in parallel through the vendored design-judge prompts; the merger's output is held to the S6.4 rules in code and becomes the gap register with GAP IDs, shown in its own panel; review tokens count under the review role, zero gaps goes to PRD drafting, and a persistent warning shows when the review model equals the interview model. Verified with graph-seam tests using a content-routed fake review model, an AG-UI endpoint test and component tests.
<!-- SECTION:FINAL_SUMMARY:END -->
