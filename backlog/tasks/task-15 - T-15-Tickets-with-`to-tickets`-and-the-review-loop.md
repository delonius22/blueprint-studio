---
id: TASK-15
title: 'T-15: Tickets with `to-tickets` and the review loop'
status: Done
assignee: []
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:57'
labels: []
dependencies:
  - TASK-13
references:
  - TICKETS.md
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The `to-tickets` method breaks the current PRD into tracer-bullet tickets with blocking edges and acceptance criteria, with open gaps kept out of its input. The user approves the breakdown or asks for changes in plain words until it is right. A cyclic breakdown is never shown as valid.

Delivers stories: US-32, US-33, US-34, US-35

Mirrors T-15 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The `ticket_planner` prompt is built as S9.1 defines, using `app-assets/to-tickets.md` verbatim; a graph-seam test shows the planner's input contains no gap text.
- [x] #2 `Ticket` exists as S2.14 defines; validation and its one retry behave as S9.2 defines.
- [x] #3 The `dag_validator` rejects unknown blockers, duplicates and cycles, naming the cycle, and renumbers valid tickets topologically (S9.3).
- [x] #4 `review_tickets` approve and revise behave as S9.4 defines; approval sets `tickets_approved_at` and `stage` `complete`.
- [x] #5 The ticket view shows the breakdown with blocking edges (S11.2).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.tickets: planner prompt = app framing (no codebase, no tracker, no quiz; every story delivered) + to-tickets.md verbatim incl. attribution; input = current PRD (S8.6, prd.current_prd) with open_gaps removed and GAP- notes removed from further_notes. S9.2 validation with one corrective retry. dag_validator (no model) rejects duplicate IDs, unknown blockers and cycles (named as an ordered list, e.g. a → c → b → a) and routes back to the planner with the error through a graph-internal planning channel; capped at 3 attempts, then last_error. Valid tickets renumbered T-01... topologically (ties by original order), blocked_by rewritten; review_tickets gate emitted; stage ticket_gate. Revise re-plans with the current tickets and the instructions; approve -> completer sets tickets_approved_at and stage complete and posts the downloads message. A run that adds nothing never re-opens a waiting gate (gates.pending_gate). Web: TicketView (edges, stories, criteria, build waves), ReviewTicketsCard (revision needs text); main panel shows tickets in ticket stages.
Validation: agent pytest 165 passed; web vitest 60 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
to-tickets (vendored verbatim) breaks the current PRD, with every open gap removed, into tracer-bullet tickets; stories are checked for coverage with one retry, a DAG validator rejects unknown blockers, duplicates and cycles (naming the cycle) and renumbers valid tickets in build order, and the user approves or revises the breakdown in plain words until approval completes the session. Verified with graph-seam tests and web component tests.
<!-- SECTION:FINAL_SUMMARY:END -->
